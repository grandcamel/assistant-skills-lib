"""Tests for formatters module."""

import pytest
from assistant_skills_lib import (
    format_table,
    format_tree,
    format_list,
    format_json,
    format_count,
    Colors,
)


class TestFormatTable:
    """Tests for format_table function."""

    def test_basic_table(self):
        """Test basic table formatting."""
        data = [
            {"name": "Alice", "age": 30},
            {"name": "Bob", "age": 25},
        ]
        result = format_table(data, headers=["name", "age"])
        assert "Alice" in result
        assert "Bob" in result
        assert "30" in result
        assert "25" in result

    def test_empty_data(self):
        """Test with empty data."""
        result = format_table([], headers=["name"])
        assert result is not None

    def test_single_row(self):
        """Test with single row."""
        data = [{"name": "Alice"}]
        result = format_table(data, headers=["name"])
        assert "Alice" in result


class TestFormatTree:
    """Tests for format_tree function."""

    def test_simple_tree(self):
        """Test simple tree formatting."""
        items = [
            {"name": "child1"},
            {"name": "child2"},
        ]
        result = format_tree("root", items)
        assert "root" in result
        assert "child1" in result
        assert "child2" in result

    def test_nested_tree(self):
        """Test nested tree formatting."""
        items = [
            {"name": "child", "children": [{"name": "grandchild"}]},
        ]
        result = format_tree("root", items)
        assert "root" in result
        assert "child" in result
        assert "grandchild" in result


class TestFormatList:
    """Tests for format_list function."""

    def test_basic_list(self):
        """Test basic list formatting."""
        items = ["item1", "item2", "item3"]
        result = format_list(items)
        assert "item1" in result
        assert "item2" in result
        assert "item3" in result

    def test_custom_bullet(self):
        """Test custom bullet character."""
        items = ["item1", "item2"]
        result = format_list(items, bullet="*")
        assert "*" in result

    def test_empty_list(self):
        """Test empty list."""
        result = format_list([])
        assert result == ""


class TestFormatJson:
    """Tests for format_json function."""

    def test_basic_json(self):
        """Test basic JSON formatting."""
        data = {"key": "value"}
        result = format_json(data)
        assert '"key"' in result
        assert '"value"' in result

    def test_nested_json(self):
        """Test nested JSON formatting."""
        data = {"outer": {"inner": "value"}}
        result = format_json(data)
        assert "outer" in result
        assert "inner" in result


class TestFormatCount:
    """Tests for format_count function."""

    def test_singular(self):
        """Test singular count."""
        result = format_count(1, "item")
        assert result == "1 item"

    def test_plural(self):
        """Test plural count."""
        result = format_count(5, "item")
        assert result == "5 items"

    def test_zero(self):
        """Test zero count."""
        result = format_count(0, "item")
        assert result == "0 items"

    def test_custom_plural(self):
        """Test custom plural form."""
        result = format_count(2, "child", "children")
        assert result == "2 children"


class TestColors:
    """Tests for Colors class."""

    def test_colors_exist(self):
        """Test that color constants exist."""
        assert hasattr(Colors, "RED")
        assert hasattr(Colors, "GREEN")
        assert hasattr(Colors, "YELLOW")
        assert hasattr(Colors, "RESET")
