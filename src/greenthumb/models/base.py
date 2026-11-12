"""Shared helpers for table models. The app runs on SQLite."""

from datetime import UTC, datetime

from sqlalchemy import DateTime
from sqlalchemy.engine import Dialect
from sqlalchemy.types import TypeDecorator


def utcnow() -> datetime:
    """Return the current UTC time (timezone-aware, per the API contract)."""
    return datetime.now(UTC)


class UTCDateTime(TypeDecorator[datetime]):
    """Timestamp that is always timezone-aware UTC in Python.

    SQLite has no timezone-aware datetime type: it stores the wall-clock fields
    and drops the offset, so reads came back naive and every comparison or API
    response had to patch UTC back in. Normalising at the column boundary makes
    that impossible to forget: binds are converted to UTC (an aware value in
    another zone would otherwise be stored with the wrong wall-clock time) and
    results always carry UTC.
    """

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect: Dialect) -> datetime | None:  # noqa: ARG002
        """Store UTC wall-clock time; naive input is UTC by contract."""
        if value is None or value.tzinfo is None:
            return value
        return value.astimezone(UTC).replace(tzinfo=None)

    def process_result_value(self, value: datetime | None, dialect: Dialect) -> datetime | None:  # noqa: ARG002
        """Attach UTC to the stored wall-clock time."""
        return value.replace(tzinfo=UTC) if value is not None else None


def utc_datetime_type() -> UTCDateTime:
    """Timestamp column type (see UTCDateTime)."""
    return UTCDateTime()
