"""Page request and response bases that every listing extends, and the count response."""

from pydantic import BaseModel, Field

DEFAULT_PAGE_LIMIT = 50
MAX_PAGE_LIMIT = 100


class PageRequest(BaseModel):
    """The paging fields of a listing request."""

    limit: int = Field(
        default=DEFAULT_PAGE_LIMIT,
        ge=1,
        le=MAX_PAGE_LIMIT,
        description="Most items to return in this page.",
    )
    cursor: str | None = Field(
        default=None,
        description="The previous page's `next_cursor`, or null for the first page.",
    )


class PageResponse[T](BaseModel):
    """One page of a listing."""

    items: list[T] = Field(description="The items in this page.")
    next_cursor: str | None = Field(
        description="Cursor for the next page, or null on the last page."
    )


class CountResponse(BaseModel):
    """The number of objects that match a filter."""

    count: int = Field(ge=0, description="Number of matching objects.")
