"""FloraCodex species search proxy route."""

from typing import Annotated

from fastapi import APIRouter, Query

from greenthumb.auth import CurrentUser
from greenthumb.schemas import SpeciesSearchResult
from greenthumb.services import floracodex

router = APIRouter(tags=["species"])


@router.get("/species/search", response_model=list[SpeciesSearchResult])
async def search_species(
    _user: CurrentUser, q: Annotated[str, Query(min_length=1, max_length=200)]
) -> list[SpeciesSearchResult]:
    """Proxy a species search to FloraCodex; empty when no API key is configured."""
    return await floracodex.search_species(q)
