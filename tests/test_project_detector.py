"""Tests for project_detector module."""

import pytest
import tempfile
from pathlib import Path
from assistant_skills_lib import (
    detect_project,
    list_skills,
    validate_structure,
    get_project_stats,
)


class TestDetectProject:
    """Tests for detect_project function."""

    def test_detect_nonexistent_path(self):
        """Test detection on nonexistent path."""
        result = detect_project("/nonexistent/path")
        assert result is None

    def test_detect_non_project_directory(self, tmp_path):
        """Test detection on non-project directory."""
        result = detect_project(str(tmp_path))
        assert result is None


class TestListSkills:
    """Tests for list_skills function."""

    def test_list_skills_empty_project(self, tmp_path):
        """Test listing skills in empty directory."""
        result = list_skills(str(tmp_path))
        assert result == []

    def test_list_skills_nonexistent_path(self):
        """Test listing skills in nonexistent path."""
        result = list_skills("/nonexistent/path")
        assert result == []


class TestValidateStructure:
    """Tests for validate_structure function."""

    def test_validate_empty_directory(self, tmp_path):
        """Test validation of empty directory."""
        result = validate_structure(str(tmp_path))
        assert "valid" in result or "errors" in result

    def test_validate_nonexistent_path(self):
        """Test validation of nonexistent path."""
        result = validate_structure("/nonexistent/path")
        assert result is not None


class TestGetProjectStats:
    """Tests for get_project_stats function."""

    def test_stats_empty_directory(self, tmp_path):
        """Test stats for empty directory."""
        result = get_project_stats(str(tmp_path))
        assert isinstance(result, dict)

    def test_stats_nonexistent_path(self):
        """Test stats for nonexistent path."""
        result = get_project_stats("/nonexistent/path")
        assert isinstance(result, dict)
