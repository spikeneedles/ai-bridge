from fastapi import WebSocket
from bridge.models import Message
import asyncio
import json
import logging

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self):
        # channel -> list of websockets
        self.active: dict[str, list[WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, channel: str) -> None:
        """Accept and register websocket for channel."""
        await websocket.accept()
        async with self._lock:
            if channel not in self.active:
                self.active[channel] = []
            self.active[channel].append(websocket)
        logger.info(f"WS connected on channel={channel}, total={self._count()}")

    async def disconnect(self, websocket: WebSocket, channel: str) -> None:
        async with self._lock:
            if channel in self.active:
                try:
                    self.active[channel].remove(websocket)
                except ValueError:
                    pass
                if not self.active[channel]:
                    del self.active[channel]
        logger.info(f"WS disconnected from channel={channel}, total={self._count()}")

    async def broadcast(self, message: Message) -> None:
        """Send message to subscribers of message.channel AND 'all' channel."""
        payload = json.dumps({"type": "message", "data": message.model_dump()})
        targets = set()
        async with self._lock:
            targets.update(self.active.get(message.channel, []))
            targets.update(self.active.get("all", []))
        await self._send_to_sockets(list(targets), payload)

    async def send_to(self, channel: str, message: Message) -> None:
        """Send to specific channel subscribers."""
        payload = json.dumps({"type": "message", "data": message.model_dump()})
        async with self._lock:
            sockets = list(self.active.get(channel, []))
        await self._send_to_sockets(sockets, payload)

    async def broadcast_task_update(self, task_data: dict) -> None:
        """Broadcast a task update event to 'tasks' channel and 'all' channel subscribers."""
        payload = json.dumps({"type": "task_update", "data": task_data})
        async with self._lock:
            targets = set()
            targets.update(self.active.get("tasks", []))
            targets.update(self.active.get("all", []))
        await self._send_to_sockets(list(targets), payload)

    async def send_raw(self, channel: str, payload: str) -> None:
        """Send raw JSON string to all subscribers of a channel."""
        async with self._lock:
            sockets = list(self.active.get(channel, []))
        await self._send_to_sockets(sockets, payload)

    async def _send_to_sockets(self, sockets: list[WebSocket], payload: str) -> None:
        dead = []
        for ws in sockets:
            try:
                await ws.send_text(payload)
            except Exception:
                dead.append(ws)
        # clean up dead sockets
        if dead:
            async with self._lock:
                for ws in dead:
                    for ch, lst in list(self.active.items()):
                        if ws in lst:
                            lst.remove(ws)
                            if not lst:
                                del self.active[ch]

    def _count(self) -> int:
        return sum(len(v) for v in self.active.values())

    def connected_count(self) -> int:
        return self._count()


manager = ConnectionManager()
