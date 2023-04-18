import argparse
import re
from pathlib import Path
from typing import List

import praw
import requests
import yaml
from praw import Reddit
from praw.models import Submission
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from common import get_engine, get_logger
from models import SubmissionCriterion, Keyword, SubmissionType, ProcessedSubmission


class ProgramConfiguration:
    """A class representing a state of the config file. This will likely get removed in the next version.

    TODO: Remove, replace with database query
    """

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
                    submission_type=SubmissionType(criterion["submissionType"]),
                    min_transactions=criterion["minTransactions"],
                    keywords=[Keyword(content=k) for k in criterion["keywords"]],
                    all_required=criterion["allRequired"],
                )
            )

        LOGGER.debug(f"  Loaded {len(self.criteria)} criteria: {self.criteria}")

        self.webhookUrl = contents["callback"]["webhookUrl"]
        self.mentionString = contents["callback"]["mentionString"]


engine = get_engine()

RE_TRANSACTIONS = re.compile(r"^\d+")
SUBREDDIT_WATCHEXCHANGE = "watchexchange"
LOGGER = get_logger("wemb.core")


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
    """Checks for new submissions in the subreddit and matches them against the criteria. Blocks "forever", or until a praw exception occurs. It's expected for the caller to re-call this if necessary"""

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

        LOGGER.debug("  Checking if submission has been processed...")
        with Session(engine) as session:
            if session.scalar(
                select(ProcessedSubmission).where(
                    ProcessedSubmission.id == submission.id
                )
            ):
                LOGGER.info("  Submission has already been processed! Skipping...")
                continue

        # This is a new submission, so we have to analyze it with respect to the criteria.
        for criterion in config.criteria:
            LOGGER.info(f"  Checking {criterion}...")

            if check_criteria(criterion, submission):
                LOGGER.info("    Matched! Sending message...")
                callback(reddit, submission, config.webhookUrl, config.mentionString)
            else:
                LOGGER.info("    Did not match")

        with Session(engine) as session:
            LOGGER.debug("  Adding submission to cache...")
            try:
                session.add(ProcessedSubmission(id=submission.id))
                session.commit()
            except IntegrityError as error:
                LOGGER.error(
                    f"  Failed to save to database! Submission with id ({submission.id}) is already in cache!"
                )
                LOGGER.debug("  Exception info:", exc_info=error)


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


def run_core(args: argparse.Namespace):
    # Dependent on a praw.ini file containing client_id, client_secret, and user_agent.
    reddit = praw.Reddit(read_only=True)

    process_submissions(reddit, args, callback=post_discord_message)
