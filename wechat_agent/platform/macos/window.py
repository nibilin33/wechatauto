from __future__ import annotations

import Quartz

from wechat_agent.platform.macos.osascript import run_osascript
from wechat_agent.platform.ports import WindowInfo


def _get_wechat_window_id() -> int:
    """Return the CGWindowID of the frontmost WeChat window via Quartz."""
    for option in (
        Quartz.kCGWindowListOptionOnScreenOnly | Quartz.kCGWindowListExcludeDesktopElements,
        Quartz.kCGWindowListOptionAll | Quartz.kCGWindowListExcludeDesktopElements,
    ):
        window_list = Quartz.CGWindowListCopyWindowInfo(option, Quartz.kCGNullWindowID)
        if not window_list:
            continue
        candidates = []
        for info in window_list:
            if info.get("kCGWindowOwnerName") not in ("WeChat", "微信"):
                continue
            bounds = info.get("kCGWindowBounds", {})
            if bounds.get("Width", 0) < 200 or bounds.get("Height", 0) < 200:
                continue
            wid = info.get("kCGWindowNumber")
            if wid is None:
                continue
            on_screen = int(info.get("kCGWindowIsOnscreen", 0))
            candidates.append((on_screen, int(wid)))
        if candidates:
            candidates.sort(key=lambda t: t[0], reverse=True)
            return candidates[0][1]
    raise RuntimeError("Could not find WeChat window via Quartz CGWindowListCopyWindowInfo")


def locate_wechat_window() -> WindowInfo:
    # NOTE: This requires Accessibility permission for osascript/System Events.
    # We intentionally keep it vision-first: this is only used to find window bounds and id.
    # Window ID is obtained via Quartz because AppleScript's `id of window` is unreliable for WeChat.
    script = r'''
tell application "WeChat"
  activate
end tell
delay 1.0
tell application "System Events"
  if not (exists process "WeChat") then error "WeChatNotRunning"
  tell process "WeChat"
    if (count of windows) is 0 then
      tell application "WeChat" to activate
      delay 1.5
    end if
    if (count of windows) is 0 then error "WeChatNoWindow"
    set w to window 1
    set p to position of w
    set s to size of w
    set t to name of w
    return (item 1 of p as string) & "|" & (item 2 of p as string) & "|" & (item 1 of s as string) & "|" & (item 2 of s as string) & "|" & t
  end tell
end tell
'''
    out = run_osascript(script).strip()
    parts = out.split("|", 4)
    if len(parts) < 5:
        raise RuntimeError(f"Unexpected osascript output: {out!r}")
    x, y, width, height, title = parts
    native_id = _get_wechat_window_id()
    return WindowInfo(
        native_id=str(native_id),
        title=title.strip(),
        x=int(float(x)),
        y=int(float(y)),
        width=int(float(width)),
        height=int(float(height)),
        scale=1.0,
    )

