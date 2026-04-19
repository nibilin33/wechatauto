from __future__ import annotations

import subprocess
import time

from wechat_agent.platform.macos.osascript import run_osascript
from wechat_agent.platform.ports import WindowInfo


def click_at(x: float, y: float) -> None:
    # Uses System Events for coordinate click; requires Accessibility permission.
    script = f'tell application "System Events" to click at {{{int(x)}, {int(y)}}}'
    run_osascript(script)


def click_norm(window: WindowInfo, x: float, y: float) -> None:
    screen_x = window.x + x * window.width
    screen_y = window.y + y * window.height
    click_at(screen_x, screen_y)


def paste_text(text: str) -> None:
    subprocess.run(["pbcopy"], input=text, text=True, check=True)
    run_osascript('tell application "System Events" to keystroke "v" using command down')


def key_combo(combo: str) -> None:
    keys = [k.strip().lower() for k in combo.split("+") if k.strip()]
    if not keys:
        return
    main = keys[-1]
    modifiers = keys[:-1]

    mod_map = {
        "cmd": "command",
        "command": "command",
        "shift": "shift",
        "alt": "option",
        "option": "option",
        "ctrl": "control",
        "control": "control",
    }
    mod_tokens = [mod_map[m] for m in modifiers if m in mod_map]
    using_part = ""
    if mod_tokens:
        using_part = " using {" + ", ".join(f"{m} down" for m in mod_tokens) + "}"
    run_osascript(f'tell application "System Events" to keystroke "{main}"{using_part}')


def press_key(key: str) -> None:
    key = key.strip().lower()
    # Common key codes: return=36, tab=48, esc=53, down=125, up=126.
    codes = {"return": 36, "enter": 36, "tab": 48, "esc": 53, "escape": 53, "down": 125, "up": 126}
    if key in codes:
        run_osascript(f'tell application "System Events" to key code {codes[key]}')
        return
    if len(key) == 1:
        run_osascript(f'tell application "System Events" to keystroke "{key}"')
        return
    raise ValueError(f"Unsupported key: {key}")


def sleep(seconds: float) -> None:
    time.sleep(seconds)

