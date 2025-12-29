"""Tests for template_engine module."""

import pytest
from assistant_skills_lib import (
    load_template,
    render_template,
    list_placeholders,
)


class TestListPlaceholders:
    """Tests for list_placeholders function."""

    def test_find_placeholders(self):
        """Test finding placeholders in template."""
        template = "Hello {{NAME}}, welcome to {{PROJECT}}!"
        placeholders = list_placeholders(template)
        assert "NAME" in placeholders
        assert "PROJECT" in placeholders

    def test_no_placeholders(self):
        """Test template with no placeholders."""
        template = "Hello, world!"
        placeholders = list_placeholders(template)
        assert len(placeholders) == 0

    def test_duplicate_placeholders(self):
        """Test duplicate placeholders are returned once."""
        template = "{{NAME}} and {{NAME}} again"
        placeholders = list_placeholders(template)
        # Should return unique placeholders
        assert placeholders.count("NAME") == 1 or len(set(placeholders)) == len(placeholders)


class TestRenderTemplate:
    """Tests for render_template function."""

    def test_basic_render(self):
        """Test basic template rendering."""
        template = "Hello {{NAME}}!"
        result = render_template(template, {"NAME": "World"})
        assert result == "Hello World!"

    def test_multiple_placeholders(self):
        """Test rendering with multiple placeholders."""
        template = "{{GREETING}}, {{NAME}}!"
        result = render_template(template, {"GREETING": "Hello", "NAME": "World"})
        assert result == "Hello, World!"

    def test_missing_placeholder_strict(self):
        """Test missing placeholder in strict mode."""
        template = "Hello {{NAME}}!"
        with pytest.raises(Exception):  # Could be KeyError or custom exception
            render_template(template, {}, strict=True)

    def test_missing_placeholder_non_strict(self):
        """Test missing placeholder in non-strict mode."""
        template = "Hello {{NAME}}!"
        result = render_template(template, {}, strict=False)
        # Should either leave placeholder or replace with empty
        assert "Hello" in result
