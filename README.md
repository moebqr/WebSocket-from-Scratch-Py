# Custom WebSocket Implementation in Python

This project implements a custom WebSocket server and client from scratch in Python. It provides a robust, low-latency, real-time communication system with features like message framing, handshakes, bi-directional communication, and heartbeat mechanism.

## Features

- Custom WebSocket server and client implementation
- SSL/TLS support for secure connections
- Heartbeat mechanism to maintain connections and detect disconnects early
- Multi-threading for handling concurrent connections
- Logging for better debugging and monitoring
- Unit tests for individual components
- Stress test script for performance analysis

## Project Structure

- `websocket_server.py`: The WebSocket server implementation
- `websocket_client.py`: The WebSocket client implementation
- `stress_test.py`: A script to test the server under load
- `test_websocket_server.py`: Unit tests for the server
- `test_websocket_client.py`: Unit tests for the client

## Requirements

- Python 3.7+
- No external libraries required for core functionality

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/moebqr/websocket-from-scratch-py.git
   cd websocket-from-scratch-py
   ```

2. (Optional) Create and activate a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
   ```

## Usage

### Running the WebSocket Server

1. Open a terminal and navigate to the project directory.
2. Run the server:
   ```
   python websocket_server.py
   ```
   The server will start and listen on localhost:8765 by default.

### Running the WebSocket Client

1. Open another terminal and navigate to the project directory.
2. Run the client:
   ```
   python websocket_client.py
   ```
   The client will connect to the server running on localhost:8765.

3. Enter messages when prompted. Type 'quit' to exit the client.

### Running the Stress Test

To test the server's performance under load:

```
python stress_test.py
```

This will simulate multiple clients connecting and sending messages to the server.

## Running Tests

To run the unit tests:

```
python -m unittest discover
```

## SSL/TLS Support

To enable SSL/TLS:

1. Generate SSL certificate and key:
   ```
   openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes
   ```

2. Update the server and client code (Still incomplete)
