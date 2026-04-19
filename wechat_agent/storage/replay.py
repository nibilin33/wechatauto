from __future__ import annotations

"""
Offline replay: read a JSONL events file and re-run the perception pipeline
on every ScreenshotCaptured event, printing the resulting semantic state.

Usage:
    python -m wechat_agent.storage.replay --events runs/<run_id>/events.jsonl
"""

import argparse
import json
from pathlib import Path
from typing import Any


def load_events(path: str) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return events


def replay_perception(
    events_path: str,
    *,
    template_dir: str | None = None,
    yolo_model: str | None = None,
) -> None:
    from wechat_agent.core.events import EventBus, JsonlEventLogger
    from wechat_agent.perception.pipeline import default_template_dir, run_perception

    events = load_events(events_path)
    run_dir = str(Path(events_path).parent)

    bus = EventBus()
    replay_log = str(Path(run_dir) / "replay_events.jsonl")
    bus.subscribe(JsonlEventLogger(replay_log))

    run_id = "replay"
    tdir = template_dir or default_template_dir("macos")

    screenshot_events = [e for e in events if e.get("type") == "ScreenshotCaptured"]
    print(f"[replay] found {len(screenshot_events)} screenshots in {events_path}")

    for ev in screenshot_events:
        img_path = ev.get("payload", {}).get("path", "")
        if not img_path or not Path(img_path).exists():
            print(f"  [skip] {img_path!r} not found")
            continue
        print(f"  [perceive] {img_path}")
        result = run_perception(
            img_path,
            bus=bus,
            run_id=run_id,
            template_dir=tdir,
            yolo_model=yolo_model,
        )
        print(
            f"    page={result.semantic.page!r}  "
            f"title={result.semantic.chat_title!r}  "
            f"messages={len(result.semantic.messages)}  "
            f"anchors={list(result.semantic.anchors.keys())}"
        )

    print(f"[replay] done. events → {replay_log}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="wechatauto-replay")
    parser.add_argument("--events", required=True, help="JSONL events file path")
    parser.add_argument("--template-dir", default=None)
    parser.add_argument("--yolo-model", default=None)
    args = parser.parse_args(argv)
    replay_perception(args.events, template_dir=args.template_dir, yolo_model=args.yolo_model)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
