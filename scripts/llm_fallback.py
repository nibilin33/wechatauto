from __future__ import annotations

import argparse
import json


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", required=True)
    args = parser.parse_args()

    # Stub: implement your preferred vision LLM here and print JSON to stdout.
    # Output schema:
    # {"elements":[{"label":"send","score":0.9,"bbox":{"x1":...,"y1":...,"x2":...,"y2":...}}]}
    #
    # For safety, default to returning no elements.
    print(json.dumps({"elements": []}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

