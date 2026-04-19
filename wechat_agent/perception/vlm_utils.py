from __future__ import annotations

import base64
import json
from typing import Any

from wechat_agent.core.models import BBox, UiElement


def encode_image_data_url(image_path: str) -> str:
    with open(image_path, "rb") as f:
        data = base64.b64encode(f.read()).decode("utf-8")
    if image_path.lower().endswith(".png"):
        mime = "image/png"
    elif image_path.lower().endswith(".webp"):
        mime = "image/webp"
    else:
        mime = "image/jpeg"
    return f"data:{mime};base64,{data}"


def parse_elements_json(text: str) -> list[UiElement]:
    """
    Parse {"elements":[{"label":..,"score":..,"bbox":{"x1":..,"y1":..,"x2":..,"y2":..}}]}
    from a model response string.
    """

    raw = (text or "").strip()
    if not raw:
        return []

    # Strip common code fences.
    if raw.startswith("```"):
        raw = raw.strip("`").strip()

    # Best-effort extraction of the first JSON object.
    start = raw.find("{")
    end = raw.rfind("}")
    if start != -1 and end != -1 and end > start:
        raw = raw[start : end + 1]

    data = json.loads(raw)
    out: list[UiElement] = []
    for item in (data.get("elements") or []):
        bbox_d = item.get("bbox") or {}
        bbox = BBox(
            x1=float(bbox_d["x1"]),
            y1=float(bbox_d["y1"]),
            x2=float(bbox_d["x2"]),
            y2=float(bbox_d["y2"]),
        )
        out.append(
            UiElement(
                bbox=bbox,
                label=str(item["label"]),
                score=float(item.get("score", 0.5)),
            )
        )
    return out


def debug_elements(elements: list[UiElement]) -> list[dict[str, Any]]:
    return [{"bbox": {"x1": e.bbox.x1, "y1": e.bbox.y1, "x2": e.bbox.x2, "y2": e.bbox.y2}, "label": e.label, "score": e.score} for e in elements]

