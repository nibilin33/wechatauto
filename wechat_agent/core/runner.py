from __future__ import annotations

import uuid
from pathlib import Path

from wechat_agent.app.config import AppConfig
from wechat_agent.core.errors import ActionFailed, VerificationFailed
from wechat_agent.core.events import EventBus, JsonlEventLogger
from wechat_agent.core.planner import plan_closed_loop
from wechat_agent.core.send_guard import SendGuard, SendGuardConfig, SendBlocked
from wechat_agent.core.task import ActionSpec, TaskPlan
from wechat_agent.platform.auto import build_platform
from wechat_agent.recovery.retry import retry
from wechat_agent.recovery.fallback import dismiss_modal, go_home
from wechat_agent.storage.logger import build_file_logger
from wechat_agent.storage.db import RunDB


def run_once(config: AppConfig) -> tuple[str, int]:
    run_id = str(uuid.uuid4())
    run_dir = config.run_dir or str(Path("runs") / run_id)
    Path(run_dir).mkdir(parents=True, exist_ok=True)

    # Event logging
    bus = EventBus()
    bus.subscribe(JsonlEventLogger(str(Path(run_dir) / "events.jsonl")))

    # Human-readable log
    logger = build_file_logger(run_dir)
    logger.info("run_id=%s contact=%r", run_id, config.contact_name)

    # Optional SQLite DB (best-effort)
    db: RunDB | None = None
    try:
        db = RunDB(str(Path(run_dir).parent.parent / "wechatauto.db"))
        db.start_run(run_id, contact=config.contact_name, goal="closed_loop", run_dir=run_dir)
    except Exception as exc:  # noqa: BLE001
        logger.warning("DB init failed (non-fatal): %s", exc)
        db = None

    # SendGuard
    guard = SendGuard(
        SendGuardConfig(
            dry_run=not config.send,
            whitelist=list(getattr(config, "whitelist", None) or []),
            cooldown_seconds=float(getattr(config, "cooldown_seconds", 30.0)),
        )
    )

    platform = build_platform(config.platform, run_dir=run_dir, config=config)
    plan = _planned_actions_for_platform(
        platform_name=getattr(platform, "name", config.platform),
        plan=plan_closed_loop(config.contact_name, config.recent_n, config.message, config.send),
    )

    bus.emit(run_id, "TaskPlanned", {"goal": plan.goal, "actions": [a.__dict__ for a in plan.actions]})
    logger.info("plan: %s", [a.name for a in plan.actions])

    exit_code = 0

    for action in plan.actions:
        bus.emit(run_id, "ActionStarted", {"name": action.name, "params": action.params})
        logger.info("→ %s %s", action.name, action.params)

        # SendGuard check before actual send
        if action.name == "send_message":
            text = action.params.get("text", "")
            if guard.dry_run:
                bus.emit(run_id, "DryRun", {"text": text})
                logger.info("  [dry-run] would send: %r", text)
                continue
            try:
                guard.check(config.contact_name, text)
            except SendBlocked as exc:
                bus.emit(run_id, "SendBlocked", {"reason": str(exc)})
                logger.warning("  [blocked] %s", exc)
                (Path(run_dir) / "error.txt").write_text(str(exc) + "\n", encoding="utf-8")
                exit_code = 2
                break

        def _dispatch(name=action.name, params=action.params):  # noqa: ANN202
            platform.dispatch(name, params, bus=bus, run_id=run_id)

        try:
            retry(
                _dispatch,
                delays=(0.5, 1.5, 3.0),
                exceptions=(ActionFailed, VerificationFailed, RuntimeError),
                on_retry=lambda attempt, exc: (
                    logger.warning("  retry %d: %s", attempt + 1, exc),
                    bus.emit(run_id, "ActionRetry", {"name": action.name, "attempt": attempt + 1, "error": repr(exc)}),
                    _try_recover(bus=bus, run_id=run_id, logger=logger),
                ),
            )
            bus.emit(run_id, "ActionFinished", {"name": action.name})
            logger.info("  ✓ %s", action.name)

            if action.name == "send_message":
                guard.record_sent(config.contact_name)
                if db is not None:
                    try:
                        db.record_sent(run_id, config.contact_name, action.params.get("text", ""))
                    except Exception:
                        pass

        except Exception as exc:  # noqa: BLE001
            bus.emit(run_id, "ActionFailed", {"name": action.name, "error": repr(exc)})
            logger.error("  ✗ %s: %s", action.name, exc)
            (Path(run_dir) / "error.txt").write_text(repr(exc) + "\n", encoding="utf-8")
            exit_code = 1
            break

    if db is not None:
        try:
            db.finish_run(run_id, exit_code)
            db.close()
        except Exception:
            pass

    logger.info("done exit_code=%d  dir=%s", exit_code, run_dir)
    return run_dir, exit_code


def _try_recover(*, bus, run_id: str, logger) -> None:
    """Best-effort recovery between retries: dismiss modal, go home."""
    try:
        dismiss_modal(bus=bus, run_id=run_id)
    except Exception as exc:  # noqa: BLE001
        logger.debug("dismiss_modal failed: %s", exc)
    try:
        go_home(bus=bus, run_id=run_id)
    except Exception as exc:  # noqa: BLE001
        logger.debug("go_home failed: %s", exc)


def _planned_actions_for_platform(*, platform_name: str, plan: TaskPlan) -> TaskPlan:
    if platform_name != "windows":
        return plan
    actions = [ActionSpec("uia_self_check", {})] + list(plan.actions)
    return TaskPlan(goal=plan.goal, actions=actions)
