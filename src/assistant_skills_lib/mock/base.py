"""
Base Mock Client for Assistant Skills

Provides a foundational mock client class with common functionality:
- Request/call recording for test assertions
- Response override capability
- Error simulation
- HTTP method stubs (get, post, put, delete)
- Context manager support

Service-specific libraries extend this class with domain-specific
operations and seed data.
"""

from __future__ import annotations

import os
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Optional, TypeVar

T = TypeVar("T", bound="BaseMockClient")


def create_mock_mode_checker(env_var_name: str) -> Callable[[], bool]:
    """Create a mock mode checker for a specific environment variable.

    Args:
        env_var_name: Name of the environment variable to check
                      (e.g., "JIRA_MOCK_MODE", "SPLUNK_MOCK_MODE")

    Returns:
        A function that returns True if mock mode is enabled.

    Example:
        is_mock_mode = create_mock_mode_checker("MYSERVICE_MOCK_MODE")
        if is_mock_mode():
            client = MockMyServiceClient()
    """

    def is_mock_mode() -> bool:
        return os.environ.get(env_var_name, "").lower() == "true"

    return is_mock_mode


class BaseMockClient:
    """Base mock client with common functionality for testing.

    Provides:
    - Request/call recording for test assertions
    - Response override capability for specific endpoints
    - Error simulation for testing error handling
    - HTTP method stubs (get, post, put, delete)
    - Context manager support
    - Unique ID generation
    - Timestamp utilities

    Attributes:
        base_url: Simulated service base URL
        timeout: Default request timeout
        calls: List of recorded API calls for verification
        responses: Dict of endpoint -> static response overrides
        errors: Dict of endpoint -> error to raise
    """

    DEFAULT_TIMEOUT = 30
    DEFAULT_MAX_RETRIES = 3
    DEFAULT_RETRY_BACKOFF = 2.0

    def __init__(
        self,
        base_url: str = "https://mock.example.com",
        timeout: int = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
        retry_backoff: float = DEFAULT_RETRY_BACKOFF,
        **kwargs: Any,
    ):
        """Initialize mock client.

        Args:
            base_url: Simulated service base URL
            timeout: Request timeout in seconds
            max_retries: Retry attempts (stored for interface compatibility)
            retry_backoff: Backoff multiplier (stored for interface compatibility)
            **kwargs: Additional arguments (for subclass compatibility)
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_backoff = retry_backoff

        # Call tracking
        self.calls: list[dict[str, Any]] = []

        # Response overrides
        self.responses: dict[str, Any] = {}

        # Error simulation
        self.errors: dict[str, Exception] = {}

        # Callbacks for dynamic responses
        self._callbacks: dict[str, Callable[..., Any]] = {}

        # Initialize seed data (subclasses override this)
        self._init_seed_data()

    def _init_seed_data(self) -> None:
        """Initialize seed data for mock responses.

        Subclasses should override this to set up domain-specific
        seed data (users, projects, issues, pages, etc.).
        """
        pass

    # =========================================================================
    # Utility Methods
    # =========================================================================

    def _generate_id(self) -> str:
        """Generate a unique ID for new resources.

        Returns:
            A 10-character numeric string ID.
        """
        return str(uuid.uuid4().int)[:10]

    def _now_iso(self) -> str:
        """Return current timestamp in ISO format.

        Returns:
            ISO formatted timestamp string.
        """
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")

    def _now_epoch(self) -> float:
        """Return current timestamp as epoch seconds.

        Returns:
            Current time as Unix epoch.
        """
        return time.time()

    # =========================================================================
    # Call Recording and Assertions
    # =========================================================================

    def _record_call(
        self,
        method: str,
        endpoint: str,
        params: Optional[dict[str, Any]] = None,
        data: Optional[dict[str, Any]] = None,
        **kwargs: Any,
    ) -> None:
        """Record an API call for later verification.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint path
            params: Query parameters
            data: Request body data
            **kwargs: Additional metadata to record
        """
        self.calls.append(
            {
                "method": method,
                "endpoint": endpoint,
                "params": params,
                "data": data,
                "timestamp": self._now_epoch(),
                **kwargs,
            }
        )

    def get_recorded_calls(
        self,
        method: Optional[str] = None,
        endpoint: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """Get recorded calls, optionally filtered.

        Args:
            method: Filter by HTTP method
            endpoint: Filter by endpoint (substring match)

        Returns:
            List of matching call records.
        """
        result = self.calls
        if method:
            result = [c for c in result if c["method"] == method]
        if endpoint:
            result = [c for c in result if endpoint in c["endpoint"]]
        return result

    def clear_calls(self) -> None:
        """Clear all recorded API calls."""
        self.calls.clear()

    def assert_called(
        self,
        method: str,
        endpoint: str,
        times: Optional[int] = None,
    ) -> None:
        """Assert an endpoint was called.

        Args:
            method: HTTP method
            endpoint: Endpoint path (substring match)
            times: Expected call count (None = at least once)

        Raises:
            AssertionError: If assertion fails.
        """
        matching = self.get_recorded_calls(method=method, endpoint=endpoint)
        if times is not None:
            assert len(matching) == times, (
                f"Expected {endpoint} to be called {times} times, "
                f"was called {len(matching)} times"
            )
        else:
            assert len(matching) > 0, f"Expected {endpoint} to be called at least once"

    def assert_not_called(self, method: str, endpoint: str) -> None:
        """Assert an endpoint was never called.

        Args:
            method: HTTP method
            endpoint: Endpoint path (substring match)

        Raises:
            AssertionError: If endpoint was called.
        """
        matching = self.get_recorded_calls(method=method, endpoint=endpoint)
        assert len(matching) == 0, (
            f"Expected {endpoint} to not be called, "
            f"was called {len(matching)} times"
        )

    # =========================================================================
    # Response Override and Error Simulation
    # =========================================================================

    def set_response(self, endpoint: str, response: Any) -> None:
        """Set a static response for an endpoint.

        Args:
            endpoint: API endpoint path
            response: Response to return for this endpoint
        """
        self.responses[endpoint] = response

    def set_callback(self, endpoint: str, callback: Callable[..., Any]) -> None:
        """Set a callback for dynamic response generation.

        Args:
            endpoint: API endpoint path
            callback: Function that returns response
        """
        self._callbacks[endpoint] = callback

    def set_error(self, endpoint: str, error: Exception) -> None:
        """Set an error to raise for an endpoint.

        Args:
            endpoint: API endpoint path
            error: Exception to raise
        """
        self.errors[endpoint] = error

    def clear_overrides(self) -> None:
        """Clear all response overrides, errors, and callbacks."""
        self.responses.clear()
        self.errors.clear()
        self._callbacks.clear()

    def _get_response(
        self,
        endpoint: str,
        default: Optional[dict[str, Any]] = None,
        **kwargs: Any,
    ) -> Any:
        """Get response for endpoint, checking overrides first.

        Args:
            endpoint: API endpoint path
            default: Default response if no override exists
            **kwargs: Additional context for callbacks

        Returns:
            Response data.

        Raises:
            Exception: If an error is configured for this endpoint.
        """
        # Check for error simulation
        if endpoint in self.errors:
            raise self.errors[endpoint]

        # Check for callback
        if endpoint in self._callbacks:
            return self._callbacks[endpoint](**kwargs)

        # Check for static override
        if endpoint in self.responses:
            return self.responses[endpoint]

        # Return default
        return default or {}

    # =========================================================================
    # HTTP Method Stubs
    # =========================================================================

    def get(
        self,
        endpoint: str,
        params: Optional[dict[str, Any]] = None,
        operation: str = "GET request",
        **kwargs: Any,
    ) -> Any:
        """Mock GET request.

        Args:
            endpoint: API endpoint path
            params: Query parameters
            operation: Description of operation (for logging)
            **kwargs: Additional arguments

        Returns:
            Mock response data.
        """
        self._record_call("GET", endpoint, params=params, **kwargs)
        return self._get_response(endpoint, params=params, **kwargs)

    def post(
        self,
        endpoint: str,
        data: Optional[dict[str, Any]] = None,
        params: Optional[dict[str, Any]] = None,
        operation: str = "POST request",
        **kwargs: Any,
    ) -> Any:
        """Mock POST request.

        Args:
            endpoint: API endpoint path
            data: Request body data
            params: Query parameters
            operation: Description of operation (for logging)
            **kwargs: Additional arguments

        Returns:
            Mock response data.
        """
        self._record_call("POST", endpoint, params=params, data=data, **kwargs)
        return self._get_response(endpoint, data=data, params=params, **kwargs)

    def put(
        self,
        endpoint: str,
        data: Optional[dict[str, Any]] = None,
        params: Optional[dict[str, Any]] = None,
        operation: str = "PUT request",
        **kwargs: Any,
    ) -> Any:
        """Mock PUT request.

        Args:
            endpoint: API endpoint path
            data: Request body data
            params: Query parameters
            operation: Description of operation (for logging)
            **kwargs: Additional arguments

        Returns:
            Mock response data.
        """
        self._record_call("PUT", endpoint, params=params, data=data, **kwargs)
        return self._get_response(endpoint, data=data, params=params, **kwargs)

    def delete(
        self,
        endpoint: str,
        params: Optional[dict[str, Any]] = None,
        operation: str = "DELETE request",
        **kwargs: Any,
    ) -> Any:
        """Mock DELETE request.

        Args:
            endpoint: API endpoint path
            params: Query parameters
            operation: Description of operation (for logging)
            **kwargs: Additional arguments

        Returns:
            Mock response data (often empty dict or None).
        """
        self._record_call("DELETE", endpoint, params=params, **kwargs)
        return self._get_response(endpoint, params=params, **kwargs)

    # =========================================================================
    # Reset and Context Manager
    # =========================================================================

    def reset(self) -> None:
        """Reset all mock data to initial state.

        Clears recorded calls, response overrides, and reinitializes
        seed data.
        """
        self.calls.clear()
        self.responses.clear()
        self.errors.clear()
        self._callbacks.clear()
        self._init_seed_data()

    def close(self) -> None:
        """Close the client (no-op for mock)."""
        pass

    def __enter__(self: T) -> T:
        """Enter context manager."""
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        """Exit context manager."""
        self.close()

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(base_url={self.base_url!r})"
