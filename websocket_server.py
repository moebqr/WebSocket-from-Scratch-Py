import socket
import threading
import hashlib
import base64
import struct
import ssl
import logging
import time

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='websocket_server.log',
    filemode='a'
)
logger = logging.getLogger(__name__)

# Add console logging
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

class WebSocketServer:
    def __init__(self, host, port, use_ssl=False, certfile=None, keyfile=None):
        # Initialize server properties
        self.host = host
        self.port = port
        self.use_ssl = use_ssl
        self.certfile = certfile
        self.keyfile = keyfile
        
        # Create a TCP socket
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((self.host, self.port))

        # Wrap socket with SSL if enabled
        if self.use_ssl:
            self.sock = ssl.wrap_socket(
                self.sock,
                server_side=True,
                certfile=self.certfile,
                keyfile=self.keyfile,
                ssl_version=ssl.PROTOCOL_TLS
            )

        logger.info(f"WebSocket server initialized on {host}:{port} (SSL: {use_ssl})")

        # Store client connections and set heartbeat parameters
        self.clients = {}
        self.heartbeat_interval = 30  # Send ping every 30 seconds
        self.heartbeat_timeout = 10  # Wait 10 seconds for pong response

    def start(self):
        # Start listening for connections
        self.sock.listen(5)
        logger.info(f"WebSocket server started on {self.host}:{self.port}")
        while True:
            client, address = self.sock.accept()
            logger.debug(f"New connection attempt from {address}")
            # Start a new thread to handle each client
            threading.Thread(target=self.handle_client, args=(client, address)).start()

    def handle_client(self, client, address):
        logger.info(f"New connection established from {address}")
        try:
            self.handshake(client)
            logger.debug(f"Handshake successful for {address}")
            self.clients[client] = {"address": address, "last_pong": time.time()}
            # Start heartbeat thread for this client
            threading.Thread(target=self.heartbeat, args=(client,)).start()
            self.handle_messages(client)
        except ConnectionResetError:
            logger.warning(f"Connection reset by {address}")
        except TimeoutError:
            logger.warning(f"Connection timeout with {address}")
        except Exception as e:
            logger.error(f"Error handling client {address}: {e}", exc_info=True)
        finally:
            self.remove_client(client)
            client.close()
            logger.info(f"Connection closed for {address}")

    def remove_client(self, client):
        # Remove client from the clients dictionary
        if client in self.clients:
            del self.clients[client]

    def heartbeat(self, client):
        while client in self.clients:
            time.sleep(self.heartbeat_interval)
            try:
                self.send_ping(client)
                start_time = time.time()
                while time.time() - start_time < self.heartbeat_timeout:
                    if time.time() - self.clients[client]["last_pong"] < self.heartbeat_timeout:
                        break
                    time.sleep(0.5)
                else:
                    # Close connection if no pong received within timeout
                    logger.warning(f"Heartbeat timeout for {self.clients[client]['address']}")
                    client.close()
                    break
            except Exception as e:
                logger.error(f"Error in heartbeat for {self.clients[client]['address']}: {e}")
                break

    def send_ping(self, client):
        # Send a ping frame to the client
        logger.debug(f"Sending ping to {self.clients[client]['address']}")
        frame = struct.pack('!BB', 0x89, 0)
        client.send(frame)

    def handle_pong(self, client):
        # Update last_pong time when a pong is received
        self.clients[client]["last_pong"] = time.time()
        logger.debug(f"Received pong from {self.clients[client]['address']}")

    def handle_messages(self, client):
        while True:
            try:
                message = self.receive_message(client)
                if message:
                    logger.debug(f"Received message: {message}")
                    self.send_message(client, f"Echo: {message}")
                    logger.debug(f"Sent echo response: Echo: {message}")
                else:
                    logger.debug("Received empty message, closing connection")
                    break
            except Exception as e:
                logger.error(f"Error handling message: {e}", exc_info=True)
                break

    def receive_message(self, client):
        try:
            client.settimeout(self.heartbeat_interval + self.heartbeat_timeout)
            header = client.recv(2)
            if not header:
                return None
            
            # Parse the header
            opcode = header[0] & 0x0F
            if opcode == 0x9:  # Ping
                self.send_pong(client)
                return None
            elif opcode == 0xA:  # Pong
                self.handle_pong(client)
                return None
            
            mask = header[1] & 0x80
            payload_length = header[1] & 0x7F

            # Handle different payload lengths
            if payload_length == 126:
                payload_length = struct.unpack('>H', client.recv(2))[0]
            elif payload_length == 127:
                payload_length = struct.unpack('>Q', client.recv(8))[0]

            # Handle masked and unmasked messages
            if mask:
                masking_key = client.recv(4)
                masked_data = client.recv(payload_length)
                data = bytes(b ^ masking_key[i % 4] for i, b in enumerate(masked_data))
            else:
                data = client.recv(payload_length)

            logger.debug(f"Received message of length {payload_length}")
            return data.decode('utf-8')
        except socket.timeout:
            logger.warning("Connection timed out while receiving message")
            raise TimeoutError("Connection timed out while receiving message")
        finally:
            client.settimeout(None)  # Remove the timeout

    def send_message(self, client, message):
        # Send a message to the client
        logger.debug(f"Sending message: {message}")
        encoded_message = message.encode('utf-8')
        header = struct.pack('!B', 0x81)  # Text frame
        length = len(encoded_message)

        # Add appropriate length bytes to the header
        if length <= 125:
            header += struct.pack('!B', length)
        elif length <= 65535:
            header += struct.pack('!BH', 126, length)
        else:
            header += struct.pack('!BQ', 127, length)

        client.send(header + encoded_message)
        logger.debug(f"Message sent successfully, length: {length}")

    def send_pong(self, client):
        # Send a pong frame to the client
        logger.debug(f"Sending pong to {self.clients[client]['address']}")
        frame = struct.pack('!BB', 0x8A, 0)
        client.send(frame)

    def handshake(self, client):
        # Perform the WebSocket handshake
        logger.debug("Starting handshake process")
        data = client.recv(1024).decode('utf-8')
        headers = {}
        for line in data.split('\r\n')[1:]:
            if ':' in line:
                key, value = line.split(':', 1)
                headers[key.strip()] = value.strip()

        if 'Sec-WebSocket-Key' not in headers:
            raise ValueError("Sec-WebSocket-Key not found in headers")

        key = headers['Sec-WebSocket-Key']
        response_key = self.generate_accept_key(key)
        response = (
            "HTTP/1.1 101 Switching Protocols\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Accept: {response_key}\r\n\r\n"
        )
        client.send(response.encode('utf-8'))
        logger.debug("Handshake completed successfully")

    def generate_accept_key(self, key):
        # Generate the Sec-WebSocket-Accept key
        GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
        sha1 = hashlib.sha1((key + GUID).encode('utf-8')).digest()
        return base64.b64encode(sha1).decode('utf-8')

if __name__ == "__main__":
    logger.info("Starting WebSocket server")
    server = WebSocketServer('localhost', 8765, use_ssl=True, certfile='path/to/cert.pem', keyfile='path/to/key.pem')
    server.start()