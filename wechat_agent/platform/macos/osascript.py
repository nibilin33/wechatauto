from __future__ import annotations

import subprocess


def run_osascript(script: str) -> str:
    result = subprocess.run(
        ["osascript", "-e", script],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        stderr = (result.stderr or "").strip()
        stdout = (result.stdout or "").strip()
        message = stderr or stdout or f"osascript failed with code {result.returncode}"
        raise RuntimeError(message)
    return (result.stdout or "").strip()

