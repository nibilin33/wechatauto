from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class BBox:
    """Normalized bbox in window space (0..1)."""

    x1: float
    y1: float
    x2: float
    y2: float


@dataclass(frozen=True)
class UiTextBlock:
    bbox: BBox
    text: str
    score: float


@dataclass(frozen=True)
class UiElement:
    bbox: BBox
    label: str
    score: float


@dataclass(frozen=True)
class ChatMessage:
    direction: str  # in|out|unknown
    text: str
    score: float


@dataclass(frozen=True)
class SemanticState:
    page: str  # home|chat|unknown
    chat_title: str | None
    messages: list[ChatMessage]
    elements: list[UiElement]
    texts: list[UiTextBlock]
    anchors: dict[str, BBox]
    confidence: float
    raw: dict[str, Any] | None = None


@dataclass(frozen=True)
class Observation:
    screenshot_path: str
    window_hint: dict[str, Any] | None


@dataclass(frozen=True)
class RunContext:
    run_id: str
    run_dir: str
