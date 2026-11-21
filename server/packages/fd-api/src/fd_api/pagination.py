"""Page request and response bases that every listing extends, and the count response."""

import base64
import binascii
from collections.abc import Callable, Sequence

from pydantic import BaseModel, Field, ValidationError

from fd_api.errors import InvalidFieldError

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


def decode_cursor[K: BaseModel](cursor: str | None, key_type: type[K]) -> K | None:
    """Reads an opaque cursor back into the listing's keyset position.

    Raises:
        InvalidFieldError: The cursor did not come from this listing.
    """
    if cursor is None:
        return None
    try:
        return key_type.model_validate_json(base64.urlsafe_b64decode(cursor.encode()))
    except (binascii.Error, ValueError, ValidationError) as error:
        raise InvalidFieldError("cursor", "Not a cursor from this listing.") from error


def _encode_cursor(key: BaseModel) -> str:
    return base64.urlsafe_b64encode(key.model_dump_json().encode()).decode()


def paginate[R, K: BaseModel](
    rows: Sequence[R], limit: int, key: Callable[[R], K]
) -> tuple[list[R], str | None]:
    """Splits rows fetched with `limit + 1` into one page and the next page's cursor."""
    page = list(rows[:limit])
    if len(rows) <= limit or not page:
        return page, None
    return page, _encode_cursor(key(page[-1]))
