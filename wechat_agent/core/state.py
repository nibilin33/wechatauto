from __future__ import annotations

from dataclasses import dataclass

from wechat_agent.core.models import SemanticState


@dataclass
class AgentState:
    """可序列化的运行态快照（用于回放/调试）。"""

    semantic: SemanticState | None = None
    step: str | None = None

