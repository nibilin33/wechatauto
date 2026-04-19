from __future__ import annotations

from wechat_agent.core.models import BBox


def clamp01(value: float) -> float:
    return 0.0 if value < 0.0 else 1.0 if value > 1.0 else value


def vision_rect_to_bbox(rect) -> BBox:
    """
    Vision boundingBox uses normalized image coordinates with origin at bottom-left.
    Convert to our normalized window coordinates with origin at top-left.
    """

    x = float(rect.origin.x)
    y = float(rect.origin.y)
    w = float(rect.size.width)
    h = float(rect.size.height)

    x1 = clamp01(x)
    x2 = clamp01(x + w)

    y_top = 1.0 - (y + h)
    y1 = clamp01(y_top)
    y2 = clamp01(y_top + h)
    return BBox(x1=x1, y1=y1, x2=x2, y2=y2)


def bbox_center(bbox: BBox) -> tuple[float, float]:
    return (bbox.x1 + bbox.x2) / 2.0, (bbox.y1 + bbox.y2) / 2.0


def bbox_contains(bbox: BBox, x: float, y: float) -> bool:
    return bbox.x1 <= x <= bbox.x2 and bbox.y1 <= y <= bbox.y2


def bbox_intersects(a: BBox, b: BBox) -> bool:
    return not (a.x2 < b.x1 or a.x1 > b.x2 or a.y2 < b.y1 or a.y1 > b.y2)


def bbox_in_region(bbox: BBox, region: BBox) -> bool:
    return bbox_intersects(bbox, region)

