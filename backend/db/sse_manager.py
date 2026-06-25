import asyncio


class SSEConnectionManager:
    def __init__(self) -> None:
        self._subscribers: dict[str, set[asyncio.Queue]] = {}
        self._lock = asyncio.Lock()

    async def broadcast(self, flag_key: str, payload: str) -> None:
        pass  # implemented in Task 6
