from __future__ import annotations

"""
SendGuard — 发送守门人

在任何实际发送前检查：
- 白名单：只向允许的联系人/群发消息
- 频率限制：同一联系人的冷却时间
- 静默时段：指定时间段不发
- 关键词黑名单：消息中包含危险词则拒绝
- dry_run：记录但不实际发送
"""

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone


_DANGEROUS_KEYWORDS = [
    "转账", "付款", "验证码", "密码", "银行卡", "身份证", "扫码",
    "红包", "借钱", "借款", "贷款",
]


@dataclass
class SendGuardConfig:
    dry_run: bool = True
    """默认 dry-run：只打印不发送。生产环境需显式关闭。"""

    whitelist: list[str] = field(default_factory=list)
    """允许发送的联系人/群名列表。空列表 = 不限制（仍受其他规则约束）。"""

    cooldown_seconds: float = 60.0
    """同一联系人两次发送之间的最短间隔（秒）。"""

    silent_hours: tuple[int, int] | None = None
    """静默时段 (start_hour, end_hour)，例如 (22, 8) 表示 22:00~次日08:00 不发。"""

    keyword_blacklist: list[str] = field(default_factory=lambda: list(_DANGEROUS_KEYWORDS))


class SendBlocked(Exception):
    """Raised when SendGuard blocks a message."""


class SendGuard:
    def __init__(self, config: SendGuardConfig | None = None) -> None:
        self._cfg = config or SendGuardConfig()
        self._last_sent: dict[str, float] = {}  # contact -> timestamp

    def check(self, contact: str, text: str) -> None:
        """
        Raise SendBlocked if the message should not be sent.
        Call this *before* invoking the send action.
        """
        cfg = self._cfg

        # Whitelist
        if cfg.whitelist and contact not in cfg.whitelist:
            raise SendBlocked(f"联系人 {contact!r} 不在白名单中")

        # Keyword blacklist
        for kw in cfg.keyword_blacklist:
            if kw in text:
                raise SendBlocked(f"消息包含黑名单关键词: {kw!r}")

        # Silent hours
        if cfg.silent_hours is not None:
            start_h, end_h = cfg.silent_hours
            now_h = datetime.now(timezone.utc).hour
            in_silent = (
                now_h >= start_h or now_h < end_h
                if start_h > end_h  # crosses midnight
                else start_h <= now_h < end_h
            )
            if in_silent:
                raise SendBlocked(f"当前处于静默时段 ({start_h}:00-{end_h}:00)")

        # Cooldown
        last = self._last_sent.get(contact)
        if last is not None:
            elapsed = time.time() - last
            if elapsed < cfg.cooldown_seconds:
                remaining = cfg.cooldown_seconds - elapsed
                raise SendBlocked(
                    f"联系人 {contact!r} 冷却中，还需等待 {remaining:.1f}s"
                )

        # Dry-run is checked by the caller, not raised here.
        # This allows callers to emit a DryRun event instead of sending.

    def record_sent(self, contact: str) -> None:
        """Call after a message is successfully sent."""
        self._last_sent[contact] = time.time()

    @property
    def dry_run(self) -> bool:
        return self._cfg.dry_run
