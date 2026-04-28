from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from faceless import __version__
from faceless.api.errors import register_exception_handlers
from faceless.api.routes import health, me
from faceless.config import get_settings
from faceless.observability.logging import configure_logging


def create_app() -> FastAPI:
    configure_logging()
    settings = get_settings()
    app = FastAPI(
        title="Faceless YT API",
        version=__version__,
        docs_url="/api/docs" if settings.environment != "prod" else None,
        redoc_url=None,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[o.strip() for o in settings.cors_allow_origins.split(",")],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)

    api_v1 = "/api/v1"
    app.include_router(health.router, prefix=api_v1)
    app.include_router(me.router, prefix=api_v1)

    return app


app = create_app()
