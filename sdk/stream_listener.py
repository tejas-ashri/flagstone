import json
import threading
import time
from collections.abc import Callable

import httpx


class StreamListener:
    def __init__(self, url: str, sdk_key: str, on_update: Callable[[dict], None]) -> None:
        self._url = url
        self._sdk_key = sdk_key
        self._on_update = on_update
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._thread.join(timeout=5)

    def _run(self) -> None:
        backoff = 1
        while not self._stop.is_set():
            try:
                with httpx.Client(
                    headers={"x-sdk-key": self._sdk_key}, timeout=None
                ) as http:
                    with http.stream("GET", self._url) as resp:
                        backoff = 1
                        for line in resp.iter_lines():
                            if self._stop.is_set():
                                return
                            if line.startswith("data:"):
                                data = line[5:].strip()
                                if data:
                                    try:
                                        self._on_update(json.loads(data))
                                    except json.JSONDecodeError:
                                        pass
            except Exception:
                if not self._stop.is_set():
                    time.sleep(min(backoff, 60))
                    backoff = min(backoff * 2, 60)
