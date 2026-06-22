"""Shared helpers for table models. The app runs on SQLite."""

from datetime import UTC, datetime

from sqlalchemy import DateTime


def utcnow() -> datetime:
    """Return the current UTC time (timezone-aware, per the API contract)."""
    return datetime.now(UTC)


def ensure_utc(value: datetime) -> datetime:
    """Attach UTC to naive datetimes.

    SQLite stores datetimes without timezone info, so reads come back naive;
    everything we store is UTC by contract.
    """
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


def utc_datetime_type() -> DateTime:
    """Timestamp column type (timezone-aware; stored naive on SQLite)."""
    return DateTime(timezone=True)
