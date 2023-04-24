import logging
import sys
from enum import Enum
from typing import Optional, Dict, Literal

LOGGER = logging.getLogger("wemb.common")

LOG_HANDLERS: Dict[str, Optional[logging.Handler]] = {"color": None, "basic": None}


class LogColor(Enum):
    """An :class:`Enum` that holds some predefined ANSI color codes, used for logging."""

    def __str__(self) -> str:
        return self.value

    # Helpful reference site: https://ansi.gabebanks.net/

    RESET = "\x1b[0m"

    RED = "\x1b[31m"
    YELLOW = "\x1b[33m"
    MAGENTA = "\x1b[35m"
    CYAN = "\x1b[36m"
    WHITE = "\x1b[37m"

    RED_BG = "\x1b[37;41m"
    YELLOW_BG = "\x1b[30;43m"
    BLUE_BG = "\x1b[30;44m"


class BasicFormatter(logging.Formatter):
    """A :class:`logging.Formatter` that formats information without colors."""

    def __init__(self) -> None:
        super().__init__(
            "{asctime}  {name:<15}  {levelname:<8}:  {message}",
            datefmt="%Y-%m-%d %H:%M:%S",
            style="{",
        )


class FancyFormatter(logging.Formatter):
    """A :class:`logging.Formatter` that formats using fancy ANSI colors. Somewhat inspired by :class:`discord.utils._ColourFormatter`."""

    LEVEL_COLOURS = {
        logging.DEBUG: LogColor.BLUE_BG,
        logging.INFO: LogColor.CYAN,
        logging.WARNING: LogColor.YELLOW,
        logging.ERROR: LogColor.RED,
        logging.CRITICAL: LogColor.RED_BG,
    }

    # Represents the "true" padding for level name. Based on the longest, which is 'CRITICAL'.
    LEVELNAME_PADDING = 8

    def __init__(self) -> None:
        # Note that levelname_padding will be injected into record at format time.
        super().__init__(
            f"{LogColor.WHITE}{{asctime}}{LogColor.RESET}  {LogColor.MAGENTA}{{name:<15}}{LogColor.RESET}  {{levelname:<{{levelname_padding}}}}:  {{message}}",
            datefmt="%Y-%m-%d %H:%M:%S",
            style="{",
        )

    def format(self, record: logging.LogRecord) -> str:
        # Override the traceback to always print in red
        if record.exc_info:
            text = self.formatException(record.exc_info)
            record.exc_text = f"{LogColor.RED}{text}{LogColor.RESET}"

        # Get appropriate color code based on the level
        color_code = self.LEVEL_COLOURS.get(
            record.levelno, self.LEVEL_COLOURS[logging.DEBUG]
        )

        # Print ANSI color only for the length of text. Avoids printing background for padded strings
        record.levelname = f"{color_code}{record.levelname}{LogColor.RESET}"

        # Because of how terminals interpret ANSI codes with differing lengths, we have to dynamically choose the padding for level name.
        record.levelname_padding = (
            len(f"{color_code}{LogColor.RESET}") + self.LEVELNAME_PADDING
        )

        output = super().format(record)

        # Remove the cache layer
        record.exc_text = None
        return output


def __get_handler(handler_type: Literal["basic", "color"]) -> logging.Handler:
    """
    Lazily loads an instance of a :class:`logging.Handler`, for the specified type.

    :param handler_type: The type of the logger. Valid values are "basic" and "color".
    :return: A :class:`logging.Handler`, of the specified type in :param:`handler_type`
    """

    # Intentionally don't catch KeyError, to make it propagate
    if LOG_HANDLERS[handler_type] is None:
        LOG_HANDLERS[handler_type] = logging.StreamHandler(stream=sys.stdout)
        LOG_HANDLERS[handler_type].setFormatter(
            BasicFormatter() if handler_type.lower() == "basic" else FancyFormatter()
        )

    return LOG_HANDLERS[handler_type]


def setup_logging(
    package_name: Optional[str],
    *,
    log_level: int | str = logging.INFO,
    disable_color: bool = False,
) -> None:
    """
    Sets the logging configuration for the specified library/package. You should use this to set up root loggers for each used library.

    :param package_name: The package or library you want to set logging up for. Omit or pass `None` for the root logger.
    :param log_level: The log level. Defaults to logging.INFO
    :param disable_color: Disables colored log output.
    :return:
    """

    if log_level is None:
        log_level = logging.INFO

    if disable_color:
        handler = __get_handler("basic")
    else:
        handler = __get_handler("color")

    logger = logging.getLogger(package_name)
    logger.addHandler(handler)

    try:
        logger.setLevel(log_level)
    except ValueError:
        logger.setLevel(logging.INFO)
        logger.warning(f"Invalid log_level ({log_level})! Defaulting to INFO...")
