"""arq worker entry point.

Pipeline stage handlers are added in their respective sub-projects (P3+).
For P1, this file establishes the WorkerSettings and a hello-world task
to verify the worker can run end-to-end.
"""

from typing import Any

from arq.connections import RedisSettings

from faceless.config import get_settings
from faceless.observability.logging import configure_logging, get_logger

log = get_logger("worker")


async def hello(ctx: dict[str, Any], name: str) -> str:
    log.info("hello.start", name=name)
    return f"hello, {name}"


async def startup(ctx: dict[str, Any]) -> None:
    configure_logging()
    log.info("worker.startup")


async def shutdown(ctx: dict[str, Any]) -> None:
    log.info("worker.shutdown")


def _redis_settings() -> RedisSettings:
    return RedisSettings.from_dsn(get_settings().redis_url)


class WorkerSettings:
    redis_settings = _redis_settings()
    on_startup = startup
    on_shutdown = shutdown
    functions = [hello]
    cron_jobs: list[Any] = []  # populated in later sub-projects
    max_jobs = 10
    job_timeout = 30 * 60  # 30 min — accommodates Kling polling later
