import logging
import os
import sys
from typing import Optional

from sqlalchemy import Engine, create_engine

ENGINE: Optional[Engine] = None


def get_logger(package_name: str) -> logging.Logger:
    """Sets basic logging configuration and returns the logger for this module. Reads an env var called WEMB_LOGLEVEL to set the log level"""
    if package_name is None:
        raise ValueError("package_name must be specified!")

    # TODO: fix logging configuration
    logging.basicConfig(
        stream=sys.stdout,
        format="{asctime} - {name:<12} {levelname:<8}:  {message}",
        style="{",
    )

    # Get log level from env var
    log_level = os.environ.get("WEMB_LOGLEVEL") or logging.DEBUG

    logger = logging.getLogger(package_name)

    try:
        logger.setLevel(log_level)
    except ValueError:
        logger.setLevel(logging.DEBUG)
        logger.warning(f"Invalid WEMB_LOGLEVEL ({log_level})! Defaulting to DEBUG...")

    return logger


def get_engine() -> Engine:
    """Gets the database engine used by this program, and creates it if necessary."""
    global ENGINE

    if ENGINE is None:
        # TODO: Extract URL string
        ENGINE = create_engine("sqlite:///test.db")
        get_logger("wemb.common").info("created engine")

    return ENGINE
