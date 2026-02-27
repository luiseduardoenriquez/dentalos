"""Health scenario — monitors /health endpoint and RabbitMQ queue depth.

Fixed 5 VUs that poll health every 10s. Also monitors RabbitMQ queue depth
via the management API every 30s.
"""

import logging
import time

import requests
from locust import constant, events, tag, task

from load_tests.scenarios._base import DentalOSUser
from load_tests.config import (
    QUEUE_DEPTH_THRESHOLD,
    RABBITMQ_API_URL,
    RABBITMQ_PASS,
    RABBITMQ_USER,
    RABBITMQ_VHOST,
)

logger = logging.getLogger("dentalos.loadtest.health")


class MonitorUser(DentalOSUser):
    """Fixed-count VU that monitors system health during load tests."""

    fixed_count = 5
    wait_time = constant(10)

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._last_queue_check = 0.0
        self._queue_check_interval = 30  # seconds

    @tag("health")
    @task
    def check_health(self) -> None:
        """GET /api/v1/health — monitors all dependency health."""
        with self.client.get(
            f"{self.api}/health",
            name="GET /health",
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 503:
                # Service degraded — expected under heavy load
                response.success()
            else:
                response.failure(f"Health check failed: {response.status_code}")

        # Check RabbitMQ queue depth periodically
        now = time.time()
        if now - self._last_queue_check >= self._queue_check_interval:
            self._last_queue_check = now
            self._check_queue_depth()

    def _check_queue_depth(self) -> None:
        """Poll RabbitMQ management API for notification queue depth."""
        try:
            url = f"{RABBITMQ_API_URL}/queues/{RABBITMQ_VHOST}/notifications"
            resp = requests.get(url, auth=(RABBITMQ_USER, RABBITMQ_PASS), timeout=5)

            if resp.status_code == 200:
                data = resp.json()
                depth = data.get("messages", 0)
                consumers = data.get("consumers", 0)

                # Fire a custom event so it shows in the Locust report
                events.request.fire(
                    request_type="MONITOR",
                    name="RabbitMQ queue depth (notifications)",
                    response_time=depth,  # Abuse response_time to log depth
                    response_length=consumers,
                    exception=None,
                    context={},
                )

                if depth > QUEUE_DEPTH_THRESHOLD:
                    logger.warning(
                        "Queue depth %d exceeds threshold %d (consumers=%d)",
                        depth, QUEUE_DEPTH_THRESHOLD, consumers,
                    )
            elif resp.status_code == 404:
                # Queue doesn't exist — workers not running
                logger.debug("Notifications queue not found (workers may not be running)")
            else:
                logger.warning("RabbitMQ API returned %d", resp.status_code)

        except requests.RequestException as e:
            logger.debug("RabbitMQ monitoring failed: %s", e)
