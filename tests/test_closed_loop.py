import unittest

from wechat_agent.actions.closed_loop import send_message, verify_sent
from wechat_agent.core.errors import VerificationFailed
from wechat_agent.core.models import BBox, SemanticState, UiTextBlock
from wechat_agent.perception.layout import Layout


class _Bus:
    def __init__(self) -> None:
        self.events = []

    def emit(self, run_id, name, payload) -> None:
        self.events.append((run_id, name, payload))


class _Driver:
    def __init__(self) -> None:
        self.elements = []
        self.layout = None
        self.semantic = None
        self.calls = []

    def click_norm(self, x: float, y: float) -> None:
        self.calls.append(("click_norm", x, y))

    def paste_text(self, text: str) -> None:
        self.calls.append(("paste_text", text))

    def key_combo(self, combo: str) -> None:
        self.calls.append(("key_combo", combo))

    def press_key(self, key: str) -> None:
        self.calls.append(("press_key", key))

    def sleep(self, seconds: float) -> None:
        self.calls.append(("sleep", seconds))


def _bbox(x1: float, y1: float, x2: float, y2: float) -> BBox:
    return BBox(x1=x1, y1=y1, x2=x2, y2=y2)


def _layout() -> Layout:
    return Layout(
        sidebar=_bbox(0.0, 0.0, 0.25, 1.0),
        sidebar_top=_bbox(0.0, 0.0, 0.25, 0.15),
        chat=_bbox(0.25, 0.0, 1.0, 1.0),
        chat_header=_bbox(0.25, 0.0, 1.0, 0.12),
        chat_messages=_bbox(0.25, 0.12, 1.0, 0.8),
        chat_composer=_bbox(0.25, 0.8, 1.0, 1.0),
        confidence=1.0,
    )


class TestClosedLoopActions(unittest.TestCase):
    def test_send_message_clicks_detected_send_button(self):
        driver = _Driver()
        driver.layout = _layout()
        send_button = _bbox(0.88, 0.9, 0.96, 0.96)
        driver.semantic = SemanticState(
            page="chat",
            chat_title="Alice",
            messages=[],
            elements=[],
            texts=[],
            anchors={"send_button": send_button},
            confidence=1.0,
        )

        send_message(driver, run_id="run-1", bus=_Bus(), text="测试消息", blocks=[])

        self.assertIn(("paste_text", "测试消息"), driver.calls)
        click_calls = [call for call in driver.calls if call[0] == "click_norm"]
        self.assertEqual(2, len(click_calls))
        self.assertAlmostEqual(0.625, click_calls[0][1])
        self.assertAlmostEqual(0.85, click_calls[0][2])
        self.assertAlmostEqual(0.92, click_calls[1][1])
        self.assertAlmostEqual(0.93, click_calls[1][2])
        self.assertNotIn(("key_combo", "cmd+return"), driver.calls)

    def test_send_message_uses_enter_when_detection_missing(self):
        driver = _Driver()
        driver.layout = _layout()

        send_message(driver, run_id="run-1", bus=_Bus(), text="测试消息", blocks=[])

        self.assertIn(("paste_text", "测试消息"), driver.calls)
        click_calls = [call for call in driver.calls if call[0] == "click_norm"]
        self.assertEqual(1, len(click_calls))
        self.assertAlmostEqual(0.625, click_calls[0][1])
        self.assertAlmostEqual(0.85, click_calls[0][2])
        self.assertNotIn(("key_combo", "cmd+return"), driver.calls)
        self.assertIn(("press_key", "return"), driver.calls)

    def test_verify_sent_accepts_fragmented_ocr_blocks(self):
        driver = _Driver()
        driver.layout = _layout()
        bus = _Bus()
        blocks = [
            UiTextBlock(bbox=_bbox(0.4, 0.4, 0.42, 0.43), text="测", score=0.9),
            UiTextBlock(bbox=_bbox(0.43, 0.4, 0.45, 0.43), text="试", score=0.9),
            UiTextBlock(bbox=_bbox(0.46, 0.4, 0.48, 0.43), text="消息", score=0.9),
        ]

        verify_sent(driver, run_id="run-1", bus=bus, text="测试消息", blocks=blocks)

        self.assertIn(("run-1", "Verified", {"type": "MessageAppeared", "ok": True}), bus.events)

    def test_verify_sent_raises_when_text_missing(self):
        driver = _Driver()
        driver.layout = _layout()
        blocks = [UiTextBlock(bbox=_bbox(0.4, 0.4, 0.5, 0.45), text="别的内容", score=0.9)]

        with self.assertRaises(VerificationFailed):
            verify_sent(driver, run_id="run-1", bus=_Bus(), text="测试消息", blocks=blocks)


if __name__ == "__main__":
    unittest.main()