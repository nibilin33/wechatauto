from __future__ import annotations

"""
Fallback / recovery strategies.

These are called by the runner when an action fails after retries.  They try
to bring the agent back to a known-good state without performing any business
action (e.g. sending a message).
"""

from wechat_agent.platform.macos.osascript import run_osascript


def dismiss_modal(bus=None, run_id: str | None = None) -> bool:
    """
    Press Escape to close any blocking modal / overlay.

    Returns True if the script ran without error.
    """
    try:
        run_osascript(
            'tell application "System Events" to key code 53'  # Escape
        )
        if bus is not None and run_id is not None:
            bus.emit(run_id, "RecoveryApplied", {"strategy": "dismiss_modal"})
        return True
    except Exception:
        return False


def go_home(bus=None, run_id: str | None = None) -> bool:
    """
    Attempt to return WeChat to the main chat-list view by pressing Escape
    one or two times and then clicking into the sidebar area.

    Returns True if the script ran without error.
    """
    try:
        run_osascript('tell application "System Events" to key code 53')
        run_osascript('tell application "System Events" to key code 53')
        if bus is not None and run_id is not None:
            bus.emit(run_id, "RecoveryApplied", {"strategy": "go_home"})
        return True
    except Exception:
        return False


def safe_exit(reason: str, bus=None, run_id: str | None = None) -> None:
    """Record a safe-exit event and raise SystemExit."""
    if bus is not None and run_id is not None:
        bus.emit(run_id, "SafeExit", {"reason": reason})
    raise SystemExit(f"Safe exit: {reason}")
