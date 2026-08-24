"""Season metadata route: hemisphere, the current season, and the plan presets."""

from fastapi import APIRouter

from greenthumb.auth import CurrentUser
from greenthumb.config import get_settings
from greenthumb.models.base import utcnow
from greenthumb.schemas import SeasonInfo, SeasonPreset
from greenthumb.services import seasons

router = APIRouter(prefix="/seasons", tags=["seasons"])


@router.get("", response_model=SeasonInfo)
async def get_season_info(_user: CurrentUser) -> SeasonInfo:
    """Return the installation's hemisphere, today's season and the season plan presets."""
    hemisphere = get_settings().HEMISPHERE
    return SeasonInfo(
        hemisphere=hemisphere.value,
        current_season=seasons.season_for(utcnow(), hemisphere).value,
        presets=[SeasonPreset(key=key, plan=dict(plan)) for key, plan in seasons.PRESETS.items()],
        season_months={season.value: list(seasons.months_for(season, hemisphere)) for season in seasons.Season},
    )
