from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ActionSpec:
    name: str
    params: dict


@dataclass(frozen=True)
class TaskPlan:
    goal: str
    actions: list[ActionSpec]

