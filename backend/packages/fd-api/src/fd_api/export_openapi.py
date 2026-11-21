"""Writes the API's OpenAPI schema to the contract file (`make openapi`)."""

import json
from typing import Any

from fd_api.main import create_app
from fd_api.settings import ApiSettings
from fd_shared.logging import get_logger

log = get_logger(__name__)


def render_openapi(settings: ApiSettings) -> str:
    """Returns the app's OpenAPI schema as the exact text committed to the contract file."""
    schema: dict[str, Any] = create_app(settings).openapi()
    return json.dumps(schema, indent=2, ensure_ascii=False) + "\n"


def main() -> None:
    """Writes the schema to `ApiSettings.openapi_path`."""
    settings = ApiSettings()
    settings.openapi_path.parent.mkdir(parents=True, exist_ok=True)
    settings.openapi_path.write_text(render_openapi(settings), encoding="utf-8")
    log.info("openapi.written", path=str(settings.openapi_path))


if __name__ == "__main__":
    main()
