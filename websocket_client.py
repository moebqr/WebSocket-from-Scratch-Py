import socket
import threading
import random
import struct
import base64
import hashlib
import ssl
import logging
import time

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='websocket_client.log',
    filemode='a'
)
logger = logging.getLogger(__name__)

# Add console logging
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

class WebSocketClient:
    def __init__(self, host, port, use_ssl=False):
        # Initialize client properties
        self.host = host
        self.port = port
        self.use_ssl = use_ssl
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # Wrap socket with SSL if enabled
        if self.use_ssl:
            context = ssl.create_default_context()
            self.sock = context.wrap_socket(self.sock, server_hostname=self.host)

        logger.info(f"WebSocket client initialized for {host}:{port} (SSL: {use_ssl})")
        self.last_pong = time.time()
        self.heartbeat_interval = 30
        self.heartbeat_timeout = 10

    def connect(self):
        try:
            # Connect to the server
            self.sock.connect((self.host, self.port))
            logger.debug(f"Socket connected to {self.host}:{self.port}")
            self.handshake()
            logger.info("Connected to WebSocket server")
            # Start heartbeat and message receiving threads
            threading.Thread(target=self.heartbeat).start()
            threading.Thread(target=self.receive_messages).start()
        except ConnectionRefusedError:
            logger.error("Connection refused. Is the server running?")
            raise
        except Exception as e:
            logger.error(f"Error connecting to server: {e}", exc_info=True)
            raise

    def handshake(self):
        # Perform the WebSocket handshake
        logger.debug("Starting handshake process")
        key = base64.b64encode(bytes([random.randint(0, 255) for _ in range(16)])).decode('utf-8')
        request = (
            f"GET / HTTP/1.1\r\n"
            f"Host: {self.host}:{self.port}\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\n"
            "Sec-WebSocket-Version: 13\r\n\r\n"
        )
        self.sock.send(request.encode('utf-8'))
        response = self.sock.recv(1024).decode('utf-8')
        
        if "101 Switching Protocols" not in response:
            raise Exception("Handshake failed")

        server_key = None
        for line in response.split('\r\n'):
            if line.startswith('Sec-WebSocket-Accept:'):
                server_key = line.split(': ')[1].strip()
                break

        if not server_key:
            raise Exception("Server did not send Sec-WebSocket-Accept")

        expected_key = self.generate_accept_key(key)
        if server_key != expected_key:
            raise Exception("Server's Sec-WebSocket-Accept does not match")
        logger.debug("Handshake completed successfully")

    def generate_accept_key(self, key):
        # Generate the expected Sec-WebSocket-Accept key
        GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
        sha1 = hashlib.sha1((key + GUID).encode('utf-8')).digest()
        return base64.b64encode(sha1).decode('utf-8')

    def receive_messages(self):
        # Continuously receive messages from the server
        logger.debug("Starting message receiving loop")
        while True:
            try:
                message = self.receive_message()
                if message:
                    logger.info(f"Received: {message}")
                else:
                    logger.debug("Received empty message, closing connection")
                    break
            except Exception as e:
                logger.error(f"Error receiving message: {e}", exc_info=True)
                break
        logger.debug("Message receiving loop ended")

    def receive_message(self):
        try:
            self.sock.settimeout(self.heartbeat_interval + self.heartbeat_timeout)
            header = self.sock.recv(2)
            if not header:
                return None
            
            # Parse the header
            opcode = header[0] & 0x0F
            if opcode == 0x9:  # Ping
                self.send_pong()
                return None
            elif opcode == 0xA:  # Pong
                self.handle_pong()
                return None
            
            mask = header[1] & 0x80
            payload_length = header[1] & 0x7F

            # Handle different payload lengths
            if payload_length == 126:
                payload_length = struct.unpack('>H', self.sock.recv(2))[0]
            elif payload_length == 127:
                payload_length = struct.unpack('>Q', self.sock.recv(8))[0]

            # Handle masked and unmasked messages
            if mask:
                masking_key = self.sock.recv(4)
                masked_data = self.sock.recv(payload_length)
                data = bytes(b ^ masking_key[i % 4] for i, b in enumerate(masked_data))
            else:
                data = self.sock.recv(payload_length)

            logger.debug(f"Received message of length {payload_length}")
            return data.decode('utf-8')
        except socket.timeout:
            logger.warning("Connection timed out while receiving message")
            raise TimeoutError("Connection timed out while receiving message")
        finally:
            self.sock.settimeout(None)  # Remove the timeout

    def send_message(self, message):
        # Send a message to the server
        logger.debug(f"Sending message: {message}")
        encoded_message = message.encode('utf-8')
        header = struct.pack('!B', 0x81)  # Text frame
        length = len(encoded_message)

        # Add appropriate length bytes to the header
        if length <= 125:
            header += struct.pack('!B', length | 0x80)
        elif length <= 65535:
            header += struct.pack('!BH', 126 | 0x80, length)
        else:
            header += struct.pack('!BQ', 127 | 0x80, length)

        masking_key = bytes([random.randint(0, 255) for _ in range(4)])
        header += masking_key

        masked_message = bytes(b ^ masking_key[i % 4] for i, b in enumerate(encoded_message))
        self.sock.send(header + masked_message)
        logger.debug(f"Message sent successfully, length: {length}")

    def close(self):
        logger.info("Closing WebSocket connection")
        self.sock.close()

    def heartbeat(self):
        while True:
            time.sleep(self.heartbeat_interval)
            try:
                self.send_ping()
                start_time = time.time()
                while time.time() - start_time < self.heartbeat_timeout:
                    if time.time() - self.last_pong < self.heartbeat_timeout:
                        break
                    time.sleep(0.5)
                else:
                    logger.warning("Heartbeat timeout")
                    self.close()
                    break
            except Exception as e:
                logger.error(f"Error in heartbeat: {e}")
                break

    def send_ping(self):
        logger.debug("Sending ping")
        frame = struct.pack('!BB', 0x89, 0)
        self.sock.send(frame)

    def handle_pong(self):
        self.last_pong = time.time()
        logger.debug("Received pong")

    def send_pong(self):
        logger.debug("Sending pong")
        frame = struct.pack('!BB', 0x8A, 0)
        self.sock.send(frame)

if __name__ == "__main__":
    logger.info("Starting WebSocket client")
    client = WebSocketClient('localhost', 8765, use_ssl=True)
    client.connect()
    
    try:
        while True:
            message = input("Enter message (or 'quit' to exit): ")
            if message.lower() == 'quit':
                logger.info("User requested to quit")
                break
            client.send_message(message)
    finally:
        client.close()
        logger.info("WebSocket client stopped")