from __future__ import annotations

from dataclasses import asdict

from wechat_agent.core.models import BBox, ChatMessage, SemanticState, UiElement, UiTextBlock
from wechat_agent.perception.layout import Layout
from wechat_agent.perception.bbox import bbox_center, bbox_in_region


CHAT_REGION = BBox(x1=0.28, y1=0.0, x2=1.0, y2=1.0)
CHAT_HEADER_REGION = BBox(x1=0.28, y1=0.0, x2=1.0, y2=0.14)
CHAT_MESSAGES_REGION = BBox(x1=0.28, y1=0.14, x2=1.0, y2=0.82)
CHAT_COMPOSER_REGION = BBox(x1=0.28, y1=0.82, x2=1.0, y2=1.0)
SIDEBAR_TOP_REGION = BBox(x1=0.0, y1=0.0, x2=0.28, y2=0.22)


def _norm_text(text: str) -> str:
    return "".join(text.split()).lower()


def find_text_block(
    blocks: list[UiTextBlock],
    *,
    keywords: list[str],
    region: BBox | None = None,
) -> UiTextBlock | None:
    best: UiTextBlock | None = None
    best_score = -1.0
    for b in blocks:
        if region is not None and not bbox_in_region(b.bbox, region):
            continue
        t = _norm_text(b.text)
        if not any(k in t for k in keywords):
            continue
        score = b.score
        if score > best_score:
            best = b
            best_score = score
    return best


def extract_chat_title(blocks: list[UiTextBlock], *, layout: Layout | None = None) -> str | None:
    # Heuristic: in the header region, pick the longest reasonably short block.
    header_region = layout.chat_header if layout is not None else CHAT_HEADER_REGION
    candidates = [b for b in blocks if bbox_in_region(b.bbox, header_region)]
    candidates = [b for b in candidates if 1 <= len(b.text) <= 30]
    if not candidates:
        return None
    candidates.sort(key=lambda b: (len(b.text), b.score), reverse=True)
    return candidates[0].text.strip()


def extract_recent_lines(blocks: list[UiTextBlock], n: int, *, layout: Layout | None = None) -> list[str]:
    messages_region = layout.chat_messages if layout is not None else CHAT_MESSAGES_REGION
    msg_blocks = [b for b in blocks if bbox_in_region(b.bbox, messages_region)]
    # Filter out very short noise and obvious UI chrome.
    msg_blocks = [b for b in msg_blocks if len(b.text.strip()) >= 2]
    msg_blocks.sort(key=lambda b: (bbox_center(b.bbox)[1], bbox_center(b.bbox)[0]))
    lines = [b.text.strip() for b in msg_blocks]
    return lines[-n:] if n > 0 else []


def extract_messages(blocks: list[UiTextBlock], *, layout: Layout) -> list[ChatMessage]:
    # Best-effort: take OCR lines inside message region, infer direction by x position.
    msg_blocks = [b for b in blocks if bbox_in_region(b.bbox, layout.chat_messages)]
    msg_blocks = [b for b in msg_blocks if len(b.text.strip()) >= 2]
    msg_blocks.sort(key=lambda b: (bbox_center(b.bbox)[1], bbox_center(b.bbox)[0]))

    msgs: list[ChatMessage] = []
    chat_mid = (layout.chat.x1 + layout.chat.x2) / 2.0
    for b in msg_blocks:
        x, _ = bbox_center(b.bbox)
        if x < chat_mid - 0.08:
            direction = "in"
        elif x > chat_mid + 0.08:
            direction = "out"
        else:
            direction = "unknown"
        msgs.append(ChatMessage(direction=direction, text=b.text.strip(), score=b.score))
    return msgs


def extract_anchors(*, blocks: list[UiTextBlock], elements: list[UiElement], layout: Layout) -> dict[str, BBox]:
    anchors: dict[str, BBox] = {}

    # UI element anchors (prefer high-confidence detections)
    for e in sorted(elements, key=lambda x: x.score, reverse=True):
        if e.label == "send" and "send_button" not in anchors and bbox_in_region(e.bbox, layout.chat_composer):
            anchors["send_button"] = e.bbox
        if e.label == "search" and "search_entry" not in anchors and bbox_in_region(e.bbox, layout.sidebar_top):
            anchors["search_entry"] = e.bbox

    # OCR fallback anchors
    if "send_button" not in anchors:
        b = find_text_block(blocks, keywords=["发送"], region=layout.chat_composer)
        if b is not None:
            anchors["send_button"] = b.bbox
    if "search_entry" not in anchors:
        b = find_text_block(blocks, keywords=["搜索"], region=layout.sidebar_top)
        if b is not None:
            anchors["search_entry"] = b.bbox

    anchors["chat_messages_region"] = layout.chat_messages
    anchors["chat_composer_region"] = layout.chat_composer
    anchors["chat_header_region"] = layout.chat_header
    anchors["sidebar_top_region"] = layout.sidebar_top
    return anchors


def parse_semantic(
    *,
    blocks: list[UiTextBlock],
    elements: list[UiElement],
    layout: Layout,
) -> SemanticState:
    title = extract_chat_title(blocks, layout=layout)
    messages = extract_messages(blocks, layout=layout)
    anchors = extract_anchors(blocks=blocks, elements=elements, layout=layout)

    page = "chat" if title or messages else "unknown"
    confidence = 0.35
    if title:
        confidence += 0.25
    if "send_button" in anchors:
        confidence += 0.15
    if "search_entry" in anchors:
        confidence += 0.10
    if len(messages) >= 3:
        confidence += 0.10
    confidence = min(0.95, confidence)
    return SemanticState(
        page=page,
        chat_title=title,
        messages=messages,
        elements=elements,
        texts=blocks,
        anchors=anchors,
        confidence=confidence,
        raw={
            "texts": [{"bbox": asdict(b.bbox), "text": b.text, "score": b.score} for b in blocks[:200]],
            "elements": [{"bbox": asdict(e.bbox), "label": e.label, "score": e.score} for e in elements[:200]],
        },
    )
