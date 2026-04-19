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


_CHAT_LIST_X_MAX = 0.38


def _emit_blocks(bus, run_id: str, blocks: list[UiTextBlock], *, limit: int = 200) -> None:
    bus.emit(
        run_id,
        "OcrCompleted",
        {
            "count": len(blocks),
            "blocks": [{"bbox": asdict(b.bbox), "text": b.text, "score": b.score} for b in blocks[:limit]],
        },
    )


def _find_in_chat_list(blocks: list[UiTextBlock], name: str) -> UiTextBlock | None:
    for block in blocks:
        if name in block.text and block.bbox.x1 < _CHAT_LIST_X_MAX:
            return block
    return None


def search_contact(driver, *, run_id: str, bus, name: str, blocks: list[UiTextBlock]) -> None:
    _emit_blocks(bus, run_id, blocks)

    direct = _find_in_chat_list(blocks, name)
    if direct is not None:
        bus.emit(run_id, "ContactFoundInList", {"name": name})
        x, y = bbox_center(direct.bbox)
        driver.click_norm(x, y)
        driver.sleep(0.6)
        return

    layout: Layout | None = getattr(driver, "layout", None)
    sidebar_top = layout.sidebar_top if layout is not None else None
    block = find_text_block(blocks, keywords=["搜索"], region=sidebar_top)
    if block is None:
        raise ActionFailed("无法定位搜索入口（UI 检测 + OCR 均未命中），请确认微信窗口在前台且界面可见。")

    x, y = bbox_center(block.bbox)
    driver.click_norm(x, y)
    driver.sleep(0.15)
    driver.key_combo("cmd+a")
    driver.paste_text(name)
    driver.sleep(0.8)


def open_chat(driver, *, run_id: str, bus, name: str, blocks: list[UiTextBlock]) -> None:
    _emit_blocks(bus, run_id, blocks)
    bus.emit(run_id, "OpenChatHint", {"name": name})

    target = _find_in_chat_list(blocks, name)
    if target is not None:
        x, y = bbox_center(target.bbox)
        driver.click_norm(x, y)
        driver.sleep(0.8)
        return

    driver.press_key("return")
    driver.sleep(0.8)


def read_recent(driver, *, run_id: str, bus, n: int, blocks: list[UiTextBlock]) -> list[str]:
    _emit_blocks(bus, run_id, blocks)
    layout: Layout | None = getattr(driver, "layout", None)
    semantic = getattr(driver, "semantic", None)
    if semantic is not None and hasattr(semantic, "messages") and semantic.messages:
        lines = [message.text for message in semantic.messages][-n:]
    else:
        lines = extract_recent_lines(blocks, n, layout=layout)
    bus.emit(run_id, "RecentMessagesRead", {"n": n, "lines": lines})
    return lines


def send_message(driver, *, run_id: str, bus, text: str, blocks: list[UiTextBlock]) -> None:
    _emit_blocks(bus, run_id, blocks)
    layout: Layout | None = getattr(driver, "layout", None)
    semantic = getattr(driver, "semantic", None)
    composer_region = layout.chat_composer if layout is not None else None

    region = composer_region
    if semantic is not None and hasattr(semantic, "anchors"):
        region = semantic.anchors.get("chat_composer_region") or region
    if region is not None:
        cx = (region.x1 + region.x2) / 2.0
        cy = region.y1 + (region.y2 - region.y1) * 0.25
        driver.click_norm(cx, cy)

    driver.sleep(0.1)
    driver.paste_text(text)
    driver.sleep(0.2)

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

    if send_bbox is not None:
        x, y = bbox_center(send_bbox)
        driver.click_norm(x, y)
    else:
        # Use osascript Return (Accessibility) which bypasses WeChat keyboard-shortcut ambiguity.
        driver.press_return_to_send()
    driver.sleep(0.6)


def verify_sent(driver, *, run_id: str, bus, text: str, blocks: list[UiTextBlock]) -> None:
    _emit_blocks(bus, run_id, blocks)
    layout: Layout | None = getattr(driver, "layout", None)
    messages_region = layout.chat_messages if layout is not None else CHAT_MESSAGES_REGION
    # Sent messages in WeChat appear right-aligned (x1 > 0.5); the compose bar
    # is left-anchored (x1 < 0.5). Filtering avoids false positives on unsent text.
    candidates = [
        b for b in blocks
        if _in_region(b.bbox, messages_region) and b.bbox.x1 > 0.5
    ]
    joined_tight = "".join(b.text for b in candidates)
    joined_loose = "\n".join(b.text for b in candidates)
    if text not in joined_tight and text not in joined_loose:
        raise VerificationFailed("发送校验失败：未在消息区 OCR 结果中找到刚发送的文本。")
    bus.emit(run_id, "Verified", {"type": "MessageAppeared", "ok": True})


def _in_region(bbox: BBox, region: BBox) -> bool:
    return not (bbox.x2 < region.x1 or bbox.x1 > region.x2 or bbox.y2 < region.y1 or bbox.y1 > region.y2)


def _pick_element(elements: list[UiElement], label: str) -> UiElement | None:
    best = None
    best_score = -1.0
    for element in elements:
        if element.label != label:
            continue
        if element.score > best_score:
            best = element
            best_score = element.score
    return best