"""
API Stability Tests

Verifies that public API exports and backwards compatibility aliases remain stable.
These tests prevent breaking changes to downstream packages like splunk-as and jira-as.
"""

import pytest


class TestBackwardsCompatibilityAliases:
    """Test that backwards compatibility aliases exist and work correctly."""

    def test_deep_merge_alias_exists(self):
        """_deep_merge must exist for splunk-as compatibility.

        splunk-as calls BaseConfigManager._deep_merge() directly.
        Removing this alias would break that package.
        """
        from assistant_skills_lib.config_manager import BaseConfigManager

        assert hasattr(BaseConfigManager, "_deep_merge"), (
            "_deep_merge alias removed but splunk-as depends on it. "
            "Add '_deep_merge = _merge_config' to maintain compatibility."
        )

    def test_deep_merge_alias_works(self):
        """_deep_merge should call _merge_config correctly."""
        from assistant_skills_lib.config_manager import BaseConfigManager

        # Create a test subclass
        class TestConfigManager(BaseConfigManager):
            def get_service_name(self) -> str:
                return "test"

            def get_default_config(self) -> dict:
                return {}

        manager = TestConfigManager()

        # Test that _deep_merge works
        base = {"a": 1, "b": {"x": 10}}
        override = {"b": {"y": 20}, "c": 3}
        result = manager._deep_merge(base, override)

        assert result == {"a": 1, "b": {"x": 10, "y": 20}, "c": 3}

    def test_cache_alias_exists(self):
        """Cache must alias SkillCache for backwards compatibility."""
        from assistant_skills_lib import Cache, SkillCache

        assert Cache is SkillCache, (
            "Cache alias removed but downstream packages may use it"
        )

    def test_get_cache_alias_exists(self):
        """get_cache must alias get_skill_cache for backwards compatibility."""
        from assistant_skills_lib import get_cache, get_skill_cache

        assert get_cache is get_skill_cache, (
            "get_cache alias removed but downstream packages may use it"
        )

    def test_api_error_alias_exists(self):
        """APIError must alias BaseAPIError for backwards compatibility."""
        from assistant_skills_lib import APIError, BaseAPIError

        assert APIError is BaseAPIError, (
            "APIError alias removed but downstream packages may use it"
        )

    def test_input_validation_error_alias_exists(self):
        """InputValidationError must alias ValidationError for backwards compatibility."""
        from assistant_skills_lib import InputValidationError, ValidationError

        assert InputValidationError is ValidationError, (
            "InputValidationError alias removed but downstream packages may use it"
        )


class TestPublicExports:
    """Test that all public exports in __all__ are importable."""

    def test_all_exports_importable(self):
        """Verify every name in __all__ can be imported."""
        from assistant_skills_lib import __all__
        import assistant_skills_lib

        missing = []
        for name in __all__:
            if not hasattr(assistant_skills_lib, name):
                missing.append(name)

        assert not missing, (
            f"These names are in __all__ but not importable: {missing}"
        )

    def test_critical_exports_exist(self):
        """Verify critical exports that downstream packages depend on."""
        critical_exports = [
            # Formatters (used by all downstream packages)
            "format_table",
            "format_list",
            "format_json",
            "print_success",
            "print_error_formatted",
            "print_warning",
            "print_info",
            "truncate",
            # Validators
            "validate_url",
            "validate_required",
            "validate_name",
            # Cache
            "SkillCache",
            "Cache",  # BC alias
            "cached",
            # Error handling
            "BaseAPIError",
            "APIError",  # BC alias
            "handle_errors",
            "AuthenticationError",
            "NotFoundError",
            "ValidationError",
        ]

        import assistant_skills_lib

        missing = []
        for name in critical_exports:
            if not hasattr(assistant_skills_lib, name):
                missing.append(name)

        assert not missing, (
            f"Critical exports missing from assistant_skills_lib: {missing}"
        )


class TestConfigManagerAPI:
    """Test that BaseConfigManager API is stable."""

    def test_required_abstract_methods(self):
        """BaseConfigManager must require these abstract methods."""
        from assistant_skills_lib.config_manager import BaseConfigManager
        import inspect

        abstract_methods = {
            name for name, method in inspect.getmembers(BaseConfigManager)
            if getattr(method, "__isabstractmethod__", False)
        }

        expected = {"get_service_name", "get_default_config"}
        assert abstract_methods == expected, (
            f"BaseConfigManager abstract methods changed. "
            f"Expected {expected}, got {abstract_methods}"
        )

    def test_public_methods_exist(self):
        """BaseConfigManager must have these public methods."""
        from assistant_skills_lib.config_manager import BaseConfigManager

        required_methods = [
            "get_api_config",
            "get_credential_from_env",
            "get_instance",
            "reset_instance",
        ]

        missing = []
        for method_name in required_methods:
            if not hasattr(BaseConfigManager, method_name):
                missing.append(method_name)

        assert not missing, (
            f"BaseConfigManager missing required methods: {missing}"
        )


class TestErrorHierarchy:
    """Test that error class hierarchy is stable."""

    def test_error_inheritance(self):
        """Error classes must inherit from correct base classes."""
        from assistant_skills_lib import (
            BaseAPIError,
            AuthenticationError,
            PermissionError,
            NotFoundError,
            RateLimitError,
            ValidationError,
            ConflictError,
            ServerError,
        )

        # All should inherit from BaseAPIError
        assert issubclass(AuthenticationError, BaseAPIError)
        assert issubclass(PermissionError, BaseAPIError)
        assert issubclass(NotFoundError, BaseAPIError)
        assert issubclass(RateLimitError, BaseAPIError)
        assert issubclass(ValidationError, BaseAPIError)
        assert issubclass(ConflictError, BaseAPIError)
        assert issubclass(ServerError, BaseAPIError)

        # BaseAPIError should be a Python Exception
        assert issubclass(BaseAPIError, Exception)
