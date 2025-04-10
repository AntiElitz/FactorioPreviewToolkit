# shared/structured_logger.py

import logging
import sys
import threading
from contextlib import contextmanager
from io import TextIOWrapper

# Thread-local storage for nesting level (per thread)
_nesting = threading.local()


def get_logging_indent() -> str:
    level = getattr(_nesting, "level", 0)
    if level == 0:
        return ""
    return "   " * level  # Indentation string


@contextmanager
def log_section(title: str):
    if not hasattr(_nesting, "level"):
        _nesting.level = 0

    log.info(title)
    _nesting.level += 1
    try:
        yield
    finally:
        _nesting.level = max(0, _nesting.level - 1)


def set_logging_indent(level: int):
    if not hasattr(_nesting, "level"):
        _nesting.level = 0
    _nesting.level = max(0, level)


class IndentedFormatter(logging.Formatter):
    def format(self, record):
        pid_part = f"PID:{record.process:>5}"
        thread_part = f"{record.threadName}"
        tag = f"[{pid_part}, {thread_part}]"
        level = f"{record.levelname:<5}"

        prefix = get_logging_indent()
        original_msg = super().format(record)
        message = record.getMessage()

        formatted_msg = f"{record.asctime} {tag:<30} {level}: {message}"
        if prefix and record.levelno >= logging.INFO:
            return formatted_msg.replace(message, f"{prefix}{message}")
        return formatted_msg


def setup_logger() -> logging.Logger:
    # Ensure UTF-8 encoding for stdout/stderr
    if sys.stdout.encoding is None or sys.stdout.encoding.lower() != "utf-8":
        sys.stdout = TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    if sys.stderr.encoding is None or sys.stderr.encoding.lower() != "utf-8":
        sys.stderr = TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

    formatter = IndentedFormatter(
        "%(asctime)s [PID:%(process)d, %(threadName)s] %(levelname)s: %(message)s"
    )

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)

    logger = logging.getLogger("structured_logger")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    logger.addHandler(stream_handler)
    logger.propagate = False

    return logger


log = setup_logger()
