from __future__ import annotations

"""
Structured logger that mirrors events to both the EventBus (JSONL) and
an optional human-readable text log.
"""

import logging
import sys
from pathlib import Path


def build_file_logger(run_dir: str, *, name: str = "wechatauto") -> logging.Logger:
    """
    Create a Logger that writes to <run_dir>/run.log and stdout.

    The logger uses the standard Python logging module so it works
    regardless of the event-bus state.
    """
    logger = logging.getLogger(f"{name}.{run_dir}")
    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    fmt = logging.Formatter("%(asctime)s  %(levelname)-7s  %(message)s", datefmt="%H:%M:%S")

    if not logger.handlers:
        # File handler
        log_path = Path(run_dir) / "run.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        fh = logging.FileHandler(log_path, encoding="utf-8")
        fh.setFormatter(fmt)
        logger.addHandler(fh)

        # Console handler
        ch = logging.StreamHandler(sys.stdout)
        ch.setFormatter(fmt)
        logger.addHandler(ch)

    return logger
