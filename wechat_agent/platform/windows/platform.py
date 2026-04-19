from __future__ import annotations

from wechat_agent.core.errors import PlatformNotImplemented


class WindowsPlatform:
    name = "windows"

    def __init__(self, run_dir: str | None = None, config=None) -> None:
        self._run_dir = run_dir
        self._config = config

    def dispatch(self, action_name: str, params: dict, *, bus, run_id: str) -> None:
        bus.emit(run_id, "PlatformDispatch", {"platform": self.name, "action": action_name, "params": params})
        raise PlatformNotImplemented(f"Windows 动作未实现：{action_name}")
