from __future__ import annotations

from dataclasses import asdict

from wechat_agent.core.errors import ActionFailed, VerificationFailed
from wechat_agent.core.models import BBox, UiElement, UiTextBlock
from wechat_agent.perception.bbox import bbox_center
from wechat_agent.perception.layout import Layout
from wechat_agent.perception.semantic_parser import (
    CHAT_MESSAGES_REGION,
    extract_recent_lines,
    find_text_block,
)


def _emit_blocks(bus, run_id: str, blocks: list[UiTextBlock], *, limit: int = 200) -> None:
    bus.emit(
        run_id,
        "OcrCompleted",
        {
            "count": len(blocks),
            "blocks": [{"bbox": asdict(b.bbox), "text": b.text, "score": b.score} for b in blocks[:limit]],
        },
    )


def search_contact(driver, *, run_id: str, bus, name: str, blocks: list[UiTextBlock]) -> None:
    _emit_blocks(bus, run_id, blocks)
    layout: Layout | None = getattr(driver, "layout", None)
    semantic = getattr(driver, "semantic", None)
    if semantic is not None and hasattr(semantic, "anchors"):
        bbox = semantic.anchors.get("search_entry")
        if bbox is not None:
            x, y = bbox_center(bbox)
            driver.click_norm(x, y)
            driver.sleep(0.1)
            driver.key_combo("cmd+a")
            driver.paste_text(name)
            driver.sleep(0.1)
            driver.press_key("return")
            driver.sleep(0.4)
            return
    sidebar_top = layout.sidebar_top if layout is not None else None
    # Prefer UI detection ("search" icon/button) then OCR "搜索".
    if hasattr(driver, "elements") and isinstance(driver.elements, list):
        elem = _pick_element(driver.elements, "search")
        if elem is not None:
            x, y = bbox_center(elem.bbox)
            driver.click_norm(x, y)
            driver.sleep(0.1)
            driver.key_combo("cmd+a")
            driver.paste_text(name)
            driver.sleep(0.1)
            driver.press_key("return")
            driver.sleep(0.4)
            return

    # Prefer clicking the "搜索" placeholder in sidebar (OCR).
    block = find_text_block(blocks, keywords=["搜索"], region=sidebar_top)
    if block is not None:
        x, y = bbox_center(block.bbox)
        driver.click_norm(x, y)
    else:
        # Fallback: a stable-ish location for the search box.
        driver.click_norm(0.12, 0.08)
    driver.sleep(0.1)
    driver.key_combo("cmd+a")
    driver.paste_text(name)
    driver.sleep(0.1)
    driver.press_key("return")
    driver.sleep(0.4)


def open_chat(driver, *, run_id: str, bus, name: str) -> None:
    # Usually Enter on the top search result opens the chat.
    bus.emit(run_id, "OpenChatHint", {"name": name})
    driver.press_key("return")
    driver.sleep(0.6)


def read_recent(driver, *, run_id: str, bus, n: int, blocks: list[UiTextBlock]) -> list[str]:
    _emit_blocks(bus, run_id, blocks)
    layout: Layout | None = getattr(driver, "layout", None)
    semantic = getattr(driver, "semantic", None)
    if semantic is not None and hasattr(semantic, "messages") and semantic.messages:
        lines = [m.text for m in semantic.messages][-n:]
    else:
        lines = extract_recent_lines(blocks, n, layout=layout)
    bus.emit(run_id, "RecentMessagesRead", {"n": n, "lines": lines})
    return lines


def send_message(driver, *, run_id: str, bus, text: str, blocks: list[UiTextBlock]) -> None:
    _emit_blocks(bus, run_id, blocks)
    layout: Layout | None = getattr(driver, "layout", None)
    semantic = getattr(driver, "semantic", None)
    composer_region = layout.chat_composer if layout is not None else None
    # Focus composer region.
    driver.click_norm(0.65, 0.92)
    driver.sleep(0.1)
    driver.paste_text(text)
    driver.sleep(0.2)

    # Prefer UI detection ("send") then OCR "发送".
    send_bbox = None
    if semantic is not None and hasattr(semantic, "anchors"):
        send_bbox = semantic.anchors.get("send_button")
    if hasattr(driver, "elements") and isinstance(driver.elements, list):
        elem = _pick_element(driver.elements, "send")
        if elem is not None:
            send_bbox = elem.bbox
    if send_bbox is None:
        send_block = find_text_block(blocks, keywords=["发送"], region=composer_region)
        if send_block is not None:
            send_bbox = send_block.bbox
    if send_bbox is None:
        raise ActionFailed("无法定位“发送”按钮（UI 检测 + OCR 均未命中），为避免误发已停止。")

    x, y = bbox_center(send_bbox)
    driver.click_norm(x, y)
    driver.sleep(0.6)


def verify_sent(driver, *, run_id: str, bus, text: str, blocks: list[UiTextBlock]) -> None:
    _emit_blocks(bus, run_id, blocks)
    # Search within message region for the outgoing text (best-effort substring match).
    layout: Layout | None = getattr(driver, "layout", None)
    messages_region = layout.chat_messages if layout is not None else CHAT_MESSAGES_REGION
    candidates = [b for b in blocks if _in_region(b.bbox, messages_region)]
    joined = "\n".join(b.text for b in candidates)
    if text not in joined:
        raise VerificationFailed("发送校验失败：未在消息区 OCR 结果中找到刚发送的文本。")
    bus.emit(run_id, "Verified", {"type": "MessageAppeared", "ok": True})


def _in_region(bbox: BBox, region: BBox) -> bool:
    # inclusive intersection
    return not (bbox.x2 < region.x1 or bbox.x1 > region.x2 or bbox.y2 < region.y1 or bbox.y1 > region.y2)


def _pick_element(elements: list[UiElement], label: str) -> UiElement | None:
    best = None
    best_score = -1.0
    for e in elements:
        if e.label != label:
            continue
        if e.score > best_score:
            best = e
            best_score = e.score
    return best
