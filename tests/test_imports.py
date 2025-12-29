"""Tests to verify all imports work correctly."""

import pytest


def test_version():
    """Test that version is accessible."""
    from assistant_skills_lib import __version__
    assert __version__ is not None
    assert isinstance(__version__, str)


def test_formatter_imports():
    """Test formatter module imports."""
    from assistant_skills_lib import (
        format_table,
        format_tree,
        format_list,
        format_json,
        Colors,
    )
    assert callable(format_table)
    assert callable(format_tree)
    assert callable(format_list)
    assert callable(format_json)
    assert Colors is not None


def test_validator_imports():
    """Test validator module imports."""
    from assistant_skills_lib import (
        validate_url,
        validate_required,
        validate_name,
        InputValidationError,
    )
    assert callable(validate_url)
    assert callable(validate_required)
    assert callable(validate_name)
    assert issubclass(InputValidationError, Exception)


def test_cache_imports():
    """Test cache module imports."""
    from assistant_skills_lib import (
        Cache,
        cached,
        get_cache,
        invalidate,
    )
    assert Cache is not None
    assert callable(cached)
    assert callable(get_cache)
    assert callable(invalidate)


def test_error_handler_imports():
    """Test error handler module imports."""
    from assistant_skills_lib import (
        APIError,
        AuthenticationError,
        NotFoundError,
        RateLimitError,
        handle_errors,
        print_error,
        ErrorContext,
    )
    assert issubclass(APIError, Exception)
    assert issubclass(AuthenticationError, APIError)
    assert issubclass(NotFoundError, APIError)
    assert issubclass(RateLimitError, APIError)
    assert callable(handle_errors)
    assert callable(print_error)
    assert ErrorContext is not None


def test_template_engine_imports():
    """Test template engine module imports."""
    from assistant_skills_lib import (
        load_template,
        render_template,
        list_placeholders,
    )
    assert callable(load_template)
    assert callable(render_template)
    assert callable(list_placeholders)


def test_project_detector_imports():
    """Test project detector module imports."""
    from assistant_skills_lib import (
        detect_project,
        list_skills,
        validate_structure,
        get_project_stats,
    )
    assert callable(detect_project)
    assert callable(list_skills)
    assert callable(validate_structure)
    assert callable(get_project_stats)


def test_direct_module_imports():
    """Test importing modules directly."""
    from assistant_skills_lib import formatters
    from assistant_skills_lib import validators
    from assistant_skills_lib import cache
    from assistant_skills_lib import error_handler
    from assistant_skills_lib import template_engine
    from assistant_skills_lib import project_detector

    assert formatters is not None
    assert validators is not None
    assert cache is not None
    assert error_handler is not None
    assert template_engine is not None
    assert project_detector is not None
