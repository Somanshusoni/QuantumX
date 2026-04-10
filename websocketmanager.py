from typing import Dict, List
from fastapi import WebSocket

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, room_name: str):
        await websocket.accept()
        if room_name not in self.active_connections:
            self.active_connections[room_name] = []
        
        self.active_connections[room_name].append(websocket)
        print(f"🔌 New public connection to {room_name}. Viewers: {len(self.active_connections[room_name])}")

    def disconnect(self, websocket: WebSocket, room_name: str):
        if room_name in self.active_connections:
            self.active_connections[room_name].remove(websocket)
            print(f"❌ Disconnected from {room_name}. Viewers: {len(self.active_connections[room_name])}")
            
            if len(self.active_connections[room_name]) == 0:
                del self.active_connections[room_name]

# Single instance shared across the whole app
manager = ConnectionManager()