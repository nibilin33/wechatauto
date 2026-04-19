from __future__ import annotations

import uuid
from pathlib import Path

from wechat_agent.app.config import AppConfig
from wechat_agent.core.events import EventBus, JsonlEventLogger
from wechat_agent.core.planner import plan_closed_loop
from wechat_agent.platform.auto import build_platform


def run_once(config: AppConfig) -> tuple[str, int]:
    run_id = str(uuid.uuid4())
    run_dir = config.run_dir or str(Path("runs") / run_id)
    Path(run_dir).mkdir(parents=True, exist_ok=True)

    bus = EventBus()
    bus.subscribe(JsonlEventLogger(str(Path(run_dir) / "events.jsonl")))

    platform = build_platform(config.platform, run_dir=run_dir, config=config)
    plan = plan_closed_loop(config.contact_name, config.recent_n, config.message, config.send)

    bus.emit(run_id, "TaskPlanned", {"goal": plan.goal, "actions": [a.__dict__ for a in plan.actions]})

    # v1：这里只搭骨架；具体动作实现后在此执行并校验。
    for action in plan.actions:
        bus.emit(run_id, "ActionStarted", {"name": action.name, "params": action.params})
        try:
            platform.dispatch(action.name, action.params, bus=bus, run_id=run_id)
            bus.emit(run_id, "ActionFinished", {"name": action.name})
        except Exception as e:  # noqa: BLE001
            bus.emit(run_id, "ActionFailed", {"name": action.name, "error": repr(e)})
            (Path(run_dir) / "error.txt").write_text(repr(e) + "\n", encoding="utf-8")
            return run_dir, 1

    return run_dir, 0
