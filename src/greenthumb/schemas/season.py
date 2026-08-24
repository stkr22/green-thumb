"""Response schemas for the season metadata endpoint."""

from sqlmodel import SQLModel


class SeasonPreset(SQLModel):
    """A starting point for a species' season plan, offered by the species form."""

    key: str
    plan: dict[str, dict[str, float | None]]


class SeasonInfo(SQLModel):
    """What the frontend needs to label and edit season plans.

    Presets are served rather than duplicated in the frontend so the numbers
    have one source of truth; they are copied into a plan as plain values, so
    the key is never stored and this list can change between releases.
    """

    hemisphere: str
    current_season: str
    presets: list[SeasonPreset]
    # season -> [start_month, end_month] for this hemisphere, so the window
    # editor can offer "spring" without the frontend knowing which months that
    # is. Southern spring is Sep-Nov, and southern summer wraps Dec-Feb.
    season_months: dict[str, list[int]]
