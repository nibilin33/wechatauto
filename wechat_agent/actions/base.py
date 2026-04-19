from __future__ import annotations

from typing import Protocol, runtime_checkable

from wechat_agent.core.models import BBox, UiElement, UiTextBlock
from wechat_agent.perception.layout import Layout
from wechat_agent.perception.semantic_parser import SemanticState


@runtime_checkable
class Driver(Protocol):
    """Minimal interface expected by all action functions."""

    elements: list[UiElement]
    layout: Layout | None
    semantic: SemanticState | None

    def click_norm(self, x: float, y: float) -> None: ...
    def paste_text(self, text: str) -> None: ...
    def key_combo(self, combo: str) -> None: ...
    def press_key(self, key: str) -> None: ...
    def sleep(self, seconds: float) -> None: ...
