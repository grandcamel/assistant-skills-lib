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


class TestValidateContext:
    """Tests for validate_context function."""

    def test_valid_context(self):
        """Test validation with all placeholders provided."""
        from assistant_skills_lib.template_engine import validate_context

        template = "Hello {{NAME}}, welcome to {{PROJECT}}!"
        context = {"NAME": "World", "PROJECT": "Test"}
        result = validate_context(template, context)

        assert result["valid"] is True
        assert result["missing"] == []
        assert set(result["used"]) == {"NAME", "PROJECT"}
        assert result["extra"] == []

    def test_missing_placeholders(self):
        """Test validation with missing placeholders."""
        from assistant_skills_lib.template_engine import validate_context

        template = "Hello {{NAME}}, welcome to {{PROJECT}}!"
        context = {"NAME": "World"}
        result = validate_context(template, context)

        assert result["valid"] is False
        assert "PROJECT" in result["missing"]
        assert "NAME" in result["used"]

    def test_extra_context_keys(self):
        """Test validation reports extra unused keys."""
        from assistant_skills_lib.template_engine import validate_context

        template = "Hello {{NAME}}!"
        context = {"NAME": "World", "UNUSED": "value"}
        result = validate_context(template, context)

        assert result["valid"] is True
        assert "UNUSED" in result["extra"]

    def test_empty_template(self):
        """Test validation with empty template."""
        from assistant_skills_lib.template_engine import validate_context

        template = "No placeholders here"
        context = {"KEY": "value"}
        result = validate_context(template, context)

        assert result["valid"] is True
        assert result["missing"] == []
        assert result["used"] == []
        assert "KEY" in result["extra"]


class TestGetTemplateDir:
    """Tests for get_template_dir function."""

    def test_returns_path(self):
        """Test that get_template_dir returns a Path object."""
        from assistant_skills_lib.template_engine import get_template_dir
        from pathlib import Path

        result = get_template_dir()

        assert isinstance(result, Path)


class TestLoadTemplate:
    """Tests for load_template function."""

    def test_load_existing_file(self, tmp_path):
        """Test loading an existing template file."""
        template_file = tmp_path / "test.md"
        template_file.write_text("Hello {{NAME}}!")

        result = load_template(str(template_file))

        assert result == "Hello {{NAME}}!"

    def test_load_nonexistent_file(self, tmp_path):
        """Test loading a nonexistent file raises error."""
        nonexistent = tmp_path / "nonexistent.md"

        with pytest.raises(FileNotFoundError):
            load_template(str(nonexistent))

    def test_load_directory_raises_error(self, tmp_path):
        """Test loading a directory raises error."""
        with pytest.raises(ValueError):
            load_template(str(tmp_path))

    def test_load_with_unicode(self, tmp_path):
        """Test loading template with unicode content."""
        template_file = tmp_path / "unicode.md"
        template_file.write_text("Hello {{NAME}}! \u2764 \U0001F600", encoding="utf-8")

        result = load_template(str(template_file))

        assert "\u2764" in result
        assert "\U0001F600" in result


class TestListTemplateFiles:
    """Tests for list_template_files function."""

    def test_returns_list(self):
        """Test that list_template_files returns a list."""
        from assistant_skills_lib.template_engine import list_template_files

        result = list_template_files()

        assert isinstance(result, list)

    def test_result_structure(self):
        """Test that results have expected structure."""
        from assistant_skills_lib.template_engine import list_template_files

        result = list_template_files()

        # Even if empty, structure should be valid
        for item in result:
            assert "name" in item
            assert "path" in item
            assert "category" in item

    def test_filter_by_category(self):
        """Test filtering by category."""
        from assistant_skills_lib.template_engine import list_template_files

        # Filter by a category substring
        result = list_template_files(category="testing")

        # All results should contain the category filter
        for item in result:
            assert "testing" in item["category"] or len(result) == 0
