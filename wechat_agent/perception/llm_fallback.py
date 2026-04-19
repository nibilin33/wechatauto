from __future__ import annotations

import json
import subprocess
from dataclasses import asdict
from typing import Any

from wechat_agent.core.models import BBox, UiElement


def run_llm_fallback(cmd: str, *, image_path: str) -> list[UiElement]:
    """
    Run an external LLM vision command and parse UI elements from stdout JSON.

    The command may contain `{image_path}` placeholder.
    Expected output schema (example):
      {"elements":[{"label":"send","score":0.9,"bbox":{"x1":0.7,"y1":0.9,"x2":0.8,"y2":0.96}}]}
    """

    rendered = cmd.format(image_path=image_path)
    result = subprocess.run(
        rendered,
        shell=True,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError((result.stderr or result.stdout or "llm fallback failed").strip())
    try:
        data = json.loads(result.stdout)
    except Exception as e:  # noqa: BLE001
        raise RuntimeError(f"Invalid llm fallback JSON: {e}") from e

    elements: list[UiElement] = []
    for item in (data.get("elements") or []):
        try:
            bbox_d = item["bbox"]
            bbox = BBox(
                x1=float(bbox_d["x1"]),
                y1=float(bbox_d["y1"]),
                x2=float(bbox_d["x2"]),
                y2=float(bbox_d["y2"]),
            )
            elements.append(
                UiElement(
                    bbox=bbox,
                    label=str(item["label"]),
                    score=float(item.get("score", 0.5)),
                )
            )
        except Exception:
            continue
    return elements


def debug_elements(elements: list[UiElement]) -> list[dict[str, Any]]:
    return [{"bbox": asdict(e.bbox), "label": e.label, "score": e.score} for e in elements]

