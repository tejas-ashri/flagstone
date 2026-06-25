import json
from pathlib import Path
from datetime import datetime, timezone


class DiskCache:
    def __init__(self, path: str = "~/.flagstone_cache.json") -> None:
        self._path = Path(path).expanduser()

    def write(self, config: dict) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._path.with_suffix(".tmp")
        tmp.write_text(json.dumps({
            "written_at": datetime.now(timezone.utc).isoformat(),
            "config": config,
        }))
        tmp.replace(self._path)

    def read(self) -> dict | None:
        if not self._path.exists():
            return None
        try:
            data = json.loads(self._path.read_text())
            return data["config"]
        except (json.JSONDecodeError, KeyError):
            return None
