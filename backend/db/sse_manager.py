import asyncio


class SSEConnectionManager:
    def __init__(self) -> None:
        self._subscribers: dict[str, set[asyncio.Queue]] = {}
        self._lock = asyncio.Lock()

    async def subscribe(self, flag_key: str = "*") -> asyncio.Queue:
        async with self._lock:
            q: asyncio.Queue = asyncio.Queue(maxsize=100)
            self._subscribers.setdefault(flag_key, set()).add(q)
        return q

    async def unsubscribe(self, flag_key: str, queue: asyncio.Queue) -> None:
        async with self._lock:
            self._subscribers.get(flag_key, set()).discard(queue)

    async def broadcast(self, flag_key: str, payload: str) -> None:
        async with self._lock:
            targets = set(self._subscribers.get(flag_key, set())) | set(
                self._subscribers.get("*", set())
            )
        for q in targets:
            try:
                q.put_nowait(payload)
            except asyncio.QueueFull:
                pass
