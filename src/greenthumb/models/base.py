"""Shared helpers for table models.

The app runs on SQLite. Column types are declared with their PostgreSQL-native
forms (ARRAY, JSONB) plus a SQLite variant, so the SQLite path is exercised
everywhere while the models remain portable to PostgreSQL if that ever changes.
"""

from datetime import UTC, datetime

from sqlalchemy import JSON, DateTime, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB


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
    """Timestamp column type: timestamptz on PostgreSQL, plain TEXT-backed on SQLite."""
    return DateTime(timezone=True)


def string_array_type() -> ARRAY:
    """Tag list column type: TEXT[] on PostgreSQL, JSON on SQLite."""
    return ARRAY(Text()).with_variant(JSON(), "sqlite")


def json_dict_type() -> JSONB:
    """Free-form dict column type: JSONB on PostgreSQL, JSON on SQLite."""
    return JSONB().with_variant(JSON(), "sqlite")
