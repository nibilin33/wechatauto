from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class WindowInfo:
    native_id: str
    title: str
    x: int
    y: int
    width: int
    height: int
    scale: float


class WindowPort(Protocol):
    def locate_wechat(self) -> WindowInfo: ...
    def activate(self, window: WindowInfo) -> None: ...


class ScreenPort(Protocol):
    def capture_window(self, window: WindowInfo, path: str) -> None: ...


class InputPort(Protocol):
    def click_norm(self, window: WindowInfo, x: float, y: float) -> None: ...
    def paste_text(self, text: str) -> None: ...
    def key_combo(self, *keys: str) -> None: ...


class Platform(Protocol):
    name: str
    def dispatch(self, action_name: str, params: dict, *, bus, run_id: str) -> None: ...
