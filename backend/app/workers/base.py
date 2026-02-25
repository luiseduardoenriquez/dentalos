"""Base worker for consuming RabbitMQ messages."""
import asyncio
import json
import logging
from abc import ABC, abstractmethod

import aio_pika

from app.core.config import settings
from app.core.queue import publish_message
from app.schemas.queue import QueueMessage

logger = logging.getLogger("dentalos.worker")


class BaseWorker(ABC):
    """Base class for RabbitMQ consumers with retry and dead-letter logic.

    Subclasses must declare :attr:`queue_name` and implement
    :meth:`process`.  The retry strategy is exponential backoff:

    - Attempt 1 fails → sleep 2 s, re-publish with retry_count=1
    - Attempt 2 fails → sleep 4 s, re-publish with retry_count=2
    - Attempt 3 fails → sleep 8 s, re-publish with retry_count=3
    - Attempt 4 fails → max_retries exceeded → message is nack'd and
      routed to the dead-letter queue by the ``x-dead-letter-exchange``
      queue argument declared in :mod:`app.core.queue`.
    """

    queue_name: str
    prefetch_count: int = 10

    @abstractmethod
    async def process(self, message: QueueMessage) -> None:
        """Process a single message. Override in subclasses."""
        ...

    async def handle_message(self, raw_message: aio_pika.IncomingMessage) -> None:
        """Parse, process, and handle retries for an incoming message.

        Uses ``process(requeue=False)`` as the context manager so that
        if processing raises an unhandled exception the message is
        *nack'd without requeue* — RabbitMQ then routes it to the DLQ
        via the dead-letter exchange.  Explicit retry is handled by
        re-publishing with an incremented ``retry_count`` before the
        message is ack'd.
        """
        async with raw_message.process(requeue=False):
            # Decode once outside the try/except so a corrupt body still
            # results in a nack (raw_message.process handles that).
            raw_body = raw_message.body.decode()
            data = json.loads(raw_body)
            msg = QueueMessage(**data)

            try:
                await self.process(msg)
                logger.info(
                    "Processed message: queue=%s job_type=%s message_id=%s",
                    self.queue_name,
                    msg.job_type,
                    msg.message_id,
                )
            except Exception:
                logger.exception(
                    "Failed to process message: queue=%s job_type=%s "
                    "message_id=%s retry_count=%d",
                    self.queue_name,
                    msg.job_type,
                    msg.message_id,
                    msg.retry_count,
                )

                if msg.retry_count < msg.max_retries:
                    msg.retry_count += 1
                    delay = 2**msg.retry_count  # 2, 4, 8 seconds
                    logger.info(
                        "Retrying message in %ds: queue=%s message_id=%s attempt=%d/%d",
                        delay,
                        self.queue_name,
                        msg.message_id,
                        msg.retry_count,
                        msg.max_retries,
                    )
                    await asyncio.sleep(delay)
                    await publish_message(self.queue_name, msg)
                else:
                    # Max retries exceeded — re-raise so the context manager
                    # nack's the message and RabbitMQ routes it to the DLQ.
                    logger.error(
                        "Max retries exceeded — dead-lettering message: "
                        "queue=%s message_id=%s",
                        self.queue_name,
                        msg.message_id,
                    )
                    raise

    async def start(self) -> None:
        """Connect to RabbitMQ and start consuming from :attr:`queue_name`."""
        connection = await aio_pika.connect_robust(settings.rabbitmq_url)
        channel = await connection.channel()
        await channel.set_qos(prefetch_count=self.prefetch_count)
        queue = await channel.get_queue(self.queue_name)
        await queue.consume(self.handle_message)
        logger.info(
            "Worker started: consuming from queue=%s prefetch=%d",
            self.queue_name,
            self.prefetch_count,
        )
