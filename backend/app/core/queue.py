"""RabbitMQ connection manager: exchanges, queues, and message publishing."""
import json
import logging

import aio_pika
from aio_pika import ExchangeType

from app.core.config import settings
from app.schemas.queue import QueueMessage

logger = logging.getLogger("dentalos.queue")

# ─── Module-level state ───────────────────────────────────────────────────────

_connection: aio_pika.abc.AbstractRobustConnection | None = None
_channel: aio_pika.abc.AbstractChannel | None = None
_exchange: aio_pika.abc.AbstractExchange | None = None

# ─── Queue / exchange names ───────────────────────────────────────────────────

EXCHANGE_DIRECT = "dentalos.direct"
EXCHANGE_DLX = "dentalos.dlx"

QUEUES = ["notifications", "clinical", "import", "maintenance"]


# ─── Lifecycle ───────────────────────────────────────────────────────────────


async def connect_rabbitmq() -> None:
    """Connect to RabbitMQ and declare all exchanges and queues.

    Gracefully degrades: logs a warning and returns without raising if
    RabbitMQ is unavailable so the API can still start.
    """
    global _connection, _channel, _exchange  # noqa: PLW0603

    try:
        _connection = await aio_pika.connect_robust(settings.rabbitmq_url)
        _channel = await _connection.channel()

        # ── Declare exchanges ─────────────────────────────────────────────
        _exchange = await _channel.declare_exchange(
            EXCHANGE_DIRECT,
            ExchangeType.DIRECT,
            durable=True,
        )
        dlx_exchange = await _channel.declare_exchange(
            EXCHANGE_DLX,
            ExchangeType.FANOUT,
            durable=True,
        )

        # ── Declare main queues + dead-letter queues ───────────────────────
        for queue_name in QUEUES:
            dlq_name = f"{queue_name}.dlq"

            # Dead-letter queue: bound to the fanout DLX
            dlq = await _channel.declare_queue(
                dlq_name,
                durable=True,
            )
            await dlq.bind(dlx_exchange, routing_key=dlq_name)

            # Main queue: routes failed messages to DLX
            main_queue = await _channel.declare_queue(
                queue_name,
                durable=True,
                arguments={"x-dead-letter-exchange": EXCHANGE_DLX},
            )
            await main_queue.bind(_exchange, routing_key=queue_name)

        logger.info(
            "RabbitMQ connected — exchange=%s queues=%s",
            EXCHANGE_DIRECT,
            QUEUES,
        )

    except Exception:
        logger.warning(
            "RabbitMQ unavailable — queue publishing disabled. "
            "Start RabbitMQ to enable async job processing.",
            exc_info=True,
        )
        _connection = None
        _channel = None
        _exchange = None


async def close_rabbitmq() -> None:
    """Close the RabbitMQ connection cleanly on application shutdown."""
    global _connection, _channel, _exchange  # noqa: PLW0603

    if _connection is not None and not _connection.is_closed:
        try:
            await _connection.close()
            logger.info("RabbitMQ connection closed")
        except Exception:
            logger.warning("Error while closing RabbitMQ connection", exc_info=True)

    _connection = None
    _channel = None
    _exchange = None


# ─── Publishing ───────────────────────────────────────────────────────────────


async def publish_message(queue_name: str, message: QueueMessage) -> None:
    """Publish a message to the named queue via the direct exchange.

    Args:
        queue_name: One of ``notifications``, ``clinical``, ``import``,
            ``maintenance``.
        message: The fully-populated :class:`QueueMessage` envelope.

    If RabbitMQ is unavailable the call is a no-op (logs a warning).
    This preserves graceful degradation — callers never need to handle
    connection errors.
    """
    if _exchange is None:
        logger.warning(
            "RabbitMQ not connected — dropping message: queue=%s job_type=%s",
            queue_name,
            message.job_type,
        )
        return

    body = message.model_dump_json().encode()

    await _exchange.publish(
        aio_pika.Message(
            body=body,
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            priority=message.priority,
            content_type="application/json",
            message_id=message.message_id,
        ),
        routing_key=queue_name,
    )

    logger.debug(
        "Published message: queue=%s job_type=%s message_id=%s",
        queue_name,
        message.job_type,
        message.message_id,
    )


# ─── Health check helper ──────────────────────────────────────────────────────


def is_connected() -> bool:
    """Return True if the RabbitMQ connection is active."""
    return _connection is not None and not _connection.is_closed


async def get_queue_json_stats() -> dict:
    """Return basic connectivity info for health-check endpoints."""
    return {
        "connected": is_connected(),
        "exchange": EXCHANGE_DIRECT,
        "queues": QUEUES,
    }
