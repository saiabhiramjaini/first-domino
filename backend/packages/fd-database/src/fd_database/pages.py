"""Keyset positions for paged reads. The API turns them into opaque cursors."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class TimeKey(BaseModel):
    """Position in a newest-first listing: the last row's time and id."""

    model_config = ConfigDict(frozen=True)

    at: datetime
    id: UUID


class CountKey(BaseModel):
    """Position in a largest-first listing: the last row's count and id."""

    model_config = ConfigDict(frozen=True)

    count: int
    id: UUID


class IndexKey(BaseModel):
    """Position in an index-ordered listing: the last row's index."""

    model_config = ConfigDict(frozen=True)

    index: int
