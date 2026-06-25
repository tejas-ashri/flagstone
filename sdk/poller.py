import threading
from collections.abc import Callable


class Poller:
    def __init__(self, refresh: Callable[[], None], interval: int) -> None:
        self._refresh = refresh
        self._interval = interval
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._thread.join(timeout=5)

    def _run(self) -> None:
        while not self._stop.wait(self._interval):
            try:
                self._refresh()
            except Exception:
                pass
