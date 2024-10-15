import datetime
import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from typing import Dict

app = FastAPI()

@app.get('/health')
async def SendHealth():
    return {"Status":"Up and running"}

# Store active connections
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, Dict[str, WebSocket]] = {}

    async def connect(self, websocket: WebSocket, conversation_id: str, user_id: str):
        await websocket.accept()
        if conversation_id not in self.active_connections:
            self.active_connections[conversation_id] = {}
        self.active_connections[conversation_id][user_id] = websocket

    def disconnect(self, conversation_id: str, user_id: str):
        if conversation_id in self.active_connections:
            del self.active_connections[conversation_id][user_id]
            if not self.active_connections[conversation_id]:
                del self.active_connections[conversation_id]

    async def send_message(self, message: str, conversation_id: str, sender_id: str):
        if conversation_id in self.active_connections:
            for user_id, connection in self.active_connections[conversation_id].items():
                message_data =  {
                    "message": message,
                    "sender_id": sender_id
                }
                await connection.send_text(json.dumps(message_data))

manager = ConnectionManager()

@app.websocket("/ws/{conversation_id}/{user_id}")
async def websocket_endpoint(websocket: WebSocket, conversation_id: str, user_id: str):
    await manager.connect(websocket, conversation_id, user_id)
    try:
        while True:
            data = await websocket.receive_text()
            await manager.send_message(data, conversation_id, user_id)
    except WebSocketDisconnect:
        manager.disconnect(conversation_id, user_id)

class Message(BaseModel):
    content: str
    sender_id: str


@app.post("/ws/notify/{conversation_id}")
async def notify_clients(conversation_id: str, message: Message):
    print(f"Received message: {message.content} from {message.sender_id} in {conversation_id}")
    await manager.send_message(message.content, conversation_id, message.sender_id)
    return {"status": "Message sent"}