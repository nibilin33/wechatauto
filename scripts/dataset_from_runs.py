from __future__ import annotations

import argparse
import random
import shutil
from pathlib import Path


def iter_shots(runs_dir: Path) -> list[Path]:
    return sorted(runs_dir.glob("*/shots/*.png"))


def ensure_dataset_dirs(out: Path) -> None:
    (out / "images" / "train").mkdir(parents=True, exist_ok=True)
    (out / "images" / "val").mkdir(parents=True, exist_ok=True)
    (out / "labels" / "train").mkdir(parents=True, exist_ok=True)
    (out / "labels" / "val").mkdir(parents=True, exist_ok=True)


def write_data_yaml(out: Path, names: list[str]) -> None:
    lines = [
        f"path: {out.as_posix()}",
        "train: images/train",
        "val: images/val",
        "names:",
    ]
    for i, n in enumerate(names):
        lines.append(f"  {i}: {n}")
    (out / "data.yaml").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", default="runs", help="runs 目录（包含 <run_id>/shots/*.png）")
    parser.add_argument("--out", default="datasets/wechat_ui", help="输出数据集目录")
    parser.add_argument("--names", default="search,send", help="类别名列表，用逗号分隔（顺序决定 class_id）")
    parser.add_argument("--val-ratio", type=float, default=0.15, help="验证集比例")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--include",
        default="",
        help="只包含这些截图文件名（逗号分隔，如 search_contact,send_message；空表示全包含）",
    )
    args = parser.parse_args()

    runs_dir = Path(args.runs)
    out = Path(args.out)
    names = [n.strip() for n in args.names.split(",") if n.strip()]
    include = {n.strip() for n in args.include.split(",") if n.strip()}

    ensure_dataset_dirs(out)
    write_data_yaml(out, names)

    shots = iter_shots(runs_dir)
    if include:
        shots = [p for p in shots if p.stem in include]

    rnd = random.Random(args.seed)
    rnd.shuffle(shots)

    val_n = int(len(shots) * float(args.val_ratio))
    val_set = set(shots[:val_n])

    copied = {"train": 0, "val": 0}
    for p in shots:
        run_id = p.parent.parent.name  # runs/<run_id>/shots/<file>.png
        split = "val" if p in val_set else "train"
        dst_name = f"{run_id}__{p.name}"
        dst_img = out / "images" / split / dst_name
        dst_lbl = out / "labels" / split / (Path(dst_name).stem + ".txt")

        shutil.copy2(p, dst_img)
        dst_lbl.touch(exist_ok=True)
        copied[split] += 1

    print(f"wrote {out}/data.yaml with {len(names)} classes")
    print(f"copied images: train={copied['train']} val={copied['val']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

