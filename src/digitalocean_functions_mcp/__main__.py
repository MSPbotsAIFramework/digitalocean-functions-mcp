"""Entry point: start the HTTP server (uvicorn)."""

import uvicorn

from .config import load_settings
from .server import build_app


def main() -> None:
    settings = load_settings()
    app = build_app(settings.do_base_url)
    uvicorn.run(app, host=settings.mcp_http_host, port=settings.mcp_http_port)


if __name__ == "__main__":
    main()
