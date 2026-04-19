from __future__ import annotations

from wechat_agent.core.task import ActionSpec, TaskPlan


def plan_closed_loop(contact_name: str, recent_n: int, message: str, send: bool) -> TaskPlan:
    actions: list[ActionSpec] = [
        ActionSpec("search_contact", {"name": contact_name}),
        ActionSpec("open_chat", {"name": contact_name}),
        ActionSpec("read_recent", {"n": recent_n}),
    ]
    if send:
        actions.append(ActionSpec("send_message", {"text": message}))
        actions.append(ActionSpec("verify_sent", {"text": message}))
    return TaskPlan(goal="closed_loop", actions=actions)

