import argparse
import signal
import sys
from time import sleep

from bot import run_bot
from common import get_logger

LOGGER = get_logger("wemb.main")


def __signal_handler(signum, frame):
    LOGGER.info("SIGINT/SIGTERM Captured! Exiting...")
    sleep(1)
    sys.exit(0)


def main():
    parser = argparse.ArgumentParser(
        prog="r/Watchexchange Monitor Bot",
        description="Monitors r/Watchexchange for items that match specific criteria",
        epilog="https://github.com/Tardnicus/watch-exchange-bot",
    )

    parser.add_argument("-f", "--config-file", default="config.yaml")

    args = parser.parse_args()

    # Set signal handler for Ctrl+C and SIGTERM
    # TODO: Improve signal handling
    signal.signal(signal.SIGINT, __signal_handler)
    signal.signal(signal.SIGTERM, __signal_handler)

    run_bot()


if __name__ == "__main__":
    main()
