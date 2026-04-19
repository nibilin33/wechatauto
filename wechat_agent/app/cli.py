from __future__ import annotations

import argparse
from pathlib import Path

from wechat_agent.app.config import AppConfig
from wechat_agent.core.runner import run_once


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="wechatauto")
    parser.add_argument("--platform", default="auto", choices=["auto", "macos", "windows", "noop"])
    parser.add_argument("--contact", required=True, help="联系人或群名（用于搜索/打开会话）")
    parser.add_argument("--recent", type=int, default=5, help="读取最近 N 条消息")
    parser.add_argument("--message", default="(test) hello", help="要发送的固定测试消息")
    parser.add_argument(
        "--send",
        action="store_true",
        help="实际发送消息（默认只跑闭环到发送前，便于安全验证）",
    )
    parser.add_argument("--run-dir", default=None, help="运行输出目录（默认 runs/<run_id>）")
    parser.add_argument("--yolo-model", default=None, help="YOLO UI 检测模型路径（.pt/.onnx，可选）")
    parser.add_argument(
        "--llm-fallback-cmd",
        default=None,
        help="大模型兜底命令（可选；需输出 elements JSON；可用 {image_path} 占位）",
    )
    parser.add_argument(
        "--vlm-provider",
        default="auto",
        choices=["auto", "none", "cmd", "openai", "qwen"],
        help="VLM 兜底提供方：openai/qwen/cmd/none（auto：有 --llm-fallback-cmd 则 cmd，否则 none）",
    )
    parser.add_argument("--openai-model", default=None, help="OpenAI 视觉模型（例如 gpt-4.1-mini）")
    parser.add_argument("--qwen-model", default=None, help="Qwen-VL 模型（例如 qwen2.5-vl-7b-instruct）")
    parser.add_argument(
        "--qwen-base-url",
        default=None,
        help="DashScope OpenAI 兼容 base_url（默认 https://dashscope.aliyuncs.com/compatible-mode/v1）",
    )
    parser.add_argument(
        "--whitelist",
        default=None,
        help="允许发送的联系人/群名，逗号分隔（空则不限制）",
    )
    parser.add_argument(
        "--cooldown",
        type=float,
        default=30.0,
        help="同一联系人两次发送的最短间隔（秒，默认 30）",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    whitelist = tuple(w.strip() for w in (args.whitelist or "").split(",") if w.strip())
    config = AppConfig(
        platform=args.platform,
        contact_name=args.contact,
        recent_n=args.recent,
        message=args.message,
        send=bool(args.send),
        run_dir=args.run_dir,
        yolo_model=args.yolo_model,
        llm_fallback_cmd=args.llm_fallback_cmd,
        vlm_provider=args.vlm_provider,
        openai_model=args.openai_model,
        qwen_model=args.qwen_model,
        qwen_base_url=args.qwen_base_url,
        whitelist=whitelist,
        cooldown_seconds=float(args.cooldown),
    )
    run_dir, exit_code = run_once(config)
    print(str(Path(run_dir).resolve()))
    return exit_code
