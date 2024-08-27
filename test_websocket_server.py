import unittest
import socket
import threading
from unittest.mock import Mock, patch
from websocket_server import WebSocketServer
import time
from threading import Event

class TestWebSocketServer(unittest.TestCase):
    def setUp(self):
        self.server = WebSocketServer('localhost', 8765)

    def test_init(self):
        self.assertEqual(self.server.host, 'localhost')
        self.assertEqual(self.server.port, 8765)
        self.assertFalse(self.server.use_ssl)

    def test_generate_accept_key(self):
        key = "dGhlIHNhbXBsZSBub25jZQ=="
        expected_accept = "s3pPLMBiTxaQ9kYGzzhZRbK+xOo="
        self.assertEqual(self.server.generate_accept_key(key), expected_accept)

    @patch('socket.socket')
    def test_handshake(self, mock_socket):
        mock_client = Mock()
        mock_client.recv.return_value = (
            b"GET / HTTP/1.1\r\n"
            b"Host: localhost:8765\r\n"
            b"Upgrade: websocket\r\n"
            b"Connection: Upgrade\r\n"
            b"Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==\r\n"
            b"Sec-WebSocket-Version: 13\r\n\r\n"
        )
        self.server.handshake(mock_client)
        mock_client.send.assert_called_once()
        sent_data = mock_client.send.call_args[0][0].decode('utf-8')
        self.assertIn("HTTP/1.1 101 Switching Protocols", sent_data)
        self.assertIn("Sec-WebSocket-Accept: s3pPLMBiTxaQ9kYGzzhZRbK+xOo=", sent_data)

    def test_receive_message(self):
        mock_client = Mock()
        mock_client.recv.side_effect = [
            b'\x81\x05',  # Frame header (text frame, 5 bytes payload)
            b'Hello'      # Payload
        ]
        message = self.server.receive_message(mock_client)
        self.assertEqual(message, "Hello")

    def test_send_message(self):
        mock_client = Mock()
        self.server.send_message(mock_client, "Hello")
        mock_client.send.assert_called_once()
        sent_data = mock_client.send.call_args[0][0]
        self.assertEqual(sent_data, b'\x81\x05Hello')

    def test_send_ping(self):
        mock_client = Mock()
        self.server.clients[mock_client] = {"address": "test", "last_pong": time.time()}
        self.server.send_ping(mock_client)
        mock_client.send.assert_called_once_with(b'\x89\x00')

    def test_handle_pong(self):
        mock_client = Mock()
        self.server.clients[mock_client] = {"address": "test", "last_pong": 0}
        self.server.handle_pong(mock_client)
        self.assertAlmostEqual(self.server.clients[mock_client]["last_pong"], time.time(), delta=0.1)

    @patch('threading.Thread')
    def test_heartbeat(self, mock_thread):
        mock_client = Mock()
        self.server.clients[mock_client] = {"address": "test", "last_pong": time.time()}
        
        def side_effect(*args, **kwargs):
            self.server.heartbeat(mock_client)
        mock_thread.side_effect = side_effect

        self.server.handle_client(mock_client, "test")
        mock_thread.assert_called()

        # Simulate a successful heartbeat
        time.sleep(self.server.heartbeat_interval + 1)
        self.assertIn(mock_client, self.server.clients)

        # Simulate a failed heartbeat
        self.server.clients[mock_client]["last_pong"] = 0
        time.sleep(self.server.heartbeat_interval + self.server.heartbeat_timeout + 1)
        self.assertNotIn(mock_client, self.server.clients)

if __name__ == '__main__':
    unittest.main()