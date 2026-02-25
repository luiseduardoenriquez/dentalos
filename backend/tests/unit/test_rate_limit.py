from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.exceptions import RateLimitError
from app.core.rate_limit import check_rate_limit


def _make_mock_redis(execute_return):
    """Create a properly mocked Redis client for pipeline operations.

    pipeline() is sync (returns Pipeline), pipeline methods are sync (buffer),
    only execute() is async.
    """
    mock_redis = MagicMock()
    mock_pipe = MagicMock()
    mock_pipe.execute = AsyncMock(return_value=execute_return)
    mock_redis.pipeline.return_value = mock_pipe
    return mock_redis


@pytest.mark.unit
class TestRateLimit:
    async def test_within_limit(self):
        mock_redis = _make_mock_redis([None, 0, None, None])
        with patch("app.core.rate_limit.redis_client", mock_redis):
            await check_rate_limit("test:key", limit=5, window_seconds=60)

    async def test_exceeds_limit(self):
        mock_redis = _make_mock_redis([None, 5, None, None])
        with patch("app.core.rate_limit.redis_client", mock_redis), pytest.raises(RateLimitError):
            await check_rate_limit("test:key", limit=5, window_seconds=60)

    async def test_redis_down_allows_request(self):
        mock_redis = MagicMock()
        mock_redis.pipeline.side_effect = ConnectionError("Redis down")
        with patch("app.core.rate_limit.redis_client", mock_redis):
            # Should not raise — graceful degradation
            await check_rate_limit("test:key", limit=5, window_seconds=60)
