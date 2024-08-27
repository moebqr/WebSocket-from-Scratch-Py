import unittest
import socket
from unittest.mock import Mock, patch
from websocket_client import WebSocketClient
import time
from threading import Event

class TestWebSocketClient(unittest.TestCase):
    def setUp(self):
        self.client = WebSocketClient('localhost', 8765)

    def test_init(self):
        self.assertEqual(self.client.host, 'localhost')
        self.assertEqual(self.client.port, 8765)
        self.assertFalse(self.client.use_ssl)

    def test_generate_accept_key(self):
        key = "dGhlIHNhbXBsZSBub25jZQ=="
        expected_accept = "s3pPLMBiTxaQ9kYGzzhZRbK+xOo="
        self.assertEqual(self.client.generate_accept_key(key), expected_accept)

    @patch('socket.socket')
    @patch('random.randint')
    def test_handshake(self, mock_randint, mock_socket):
        mock_randint.return_value = 0  # To make the Sec-WebSocket-Key predictable
        self.client.sock = Mock()
        self.client.sock.recv.return_value = (
            b"HTTP/1.1 101 Switching Protocols\r\n"
            b"Upgrade: websocket\r\n"
            b"Connection: Upgrade\r\n"
            b"Sec-WebSocket-Accept: s3pPLMBiTxaQ9kYGzzhZRbK+xOo=\r\n\r\n"
        )
        self.client.handshake()
        self.client.sock.send.assert_called_once()
        sent_data = self.client.sock.send.call_args[0][0].decode('utf-8')
        self.assertIn("Sec-WebSocket-Key: AAAAAAAAAAAAAAAAAAAAAA==", sent_data)

    def test_receive_message(self):
        self.client.sock = Mock()
        self.client.sock.recv.side_effect = [
            b'\x81\x05',  # Frame header (text frame, 5 bytes payload)
            b'Hello'      # Payload
        ]
        message = self.client.receive_message()
        self.assertEqual(message, "Hello")

    def test_send_message(self):
        self.client.sock = Mock()
        self.client.send_message("Hello")
        self.client.sock.send.assert_called_once()
        sent_data = self.client.sock.send.call_args[0][0]
        self.assertEqual(len(sent_data), 11)  # 2 bytes header, 4 bytes mask, 5 bytes payload
        self.assertEqual(sent_data[0], 0x81)  # Text frame
        self.assertEqual(sent_data[1], 0x85)  # Masked, 5 bytes payload

    def test_send_ping(self):
        self.client.sock = Mock()
        self.client.send_ping()
        self.client.sock.send.assert_called_once_with(b'\x89\x00')

    def test_handle_pong(self):
        initial_time = self.client.last_pong
        time.sleep(0.1)
        self.client.handle_pong()
        self.assertGreater(self.client.last_pong, initial_time)

    @patch('threading.Thread')
    def test_heartbeat(self, mock_thread):
        self.client.sock = Mock()
        
        def side_effect(*args, **kwargs):
            self.client.heartbeat()
        mock_thread.side_effect = side_effect

        self.client.connect()
        mock_thread.assert_called()

        # Simulate a successful heartbeat
        time.sleep(self.client.heartbeat_interval + 1)
        self.assertTrue(self.client.sock.send.called)

        # Simulate a failed heartbeat
        self.client.last_pong = 0
        time.sleep(self.client.heartbeat_interval + self.client.heartbeat_timeout + 1)
        self.client.sock.close.assert_called()

if __name__ == '__main__':
    unittest.main()