from __future__ import annotations

import json
import time
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable


@dataclass(frozen=True)
class Event:
    event_id: str
    run_id: str
    timestamp_ms: int
    type: str
    payload: dict[str, Any]


class EventBus:
    def __init__(self) -> None:
        self._handlers: list[Callable[[Event], None]] = []

    def subscribe(self, handler: Callable[[Event], None]) -> None:
        self._handlers.append(handler)

    def emit(self, run_id: str, type_: str, payload: dict[str, Any]) -> Event:
        event = Event(
            event_id=str(uuid.uuid4()),
            run_id=run_id,
            timestamp_ms=int(time.time() * 1000),
            type=type_,
            payload=payload,
        )
        for handler in list(self._handlers):
            handler(event)
        return event


class JsonlEventLogger:
    def __init__(self, path: str) -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def __call__(self, event: Event) -> None:
        line = json.dumps(asdict(event), ensure_ascii=False)
        with self._path.open("a", encoding="utf-8") as f:
            f.write(line + "\n")

