from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class AppConfig:
    platform: str  # auto|macos|windows|noop
    contact_name: str
    recent_n: int
    message: str
    send: bool
    run_dir: str | None = None
    yolo_model: str | None = None
    llm_fallback_cmd: str | None = None
    vlm_provider: str | None = None  # none|cmd|openai|qwen
    openai_model: str | None = None
    qwen_model: str | None = None
    qwen_base_url: str | None = None
    # SendGuard options
    whitelist: tuple[str, ...] = ()
    cooldown_seconds: float = 30.0
