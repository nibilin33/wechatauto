from __future__ import annotations

"""Windows WeChat automation via UI Automation.

WeChat 4.1+ may hide its internal UIA tree unless Windows Narrator has been
enabled before login. When that happens, the main window is visible but the
search box, session list, and chat input are not exposed to UI Automation.
"""

import time

from wechat_agent.core.errors import ActionFailed, PlatformNotImplemented, VerificationFailed


_WECHAT_UIA_HINT = (
    "微信 4.1+ 可能默认屏蔽内部 UIA 树。若窗口存在但搜索框、会话列表或输入框不可见，"
    "请在登录微信前先开启 Windows 讲述人（Narrator），保持一段时间后再关闭，然后重试。"
)


def _load_uiautomation():
    try:
        import uiautomation as auto  # type: ignore[import-not-found]
    except ImportError as exc:  # pragma: no cover - exercised on Windows only
        raise ActionFailed(
            "Windows 平台依赖缺失：请安装 uiautomation（例如 `pip install uiautomation`）。"
        ) from exc
    return auto


class _WindowsWeChatController:
    def __init__(self) -> None:
        self._auto = _load_uiautomation()
        self._last_contact: str | None = None

    def locate_window(self) -> dict:
        window = self._get_wechat_window()
        rect = self._rect_tuple(window)
        return {
            "platform": "windows",
            "native_id": str(getattr(window, "NativeWindowHandle", "")),
            "title": self._text_of(getattr(window, "Name", "")) or "微信",
            "x": rect[0] if rect is not None else 0,
            "y": rect[1] if rect is not None else 0,
            "width": rect[2] - rect[0] if rect is not None else 0,
            "height": rect[3] - rect[1] if rect is not None else 0,
            "scale": 1.0,
        }

    def search_contact(self, contact_name: str) -> None:
        if self._activate_from_session_list(contact_name):
            self._last_contact = contact_name
            return

        window = self._get_wechat_window()
        self._activate_window(window)
        search_box = self._find_search_box(window)
        if search_box is None:
            raise ActionFailed(f"Windows UIA 未找到微信搜索框。{_WECHAT_UIA_HINT}")

        search_box.Click()
        time.sleep(0.2)
        search_box.SendKeys("{Ctrl}a")
        time.sleep(0.1)

        if self._set_clipboard_text(contact_name):
            search_box.SendKeys("{Ctrl}v")
        else:
            search_box.SendKeys(self._escape_sendkeys(contact_name), interval=0.01)
        time.sleep(0.8)
        self._last_contact = contact_name

    def open_chat(self, contact_name: str) -> None:
        if self._activate_from_session_list(contact_name):
            self._last_contact = contact_name
            return

        window = self._get_wechat_window()
        self._activate_window(window)
        search_box = self._find_search_box(window)
        if search_box is not None:
            search_box.SendKeys("{Enter}")
        else:
            self._auto.SendKeys("{Enter}", waitTime=0.1)
        time.sleep(0.8)
        self._last_contact = contact_name

    def read_recent(self, n: int) -> list[str]:
        window = self._get_wechat_window()
        rect = self._rect_tuple(window)
        if rect is None:
            return []

        left, top, right, bottom = rect
        width = max(1, right - left)
        height = max(1, bottom - top)
        min_x = left + width * 0.33
        min_y = top + height * 0.10
        max_y = top + height * 0.82

        entries: list[tuple[int, int, str]] = []
        seen: set[tuple[str, int, int]] = set()
        for control in self._walk_controls(window, max_depth=12):
            text = self._text_of(getattr(control, "Name", ""))
            if not text or len(text) > 500:
                continue
            if text in {"微信", "WeChat", "搜索", "Search", "发送", "Send"}:
                continue
            if self._last_contact is not None and text == self._last_contact:
                continue

            box = self._rect_tuple(control)
            if box is None:
                continue
            c_left, c_top, c_right, _ = box
            center_x = (c_left + c_right) / 2.0
            if center_x < min_x or c_top < min_y or c_top > max_y:
                continue

            key = (text, round(c_top / 6), round(c_left / 6))
            if key in seen:
                continue
            seen.add(key)
            entries.append((c_top, c_left, text))

        entries.sort(key=lambda item: (item[0], item[1]))
        lines = [text for _, _, text in entries]
        lines = self._dedupe_preserving_order(lines)
        return lines[-n:] if n > 0 else []

    def send_message(self, message: str) -> None:
        window = self._get_wechat_window()
        self._activate_window(window)
        chat_edit = self._find_chat_input(window)
        if chat_edit is None:
            raise ActionFailed(f"Windows UIA 未找到微信聊天输入框。{_WECHAT_UIA_HINT}")

        chat_edit.Click()
        time.sleep(0.2)

        if self._set_clipboard_text(message):
            chat_edit.SendKeys("{Ctrl}v")
            time.sleep(0.2)
            chat_edit.SendKeys("{Enter}")
        else:
            escaped_message = self._escape_sendkeys(message)
            formatted_message = escaped_message.replace("\n", "{Shift}{Enter}")
            chat_edit.SendKeys(formatted_message + "{Enter}", interval=0.01)
        time.sleep(0.3)

    def verify_sent(self, text: str) -> None:
        lines = self.read_recent(20)
        joined_tight = "".join(lines)
        joined_loose = "\n".join(lines)
        if text not in joined_tight and text not in joined_loose:
            raise VerificationFailed(
                f"Windows UIA 校验失败：未在最近消息中找到刚发送的文本。{_WECHAT_UIA_HINT}"
            )

    def _get_wechat_window(self):
        candidates = [
            self._auto.WindowControl(searchDepth=1, Name="微信", ClassName="mmui::MainWindow"),
            self._auto.WindowControl(searchDepth=1, Name="WeChat", ClassName="mmui::MainWindow"),
            self._auto.WindowControl(searchDepth=1, ClassName="mmui::MainWindow"),
        ]
        for window in candidates:
            if window.Exists(0, 0):
                return window

        self._auto.SendKeys("{Ctrl}{Alt}w", waitTime=0.1)
        time.sleep(1.0)
        for window in candidates:
            if window.Exists(0, 0):
                return window
        raise ActionFailed(f"未找到微信窗口，请确认微信已启动且窗口可见。{_WECHAT_UIA_HINT}")

    def _activate_from_session_list(self, contact_name: str) -> bool:
        try:
            window = self._get_wechat_window()
            self._activate_window(window)
            session_item = window.Control(
                ClassName="mmui::ChatSessionCell",
                AutomationId=f"session_item_{contact_name}",
                searchDepth=15,
            )
            if not session_item.Exists(0, 0):
                return False
            if self._is_session_selected(session_item):
                return True
            session_item.Click()
            time.sleep(0.3)
            return self._is_session_selected(session_item)
        except Exception:
            return False

    def _is_session_selected(self, session_item) -> bool:
        try:
            pattern = session_item.GetPattern(10010)
            return bool(pattern and getattr(pattern, "IsSelected", False))
        except Exception:
            return False

    def _find_search_box(self, window):
        candidates = [
            window.EditControl(Name="搜索"),
            window.EditControl(Name="Search"),
            window.EditControl(searchDepth=12, Name="搜索"),
            window.EditControl(searchDepth=12, Name="Search"),
        ]
        for control in candidates:
            if control.Exists(0, 0):
                return control
        return None

    def _find_chat_input(self, window):
        candidates = [
            window.EditControl(foundIndex=1),
            window.EditControl(searchDepth=20, foundIndex=1),
            window.EditControl(searchDepth=20),
        ]
        for control in candidates:
            if control.Exists(0, 0):
                return control
        return None

    def _activate_window(self, window) -> None:
        try:
            window.SetActive()
        except Exception:
            pass
        time.sleep(0.2)

    def _set_clipboard_text(self, text: str, max_retries: int = 3) -> bool:
        for _ in range(max_retries):
            try:
                self._auto.SetClipboardText(text)
                time.sleep(0.05)
                if self._auto.GetClipboardText() == text:
                    return True
            except Exception:
                pass
            time.sleep(0.1)
        return False

    def _walk_controls(self, control, *, max_depth: int, depth: int = 0):
        if depth >= max_depth:
            return
        try:
            children = control.GetChildren()
        except Exception:
            children = []
        for child in children:
            yield child
            yield from self._walk_controls(child, max_depth=max_depth, depth=depth + 1)

    @staticmethod
    def _text_of(value) -> str:
        return str(value or "").strip()

    @staticmethod
    def _dedupe_preserving_order(lines: list[str]) -> list[str]:
        out: list[str] = []
        for line in lines:
            if not out or out[-1] != line:
                out.append(line)
        return out

    @staticmethod
    def _escape_sendkeys(text: str) -> str:
        return text.replace("{", "{{").replace("}", "}}")

    @staticmethod
    def _rect_tuple(control) -> tuple[int, int, int, int] | None:
        rect = getattr(control, "BoundingRectangle", None)
        if rect is None:
            return None
        left = getattr(rect, "left", getattr(rect, "Left", None))
        top = getattr(rect, "top", getattr(rect, "Top", None))
        right = getattr(rect, "right", getattr(rect, "Right", None))
        bottom = getattr(rect, "bottom", getattr(rect, "Bottom", None))
        if None in (left, top, right, bottom):
            return None
        return int(left), int(top), int(right), int(bottom)


class WindowsPlatform:
    name = "windows"

    def __init__(self, run_dir: str | None = None, config=None) -> None:
        self._run_dir = run_dir
        self._config = config
        self._controller = None

    def _build_controller(self):
        return _WindowsWeChatController()

    def _get_controller(self):
        if self._controller is None:
            self._controller = self._build_controller()
        return self._controller

    def dispatch(self, action_name: str, params: dict, *, bus, run_id: str) -> None:
        bus.emit(run_id, "PlatformDispatch", {"platform": self.name, "action": action_name, "params": params})
        controller = self._get_controller()
        bus.emit(run_id, "WindowLocated", controller.locate_window())

        if action_name == "search_contact":
            controller.search_contact(params["name"])
            return
        if action_name == "open_chat":
            controller.open_chat(params["name"])
            return
        if action_name == "read_recent":
            lines = controller.read_recent(int(params["n"]))
            bus.emit(run_id, "RecentMessagesRead", {"n": int(params["n"]), "lines": lines})
            return
        if action_name == "send_message":
            controller.send_message(params["text"])
            return
        if action_name == "verify_sent":
            controller.verify_sent(params["text"])
            bus.emit(run_id, "Verified", {"type": "MessageAppeared", "ok": True})
            return
        raise PlatformNotImplemented(f"Windows 动作未实现：{action_name}")
