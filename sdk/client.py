import threading

import httpx

from sdk.evaluator import evaluate
from sdk.poller import Poller
from sdk.stream_listener import StreamListener


class FlagClient:
    def __init__(
        self,
        sdk_key: str,
        base_url: str = "http://localhost:8000",
        poll_interval: int = 30,
        use_sse: bool = False,
        flush_interval: int = 10,
    ) -> None:
        self._sdk_key = sdk_key
        self._base_url = base_url.rstrip("/")
        self._flags: dict[str, dict] = {}
        self._lock = threading.Lock()
        self._http = httpx.Client(headers={"x-sdk-key": sdk_key}, timeout=10)
        self._event_buffer: list[dict] = []
        self._flush_lock = threading.Lock()
        self._flush_interval = flush_interval
        try:
            self._refresh()
        except Exception:
            pass
        if use_sse:
            self._listener = StreamListener(
                url=f"{self._base_url}/sdk/stream",
                sdk_key=sdk_key,
                on_update=self._on_sse_update,
            )
            self._listener.start()
        else:
            self._poller = Poller(self._refresh, poll_interval)
            self._poller.start()
        self._schedule_flush()

    def is_enabled(self, flag_key: str, user: dict) -> bool:
        variation_index = self.get_variation(flag_key, user)
        self._buffer_event("exposure", flag_key, variation_index, user)
        with self._lock:
            flag = self._flags.get(flag_key)
        if flag is None:
            return False
        return bool(flag["variations"][variation_index])

    def get_variation(self, flag_key: str, user: dict) -> int:
        with self._lock:
            flag = self._flags.get(flag_key)
        if flag is None:
            return 0
        return evaluate(flag, user)

    def track_conversion(self, flag_key: str, user: dict) -> None:
        with self._lock:
            flag = self._flags.get(flag_key)
        variation_index = evaluate(flag, user) if flag else 0
        self._buffer_event("conversion", flag_key, variation_index, user)

    def _buffer_event(self, event_type: str, flag_key: str, variation_index: int, user: dict) -> None:
        with self._flush_lock:
            self._event_buffer.append({
                "flag_key": flag_key,
                "event_type": event_type,
                "variation_index": variation_index,
                "user_id": user.get("id", ""),
                "attributes": {k: v for k, v in user.items() if k != "id"},
            })
            if len(self._event_buffer) >= 100:
                self._flush_now()

    def _flush_now(self) -> None:
        events, self._event_buffer = self._event_buffer, []
        if events:
            try:
                self._http.post(
                    f"{self._base_url}/sdk/events",
                    json={"events": events},
                    timeout=5,
                )
            except Exception:
                pass

    def _schedule_flush(self) -> None:
        if hasattr(self, "_flush_timer"):
            self._flush_timer.cancel()
        t = threading.Timer(self._flush_interval, self._timed_flush)
        t.daemon = True
        t.start()
        self._flush_timer = t

    def _timed_flush(self) -> None:
        with self._flush_lock:
            self._flush_now()
        self._schedule_flush()

    def _refresh(self) -> None:
        resp = self._http.get(f"{self._base_url}/sdk/config")
        resp.raise_for_status()
        config = resp.json()
        with self._lock:
            self._flags = config.get("flags", {})

    def _on_sse_update(self, event: dict) -> None:
        key = event.get("key")
        if event.get("event") == "deleted":
            if key:
                with self._lock:
                    self._flags.pop(key, None)
        elif key and "flag" in event:
            with self._lock:
                self._flags[key] = event["flag"]
        else:
            try:
                self._refresh()
            except Exception:
                pass

    def close(self) -> None:
        if hasattr(self, "_flush_timer"):
            self._flush_timer.cancel()
        if hasattr(self, "_poller"):
            self._poller.stop()
        if hasattr(self, "_listener"):
            self._listener.stop()
        self._http.close()
