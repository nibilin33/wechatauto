from __future__ import annotations

from dataclasses import asdict, dataclass

from wechat_agent.core.models import BBox, UiElement, UiTextBlock
from wechat_agent.perception.bbox import bbox_center, bbox_in_region


@dataclass(frozen=True)
class Layout:
    sidebar: BBox
    sidebar_top: BBox
    chat: BBox
    chat_header: BBox
    chat_messages: BBox
    chat_composer: BBox
    confidence: float


DEFAULT_SIDEBAR_WIDTH = 0.28
DEFAULT_HEADER_H = 0.14
DEFAULT_COMPOSER_Y1 = 0.82


def infer_layout(*, texts: list[UiTextBlock], elements: list[UiElement]) -> Layout:
    """
    Infer major regions by combining:
    - UI detections (search/send/etc.)
    - OCR text blocks (e.g. "搜索", chat title)

    Output uses normalized coordinates (0..1), origin top-left.
    """

    sidebar_w = _infer_sidebar_width(texts=texts, elements=elements)
    composer_y1 = _infer_composer_top(texts=texts, elements=elements)
    header_h = _infer_header_height(texts=texts, sidebar_w=sidebar_w)

    sidebar = BBox(x1=0.0, y1=0.0, x2=sidebar_w, y2=1.0)
    sidebar_top = BBox(x1=0.0, y1=0.0, x2=sidebar_w, y2=0.22)
    chat = BBox(x1=sidebar_w, y1=0.0, x2=1.0, y2=1.0)
    chat_header = BBox(x1=sidebar_w, y1=0.0, x2=1.0, y2=header_h)
    chat_composer = BBox(x1=sidebar_w, y1=composer_y1, x2=1.0, y2=1.0)
    chat_messages = BBox(x1=sidebar_w, y1=header_h, x2=1.0, y2=composer_y1)

    confidence = 0.35
    if _has_label(elements, "send") or _has_label(elements, "search"):
        confidence += 0.25
    if _has_keyword(texts, "搜索"):
        confidence += 0.15
    if _has_probable_title(texts, sidebar_w=sidebar_w):
        confidence += 0.15
    return Layout(
        sidebar=sidebar,
        sidebar_top=sidebar_top,
        chat=chat,
        chat_header=chat_header,
        chat_messages=chat_messages,
        chat_composer=chat_composer,
        confidence=min(0.95, confidence),
    )


def layout_to_debug(layout: Layout) -> dict:
    return {
        "sidebar": asdict(layout.sidebar),
        "sidebar_top": asdict(layout.sidebar_top),
        "chat": asdict(layout.chat),
        "chat_header": asdict(layout.chat_header),
        "chat_messages": asdict(layout.chat_messages),
        "chat_composer": asdict(layout.chat_composer),
        "confidence": layout.confidence,
    }


def _has_label(elements: list[UiElement], label: str) -> bool:
    return any(e.label == label for e in elements)


def _has_keyword(texts: list[UiTextBlock], keyword: str) -> bool:
    return any(keyword in (t.text or "") for t in texts)


def _infer_sidebar_width(*, texts: list[UiTextBlock], elements: list[UiElement]) -> float:
    # 1) prefer detected search element (usually inside sidebar top)
    search = _best_label(elements, "search")
    if search is not None and 0.05 <= search.bbox.x2 <= 0.55:
        return _clamp(search.bbox.x2 + 0.03, 0.18, 0.45)

    # 2) OCR keyword "搜索" (or "微信" search placeholder in Chinese UI)
    candidates = [t for t in texts if "搜索" in (t.text or "")]
    candidates = [t for t in candidates if 0.0 <= t.bbox.x2 <= 0.55 and t.bbox.y2 <= 0.35]
    if candidates:
        candidates.sort(key=lambda b: (b.score, -b.bbox.x2), reverse=True)
        return _clamp(candidates[0].bbox.x2 + 0.03, 0.18, 0.45)

    return DEFAULT_SIDEBAR_WIDTH


def _infer_composer_top(*, texts: list[UiTextBlock], elements: list[UiElement]) -> float:
    # 1) prefer detected send element (typically inside composer)
    send = _best_label(elements, "send")
    if send is not None and 0.55 <= send.bbox.x1 <= 1.0 and 0.65 <= send.bbox.y1 <= 1.0:
        # composer starts a bit above send button
        return _clamp(send.bbox.y1 - 0.05, 0.68, 0.90)

    # 2) OCR "发送" text within bottom area
    candidates = [t for t in texts if "发送" in (t.text or "")]
    candidates = [t for t in candidates if t.bbox.y1 >= 0.70]
    if candidates:
        candidates.sort(key=lambda b: b.score, reverse=True)
        return _clamp(candidates[0].bbox.y1 - 0.06, 0.68, 0.90)

    return DEFAULT_COMPOSER_Y1


def _infer_header_height(*, texts: list[UiTextBlock], sidebar_w: float) -> float:
    # find probable chat title near top of chat region, use its bottom as header boundary.
    title = _best_title_block(texts, sidebar_w=sidebar_w)
    if title is None:
        return DEFAULT_HEADER_H
    return _clamp(title.bbox.y2 + 0.03, 0.10, 0.22)


def _best_label(elements: list[UiElement], label: str) -> UiElement | None:
    best = None
    best_score = -1.0
    for e in elements:
        if e.label != label:
            continue
        if e.score > best_score:
            best = e
            best_score = e.score
    return best


def _best_title_block(texts: list[UiTextBlock], *, sidebar_w: float) -> UiTextBlock | None:
    chat_top = BBox(x1=sidebar_w, y1=0.0, x2=1.0, y2=0.20)
    candidates = [t for t in texts if bbox_in_region(t.bbox, chat_top)]
    candidates = [t for t in candidates if 1 <= len((t.text or "").strip()) <= 30]
    if not candidates:
        return None
    # prefer centered-ish and longer text
    def key(t: UiTextBlock):
        x, y = bbox_center(t.bbox)
        return (t.score, len((t.text or "").strip()), -abs(x - (sidebar_w + (1 - sidebar_w) / 2)), -y)

    candidates.sort(key=key, reverse=True)
    return candidates[0]


def _has_probable_title(texts: list[UiTextBlock], *, sidebar_w: float) -> bool:
    return _best_title_block(texts, sidebar_w=sidebar_w) is not None


def _clamp(v: float, lo: float, hi: float) -> float:
    if v < lo:
        return lo
    if v > hi:
        return hi
    return v

