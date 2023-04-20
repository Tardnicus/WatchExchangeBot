import signal
import sys
from logging import Logger
from time import sleep
from typing import Optional

import configargparse

from bot import run_bot
from common import get_logger, set_log_level

LOGGER: Optional[Logger] = None


def __signal_handler(signum, frame):
    LOGGER.info("SIGINT/SIGTERM Captured! Exiting...")
    sleep(1)
    sys.exit(0)


def main():
    global LOGGER

    parser = configargparse.ArgumentParser(
        prog="r/Watchexchange Monitor Bot",
        description="Monitors r/Watchexchange for items that match specific criteria",
        epilog="https://github.com/Tardnicus/watch-exchange-bot",
    )

    # TODO: Remove webhook url and mention string
    parser.add_argument(
        "--webhook-url",
        required=True,
        help="A webhook URL in the form of https://discord.com/api/webhooks/<id>/<token>.",
        env_var="WEMB_WEBHOOK_URL",
    )
    parser.add_argument(
        "--mention-string",
        required=True,
        help="A mention string in the form of <@&role_id>. Use '<@&role_id>' for roles, and '<@user_id>' for specific users.",
        env_var="WEMB_MENTION_STRING",
    )
    parser.add_argument(
        "--discord-api-token",
        required=True,
        help="A discord API token, used for authenticating the bot process.",
        env_var="WEMB_DISCORD_API_TOKEN",
    )
    parser.add_argument(
        "--praw-client-id",
        required=True,
        help="Client ID, used for authenticating with Reddit",
        env_var="PRAW_CLIENT_ID",
    )
    parser.add_argument(
        "--praw-client-secret",
        required=True,
        help="Client secret, used for authenticating with Reddit",
        env_var="PRAW_CLIENT_SECRET",
    )
    parser.add_argument(
        "--praw-user-agent",
        required=True,
        help="User agent, used for identification with Reddit",
        env_var="PRAW_USER_AGENT",
    )
    parser.add_argument(
        "-l",
        "--log-level",
        default="INFO",
        help="The logging level of the application. Must be one of the levels specified in https://docs.python.org/3.10/library/logging.html#logging-levels.",
        choices=[
            "CRITICAL",
            "ERROR",
            "WARNING",
            "INFO",
            "DEBUG",
            "NOTSET",
        ],
        env_var="WEMB_LOGLEVEL",
    )

    args = parser.parse_args()

    set_log_level(args.log_level)
    LOGGER = get_logger("wemb.main")

    LOGGER.info("Initialized!")

    # Set signal handler for Ctrl+C and SIGTERM
    # TODO: Improve signal handling
    signal.signal(signal.SIGINT, __signal_handler)
    signal.signal(signal.SIGTERM, __signal_handler)

    # Run main bot process. After ready, it spawns an event loop for submission scanning.
    run_bot(args)


if __name__ == "__main__":
    main()
