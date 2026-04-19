from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

from wechat_agent.core.models import BBox, UiElement


def detect_ui_elements_yolo(
    image_path: str,
    *,
    model_path: str,
    conf: float = 0.25,
) -> list[UiElement]:
    """
    YOLO detector wrapper (optional dependency).

    Requires `ultralytics` at runtime. The model should be trained to output
    stable UI labels such as: `send`, `search`, `back`, `close`, etc.
    """

    path = Path(model_path)
    if not path.exists():
        return []

    try:
        from ultralytics import YOLO  # type: ignore
    except Exception as e:  # noqa: BLE001
        raise RuntimeError("ultralytics 未安装，无法启用 YOLO 检测。") from e

    model = YOLO(str(path))
    results = model.predict(source=image_path, conf=conf, verbose=False)
    if not results:
        return []

    r0 = results[0]
    h, w = r0.orig_shape[:2]
    names = r0.names or {}

    elements: list[UiElement] = []
    if r0.boxes is None:
        return []
    for b in r0.boxes:
        # xyxy is a tensor-like object; convert to list of floats
        xyxy = b.xyxy[0].tolist()
        x1, y1, x2, y2 = [float(v) for v in xyxy]
        cls_id = int(b.cls[0].item()) if hasattr(b, "cls") else -1
        label = str(names.get(cls_id, cls_id))
        score = float(b.conf[0].item()) if hasattr(b, "conf") else 0.5
        elements.append(
            UiElement(
                bbox=BBox(x1=x1 / w, y1=y1 / h, x2=x2 / w, y2=y2 / h),
                label=label,
                score=score,
            )
        )
    return elements


def debug_elements(elements: list[UiElement]) -> list[dict[str, Any]]:
    return [{"bbox": asdict(e.bbox), "label": e.label, "score": e.score} for e in elements]

