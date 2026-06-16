"""Response schemas for the FloraCodex species search proxy."""

from sqlmodel import SQLModel


class SpeciesSearchResult(SQLModel):
    """A species hit from FloraCodex, trimmed to what the autocomplete needs."""

    pid: str
    name: str
    scientific_name: str | None = None
    image_url: str | None = None
