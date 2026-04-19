from __future__ import annotations

import subprocess
import time

import Quartz

from wechat_agent.platform.ports import WindowInfo

# macOS virtual key codes (US layout)
_KEY_CODES: dict[str, int] = {
    "a": 0, "s": 1, "d": 2, "f": 3, "h": 4, "g": 5, "z": 6, "x": 7,
    "c": 8, "v": 9, "b": 11, "q": 12, "w": 13, "e": 14, "r": 15,
    "y": 16, "t": 17, "1": 18, "2": 19, "3": 20, "4": 21, "6": 22,
    "5": 23, "=": 24, "9": 25, "7": 26, "-": 27, "8": 28, "0": 29,
    "]": 30, "o": 31, "u": 32, "[": 33, "i": 34, "p": 35,
    "return": 36, "enter": 36, "l": 37, "j": 38, "'": 39, "k": 40,
    ";": 41, "\\": 42, ",": 43, "/": 44, "n": 45, "m": 46, ".": 47,
    "tab": 48, "space": 49, "`": 50, "delete": 51, "esc": 53, "escape": 53,
    "left": 123, "right": 124, "down": 125, "up": 126,
}

_MOD_FLAGS: dict[str, int] = {
    "cmd": Quartz.kCGEventFlagMaskCommand,
    "command": Quartz.kCGEventFlagMaskCommand,
    "shift": Quartz.kCGEventFlagMaskShift,
    "alt": Quartz.kCGEventFlagMaskAlternate,
    "option": Quartz.kCGEventFlagMaskAlternate,
    "ctrl": Quartz.kCGEventFlagMaskControl,
    "control": Quartz.kCGEventFlagMaskControl,
}


def _osascript(script: str) -> bool:
    """Run an osascript snippet. Returns True on success, False on error."""
    result = subprocess.run(
        ["osascript", "-e", script],
        check=False, capture_output=True, text=True,
    )
    return result.returncode == 0


def _osascript_click(x: int, y: int) -> bool:
    return _osascript(f'tell application "System Events" to click at {{{x}, {y}}}')


def _cg_click(x: int, y: int) -> None:
    pos = Quartz.CGPointMake(x, y)
    move = Quartz.CGEventCreateMouseEvent(None, Quartz.kCGEventMouseMoved, pos, Quartz.kCGMouseButtonLeft)
    Quartz.CGEventPost(Quartz.kCGHIDEventTap, move)
    time.sleep(0.08)
    for etype in (Quartz.kCGEventLeftMouseDown, Quartz.kCGEventLeftMouseUp):
        ev = Quartz.CGEventCreateMouseEvent(None, etype, pos, Quartz.kCGMouseButtonLeft)
        Quartz.CGEventPost(Quartz.kCGHIDEventTap, ev)
    time.sleep(0.08)


def _cg_key(key_code: int, flags: int = 0) -> None:
    for down in (True, False):
        ev = Quartz.CGEventCreateKeyboardEvent(None, key_code, down)
        if flags:
            Quartz.CGEventSetFlags(ev, flags)
        Quartz.CGEventPost(Quartz.kCGHIDEventTap, ev)
    time.sleep(0.05)


def click_at(x: float, y: float) -> None:
    ix, iy = int(x), int(y)
    # Try System Events first (most reliable for WeChat UI elements).
    # Fall back to CGEvent if osascript lacks Accessibility permission.
    if not _osascript_click(ix, iy):
        _cg_click(ix, iy)


def click_norm(window: WindowInfo, x: float, y: float) -> None:
    screen_x = window.x + x * window.width
    screen_y = window.y + y * window.height
    click_at(screen_x, screen_y)


def paste_text(text: str) -> None:
    subprocess.run(["pbcopy"], input=text, text=True, check=True)
    time.sleep(0.05)
    _cg_key(_KEY_CODES["v"], Quartz.kCGEventFlagMaskCommand)


def key_combo(combo: str) -> None:
    parts = [k.strip().lower() for k in combo.split("+") if k.strip()]
    if not parts:
        return
    main_key = parts[-1]
    flags = 0
    for m in parts[:-1]:
        flags |= _MOD_FLAGS.get(m, 0)
    code = _KEY_CODES.get(main_key)
    if code is None:
        raise ValueError(f"Unsupported key in combo: {main_key!r}")
    _cg_key(code, flags)


def press_key(key: str) -> None:
    key = key.strip().lower()
    code = _KEY_CODES.get(key)
    if code is None:
        raise ValueError(f"Unsupported key: {key!r}")
    _cg_key(code)


def press_return_to_send() -> None:
    """Send Return via osascript (Accessibility) then fall back to CGEvent."""
    if not _osascript("tell application \"System Events\" to key code 36"):
        _cg_key(_KEY_CODES["return"])


def sleep(seconds: float) -> None:
    time.sleep(seconds)
