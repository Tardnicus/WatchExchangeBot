import logging
import re
from argparse import Namespace
from typing import List, Optional

import requests
from asyncpraw import Reddit
from asyncpraw.models import Submission
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession, AsyncEngine
from sqlalchemy.orm import selectinload

from models import SubmissionCriterion, ProcessedSubmission

DB_SESSION: Optional[async_sessionmaker[AsyncEngine]] = None

RE_TRANSACTIONS = re.compile(r"^\d+")
SUBREDDIT_WATCHEXCHANGE = "watchexchange"
LOGGER = logging.getLogger("wemb.monitor")


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


async def process_submissions(reddit: Reddit, args, callback=None):
    """Checks for new submissions in the subreddit and matches them against the criteria. Blocks "forever", or until a praw exception occurs. It's expected for the caller to re-call this if necessary"""

    LOGGER.info("Started Stream!")

    subreddit = await reddit.subreddit(SUBREDDIT_WATCHEXCHANGE)

    submission: Submission
    async for submission in subreddit.stream.submissions():
        LOGGER.info("")
        LOGGER.info(f"Incoming submission ({submission.id}):")
        LOGGER.debug(f"  URL: {get_permalink(reddit, submission)}")
        LOGGER.debug(f"  Title: {submission.title}")
        LOGGER.debug(f"  Flair: {submission.author_flair_text}")

        LOGGER.debug("  Checking if submission has been processed...")

        session: AsyncSession
        async with DB_SESSION() as session:
            if await session.get(ProcessedSubmission, submission.id):
                LOGGER.info("  Submission has already been processed! Skipping...")
                continue

        session: AsyncSession
        async with DB_SESSION() as session:
            # noinspection PyTypeChecker
            # Eager load .keywords, because we're printing the repr
            criteria: List[SubmissionCriterion] = (
                await session.scalars(
                    select(SubmissionCriterion).options(
                        selectinload(SubmissionCriterion.keywords)
                    )
                )
            ).all()

            if len(criteria) == 0:
                LOGGER.warning("  No criteria loaded, nothing to do.")

            # This is a new submission, so we have to analyze it with respect to the criteria.
            for criterion in criteria:
                LOGGER.info(f"  Checking {criterion}...")

                if check_criteria(criterion, submission):
                    LOGGER.info("    Matched! Sending message...")
                    callback(reddit, submission, args.webhook_url, args.mention_string)
                else:
                    LOGGER.info("    Did not match")

        session: AsyncSession
        async with DB_SESSION() as session:
            LOGGER.debug("  Adding submission to cache...")
            try:
                session.add(ProcessedSubmission(id=submission.id))
                await session.commit()
            except IntegrityError as error:
                LOGGER.error(
                    f"  Failed to save to database! Submission with id ({submission.id}) is already in cache!"
                )
                LOGGER.error("  Exception info:", exc_info=error)


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


async def run_monitor(
    args: Namespace, *, session_factory: async_sessionmaker[AsyncSession]
):
    global DB_SESSION

    DB_SESSION = session_factory

    LOGGER.info("Initialized!")

    async with Reddit(
        client_id=args.praw_client_id,
        client_secret=args.praw_client_secret,
        user_agent=args.praw_user_agent,
        read_only=True,
    ) as reddit:
        # Handle disconnections that would otherwise cause this outer function to exit
        while True:
            LOGGER.info("Starting stream...")
            await process_submissions(reddit, args, callback=post_discord_message)
