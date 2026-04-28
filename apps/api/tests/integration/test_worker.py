import pytest
from arq import create_pool
from arq.worker import Worker

from faceless.worker import WorkerSettings


@pytest.mark.asyncio
async def test_can_enqueue_and_run_hello_task():
    pool = await create_pool(WorkerSettings.redis_settings)
    try:
        await pool.flushdb()
        job = await pool.enqueue_job("hello", "world")
        assert job is not None

        worker = Worker(
            functions=WorkerSettings.functions,
            redis_settings=WorkerSettings.redis_settings,
            on_startup=WorkerSettings.on_startup,
            on_shutdown=WorkerSettings.on_shutdown,
            burst=True,
            poll_delay=0.1,
        )
        await worker.async_run()

        result = await job.result(timeout=5)
        assert result == "hello, world"
    finally:
        await pool.close()
