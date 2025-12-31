"""
Error Handling for Assistant Skills

Provides:
- Base exception hierarchy for API errors
- Generic error handling decorator
- Generic error sanitization for sensitive data
- Generic formatted error output

Usage:
    from assistant_skills_lib.error_handler import handle_errors, BaseAPIError, print_error

    @handle_errors
    def main():
        # Your code here
        pass
"""

import functools
import re
import sys
import traceback
from typing import Any, Callable, Optional, Union

# Try to import requests for specific exception handling at the base level
try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False


class BaseAPIError(Exception):
    """
    Base exception for all API-related errors.
    Service-specific errors should inherit from this.
    """

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        response_data: Optional[Union[str, dict[str, Any]]] = None, # Raw response data, can be text or parsed JSON
        operation: Optional[str] = None,
        details: Optional[dict[str, Any]] = None, # For additional service-specific details
    ):
        self.message = message
        self.status_code = status_code
        self.response_data = response_data
        self.operation = operation
        self.details = details or {}
        super().__init__(self.message)

    def __str__(self) -> str:
        parts = []
        if self.operation:
            parts.append(f"[{self.operation}]")
        if self.status_code:
            parts.append(f"(HTTP {self.status_code})")
        parts.append(self.message)
        return " ".join(parts)


class AuthenticationError(BaseAPIError):
    """Raised when authentication fails (e.g., 401 Unauthorized)."""
    pass


class PermissionError(BaseAPIError):
    """Raised when user lacks permission (e.g., 403 Forbidden)."""
    pass


class ValidationError(BaseAPIError):
    """Raised for invalid input or bad requests (e.g., 400 Bad Request)."""
    pass


class NotFoundError(BaseAPIError):
    """Raised when resource is not found (e.g., 404 Not Found)."""
    pass


class RateLimitError(BaseAPIError):
    """Raised when rate limit is exceeded (e.g., 429 Too Many Requests)."""

    def __init__(
        self,
        message: str,
        retry_after: Optional[int] = None,
        **kwargs: Any
    ):
        super().__init__(message, **kwargs)
        self.retry_after = retry_after


class ConflictError(BaseAPIError):
    """Raised on resource conflicts (e.g., 409 Conflict)."""
    pass


class ServerError(BaseAPIError):
    """Raised for server-side errors (e.g., 5xx)."""
    pass

# Generic authorization error (e.g. for Splunk's AuthorizationError)
class AuthorizationError(PermissionError):
    """Raised when user lacks specific authorization."""
    pass


def sanitize_error_message(message: str) -> str:
    """
    Remove common sensitive information from error messages.
    Service-specific sanitization should extend this.

    Args:
        message: The error message to sanitize

    Returns:
        Sanitized message with sensitive data removed
    """
    if not isinstance(message, str):
        return str(message) # Ensure message is a string

    # Common patterns to sanitize
    patterns = [
        # Generic API tokens/keys (various formats)
        (r'(?i)(api[_-]?token|token|apikey|api[_-]?key)["\s:=]+[A-Za-z0-9_\-]{10,}', r'\1=[REDACTED]'),
        # Email addresses
        (r'(?i)(email|user)["\s:=]+[\w.+-]+@[\w.-]+', r'\1=[REDACTED]'),
        # Bearer tokens
        (r'Bearer\s+[A-Za-z0-9_\-\.]+', 'Bearer [REDACTED]'),
        # Basic auth base64
        (r'Basic\s+[A-Za-z0-9+/=]+', 'Basic [REDACTED]'),
        # URLs with credentials
        (r'https?://[^:]+:[^@]+@', 'https://[REDACTED]@'),
        # Session IDs
        (r'(?i)(session[_-]?id|jsessionid)["\s:=]+[A-Za-z0-9_\-]+', r'\1=[REDACTED]'),
        # Generic secrets/passwords
        (r'(?i)(secret|password|passwd|pwd)["\s:=]+[^\s"\\]+', r'\1=[REDACTED]'),
    ]

    sanitized = message
    for pattern, replacement in patterns:
        sanitized = re.sub(pattern, replacement, sanitized)

    return sanitized


def print_error(
    message: str,
    error: Optional[BaseAPIError] = None, # Expects BaseAPIError or subclass
    suggestion: Optional[str] = None,
    show_traceback: bool = False,
    extra_hints: Optional[dict[type[BaseAPIError], str]] = None,
) -> None:
    """
    Print a formatted error message to stderr.

    Args:
        message: The main error message
        error: Optional BaseAPIError object or subclass
        suggestion: Optional suggestion for resolution
        show_traceback: Whether to print the full traceback
        extra_hints: Dictionary mapping error types to specific hints (e.g., {AuthenticationError: "Check token"})
    """
    print(f"\n[ERROR] {message}", file=sys.stderr)

    if error:
        error_str = sanitize_error_message(str(error))
        print(f"  Details: {error_str}", file=sys.stderr)

        # Generic hints
        if isinstance(error, AuthenticationError):
            print("  Hint: Check your API credentials/token", file=sys.stderr)
        elif isinstance(error, PermissionError):
            print("  Hint: Verify you have access to this resource", file=sys.stderr)
        elif isinstance(error, RateLimitError) and error.retry_after:
            print(f"  Hint: Wait {error.retry_after} seconds before retrying", file=sys.stderr)
        elif isinstance(error, NotFoundError):
            print("  Hint: Check that the resource ID/key is correct", file=sys.stderr)

        # Service-specific hints provided by subclass
        if extra_hints:
            for error_type, hint in extra_hints.items():
                if isinstance(error, error_type):
                    print(f"  Hint: {hint}", file=sys.stderr)
                    break # Apply only the first matching hint

    if suggestion:
        print(f"  Suggestion: {suggestion}", file=sys.stderr)

    if show_traceback and error:
        print("\n  Traceback:", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)

    print("", file=sys.stderr)


def handle_errors(func: Callable) -> Callable:
    """
    Decorator to handle errors in main functions.

    Catches common BaseAPIError exceptions and prints formatted error messages,
    then exits with appropriate status code.
    Service-specific error handling should call super().handle_errors
    or extend this with custom exception catches.

    Usage:
        @handle_errors
        def main():
            # Your code here
            pass

    Args:
        func: The function to wrap

    Returns:
        Wrapped function with error handling
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        try:
            return func(*args, **kwargs)
        except KeyboardInterrupt:
            print("\n\nOperation cancelled by user.", file=sys.stderr)
            sys.exit(130)
        except AuthenticationError as e:
            print_error("Authentication failed", e)
            sys.exit(1)
        except PermissionError as e:
            print_error("Permission denied", e)
            sys.exit(1)
        except ValidationError as e:
            print_error("Invalid input", e)
            sys.exit(1)
        except NotFoundError as e:
            print_error("Resource not found", e)
            sys.exit(1)
        except RateLimitError as e:
            print_error("Rate limit exceeded", e)
            sys.exit(1)
        except ConflictError as e:
            print_error("Conflict error", e)
            sys.exit(1)
        except ServerError as e:
            print_error("Server error", e)
            sys.exit(1)
        except BaseAPIError as e:
            print_error("API error", e)
            sys.exit(1)
        except Exception as e:
            # Handle requests exceptions if available
            if HAS_REQUESTS:
                if isinstance(e, requests.exceptions.ConnectionError):
                    print_error(
                        "Connection failed",
                        e,
                        suggestion="Check your network connection and API URL"
                    )
                    sys.exit(1)
                elif isinstance(e, requests.exceptions.Timeout):
                    print_error(
                        "Request timed out",
                        e,
                        suggestion="The server took too long to respond. Try again later."
                    )
                    sys.exit(1)

            print_error(
                "Unexpected error",
                e,
                show_traceback=True
            )
            sys.exit(1)

    return wrapper


class ErrorContext:
    """
    Context manager for error handling with custom messages.
    It expects BaseAPIError or its subclasses.

    Usage:
        with ErrorContext("creating resource", resource_id=id):
            client.post("/api/resources", data=resource_data)
    """

    def __init__(self, operation: str, **context: Any):
        self.operation = operation
        self.context = context

    def __enter__(self) -> 'ErrorContext':
        return self

    def __exit__(self, exc_type: Optional[type[BaseAPIError]], exc_val: Optional[BaseAPIError], exc_tb: Any) -> bool:
        if exc_type is not None and issubclass(exc_type, BaseAPIError):
            # Enhance error message with context
            context_str = ", ".join(f"{k}={v}" for k, v in self.context.items())
            exc_val.operation = f"{self.operation} ({context_str})" if context_str else self.operation
        return False  # Don't suppress the exception


# Backwards-compatible alias
APIError = BaseAPIError


def handle_api_error(response: Any, operation: Optional[str] = None) -> None:
    """
    Handle API error responses by raising appropriate exceptions.

    This is a generic handler that can be extended by service-specific implementations.
    Requires the 'requests' library for full functionality.

    Args:
        response: The HTTP response object (expects requests.Response)
        operation: Optional operation name for error context

    Raises:
        AuthenticationError: For 401 responses
        PermissionError: For 403 responses
        NotFoundError: For 404 responses
        RateLimitError: For 429 responses
        ValidationError: For 400 responses
        ConflictError: For 409 responses
        ServerError: For 5xx responses
        BaseAPIError: For other error responses
    """
    if not HAS_REQUESTS:
        raise ImportError("handle_api_error requires the 'requests' library")

    if not hasattr(response, 'status_code'):
        return  # Not a response object

    if response.ok:
        return  # No error to handle

    status_code = response.status_code

    # Try to extract error message from response
    try:
        error_data = response.json()
        if isinstance(error_data, dict):
            message = error_data.get('message') or error_data.get('error') or error_data.get('errorMessage') or str(error_data)
        else:
            message = str(error_data)
    except (ValueError, AttributeError):
        message = response.text or f"HTTP {status_code}"

    kwargs = {
        'message': message,
        'status_code': status_code,
        'response_data': response.text,
        'operation': operation,
    }

    if status_code == 401:
        raise AuthenticationError(**kwargs)
    elif status_code == 403:
        raise PermissionError(**kwargs)
    elif status_code == 404:
        raise NotFoundError(**kwargs)
    elif status_code == 429:
        retry_after = response.headers.get('Retry-After')
        raise RateLimitError(
            retry_after=int(retry_after) if retry_after else None,
            **kwargs
        )
    elif status_code == 400:
        raise ValidationError(**kwargs)
    elif status_code == 409:
        raise ConflictError(**kwargs)
    elif status_code >= 500:
        raise ServerError(**kwargs)
    else:
        raise BaseAPIError(**kwargs)
