from datetime import datetime
from enum import Enum, unique
from typing import List

from sqlalchemy import ForeignKey
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
    validates,
)


@unique
class SubmissionType(Enum):
    """Represents a type of submission (either WTS or WTB)."""

    def __init__(self, value):
        # Formats a string such as [wts] or [wtb] for comparison purposes
        self.formatted_value = f"[{str(value).lower()}]"

    WTB = "WTB"
    WTS = "WTS"


class Base(DeclarativeBase):
    pass


class Keyword(Base):
    """Represents a single keyword used as part of a SubmissionCriterion."""

    __tablename__ = "keyword"

    id: Mapped[int] = mapped_column(primary_key=True)
    content: Mapped[str] = mapped_column()

    criterion_id: Mapped[int] = mapped_column(ForeignKey("submission_criterion.id"))
    criterion: Mapped["SubmissionCriterion"] = relationship(back_populates="keywords")

    def __repr__(self) -> str:
        return f"Keyword(content={self.content!r}, criterion_id={self.criterion_id!r})"


class SubmissionCriterion(Base):
    """Class that represents some criteria for finding a submission on the subreddit. Each instance of this object represents a different query.

    submission_type - Which submission stream to consider. Either "WTB" (Want to buy) or "WTS" (Want to sell)
    min_transactions - The minimum number of transactions the author of the submission needs to have to be considered. Default 5.
    keywords - A list of string keywords (case **insensitive**) to filter the title with. See below for behaviour.
    all_required - If true, ALL keywords are required to be in the title to be considered. Else, only one needs to match.
    """

    __tablename__ = "submission_criterion"

    id: Mapped[int] = mapped_column(primary_key=True)
    submission_type: Mapped[SubmissionType]
    min_transactions: Mapped[int] = mapped_column(default=5)
    keywords: Mapped[List["Keyword"]] = relationship(
        back_populates="criterion", cascade="all, delete, delete-orphan"
    )
    all_required: Mapped[bool] = mapped_column(default=True)

    @validates("min_transactions")
    def validate_min_transactions(self, key, value):
        if value < 0:
            raise ValueError("min_transactions must be a positive integer!")
        return value

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
                if k.content.lower() not in title:
                    return False

            # None of the keywords caused the loop to exit, which means we found all of them
            return True

        else:
            # Check if any of the keywords match
            for k in self.keywords:
                if k.content.lower() in title:
                    return True

        return False

    def __repr__(self) -> str:
        return f"SubmissionCriterion(id={self.id!r}, submission_type={self.submission_type!r}, min_transactions={self.min_transactions!r}, keywords={self.keywords!r}, all_required={self.all_required!r})"


class ProcessedSubmission(Base):
    """Used as a cache to keep track of already-processed submissions, to prevent a restart of the app from triggering another notification."""

    __tablename__ = "processed_submission"

    id: Mapped[str] = mapped_column(primary_key=True, autoincrement=False)
    date_processed: Mapped[datetime] = mapped_column(default=datetime.now)

    def __repr__(self) -> str:
        return f"ProcessedSubmission(id={self.id!r}, date_processed={self.date_processed!r})"
