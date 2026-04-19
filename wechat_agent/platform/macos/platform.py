from __future__ import annotations

from pathlib import Path

from wechat_agent.core.errors import PlatformNotImplemented
from wechat_agent.actions.closed_loop import (
    open_chat,
    read_recent,
    search_contact,
    send_message,
    verify_sent,
)
from wechat_agent.platform.macos.screen import capture_wechat_window
from wechat_agent.platform.macos.input import click_norm, key_combo, paste_text, press_key, sleep
from wechat_agent.platform.macos.window import locate_wechat_window
from wechat_agent.perception.pipeline import default_template_dir, run_perception


class MacOSPlatform:
    name = "macos"

    def __init__(self, run_dir: str | None = None, config=None) -> None:
        self._run_dir = run_dir
        self._config = config

    def dispatch(self, action_name: str, params: dict, *, bus, run_id: str) -> None:
        bus.emit(run_id, "PlatformDispatch", {"platform": self.name, "action": action_name, "params": params})

        window = locate_wechat_window()
        bus.emit(
            run_id,
            "WindowLocated",
            {
                "platform": self.name,
                "native_id": window.native_id,
                "title": window.title,
                "x": window.x,
                "y": window.y,
                "width": window.width,
                "height": window.height,
                "scale": window.scale,
            },
        )

        if self._run_dir:
            shots_dir = Path(self._run_dir) / "shots"
            shots_dir.mkdir(parents=True, exist_ok=True)
            path = str(shots_dir / f"{action_name}.png")
            cap = capture_wechat_window(window, path)
            bus.emit(
                run_id,
                "ScreenshotCaptured",
                {"path": path, "platform": self.name, "native_id": window.native_id, **cap},
            )
        else:
            path = ""

        def driver():  # noqa: ANN202
            # Bind window into a tiny driver interface expected by actions.
            class _Driver:
                def __init__(self) -> None:
                    self.elements = []
                    self.layout = None
                    self.semantic = None

                def click_norm(self, x: float, y: float) -> None:
                    click_norm(window, x, y)

                def paste_text(self, text: str) -> None:
                    paste_text(text)

                def key_combo(self, combo: str) -> None:
                    key_combo(combo)

                def press_key(self, key: str) -> None:
                    press_key(key)

                def sleep(self, seconds: float) -> None:
                    sleep(seconds)

            return _Driver()

        drv = driver()
        perception_cache = None

        def get_perception():  # noqa: ANN202
            nonlocal perception_cache
            if perception_cache is None:
                template_dir = default_template_dir("macos")
                yolo_model = getattr(self._config, "yolo_model", None)
                llm_cmd = getattr(self._config, "llm_fallback_cmd", None)
                vlm_provider = getattr(self._config, "vlm_provider", None)
                openai_model = getattr(self._config, "openai_model", None)
                qwen_model = getattr(self._config, "qwen_model", None)
                qwen_base_url = getattr(self._config, "qwen_base_url", None)
                perception_cache = run_perception(
                    path,
                    bus=bus,
                    run_id=run_id,
                    template_dir=template_dir,
                    yolo_model=yolo_model,
                    llm_fallback_cmd=llm_cmd,
                    vlm_provider=vlm_provider,
                    openai_model=openai_model,
                    qwen_model=qwen_model,
                    qwen_base_url=qwen_base_url,
                    artifacts_dir=str(Path(self._run_dir) / "vlm") if self._run_dir else None,
                    require_labels={"search", "send"},
                )
            return perception_cache

        drv.elements = get_perception().elements
        drv.layout = get_perception().layout
        drv.semantic = get_perception().semantic

        if action_name == "search_contact":
            return search_contact(drv, run_id=run_id, bus=bus, name=params["name"], blocks=get_perception().texts)
        if action_name == "open_chat":
            return open_chat(drv, run_id=run_id, bus=bus, name=params["name"])
        if action_name == "read_recent":
            return read_recent(drv, run_id=run_id, bus=bus, n=int(params["n"]), blocks=get_perception().texts)
        if action_name == "send_message":
            return send_message(drv, run_id=run_id, bus=bus, text=params["text"], blocks=get_perception().texts)
        if action_name == "verify_sent":
            # capture a fresh screenshot for verification if we have a run dir
            if self._run_dir:
                verify_path = str((Path(self._run_dir) / "shots") / f"{action_name}_after.png")
                cap2 = capture_wechat_window(window, verify_path)
                bus.emit(
                    run_id,
                    "ScreenshotCaptured",
                    {"path": verify_path, "platform": self.name, "native_id": window.native_id, **cap2},
                )
                template_dir = default_template_dir("macos")
                yolo_model = getattr(self._config, "yolo_model", None)
                llm_cmd = getattr(self._config, "llm_fallback_cmd", None)
                vlm_provider = getattr(self._config, "vlm_provider", None)
                openai_model = getattr(self._config, "openai_model", None)
                qwen_model = getattr(self._config, "qwen_model", None)
                qwen_base_url = getattr(self._config, "qwen_base_url", None)
                p2 = run_perception(
                    verify_path,
                    bus=bus,
                    run_id=run_id,
                    template_dir=template_dir,
                    yolo_model=yolo_model,
                    llm_fallback_cmd=llm_cmd,
                    vlm_provider=vlm_provider,
                    openai_model=openai_model,
                    qwen_model=qwen_model,
                    qwen_base_url=qwen_base_url,
                    artifacts_dir=str(Path(self._run_dir) / "vlm") if self._run_dir else None,
                    require_labels={"search", "send"},
                )
                blocks2 = p2.texts
            else:
                blocks2 = get_perception().texts
            return verify_sent(drv, run_id=run_id, bus=bus, text=params["text"], blocks=blocks2)

        raise PlatformNotImplemented(f"macOS 动作未实现：{action_name}")
