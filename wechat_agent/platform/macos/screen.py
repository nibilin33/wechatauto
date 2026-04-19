from __future__ import annotations

import subprocess
from pathlib import Path
import re

from wechat_agent.platform.ports import WindowInfo


def _get_pixel_size(path: str) -> tuple[int, int]:
    result = subprocess.run(
        ["sips", "-g", "pixelWidth", "-g", "pixelHeight", path],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError((result.stderr or result.stdout or "sips failed").strip())
    pixel_width: int | None = None
    pixel_height: int | None = None
    for line in (result.stdout or "").splitlines():
        line = line.strip()
        m = re.search(r"pixelWidth:\s*(\d+)\s*$", line)
        if m:
            pixel_width = int(m.group(1))
            continue
        m = re.search(r"pixelHeight:\s*(\d+)\s*$", line)
        if m:
            pixel_height = int(m.group(1))
    if pixel_width is None or pixel_height is None:
        raise RuntimeError(f"Unexpected sips output: {result.stdout!r}")
    return pixel_width, pixel_height


def capture_wechat_window(window: WindowInfo, path: str) -> dict:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    # -l captures a specific window by its window id.
    # https://ss64.com/mac/screencapture.html (built-in)
    result = subprocess.run(
        ["screencapture", "-x", "-o", "-l", str(window.native_id), path],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        stderr = (result.stderr or "").strip()
        stdout = (result.stdout or "").strip()
        message = stderr or stdout or f"screencapture failed with code {result.returncode}"
        raise RuntimeError(message)
    pixel_width, pixel_height = _get_pixel_size(path)
    scale_x = pixel_width / max(window.width, 1)
    scale_y = pixel_height / max(window.height, 1)
    return {
        "pixel_width": pixel_width,
        "pixel_height": pixel_height,
        "scale_x": scale_x,
        "scale_y": scale_y,
    }
