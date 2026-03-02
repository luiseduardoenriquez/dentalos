"""CLI entry point for DentalOS background workers.

Usage:
    python -m app.workers.main              # Start all workers
    python -m app.workers.main --worker voice   # Start voice worker only

Workers consume from RabbitMQ queues and process async jobs.
"""

import asyncio
import logging
import signal
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("dentalos.worker.main")


async def main(worker_name: str | None = None) -> None:
    """Start one or all workers and block until interrupted."""
    # Ensure RabbitMQ exchanges + queues exist (sets up module-level _exchange
    # needed by publish_message for retry logic in BaseWorker).
    from app.core.queue import connect_rabbitmq

    await connect_rabbitmq()

    # Select and start workers
    workers = []

    if worker_name is None or worker_name == "voice":
        from app.workers.voice_worker import voice_worker

        workers.append(voice_worker)

    if worker_name is None or worker_name == "notification":
        from app.workers.notification_worker import notification_worker

        workers.append(notification_worker)

    if worker_name is None or worker_name == "compliance":
        from app.workers.compliance_worker import compliance_worker

        workers.append(compliance_worker)

    if worker_name is None or worker_name == "import":
        from app.workers.import_worker import import_worker

        workers.append(import_worker)

    if worker_name is None or worker_name == "maintenance":
        from app.workers.maintenance_worker import maintenance_worker

        workers.append(maintenance_worker)

    if not workers:
        logger.error("No workers matched name: %s", worker_name)
        sys.exit(1)

    for w in workers:
        await w.start()

    logger.info("All workers started. Press Ctrl+C to stop.")

    # Keep alive until interrupted
    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop_event.set)
    await stop_event.wait()

    logger.info("Shutting down workers...")


if __name__ == "__main__":
    worker_arg = None
    if "--worker" in sys.argv:
        idx = sys.argv.index("--worker")
        if idx + 1 < len(sys.argv):
            worker_arg = sys.argv[idx + 1]

    asyncio.run(main(worker_arg))
