"""Logging configuration for Awen Subtitle Engine"""

import logging
import sys
from pathlib import Path

from app.config import TEMP_DIR


def setup_logging(level: str = "INFO", log_file: str | None = None) -> logging.Logger:
    """
    Configure application-wide logging.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional path to a log file. Defaults to <TEMP_DIR>/ase.log.

    Returns:
        The root application logger.
    """
    log_level = getattr(logging, level.upper(), logging.INFO)

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)

    # File handler
    if log_file is None:
        log_dir = Path(TEMP_DIR)
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = str(log_dir / "ase.log")

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    # Root app logger
    logger = logging.getLogger("ase")
    logger.setLevel(logging.DEBUG)
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    # Silence noisy third-party loggers
    logging.getLogger("watchdog").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

    return logger


def get_logger(name: str) -> logging.Logger:
    """Get a child logger under the 'ase' namespace."""
    return logging.getLogger(f"ase.{name}")
