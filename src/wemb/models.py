from datetime import datetime
from enum import Enum, unique
from typing import List

from sqlalchemy import ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


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
    """Represents a single criterion to be matched against posts."""

    __tablename__ = "submission_criterion"

    id: Mapped[int] = mapped_column(primary_key=True)
    submission_type: Mapped[SubmissionType]
    min_transactions: Mapped[int] = mapped_column(default=5)
    keywords: Mapped[List["Keyword"]] = relationship(
        back_populates="criterion", cascade="all, delete, delete-orphan"
    )
    all_required: Mapped[bool] = mapped_column(default=True)

    def __repr__(self) -> str:
        return f"SubmissionCriterion(id={self.id!r}, submission_type={self.submission_type!r}, min_transactions={self.min_transactions!r}, keywords={self.keywords!r}, all_required={self.all_required!r})"


class ProcessedPost(Base):
    """Used as a cache to keep track of already-processed posts, to prevent a restart from triggering another notification."""

    __tablename__ = "processed_post"

    id: Mapped[str] = mapped_column(primary_key=True, autoincrement=False)
    date_processed: Mapped[datetime] = mapped_column(default=datetime.now)

    def __repr__(self) -> str:
        return f"ProcessedPost(id={self.id!r}, date_processed={self.date_processed!r})"
