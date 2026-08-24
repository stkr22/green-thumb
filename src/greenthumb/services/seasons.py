"""Seasonal care scheduling: pure calendar and rate maths, no DB or I/O.

Plants grow in warm, bright months and idle in cold, dark ones, so a single
year-round interval either overwaters in winter or underwaters in summer. A
season plan scales a reminder's growing-season interval per season, and may
suspend an event type entirely (``None``) for seasons where it must not happen
at all - feeding a dormant plant builds up fertiliser salts that damage roots.

Due dates come from accumulating a daily care *rate* until it reaches 1.0
rather than multiplying the interval by today's multiplier. Multiplying by the
current season would move every due date the moment the season flips, so on 1
March a whole collection would turn overdue at once; accumulating means days
already spent at the winter pace stay priced at the winter pace. It also makes
suspension fall out for free (a suspended day simply contributes nothing) and
leaves room to swap the discrete seasons for a smooth daylength curve later:
:func:`multiplier_for` is the only seam that would change.

Suspension here means "dormant days do not count", which suits watering and
fertilising. It deliberately does not model "this may only happen in spring"
(repotting, pruning): stretching a 2-year repotting interval across active days
only would push it out by years. Those belong to a separate annual-window
schedule kind, so the shipped presets cover watering and fertilising only.
"""

from collections.abc import Mapping
from datetime import date, datetime, timedelta
from enum import StrEnum

# A season plan maps event type -> season -> multiplier on the growing-season
# interval. None suspends the event type for that season. Event types absent
# from a plan are unscaled, so custom care types keep their plain interval.
# Read-only Mapping rather than dict so a caller's dict[str, float] (a plan with
# nothing suspended) is accepted without a cast.
SeasonMultipliers = Mapping[str, float | None]
SeasonPlan = Mapping[str, SeasonMultipliers]

# Two years is far past any real care interval; a plan suspended in every
# season would otherwise loop forever looking for a due date that never comes.
MAX_LOOKAHEAD_DAYS = 730

# Guards against float sums landing a hair below 1.0 (seven additions of 1/7
# need not total exactly 1.0), which would otherwise push a due date a whole
# day out and break the "no seasonality behaves exactly as before" contract.
_RATE_EPSILON = 1e-9

# Anything slower than a tenfold stretch is better expressed as a longer base
# interval, and the cap keeps a typo from silently parking a reminder.
_MAX_MULTIPLIER = 10


class Season(StrEnum):
    """Meteorological seasons, used as the keys of a season plan."""

    SPRING = "spring"
    SUMMER = "summer"
    AUTUMN = "autumn"
    WINTER = "winter"


class Hemisphere(StrEnum):
    """Which half of the globe the installation sits in."""

    NORTH = "north"
    SOUTH = "south"


# Indexed by month - 1. Meteorological rather than astronomical seasons: whole
# months are what users reason about, and the few days of difference are noise
# next to a watering interval.
_NORTHERN_SEASON_BY_MONTH = (
    Season.WINTER,
    Season.WINTER,
    Season.SPRING,
    Season.SPRING,
    Season.SPRING,
    Season.SUMMER,
    Season.SUMMER,
    Season.SUMMER,
    Season.AUTUMN,
    Season.AUTUMN,
    Season.AUTUMN,
    Season.WINTER,
)

# Starting points offered by the species form. They are copied into the plan as
# plain numbers the user can then edit - the preset name is never stored, so
# this table can change between releases without stranding existing data.
PRESETS: dict[str, SeasonPlan] = {
    "tropical": {
        "watering": {"spring": 1.0, "summer": 0.9, "autumn": 1.2, "winter": 1.5},
        "fertilising": {"spring": 1.0, "summer": 1.0, "autumn": 1.5, "winter": None},
    },
    "standard": {
        "watering": {"spring": 1.0, "summer": 0.85, "autumn": 1.3, "winter": 2.0},
        "fertilising": {"spring": 1.0, "summer": 1.0, "autumn": None, "winter": None},
    },
    "succulent": {
        "watering": {"spring": 1.0, "summer": 0.8, "autumn": 1.5, "winter": 3.5},
        "fertilising": {"spring": 1.0, "summer": 1.0, "autumn": None, "winter": None},
    },
    # Cyclamen, forced bulbs and similar grow through the cold months and rest
    # in summer heat, so the whole curve inverts.
    "winter_grower": {
        "watering": {"spring": 1.3, "summer": 3.0, "autumn": 1.0, "winter": 1.0},
        "fertilising": {"spring": 1.0, "summer": None, "autumn": 1.0, "winter": 1.0},
    },
}


def season_for(moment: date, hemisphere: Hemisphere) -> Season:
    """Return the season a given day falls in for the installation's hemisphere."""
    month = moment.month
    if hemisphere is Hemisphere.SOUTH:
        month = (month + 5) % 12 + 1
    return _NORTHERN_SEASON_BY_MONTH[month - 1]


def months_for(season: Season, hemisphere: Hemisphere) -> tuple[int, int]:
    """First and last month of a season, so the UI can offer "spring" as a window."""
    months = [month for month in range(1, 13) if season_for(date(2001, month, 1), hemisphere) is season]
    # Southern winter is Jun-Aug and northern winter wraps Dec-Feb; taking the
    # run that wraps the year boundary keeps the pair in calendar order.
    if months == [1, 2, 12]:
        return 12, 2
    return months[0], months[-1]


def in_window(moment: date, start_month: int, end_month: int) -> bool:
    """Whether a date falls in an inclusive month window, which may wrap the year."""
    if start_month <= end_month:
        return start_month <= moment.month <= end_month
    return moment.month >= start_month or moment.month <= end_month


def next_window_start(moment: datetime, start_month: int, end_month: int) -> datetime:
    """Return the moment the window next opens at or after ``moment`` (``moment`` itself if open).

    This is how a due date is deferred into its allowed months. Unlike a
    suspended season, the schedule still runs at full speed while the window is
    shut - a two-year repotting interval stays two years, it just lands in
    spring. Time of day is preserved rather than reset to midnight, so the due
    date keeps the hour of the care event that produced it.
    """
    if in_window(moment, start_month, end_month):
        return moment
    year = moment.year if moment.month < start_month else moment.year + 1
    return moment.replace(year=year, month=start_month, day=1)


def multiplier_for(multipliers: SeasonMultipliers | None, season: Season) -> float | None:
    """Return the interval multiplier for one season, or None when suspended.

    A missing plan or a season the plan does not mention means "no seasonal
    change", so partially filled plans stay usable.
    """
    if not multipliers:
        return 1.0
    if season.value not in multipliers:
        return 1.0
    return multipliers[season.value]


def daily_rate(base_interval_days: int, multiplier: float | None) -> float:
    """Fraction of the way towards due that one day at this multiplier contributes."""
    if multiplier is None:
        return 0.0
    return 1.0 / (base_interval_days * multiplier)


def effective_interval_days(base_interval_days: int, multiplier: float | None) -> int | None:
    """Return the interval as a whole number of days for display, or None when suspended."""
    if multiplier is None:
        return None
    return max(1, round(base_interval_days * multiplier))


def due_at(
    last_event_at: datetime,
    base_interval_days: int,
    multipliers: SeasonMultipliers | None,
    hemisphere: Hemisphere,
) -> datetime | None:
    """Next due moment after ``last_event_at``, or None if none falls within the lookahead.

    Walks forward a day at a time accumulating :func:`daily_rate` and returns
    the end of the day that tips the total to 1.0. With no seasonality this is
    exactly ``last_event_at + base_interval_days``; the time of day is carried
    through, so backdated logs keep their hour.
    """
    if not multipliers:
        return last_event_at + timedelta(days=base_interval_days)

    moment = last_event_at
    accumulated = 0.0
    for _ in range(MAX_LOOKAHEAD_DAYS):
        accumulated += daily_rate(base_interval_days, multiplier_for(multipliers, season_for(moment, hemisphere)))
        moment += timedelta(days=1)
        if accumulated >= 1.0 - _RATE_EPSILON:
            return moment
    return None


def first_active_day(from_moment: datetime, multipliers: SeasonMultipliers | None, hemisphere: Hemisphere) -> datetime:
    """First moment from ``from_moment`` on whose season is not suspended.

    A reminder with no care logged yet counts as due immediately, but not while
    its event type is suspended: a plant bought in November should not ask to be
    fed straight away. Falls back to ``from_moment`` if the plan suspends every
    season, so a misconfigured plan surfaces as a due reminder rather than
    silently vanishing.
    """
    moment = from_moment
    for _ in range(MAX_LOOKAHEAD_DAYS):
        if multiplier_for(multipliers, season_for(moment, hemisphere)) is not None:
            return moment
        moment += timedelta(days=1)
    return from_moment


def validate_season_multipliers(multipliers: SeasonMultipliers, label: str = "season plan") -> SeasonMultipliers:
    """Return one event type's multipliers unchanged, raising ValueError if malformed.

    These arrive as free-form JSON from the API, so season keys and multiplier
    ranges are checked before they reach the scheduler, where a zero or negative
    multiplier would mean an infinite or reversed interval.
    """
    if not isinstance(multipliers, dict):
        raise ValueError(f"{label} must be an object of season -> multiplier")
    unknown = set(multipliers) - {season.value for season in Season}
    if unknown:
        raise ValueError(f"Unknown season(s) in {label}: {', '.join(sorted(unknown))}")
    for season, multiplier in multipliers.items():
        if multiplier is None:
            continue
        if not isinstance(multiplier, int | float) or isinstance(multiplier, bool):
            raise ValueError(f"Multiplier for {season} in {label} must be a number or null")
        if not 0 < multiplier <= _MAX_MULTIPLIER:
            raise ValueError(f"Multiplier for {season} in {label} must be between 0 and {_MAX_MULTIPLIER}")
    return multipliers


def validate_season_plan(plan: SeasonPlan) -> SeasonPlan:
    """Return the plan unchanged, raising ValueError if any event type's multipliers are malformed."""
    if not isinstance(plan, dict):
        raise ValueError("Season plan must be an object of event type -> season multipliers")
    for event_type, multipliers in plan.items():
        validate_season_multipliers(multipliers, f"'{event_type}'")
    return plan


__all__ = [
    "MAX_LOOKAHEAD_DAYS",
    "PRESETS",
    "Hemisphere",
    "Season",
    "SeasonMultipliers",
    "SeasonPlan",
    "daily_rate",
    "due_at",
    "effective_interval_days",
    "first_active_day",
    "in_window",
    "months_for",
    "multiplier_for",
    "next_window_start",
    "season_for",
    "validate_season_multipliers",
    "validate_season_plan",
]
