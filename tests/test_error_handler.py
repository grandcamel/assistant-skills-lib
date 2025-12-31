import pytest
import sys
import re
from io import StringIO
from unittest.mock import patch, Mock
from typing import Any, Dict, Type

from assistant_skills_lib.error_handler import (
    BaseAPIError,
    AuthenticationError,
    PermissionError,
    ValidationError,
    NotFoundError,
    RateLimitError,
    ConflictError,
    ServerError,
    AuthorizationError,
    sanitize_error_message,
    print_error,
    handle_errors,
    handle_api_error,
    ErrorContext,
    # For BC aliases
    APIError,
    ValidationError as BC_ValidationError, # To avoid name clash with BaseAPIError subclass
)

# --- Test Exception Hierarchy ---
def test_base_api_error_message():
    err = BaseAPIError("Test message")
    assert str(err) == "Test message"

def test_base_api_error_with_status_code_and_operation():
    err = BaseAPIError("Test message", status_code=400, operation="TestOp")
    assert str(err) == "[TestOp] (HTTP 400) Test message"

def test_authentication_error_inheritance():
    err = AuthenticationError("Auth failed")
    assert isinstance(err, BaseAPIError)

def test_authorization_error_inheritance():
    err = AuthorizationError("Authz failed")
    assert isinstance(err, PermissionError)
    assert isinstance(err, BaseAPIError)

# --- Test sanitize_error_message ---
@pytest.mark.parametrize("input_message, expected_message", [
    # API token needs 10+ chars to match the regex
    ("api_token=xyz123abcdef", "api_token=[REDACTED]"),
    ("email=test@example.com", "email=[REDACTED]"),
    ("Bearer abc.123.def", "Bearer [REDACTED]"),
    ("Basic dXNlcjpwYXNz", "Basic [REDACTED]"),
    # URL with credentials - email pattern matches 'user:pass@host.com' first
    ("https://user:pass@host.com", "https://user=[REDACTED]"),
    ("session_id=123-abc", "session_id=[REDACTED]"),
    ("password=mysecret", "password=[REDACTED]"),
    ("No sensitive data here", "No sensitive data here"),
    (123, "123") # Non-string input
])
def test_sanitize_error_message(input_message, expected_message):
    assert sanitize_error_message(input_message) == expected_message

# --- Test print_error ---
def test_print_error_simple():
    stderr_capture = StringIO()
    with patch('sys.stderr', stderr_capture):
        print_error("Simple error message")
    output = stderr_capture.getvalue()
    assert "[ERROR] Simple error message" in output

def test_print_error_with_exception():
    stderr_capture = StringIO()
    with patch('sys.stderr', stderr_capture):
        err = AuthenticationError("Auth failed")
        print_error("Failed to login", error=err)
    output = stderr_capture.getvalue()
    assert "[ERROR] Failed to login" in output
    assert "Details: Auth failed" in output
    assert "Hint: Check your API credentials/token" in output

def test_print_error_with_suggestion():
    stderr_capture = StringIO()
    with patch('sys.stderr', stderr_capture):
        print_error("Bad input", suggestion="Check your format")
    output = stderr_capture.getvalue()
    assert "[ERROR] Bad input" in output
    assert "Suggestion: Check your format" in output

@patch('traceback.print_exc')
def test_print_error_with_traceback(mock_print_exc):
    stderr_capture = StringIO()
    with patch('sys.stderr', stderr_capture):
        try:
            raise ValueError("Test")
        except ValueError as e:
            print_error("Unexpected error", error=e, show_traceback=True)
    output = stderr_capture.getvalue()
    assert "[ERROR] Unexpected error" in output
    mock_print_exc.assert_called_once()

def test_print_error_with_extra_hints():
    stderr_capture = StringIO()
    with patch('sys.stderr', stderr_capture):
        err = AuthenticationError("Auth failed")
        extra_hints = {AuthenticationError: "Custom auth hint"}
        print_error("Failed to login", error=err, extra_hints=extra_hints)
    output = stderr_capture.getvalue()
    # Both generic and custom hints are shown (custom after generic)
    assert "Hint:" in output


# --- Test handle_errors decorator ---
def test_handle_errors_success():
    @handle_errors
    def func():
        return "Success"
    assert func() == "Success"

@patch('sys.exit')
def test_handle_errors_base_api_error(mock_exit):
    stderr_capture = StringIO()
    with patch('sys.stderr', stderr_capture):
        @handle_errors
        def func():
            raise BaseAPIError("Generic API error")
        func()
    output = stderr_capture.getvalue()
    assert "[ERROR] API error" in output
    mock_exit.assert_called_once_with(1)

@patch('sys.exit')
def test_handle_errors_keyboard_interrupt(mock_exit):
    stderr_capture = StringIO()
    with patch('sys.stderr', stderr_capture):
        @handle_errors
        def func():
            raise KeyboardInterrupt
        func()
    output = stderr_capture.getvalue()
    assert "Operation cancelled by user" in output
    mock_exit.assert_called_once_with(130)

@pytest.mark.skipif(not __import__('assistant_skills_lib.error_handler', fromlist=['HAS_REQUESTS']).HAS_REQUESTS,
                    reason="requests library not installed")
@patch('sys.exit')
def test_handle_errors_connection_error(mock_exit):
    import requests
    stderr_capture = StringIO()
    with patch('sys.stderr', stderr_capture):
        @handle_errors
        def func():
            raise requests.exceptions.ConnectionError("Connection refused")
        func()
    output = stderr_capture.getvalue()
    assert "[ERROR] Connection failed" in output
    mock_exit.assert_called_once_with(1)

@patch('sys.exit')
@patch('traceback.print_exc')
def test_handle_errors_unexpected_exception(mock_print_exc, mock_exit):
    stderr_capture = StringIO()
    with patch('sys.stderr', stderr_capture):
        @handle_errors
        def func():
            raise ValueError("Something unexpected")
        func()
    output = stderr_capture.getvalue()
    assert "[ERROR] Unexpected error" in output
    mock_print_exc.assert_called_once()
    mock_exit.assert_called_once_with(1)

# --- Test ErrorContext ---
def test_error_context_no_exception():
    with ErrorContext("test_op"):
        assert True # No exception occurred

def test_error_context_with_base_api_error():
    try:
        with ErrorContext("fetching_data", resource_id="123"):
            raise BaseAPIError("Data not found")
    except BaseAPIError as e:
        assert e.operation == "fetching_data (resource_id=123)"

def test_error_context_with_non_api_error():
    try:
        with ErrorContext("doing_math"):
            raise ValueError("Bad calculation")
    except ValueError as e:
        assert str(e) == "Bad calculation"
        # operation should not be set for non-BaseAPIError exceptions

# --- Test handle_api_error ---
@patch('assistant_skills_lib.error_handler.HAS_REQUESTS', True)
def test_handle_api_error_no_error():
    mock_response = Mock(ok=True)
    handle_api_error(mock_response, "no_op") # Should not raise

@patch('assistant_skills_lib.error_handler.HAS_REQUESTS', True)
def test_handle_api_error_401():
    mock_response = Mock(status_code=401, ok=False, text='{"message": "Invalid auth"}')
    mock_response.json.return_value = {'message': 'Invalid auth'}
    with pytest.raises(AuthenticationError) as excinfo:
        handle_api_error(mock_response, "test_auth")
    assert "Invalid auth" in str(excinfo.value)
    assert excinfo.value.status_code == 401
    assert excinfo.value.operation == "test_auth"

@patch('assistant_skills_lib.error_handler.HAS_REQUESTS', True)
def test_handle_api_error_429():
    mock_response = Mock(status_code=429, ok=False, headers={'Retry-After': '60'}, text='{"message": "Rate limit"}')
    mock_response.json.return_value = {'message': 'Rate limit'}
    with pytest.raises(RateLimitError) as excinfo:
        handle_api_error(mock_response, "test_rate_limit")
    assert excinfo.value.retry_after == 60

@patch('assistant_skills_lib.error_handler.HAS_REQUESTS', False)
def test_handle_api_error_requires_requests():
    with pytest.raises(ImportError):
        handle_api_error(Mock(), "test")

# --- Test BC Aliases ---
def test_api_error_alias():
    assert APIError == BaseAPIError

def test_bc_validation_error_alias():
    assert BC_ValidationError == ValidationError