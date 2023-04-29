import asyncio
import logging
import re
from argparse import Namespace
from asyncio import CancelledError
from typing import List, Optional, Callable, Coroutine

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


async def process_submissions(
    reddit: Reddit,
    *,
    callback: Callable[[SubmissionCriterion, Submission, Reddit], Coroutine],
):
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
                    await callback(criterion, submission, reddit)
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


async def run_monitor(
    args: Namespace,
    *,
    session_factory: async_sessionmaker[AsyncSession],
    callback: Callable[[SubmissionCriterion, Submission, Reddit], Coroutine],
):
    global DB_SESSION

    DB_SESSION = session_factory

    while True:
        LOGGER.info("Initializing monitor loop...")
        try:
            async with Reddit(
                client_id=args.praw_client_id,
                client_secret=args.praw_client_secret,
                user_agent=args.praw_user_agent,
                read_only=True,
            ) as reddit:
                LOGGER.info("Starting stream...")
                await process_submissions(reddit, callback=callback)

        except CancelledError as error:
            # https://docs.python.org/3/library/asyncio-task.html#task-cancellation
            LOGGER.debug("Monitor loop has been cancelled! Exiting...")
            raise error

        except Exception as error:
            # This is intentionally a broad exception clause to make sure the task doesn't quit before the program closes.
            # Ideally, this should slowly become less relied on as more exceptions are caught within process_submissions()
            LOGGER.error(
                f"Uncaught exception in monitor loop: {error!s}", exc_info=error
            )
            LOGGER.info("Restarting monitor loop!")

            # Add some sleep buffer to make sure we're not hammering Reddit's login endpoint. stream.submissions() grabs the last 100 submissions anyway, so we won't be missing out on data.
            await asyncio.sleep(10)
