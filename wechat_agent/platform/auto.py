from __future__ import annotations

import sys

from wechat_agent.platform.noop import NoopPlatform


def build_platform(kind: str, *, run_dir: str | None = None, config=None):
    if kind == "noop":
        return NoopPlatform()
    if kind == "auto":
        if sys.platform.startswith("darwin"):
            kind = "macos"
        elif sys.platform.startswith("win"):
            kind = "windows"
        else:
            return NoopPlatform()
    if kind == "macos":
        from wechat_agent.platform.macos.platform import MacOSPlatform

        return MacOSPlatform(run_dir=run_dir, config=config)
    if kind == "windows":
        from wechat_agent.platform.windows.platform import WindowsPlatform

        return WindowsPlatform(run_dir=run_dir, config=config)
    return NoopPlatform()
