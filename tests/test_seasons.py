"""Season plan maths: season boundaries, rate accumulation, suspension, validation."""

from datetime import UTC, datetime, timedelta

import pytest

from greenthumb.services import seasons
from greenthumb.services.seasons import Hemisphere, Season

NORTH = Hemisphere.NORTH
SOUTH = Hemisphere.SOUTH

# All-1.0 plan: the scheduler must treat this exactly like no plan at all.
NEUTRAL = {"spring": 1.0, "summer": 1.0, "autumn": 1.0, "winter": 1.0}
# Winter at double the interval, everything else unchanged.
WINTER_SLOW = {"spring": 1.0, "summer": 1.0, "autumn": 1.0, "winter": 2.0}
# Suspended for the whole cold half of the year.
WINTER_OFF = {"spring": 1.0, "summer": 1.0, "autumn": None, "winter": None}


def _at(year: int, month: int, day: int) -> datetime:
    return datetime(year, month, day, 9, 30, tzinfo=UTC)


@pytest.mark.parametrize(
    ("month", "expected"),
    [
        (1, Season.WINTER),
        (2, Season.WINTER),
        (3, Season.SPRING),
        (5, Season.SPRING),
        (6, Season.SUMMER),
        (8, Season.SUMMER),
        (9, Season.AUTUMN),
        (11, Season.AUTUMN),
        (12, Season.WINTER),
    ],
)
def test_northern_seasons_by_month(month: int, expected: Season):
    assert seasons.season_for(_at(2026, month, 15), NORTH) is expected


@pytest.mark.parametrize(
    ("month", "expected"),
    [
        (1, Season.SUMMER),
        (3, Season.AUTUMN),
        (6, Season.WINTER),
        (7, Season.WINTER),
        (9, Season.SPRING),
        (12, Season.SUMMER),
    ],
)
def test_southern_seasons_are_mirrored(month: int, expected: Season):
    assert seasons.season_for(_at(2026, month, 15), SOUTH) is expected


def test_season_boundary_days_flip_on_the_first():
    assert seasons.season_for(_at(2026, 2, 28), NORTH) is Season.WINTER
    assert seasons.season_for(_at(2026, 3, 1), NORTH) is Season.SPRING


def test_leap_day_is_winter():
    assert seasons.season_for(_at(2024, 2, 29), NORTH) is Season.WINTER


def test_missing_or_partial_plans_are_unscaled():
    assert seasons.multiplier_for(None, Season.WINTER) == 1.0
    assert seasons.multiplier_for({}, Season.WINTER) == 1.0
    assert seasons.multiplier_for({"summer": 0.5}, Season.WINTER) == 1.0


def test_suspended_season_yields_no_rate():
    assert seasons.multiplier_for(WINTER_OFF, Season.WINTER) is None
    assert seasons.daily_rate(7, None) == 0.0


def test_effective_interval_rounds_and_reports_suspension():
    assert seasons.effective_interval_days(7, 2.0) == 14
    assert seasons.effective_interval_days(7, 0.85) == 6
    assert seasons.effective_interval_days(7, None) is None


def test_effective_interval_never_drops_below_a_day():
    assert seasons.effective_interval_days(1, 0.2) == 1


@pytest.mark.parametrize("interval", [1, 3, 7, 10, 14, 30, 90, 365])
def test_neutral_plan_matches_plain_interval_arithmetic(interval: int):
    """Regression guard: seasonality off must reproduce the pre-season due date exactly."""
    last = _at(2026, 6, 1)
    assert seasons.due_at(last, interval, None, NORTH) == last + timedelta(days=interval)
    assert seasons.due_at(last, interval, NEUTRAL, NORTH) == last + timedelta(days=interval)


def test_due_date_keeps_the_logged_time_of_day():
    last = datetime(2026, 6, 1, 7, 15, tzinfo=UTC)
    assert seasons.due_at(last, 7, WINTER_SLOW, NORTH) == datetime(2026, 6, 8, 7, 15, tzinfo=UTC)


def test_winter_multiplier_stretches_the_interval():
    last = _at(2026, 12, 1)
    assert seasons.due_at(last, 7, WINTER_SLOW, NORTH) == last + timedelta(days=14)


def test_summer_multiplier_shortens_the_interval():
    last = _at(2026, 6, 1)
    plan = {"spring": 1.0, "summer": 0.5, "autumn": 1.0, "winter": 1.0}
    assert seasons.due_at(last, 10, plan, NORTH) == last + timedelta(days=5)


def test_debt_accrued_in_winter_keeps_its_winter_price():
    """A season flip must not retro-price days already spent at the old pace.

    Watered 21 Feb on a 7-day base with winter at 2.0: the eight remaining
    winter days earn 8/14 of the interval, and the rest is paid at the spring
    rate from 1 March - three more days, not a jump to overdue the moment
    spring starts.
    """
    last = _at(2026, 2, 21)
    due = seasons.due_at(last, 7, WINTER_SLOW, NORTH)
    assert due == _at(2026, 3, 4)


def test_suspended_seasons_accrue_nothing_and_resume_in_spring():
    """Fertilising stopped in autumn should come due shortly after spring starts."""
    last = _at(2026, 9, 1)
    due = seasons.due_at(last, 30, WINTER_OFF, NORTH)
    assert due is not None
    assert seasons.season_for(due, NORTH) is Season.SPRING
    # Autumn and winter contribute nothing, so the full 30 days start on 1 March.
    assert due == _at(2027, 3, 31)


def test_plan_suspended_all_year_has_no_due_date():
    always_off = dict.fromkeys(("spring", "summer", "autumn", "winter"))
    assert seasons.due_at(_at(2026, 6, 1), 7, always_off, NORTH) is None


def test_southern_hemisphere_slows_watering_in_july():
    last = _at(2026, 7, 1)
    assert seasons.due_at(last, 7, WINTER_SLOW, SOUTH) == last + timedelta(days=14)
    assert seasons.due_at(last, 7, WINTER_SLOW, NORTH) == last + timedelta(days=7)


def test_first_active_day_skips_suspended_seasons():
    november = _at(2026, 11, 10)
    assert seasons.first_active_day(november, WINTER_OFF, NORTH) == _at(2027, 3, 1)


def test_first_active_day_returns_now_when_season_is_active():
    june = _at(2026, 6, 10)
    assert seasons.first_active_day(june, WINTER_OFF, NORTH) == june


def test_first_active_day_falls_back_when_every_season_is_suspended():
    always_off = dict.fromkeys(("spring", "summer", "autumn", "winter"))
    june = _at(2026, 6, 10)
    assert seasons.first_active_day(june, always_off, NORTH) == june


@pytest.mark.parametrize(
    ("month", "expected"),
    [(1, False), (2, False), (3, True), (4, True), (5, True), (6, False), (12, False)],
)
def test_in_window_within_the_year(month: int, expected: bool):
    assert seasons.in_window(_at(2026, month, 15), 3, 5) is expected


@pytest.mark.parametrize(
    ("month", "expected"),
    [(10, False), (11, True), (12, True), (1, True), (2, True), (3, False)],
)
def test_in_window_wrapping_the_year(month: int, expected: bool):
    assert seasons.in_window(_at(2026, month, 15), 11, 2) is expected


def test_next_window_start_returns_the_moment_when_already_open():
    april = _at(2026, 4, 10)
    assert seasons.next_window_start(april, 3, 5) == april


def test_next_window_start_waits_for_this_year_when_the_window_is_ahead():
    assert seasons.next_window_start(_at(2026, 1, 20), 3, 5) == _at(2026, 3, 1)


def test_next_window_start_rolls_to_next_year_when_the_window_has_passed():
    assert seasons.next_window_start(_at(2026, 7, 20), 3, 5) == _at(2027, 3, 1)


def test_next_window_start_handles_a_wrapping_window():
    # June is outside Nov-Feb, so the next opening is November of the same year.
    assert seasons.next_window_start(_at(2026, 6, 1), 11, 2) == _at(2026, 11, 1)


def test_next_window_start_keeps_the_time_of_day():
    moment = datetime(2026, 7, 20, 6, 45, tzinfo=UTC)
    assert seasons.next_window_start(moment, 3, 5) == datetime(2027, 3, 1, 6, 45, tzinfo=UTC)


@pytest.mark.parametrize(
    ("season", "hemisphere", "expected"),
    [
        (Season.SPRING, NORTH, (3, 5)),
        (Season.SUMMER, NORTH, (6, 8)),
        (Season.WINTER, NORTH, (12, 2)),
        (Season.SPRING, SOUTH, (9, 11)),
        (Season.WINTER, SOUTH, (6, 8)),
        (Season.SUMMER, SOUTH, (12, 2)),
    ],
)
def test_months_for_season(season: Season, hemisphere: Hemisphere, expected: tuple[int, int]):
    assert seasons.months_for(season, hemisphere) == expected


def test_presets_are_valid_plans():
    for name, plan in seasons.PRESETS.items():
        assert seasons.validate_season_plan(plan) is plan, name


def test_presets_keep_growing_season_watering_at_or_below_baseline():
    """Spring and summer are the baseline the user typed; presets may only slow, not speed, the cold half."""
    for name, plan in seasons.PRESETS.items():
        if name == "winter_grower":
            continue
        watering = plan["watering"]
        assert watering["winter"] is not None and watering["winter"] >= 1.0, name
        assert watering["summer"] is not None and watering["summer"] <= 1.0, name


@pytest.mark.parametrize(
    "plan",
    [
        {"watering": {"sprong": 1.0}},
        {"watering": {"winter": 0}},
        {"watering": {"winter": -1}},
        {"watering": {"winter": 99}},
        {"watering": {"winter": "slow"}},
        {"watering": {"winter": True}},
        {"watering": [1, 2]},
    ],
)
def test_validate_rejects_malformed_plans(plan):
    with pytest.raises(ValueError, match=r".+"):
        seasons.validate_season_plan(plan)


def test_validate_accepts_partial_plans_and_nulls():
    plan = {"watering": {"winter": 2.0}, "fertilising": {"winter": None}}
    assert seasons.validate_season_plan(plan) is plan
