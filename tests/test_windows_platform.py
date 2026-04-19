import unittest

from wechat_agent.core.errors import PlatformNotImplemented
from wechat_agent.platform.windows.platform import WindowsPlatform


class _Bus:
    def __init__(self) -> None:
        self.events = []

    def emit(self, run_id, name, payload) -> None:
        self.events.append((run_id, name, payload))


class _Controller:
    def __init__(self) -> None:
        self.calls = []

    def locate_window(self) -> dict:
        self.calls.append(("locate_window",))
        return {
            "platform": "windows",
            "native_id": "42",
            "title": "微信",
            "x": 10,
            "y": 20,
            "width": 800,
            "height": 600,
            "scale": 1.0,
        }

    def search_contact(self, name: str) -> None:
        self.calls.append(("search_contact", name))

    def open_chat(self, name: str) -> None:
        self.calls.append(("open_chat", name))

    def read_recent(self, n: int) -> list[str]:
        self.calls.append(("read_recent", n))
        return ["hi", "latest"][-n:]

    def send_message(self, text: str) -> None:
        self.calls.append(("send_message", text))

    def verify_sent(self, text: str) -> None:
        self.calls.append(("verify_sent", text))


class _WindowsPlatformForTest(WindowsPlatform):
    def __init__(self, controller) -> None:
        super().__init__(run_dir=None, config=None)
        self._test_controller = controller

    def _build_controller(self):
        return self._test_controller


class TestWindowsPlatform(unittest.TestCase):
    def test_dispatch_routes_search_contact(self):
        controller = _Controller()
        platform = _WindowsPlatformForTest(controller)
        bus = _Bus()

        platform.dispatch("search_contact", {"name": "Alice"}, bus=bus, run_id="run-1")

        self.assertIn(("search_contact", "Alice"), controller.calls)
        self.assertEqual("PlatformDispatch", bus.events[0][1])
        self.assertEqual("WindowLocated", bus.events[1][1])

    def test_dispatch_emits_recent_messages(self):
        controller = _Controller()
        platform = _WindowsPlatformForTest(controller)
        bus = _Bus()

        platform.dispatch("read_recent", {"n": 2}, bus=bus, run_id="run-1")

        self.assertIn(("read_recent", 2), controller.calls)
        self.assertEqual(("run-1", "RecentMessagesRead", {"n": 2, "lines": ["hi", "latest"]}), bus.events[-1])

    def test_dispatch_emits_verified_after_verify_sent(self):
        controller = _Controller()
        platform = _WindowsPlatformForTest(controller)
        bus = _Bus()

        platform.dispatch("verify_sent", {"text": "测试消息"}, bus=bus, run_id="run-1")

        self.assertIn(("verify_sent", "测试消息"), controller.calls)
        self.assertEqual(("run-1", "Verified", {"type": "MessageAppeared", "ok": True}), bus.events[-1])

    def test_dispatch_rejects_unknown_action(self):
        controller = _Controller()
        platform = _WindowsPlatformForTest(controller)

        with self.assertRaises(PlatformNotImplemented):
            platform.dispatch("unknown", {}, bus=_Bus(), run_id="run-1")


if __name__ == "__main__":
    unittest.main()