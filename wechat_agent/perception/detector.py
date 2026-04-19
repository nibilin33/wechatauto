from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

import cv2
import numpy as np

from wechat_agent.core.models import BBox, UiElement


def _stem_to_label(stem: str) -> str:
    # Allow multiple variants per label: send__dark.png, send__v4.png, etc.
    return stem.split("__", 1)[0]


def _iou(a: BBox, b: BBox) -> float:
    x1 = max(a.x1, b.x1)
    y1 = max(a.y1, b.y1)
    x2 = min(a.x2, b.x2)
    y2 = min(a.y2, b.y2)
    inter_w = max(0.0, x2 - x1)
    inter_h = max(0.0, y2 - y1)
    inter = inter_w * inter_h
    if inter <= 0.0:
        return 0.0
    area_a = max(0.0, a.x2 - a.x1) * max(0.0, a.y2 - a.y1)
    area_b = max(0.0, b.x2 - b.x1) * max(0.0, b.y2 - b.y1)
    denom = area_a + area_b - inter
    return inter / denom if denom > 0 else 0.0


def _nms(elements: list[UiElement], *, iou_threshold: float) -> list[UiElement]:
    kept: list[UiElement] = []
    for e in sorted(elements, key=lambda x: x.score, reverse=True):
        if all(_iou(e.bbox, k.bbox) < iou_threshold for k in kept):
            kept.append(e)
    return kept


def detect_ui_elements(
    image_path: str,
    *,
    templates_dir: str,
    threshold: float = 0.78,
    scales: tuple[float, ...] = (0.85, 0.95, 1.0, 1.25, 1.5, 2.0),
    max_per_label: int = 3,
    nms_iou: float = 0.3,
) -> list[UiElement]:
    """
    Simple UI detector via template matching.

    - Templates: PNG files under templates_dir (recursive).
    - Label: file stem before '__' (e.g. send__dark.png -> 'send').
    - Output bboxes are normalized (0..1) in top-left origin, relative to the screenshot image.
    """

    templates_root = Path(templates_dir)
    if not templates_root.exists():
        return []

    img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    if img is None:
        return []
    img_h, img_w = img.shape[:2]
    if img_h <= 0 or img_w <= 0:
        return []

    by_label: dict[str, list[UiElement]] = {}

    for tpl_path in templates_root.rglob("*.png"):
        tpl = cv2.imread(str(tpl_path), cv2.IMREAD_GRAYSCALE)
        if tpl is None:
            continue
        label = _stem_to_label(tpl_path.stem)
        for s in scales:
            if s <= 0:
                continue
            scaled = tpl if s == 1.0 else cv2.resize(tpl, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
            th, tw = scaled.shape[:2]
            if th < 6 or tw < 6:
                continue
            if th >= img_h or tw >= img_w:
                continue

            res = cv2.matchTemplate(img, scaled, cv2.TM_CCOEFF_NORMED)
            ys, xs = np.where(res >= threshold)
            if len(xs) == 0:
                continue

            scores = res[ys, xs]
            # Pick top candidates for this template-scale quickly.
            order = np.argsort(scores)[::-1][: max_per_label * 4]
            for idx in order:
                x = int(xs[idx])
                y = int(ys[idx])
                score = float(scores[idx])
                bbox = BBox(
                    x1=x / img_w,
                    y1=y / img_h,
                    x2=(x + tw) / img_w,
                    y2=(y + th) / img_h,
                )
                by_label.setdefault(label, []).append(UiElement(bbox=bbox, label=label, score=score))

    out: list[UiElement] = []
    for label, elems in by_label.items():
        elems = _nms(elems, iou_threshold=nms_iou)
        out.extend(elems[:max_per_label])
    return sorted(out, key=lambda e: e.score, reverse=True)


def debug_elements(elements: list[UiElement]) -> list[dict]:
    return [{"bbox": asdict(e.bbox), "label": e.label, "score": e.score} for e in elements]

