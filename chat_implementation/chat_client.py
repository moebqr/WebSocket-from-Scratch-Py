import logging
import threading
from websocket_client import WebSocketClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ChatClient(WebSocketClient):
    def __init__(self, host, port):
        super().__init__(host, port)
        self.username = None

    def connect(self):
        super().connect()
        self.username = input("Enter your username: ")
        self.send_message(self.username)
        threading.Thread(target=self.receive_messages, daemon=True).start()

    def receive_messages(self):
        while True:
            try:
                message = self.receive_message()
                if message:
                    print(message)
                else:
                    logger.info("Connection closed by server")
                    break
            except Exception as e:
                logger.error(f"Error receiving message: {e}", exc_info=True)
                break

    def send_chat_message(self, message):
        self.send_message(message)

if __name__ == "__main__":
    client = ChatClient('localhost', 8765)
    client.connect()

    print("Connected to chat server. Type your messages and press Enter to send.")
    print("Type 'quit' to exit.")

    try:
        while True:
            message = input()
            if message.lower() == 'quit':
                break
            client.send_chat_message(message)
    except KeyboardInterrupt:
        pass
    finally:
        client.close()
        logger.info("Chat client stopped")