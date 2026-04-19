from __future__ import annotations


class NoopPlatform:
    name = "noop"

    def dispatch(self, action_name: str, params: dict, *, bus, run_id: str) -> None:
        bus.emit(run_id, "NoopDispatch", {"action": action_name, "params": params})

