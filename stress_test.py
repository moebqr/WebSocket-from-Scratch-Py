import asyncio
import websockets
import time

async def connect_and_send(uri, messages_per_client):
    async with websockets.connect(uri) as websocket:
        for i in range(messages_per_client):
            await websocket.send(f"Message {i}")
            response = await websocket.recv()
            print(f"Received: {response}")

async def stress_test(num_clients, messages_per_client):
    uri = "ws://localhost:8765"
    tasks = [connect_and_send(uri, messages_per_client) for _ in range(num_clients)]
    start_time = time.time()
    await asyncio.gather(*tasks)
    end_time = time.time()
    total_messages = num_clients * messages_per_client
    duration = end_time - start_time
    print(f"Sent {total_messages} messages in {duration:.2f} seconds")
    print(f"Average throughput: {total_messages / duration:.2f} messages/second")

if __name__ == "__main__":
    asyncio.run(stress_test(100, 10))  # 100 clients, 10 messages each