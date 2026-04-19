from __future__ import annotations

from wechat_agent.platform.macos.osascript import run_osascript
from wechat_agent.platform.ports import WindowInfo


def locate_wechat_window() -> WindowInfo:
    # NOTE: This requires Accessibility permission for osascript/System Events.
    # We intentionally keep it vision-first: this is only used to find window bounds and id.
    script = r'''
tell application "System Events"
  if not (exists process "WeChat") then error "WeChatNotRunning"
  tell process "WeChat"
    set frontmost to true
    set w to window 1
    set wid to id of w
    set p to position of w
    set s to size of w
    set t to name of w
    return (wid as string) & "|" & (item 1 of p as string) & "|" & (item 2 of p as string) & "|" & (item 1 of s as string) & "|" & (item 2 of s as string) & "|" & t
  end tell
end tell
'''
    out = run_osascript(script).strip()
    parts = out.split("|", 5)
    if len(parts) < 6:
        raise RuntimeError(f"Unexpected osascript output: {out!r}")
    native_id, x, y, width, height, title = parts
    return WindowInfo(
        native_id=native_id.strip(),
        title=title.strip(),
        x=int(float(x)),
        y=int(float(y)),
        width=int(float(width)),
        height=int(float(height)),
        scale=1.0,
    )

