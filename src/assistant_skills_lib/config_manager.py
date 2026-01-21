"""
Generic Configuration Management for Assistant Skills

Handles loading and merging configuration from multiple sources:
1. Environment variables (highest priority)
2. .claude/settings.local.json (personal settings, gitignored)
3. .claude/settings.json (team defaults, committed)
4. Hardcoded defaults (fallbacks)
"""

import json
import os
import threading
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Optional, TypeVar

# Generic type for subclasses of BaseConfigManager
T = TypeVar('T', bound='BaseConfigManager')


class BaseConfigManager(ABC):
    """
    Manages configuration from multiple sources for a given service.
    This is an abstract base class, designed to be extended by service-specific managers.
    """

    # Class-level singleton registry and lock for thread-safe access
    _instances: dict[type, "BaseConfigManager"] = {}
    _instance_lock = threading.Lock()

    def __init__(self):
        """
        Initialize configuration manager.
        """
        self.service_name = self.get_service_name()
        if not self.service_name:
            raise ValueError("Service name must be defined by get_service_name() in subclass.")

        self.env_prefix = self.service_name.upper()  # e.g., JIRA, CONFLUENCE, SPLUNK
        self.config = self._load_config()

    @abstractmethod
    def get_service_name(self) -> str:
        """
        Returns the name of the service (e.g., 'jira', 'confluence').
        This must be implemented by subclasses.
        """
        pass

    def _find_claude_dir(self) -> Optional[Path]:
        """
        Find .claude directory by walking up from current directory.
        """
        current = Path.cwd()
        # Search up to the user's home directory, but not beyond.
        home = Path.home()
        while current != current.parent and current != home.parent:
            claude_dir = current / '.claude'
            if claude_dir.is_dir():
                return claude_dir
            current = current.parent
        return None

    def _load_config(self) -> dict[str, Any]:
        """
        Load and merge configuration from all sources.
        Configuration is structured by service name at the top level.
        """
        # Start with default config for this service
        config = self.get_default_config()

        claude_dir = self._find_claude_dir()

        if claude_dir:
            # Load global settings.json first
            global_settings_path = claude_dir / 'settings.json'
            if global_settings_path.exists():
                try:
                    with open(global_settings_path) as f:
                        global_config = json.load(f).get(self.service_name, {})
                    config = self._merge_config(config, global_config)
                except json.JSONDecodeError:
                    # Ignore malformed config files, or log a warning
                    pass

            # Load local settings.local.json (overrides global settings)
            local_settings_path = claude_dir / 'settings.local.json'
            if local_settings_path.exists():
                try:
                    with open(local_settings_path) as f:
                        local_config = json.load(f).get(self.service_name, {})
                    config = self._merge_config(config, local_config)
                except json.JSONDecodeError:
                    # Ignore malformed config files, or log a warning
                    pass

        # Return the merged config under the service name key
        return {self.service_name: config}

    def _merge_config(self, base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
        """
        Recursively merge override config into base config.
        """
        result = base.copy()
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_config(result[key], value)
            else:
                result[key] = value
        return result

    def get_api_config(self) -> dict[str, Any]:
        """
        Get API configuration (timeout, retries, etc.).
        """
        # Start with some sane generic defaults
        defaults = {
            'timeout': 30,
            'max_retries': 3,
            'retry_backoff': 2.0
        }
        # Merge with service-specific config from settings files
        api_config = self.config.get(self.service_name, {}).get('api', {})
        defaults.update(api_config)
        return defaults

    def get_credential_from_env(self, cred_name: str) -> Optional[str]:
        """
        Get a credential from environment variables, checking service-specific and generic names.
        e.g., for cred_name='API_TOKEN' and service='JIRA', checks JIRA_API_TOKEN then API_TOKEN.
        """
        service_specific_var = f"{self.env_prefix}_{cred_name.upper()}"
        generic_var = cred_name.upper()

        # Check service-specific var first, then generic
        return os.getenv(service_specific_var) or os.getenv(generic_var)

    @abstractmethod
    def get_default_config(self) -> dict[str, Any]:
        """
        Returns the default configuration dictionary for the service.
        This must be implemented by subclasses.
        """
        pass

    @classmethod
    def get_instance(cls: type[T]) -> T:
        """
        Get or create a singleton instance for the concrete subclass.

        Thread-safe singleton access using double-checked locking pattern.
        Each concrete subclass maintains its own singleton instance.

        Returns:
            The singleton instance for this subclass
        """
        if cls not in cls._instances:
            with cls._instance_lock:
                # Double-check after acquiring lock
                if cls not in cls._instances:
                    cls._instances[cls] = cls()
        return cls._instances[cls]  # type: ignore[return-value]

    @classmethod
    def reset_instance(cls: type[T]) -> None:
        """
        Reset the singleton instance for this subclass.

        Thread-safe method primarily for testing purposes.
        """
        with cls._instance_lock:
            if cls in cls._instances:
                del cls._instances[cls]


def get_config_manager(service_name: str) -> BaseConfigManager:
    """
    Factory function to get a generic BaseConfigManager instance for a given service.
    Note: This factory only returns the BaseConfigManager, not a service-specific subclass.
    Subclasses should use their own get_instance() or direct instantiation.
    """
    # This factory function is primarily for demonstrating how a BaseConfigManager
    # might be instantiated generically if needed. For service-specific managers,
    # it's better to instantiate the concrete subclass directly or via its get_instance()
    # method.
    class GenericServiceConfigManager(BaseConfigManager):
        _service_name_val: str
        _default_config_val: dict[str, Any]

        def __init__(self, service_name_val: str, default_config_val: dict[str, Any]):
            self._service_name_val = service_name_val
            self._default_config_val = default_config_val
            super().__init__()

        def get_service_name(self) -> str:
            return self._service_name_val

        def get_default_config(self) -> dict[str, Any]:
            return self._default_config_val

    # Placeholder for default config if none is provided. In a real scenario,
    # you might load this from a global defaults file or pass it in.
    # For now, it will just return a minimal structure under the service_name key.
    minimal_default_config = {
        service_name: {
            'api': {
                'timeout': 30,
                'max_retries': 3,
                'retry_backoff': 2.0
            }
        }
    }

    return GenericServiceConfigManager(service_name, minimal_default_config)
