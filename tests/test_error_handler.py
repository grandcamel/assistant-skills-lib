"""Tests for error_handler module."""

import pytest
from assistant_skills_lib import (
    APIError,
    AuthenticationError,
    NotFoundError,
    RateLimitError,
    ValidationError,
    sanitize_error_message,
    ErrorContext,
)


class TestAPIError:
    """Tests for APIError and subclasses."""

    def test_api_error_basic(self):
        """Test basic APIError."""
        error = APIError("Something went wrong", status_code=500)
        assert str(error) == "(500) Something went wrong"
        assert error.status_code == 500

    def test_api_error_with_operation(self):
        """Test APIError with operation."""
        error = APIError("Failed", status_code=500, operation="fetch user")
        assert "[fetch user]" in str(error)
        assert "(500)" in str(error)

    def test_authentication_error(self):
        """Test AuthenticationError."""
        error = AuthenticationError("Invalid token", status_code=401)
        assert isinstance(error, APIError)
        assert error.status_code == 401

    def test_not_found_error(self):
        """Test NotFoundError."""
        error = NotFoundError("User not found", status_code=404)
        assert isinstance(error, APIError)
        assert error.status_code == 404

    def test_rate_limit_error(self):
        """Test RateLimitError with retry_after."""
        error = RateLimitError("Too many requests", status_code=429, retry_after=60)
        assert isinstance(error, APIError)
        assert error.retry_after == 60

    def test_validation_error(self):
        """Test ValidationError."""
        error = ValidationError("Invalid input", status_code=400)
        assert isinstance(error, APIError)
        assert error.status_code == 400


class TestSanitizeErrorMessage:
    """Tests for sanitize_error_message function."""

    def test_sanitize_api_token(self):
        """Test sanitizing API token."""
        message = 'api_token="abc123secret456"'
        result = sanitize_error_message(message)
        assert "abc123secret456" not in result
        assert "REDACTED" in result

    def test_sanitize_bearer_token(self):
        """Test sanitizing Bearer token."""
        message = "Authorization: Bearer eyJhbGciOiJIUzI1NiJ9"
        result = sanitize_error_message(message)
        assert "eyJhbGciOiJIUzI1NiJ9" not in result
        assert "REDACTED" in result

    def test_sanitize_password(self):
        """Test sanitizing password."""
        message = 'password="mysecretpass"'
        result = sanitize_error_message(message)
        assert "mysecretpass" not in result
        assert "REDACTED" in result

    def test_sanitize_url_credentials(self):
        """Test sanitizing URL with credentials."""
        message = "https://user:pass@api.example.com"
        result = sanitize_error_message(message)
        assert "user:pass" not in result
        assert "REDACTED" in result

    def test_no_sanitization_needed(self):
        """Test message with no sensitive data."""
        message = "Connection timeout after 30 seconds"
        result = sanitize_error_message(message)
        assert result == message


class TestErrorContext:
    """Tests for ErrorContext context manager."""

    def test_error_context_enhances_error(self):
        """Test that ErrorContext enhances APIError."""
        with pytest.raises(APIError) as exc_info:
            with ErrorContext("creating resource", resource_id=123):
                raise APIError("Failed to create")

        assert "creating resource" in exc_info.value.operation
        assert "resource_id=123" in exc_info.value.operation

    def test_error_context_no_error(self):
        """Test ErrorContext with no error."""
        # Should not raise
        with ErrorContext("doing something"):
            result = 1 + 1
        assert result == 2

    def test_error_context_non_api_error(self):
        """Test ErrorContext with non-APIError."""
        with pytest.raises(ValueError):
            with ErrorContext("doing something"):
                raise ValueError("Not an API error")
