# -*- coding: utf-8 -*-
import uvicorn

from chaoxing.web.app import app
from chaoxing.web.settings import get_backend_settings


def main() -> None:
    settings = get_backend_settings()
    uvicorn.run(
        "web_api:app",
        host=settings.server_host,
        port=settings.server_port,
        reload=settings.server_reload,
    )


if __name__ == "__main__":
    main()
