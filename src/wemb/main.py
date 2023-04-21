from logging import Logger
from typing import Optional

import configargparse

from bot import run_bot
from common import get_logger

LOGGER: Optional[Logger] = None


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
        "--allow-dirty-shutdown",
        default=False,
        action="store_true",
        help="Allows dirty/messy shutdowns when asyncio event handlers are not supported.",
        env_var="WEMB_ALLOW_DIRTY_SHUTDOWN",
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

    args = parser.parse_args()

    LOGGER = get_logger("wemb.main")

    LOGGER.info("Initialized!")

    # Run main bot process. After ready, it spawns an event loop for submission scanning.
    run_bot(args)


if __name__ == "__main__":
    main()
