import threading

import httpx

from sdk.evaluator import evaluate
from sdk.poller import Poller


class FlagClient:
    def __init__(
        self,
        sdk_key: str,
        base_url: str = "http://localhost:8000",
        poll_interval: int = 30,
    ) -> None:
        self._sdk_key = sdk_key
        self._base_url = base_url.rstrip("/")
        self._flags: dict[str, dict] = {}
        self._lock = threading.Lock()
        self._http = httpx.Client(headers={"x-sdk-key": sdk_key}, timeout=10)
        try:
            self._refresh()
        except Exception:
            pass
        self._poller = Poller(self._refresh, poll_interval)
        self._poller.start()

    def is_enabled(self, flag_key: str, user: dict) -> bool:
        with self._lock:
            flag = self._flags.get(flag_key)
        if flag is None:
            return False
        return bool(flag["variations"][evaluate(flag, user)])

    def get_variation(self, flag_key: str, user: dict) -> int:
        with self._lock:
            flag = self._flags.get(flag_key)
        if flag is None:
            return 0
        return evaluate(flag, user)

    def _refresh(self) -> None:
        resp = self._http.get(f"{self._base_url}/sdk/config")
        resp.raise_for_status()
        config = resp.json()
        with self._lock:
            self._flags = config.get("flags", {})

    def close(self) -> None:
        self._poller.stop()
        self._http.close()
