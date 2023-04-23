import logging

import configargparse

from bot import run_bot
from common import setup_logging

LOGGER = logging.getLogger("wemb.main")


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

    # Program settings
    parser.add_argument(
        "--allow-dirty-shutdown",
        default=False,
        action="store_true",
        help="Allows dirty/messy shutdowns when asyncio event handlers are not supported.",
        env_var="WEMB_ALLOW_DIRTY_SHUTDOWN",
    )

    # Authentication info
    parser.add_argument(
        "--discord-api-token",
        required=True,
        help="Discord API token, used for authenticating the bot process.",
        env_var="DISCORD_API_TOKEN",
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

    # Log levels
    parser.add_argument(
        "--wemb-log-level",
        default=logging.INFO,
        help="Logging level of this program. Defaults to INFO",
        env_var="WEMB_LOGLEVEL",
    )
    parser.add_argument(
        "--discord-log-level",
        default=logging.INFO,
        help="Logging level of the used discord library. Defaults to INFO.",
        env_var="DISCORD_LOGLEVEL",
    )
    parser.add_argument(
        "--praw-log-level",
        default=logging.INFO,
        help="Logging level of the used asyncpraw library. Defaults to INFO",
        env_var="PRAW_LOGLEVEL",
    )

    args = parser.parse_args()

    # Set up logging for all package roots available.
    setup_logging("wemb", log_level=args.wemb_log_level)
    setup_logging("discord", log_level=args.discord_log_level)
    setup_logging("asyncpraw", log_level=args.praw_log_level)
    setup_logging("asyncprawcore", log_level=args.praw_log_level)

    LOGGER.info("Initialized!")

    # Run main bot process. After ready, it spawns an event loop for submission scanning.
    run_bot(args)


if __name__ == "__main__":
    main()
