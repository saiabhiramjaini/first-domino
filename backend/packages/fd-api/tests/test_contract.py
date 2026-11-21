"""The committed contract file matches the live API schema."""

from fd_api.export_openapi import render_openapi
from fd_api.settings import ApiSettings


def test_committed_openapi_matches_live_schema(settings: ApiSettings) -> None:
    committed = settings.openapi_path.read_text(encoding="utf-8")
    assert committed == render_openapi(settings), (
        "api/openapi.json is stale. Run `make openapi` and `make sdk-models`, then commit both."
    )
