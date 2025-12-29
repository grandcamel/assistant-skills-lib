"""Tests for validators module."""

import pytest
from assistant_skills_lib import (
    validate_url,
    validate_required,
    validate_name,
    validate_path,
    validate_choice,
    InputValidationError,
)


class TestValidateUrl:
    """Tests for validate_url function."""

    def test_valid_https_url(self):
        """Test valid HTTPS URL."""
        result = validate_url("https://example.com")
        assert result == "https://example.com"

    def test_valid_http_url(self):
        """Test valid HTTP URL."""
        result = validate_url("http://example.com")
        assert result == "http://example.com"

    def test_url_with_path(self):
        """Test URL with path."""
        result = validate_url("https://example.com/api/v1")
        assert result == "https://example.com/api/v1"

    def test_invalid_url(self):
        """Test invalid URL."""
        with pytest.raises(InputValidationError):
            validate_url("not-a-url")

    def test_empty_url(self):
        """Test empty URL."""
        with pytest.raises(InputValidationError):
            validate_url("")


class TestValidateRequired:
    """Tests for validate_required function."""

    def test_valid_value(self):
        """Test valid non-empty value."""
        result = validate_required("hello", "field")
        assert result == "hello"

    def test_whitespace_only(self):
        """Test whitespace-only value."""
        with pytest.raises(InputValidationError):
            validate_required("   ", "field")

    def test_none_value(self):
        """Test None value."""
        with pytest.raises(InputValidationError):
            validate_required(None, "field")

    def test_empty_string(self):
        """Test empty string."""
        with pytest.raises(InputValidationError):
            validate_required("", "field")


class TestValidateName:
    """Tests for validate_name function."""

    def test_valid_name(self):
        """Test valid name."""
        result = validate_name("my-skill", "skill name")
        assert result == "my-skill"

    def test_name_with_underscore(self):
        """Test name with underscore."""
        result = validate_name("my_skill", "skill name")
        assert result == "my_skill"

    def test_name_with_numbers(self):
        """Test name with numbers."""
        result = validate_name("skill123", "skill name")
        assert result == "skill123"

    def test_invalid_name_with_spaces(self):
        """Test invalid name with spaces."""
        with pytest.raises(InputValidationError):
            validate_name("my skill", "skill name")


class TestValidatePath:
    """Tests for validate_path function."""

    def test_valid_path(self):
        """Test valid path."""
        import tempfile
        from pathlib import Path

        with tempfile.NamedTemporaryFile() as f:
            result = validate_path(f.name, "file")
            # Result may be Path or str, compare resolved paths
            assert Path(result).resolve() == Path(f.name).resolve()

    def test_nonexistent_path(self):
        """Test nonexistent path raises error."""
        with pytest.raises(InputValidationError):
            validate_path("/nonexistent/path/to/file.txt", "file")


class TestValidateChoice:
    """Tests for validate_choice function."""

    def test_valid_choice(self):
        """Test valid choice."""
        result = validate_choice("active", ["active", "inactive"], "status")
        assert result == "active"

    def test_invalid_choice(self):
        """Test invalid choice."""
        with pytest.raises(InputValidationError):
            validate_choice("unknown", ["active", "inactive"], "status")

    def test_case_insensitive(self):
        """Test case insensitivity - function accepts different cases."""
        # validate_choice is case-insensitive
        result = validate_choice("Active", ["active", "inactive"], "status")
        assert result.lower() == "active"
