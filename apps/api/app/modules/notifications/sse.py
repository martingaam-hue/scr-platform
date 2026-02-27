"""SSE (Server-Sent Events) connection manager for real-time notifications."""

import asyncio
import json
import uuid

import structlog

logger = structlog.get_logger()


class SSEManager:
    """Manages SSE connections per user using asyncio.Queue."""

    def __init__(self) -> None:
        self._connections: dict[uuid.UUID, list[asyncio.Queue]] = {}

    async def connect(self, user_id: uuid.UUID) -> asyncio.Queue:
        """Register a new SSE connection for a user."""
        queue: asyncio.Queue = asyncio.Queue()
        if user_id not in self._connections:
            self._connections[user_id] = []
        self._connections[user_id].append(queue)
        logger.info("sse_connected", user_id=str(user_id), total=len(self._connections[user_id]))
        return queue

    def disconnect(self, user_id: uuid.UUID, queue: asyncio.Queue) -> None:
        """Remove an SSE connection for a user."""
        if user_id in self._connections:
            try:
                self._connections[user_id].remove(queue)
            except ValueError:
                pass
            if not self._connections[user_id]:
                del self._connections[user_id]
        logger.info("sse_disconnected", user_id=str(user_id))

    async def push(self, user_id: uuid.UUID, event_data: dict) -> None:
        """Push an event to all SSE connections for a user."""
        queues = self._connections.get(user_id, [])
        for queue in queues:
            await queue.put(event_data)


# Module-level singleton
sse_manager = SSEManager()
