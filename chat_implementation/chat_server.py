import logging
from websocket_server import WebSocketServer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ChatServer(WebSocketServer):
    def __init__(self, host, port):
        super().__init__(host, port)
        self.clients = {}  # {client_socket: username}

    def handle_client(self, client, address):
        logger.info(f"New connection from {address}")
        try:
            self.handshake(client)
            self.register_client(client)
            self.handle_messages(client)
        except Exception as e:
            logger.error(f"Error handling client {address}: {e}", exc_info=True)
        finally:
            self.unregister_client(client)
            client.close()
            logger.info(f"Connection closed for {address}")

    def register_client(self, client):
        self.send_message(client, "Welcome! Please enter your username:")
        username = self.receive_message(client).strip()
        self.clients[client] = username
        self.broadcast(f"{username} has joined the chat!")

    def unregister_client(self, client):
        if client in self.clients:
            username = self.clients[client]
            del self.clients[client]
            self.broadcast(f"{username} has left the chat.")

    def handle_messages(self, client):
        while True:
            try:
                message = self.receive_message(client)
                if message:
                    username = self.clients[client]
                    self.broadcast(f"{username}: {message}")
                else:
                    break
            except Exception as e:
                logger.error(f"Error handling message: {e}", exc_info=True)
                break

    def broadcast(self, message):
        logger.info(f"Broadcasting: {message}")
        for client in self.clients:
            try:
                self.send_message(client, message)
            except Exception as e:
                logger.error(f"Error sending message to client: {e}", exc_info=True)

if __name__ == "__main__":
    server = ChatServer('localhost', 8765)
    logger.info("Chat server starting...")
    server.start()