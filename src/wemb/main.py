import argparse
import logging
import os
import re
import signal
import sys
from enum import Enum, unique
from pathlib import Path
from time import sleep
from typing import List, Optional, Union

import praw
import requests
import yaml
from praw import Reddit
from praw.models import Submission
from sqlalchemy import create_engine

# TODO: Extract URL string
engine = create_engine("sqlite:///test.db", echo=True)


def __get_logger() -> logging.Logger:
    """Sets basic logging configuration and returns the logger for this module. Reads an env var called WEMB_LOGLEVEL to set the log level"""
    logging.basicConfig(
        stream=sys.stdout,
        format="{asctime} - {name:<12} {levelname:<8}:  {message}",
        style="{",
    )

    # Get log level from env var
    log_level = os.environ.get("WEMB_LOGLEVEL") or logging.DEBUG

    logger = logging.getLogger("wemb.core")

    try:
        logger.setLevel(log_level)
    except ValueError:
        logger.setLevel(logging.DEBUG)
        logger.warning(f"Invalid WEMB_LOGLEVEL ({log_level})! Defaulting to DEBUG...")

    return logger


@unique
class SubmissionType(Enum):
    """Represents a type of submission (either WTS or WTB)"""

    def __init__(self, value):
        # Formats a string such as [wts] or [wtb] for comparison purposes
        self.formatted_value = f"[{str(value).lower()}]"

    WTB = "WTB"
    WTS = "WTS"


class SubmissionCriterion:
    """Class that represents some criteria for finding a post on the subreddit. Each instance of this object represents a different query.

    submission_type - Which post stream to consider. Either "WTB" (Want to buy) or "WTS" (Want to sell)
    min_transactions - The minimum number of transactions the author of the submission needs to have to be considered. Default 5.
    keywords - A list of string keywords (case **insensitive**) to filter the title with. See below for behaviour.
    all_required - If true, ALL keywords are required to be in the title to be considered. Else, only one needs to match.
    """

    @staticmethod
    def __process_keywords(initial: Optional[List[str]]) -> List[str]:
        keywords = list()

        if initial is None or len(initial) == 0:
            # Append an empty string item so loop logic works
            keywords.append("")
        else:
            for element in initial:
                keywords.append(element.lower())

        return keywords

    def __init__(
        self,
        submission_type: Union[SubmissionType, str],
        min_transactions: int = 5,
        keywords: Optional[List[str]] = None,
        all_required: bool = True,
    ):
        self.submission_type: SubmissionType = SubmissionType(submission_type)
        self.min_transactions: int = min_transactions
        self.keywords: List[str] = self.__process_keywords(keywords)
        self.all_required: bool = all_required

        if min_transactions < 0:
            raise ValueError("min_transactions must be a positive integer!")

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}<{self.submission_type.value}, {self.min_transactions}, {self.keywords}, {self.all_required}>"

    def check_title(self, title: str):
        """Checks if the passed-in title matches any of the keyword-based criteria in this object. Behaviour depends on self.all_required."""
        title = title.lower()

        # Check if something like "[WTB]" is in the title
        if self.submission_type.formatted_value not in title:
            return False

        if self.all_required:
            # Check if ALL the keywords match
            for k in self.keywords:
                # Found a keyword that's not in the title, so we return false
                if k not in title:
                    return False
            # None of the keywords caused the loop to exit, which means we found all of them
            return True

        else:
            # Check if any of the keywords match
            for k in self.keywords:
                if k in title:
                    return True

        return False


class ProgramConfiguration:
    """A class representing a state of the config file. This will likely get removed in the next version"""

    def __init__(self, config_file: str):
        config_path = Path(config_file)

        if not config_path.is_file():
            raise ValueError(f"Config file at {config_path} does not exist!")

        with config_path.open() as file:
            contents = yaml.safe_load(file)

        self.criteria: List[SubmissionCriterion] = list()

        # Read every serialized version of the criteria and save it to this object.
        for criterion in contents["criteria"]:
            self.criteria.append(
                SubmissionCriterion(
                    criterion["submissionType"],
                    min_transactions=criterion["minTransactions"],
                    keywords=criterion["keywords"],
                    all_required=criterion["allRequired"],
                )
            )

        LOGGER.debug(f"  Loaded {len(self.criteria)} criteria: {self.criteria}")

        self.webhookUrl = contents["callback"]["webhookUrl"]
        self.mentionString = contents["callback"]["mentionString"]


RE_TRANSACTIONS = re.compile(r"^\d+")
SUBREDDIT_WATCHEXCHANGE = "watchexchange"
LOGGER = __get_logger()


def get_permalink(reddit: Reddit, submission: Submission):
    """Gets a permalink to the submission passed in the second argument"""

    return f"{reddit.config.reddit_url + submission.permalink}"


def check_criteria(criterion: SubmissionCriterion, submission: Submission) -> bool:
    """Helper function that checks a given criterion object against a submission. Returns true if all gates pass, false otherwise."""

    # Check the title. If that doesn't match, go to the next item and mark this as processed
    if not criterion.check_title(submission.title):
        LOGGER.debug("    Failed on title criteria (1/2)")
        return False

    # Check minimum transactions of the submitting user
    try:
        if (
            int(RE_TRANSACTIONS.match(submission.author_flair_text)[0])
            < criterion.min_transactions
        ):
            LOGGER.debug("    Failed on minimum transaction count (2/2)")
            return False
    except TypeError:
        LOGGER.warning(f"    Submission has INVALID user flair!")
        return False

    # If both gates have been passed, we have matched all criteria
    return True


def process_submissions(reddit: praw.Reddit, args, callback=None):
    """Checks for new posts in the subreddit and matches them against the criteria. Blocks "forever", or until a praw exception occurs. It's expected for the caller to re-call this if necessary"""

    LOGGER.info("Reading configuration!")

    config = ProgramConfiguration(args.config_file)

    LOGGER.info("Started Stream!")

    submission: Submission
    for submission in reddit.subreddit(SUBREDDIT_WATCHEXCHANGE).stream.submissions():
        LOGGER.info("")
        LOGGER.info(f"Incoming submission ({submission.id}):")
        LOGGER.debug(f"  URL: {get_permalink(reddit, submission)}")
        LOGGER.debug(f"  Title: {submission.title}")
        LOGGER.debug(f"  Flair: {submission.author_flair_text}")

        # This is a new post, so we have to analyze it with respect to the criteria.
        for criterion in config.criteria:
            LOGGER.info(f"  Checking {criterion}...")

            if check_criteria(criterion, submission):
                LOGGER.info("    Matched! Sending message...")
                callback(reddit, submission, config.webhookUrl, config.mentionString)
            else:
                LOGGER.info("    Did not match")


def post_discord_message(
    reddit: Reddit, submission: Submission, webhook_url, mention_string
):
    """Posts a message using a webhook, including the submission URL and mentioning a user/role"""

    response = requests.post(
        webhook_url,
        json={
            "content": f"{mention_string} {get_permalink(reddit, submission)}",
        },
    )

    LOGGER.debug(f"Response: {response}")


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

    # Dependent on a praw.ini file containing client_id, client_secret, and user_agent.
    reddit = praw.Reddit(read_only=True)

    # Set signal handler for Ctrl+C and SIGTERM
    signal.signal(signal.SIGINT, __signal_handler)
    signal.signal(signal.SIGTERM, __signal_handler)

    process_submissions(reddit, args, callback=post_discord_message)


if __name__ == "__main__":
    main()
