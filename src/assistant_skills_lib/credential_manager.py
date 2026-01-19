"""
Base credential management for Assistant Skills.

Provides secure credential storage with multiple backends:
1. Environment variables - always checked first for retrieval
2. System keychain (via keyring library) - preferred for storage
3. settings.local.json - fallback for storage

Security considerations:
- Never logs or prints credentials
- Uses sanitize_error_message() for exception messages
- Sets restrictive file permissions (0600) on JSON storage
"""

from __future__ import annotations

import gc
import json
import os
import stat
from abc import ABC, abstractmethod
from enum import Enum
from pathlib import Path
from typing import Any

from .error_handler import BaseAPIError, ValidationError, sanitize_error_message

# Try to import keyring, gracefully handle if not installed
try:
    import keyring

    KEYRING_AVAILABLE = True
except ImportError:
    KEYRING_AVAILABLE = False


class CredentialBackend(Enum):
    """Available credential storage backends."""

    KEYCHAIN = (
        "keychain"  # macOS Keychain, Windows Credential Manager, Linux Secret Service
    )
    JSON_FILE = "json_file"  # settings.local.json
    ENVIRONMENT = "environment"  # Environment variables (read-only for retrieval)


class CredentialNotFoundError(BaseAPIError):
    """Raised when credentials cannot be found in any backend."""

    def __init__(self, service_name: str, hint: str | None = None, **kwargs):
        message = f"No {service_name} credentials found"
        if hint:
            message = message + "\n\n" + hint
        super().__init__(message, **kwargs)


class BaseCredentialManager(ABC):
    """
    Abstract base class for credential management across multiple storage backends.

    Subclasses must implement:
    - get_service_name(): Return keychain service name (e.g., "jira-assistant")
    - get_env_prefix(): Return environment variable prefix (e.g., "JIRA")
    - get_credential_fields(): Return list of credential field names
    - validate_credentials(): Validate credentials via test API call

    Priority for retrieval:
    1. Environment variables ({PREFIX}_FIELD_NAME)
    2. System keychain (if keyring available)
    3. settings.local.json

    Priority for storage:
    1. System keychain (if keyring available)
    2. settings.local.json (fallback)
    """

    def __init__(self):
        """Initialize credential manager."""
        self._claude_dir = self._find_claude_dir()

    @abstractmethod
    def get_service_name(self) -> str:
        """
        Return the keychain service name.

        Example: "jira-assistant", "splunk-assistant", "confluence-assistant"
        """
        pass

    @abstractmethod
    def get_env_prefix(self) -> str:
        """
        Return the environment variable prefix.

        Example: "JIRA", "SPLUNK", "CONFLUENCE"
        """
        pass

    @abstractmethod
    def get_credential_fields(self) -> list[str]:
        """
        Return list of credential field names.

        Example: ["site_url", "email", "api_token"]
        """
        pass

    @abstractmethod
    def validate_credentials(self, credentials: dict[str, str]) -> dict[str, Any]:
        """
        Validate credentials by making a test API call.

        Args:
            credentials: Dictionary of credential values

        Returns:
            Response data on success (e.g., user info)

        Raises:
            AuthenticationError: If credentials are invalid
            BaseAPIError: If connection fails
        """
        pass

    def get_credential_not_found_hint(self) -> str:
        """
        Return help text for credential not found error.

        Override this to provide service-specific setup instructions.
        """
        prefix = self.get_env_prefix()
        fields = self.get_credential_fields()

        hint = "Set environment variables:\n"
        for field in fields:
            env_var = f"{prefix}_{field.upper()}"
            hint += f"  export {env_var}='your-{field.replace('_', '-')}'\n"
        return hint

    def _find_claude_dir(self) -> Path | None:
        """
        Find .claude directory by walking up from current directory.

        Returns:
            Path to .claude directory or None if not found
        """
        current = Path.cwd()

        while current != current.parent:
            claude_dir = current / ".claude"
            if claude_dir.is_dir():
                return claude_dir
            current = current.parent

        return None

    @staticmethod
    def is_keychain_available() -> bool:
        """
        Check if keyring is installed and functional.

        Returns:
            True if keyring is available and working, False otherwise
        """
        if not KEYRING_AVAILABLE:
            return False

        try:
            # Test keyring functionality with a dummy operation
            keyring.get_keyring()
            return True
        except Exception:
            return False

    def get_credentials_from_env(self) -> dict[str, str | None]:
        """
        Get credentials from environment variables.

        Returns:
            Dictionary of credential field -> value (may be None)
        """
        prefix = self.get_env_prefix()
        fields = self.get_credential_fields()

        result = {}
        for field in fields:
            env_var = f"{prefix}_{field.upper()}"
            result[field] = os.getenv(env_var)

        return result

    def get_credentials_from_keychain(self) -> dict[str, str | None]:
        """
        Get credentials from system keychain.

        Returns:
            Dictionary of credential field -> value (all None if not found)
        """
        fields = self.get_credential_fields()
        empty_result = {field: None for field in fields}

        if not self.is_keychain_available():
            return empty_result

        try:
            credential_json = keyring.get_password(
                self.get_service_name(), "credentials"
            )
            if not credential_json:
                return empty_result

            creds = json.loads(credential_json)
            return {field: creds.get(field) for field in fields}
        except Exception:
            return empty_result

    def get_credentials_from_json(self) -> dict[str, str | None]:
        """
        Get credentials from settings.local.json.

        Returns:
            Dictionary of credential field -> value (may be None)
        """
        fields = self.get_credential_fields()
        empty_result = {field: None for field in fields}

        if not self._claude_dir:
            return empty_result

        local_settings = self._claude_dir / "settings.local.json"

        if not local_settings.exists():
            return empty_result

        try:
            with open(local_settings) as f:
                config = json.load(f)

            # Get service-specific config section
            service_name = self.get_service_name().replace("-assistant", "")
            service_config = config.get(service_name, {})
            credentials = service_config.get("credentials", {})

            return {field: credentials.get(field) for field in fields}
        except Exception:
            return empty_result

    def get_credentials(self) -> dict[str, str]:
        """
        Retrieve all credentials.

        Checks in priority order:
        1. Environment variables
        2. System keychain
        3. settings.local.json

        Returns:
            Dictionary of credential field -> value

        Raises:
            CredentialNotFoundError: If any credential not found
        """
        fields = self.get_credential_fields()
        result: dict[str, str | None] = {field: None for field in fields}

        # Priority 1: Environment variables (highest priority)
        env_creds = self.get_credentials_from_env()
        for field, value in env_creds.items():
            if value:
                result[field] = value

        # Priority 2: Keychain
        if any(v is None for v in result.values()):
            kc_creds = self.get_credentials_from_keychain()
            for field, value in kc_creds.items():
                if result.get(field) is None and value:
                    result[field] = value

        # Priority 3: JSON file
        if any(v is None for v in result.values()):
            json_creds = self.get_credentials_from_json()
            for field, value in json_creds.items():
                if result.get(field) is None and value:
                    result[field] = value

        # Check for missing credentials
        missing = [field for field, value in result.items() if value is None]
        if missing:
            raise CredentialNotFoundError(
                self.get_service_name(),
                hint=self.get_credential_not_found_hint(),
            )

        # Return with type assertion (all values are now strings)
        return {k: v for k, v in result.items() if v is not None}

    def store_credentials(
        self,
        credentials: dict[str, str],
        backend: CredentialBackend | None = None,
    ) -> CredentialBackend:
        """
        Store credentials in the specified or preferred backend.

        Args:
            credentials: Dictionary of credential values
            backend: Specific backend to use (default: auto-select best available)

        Returns:
            The backend where credentials were stored

        Raises:
            ValidationError: If credentials are invalid
            BaseAPIError: If storage fails
        """
        fields = self.get_credential_fields()

        # Validate all required fields are present
        for field in fields:
            value = credentials.get(field)
            if not value or not str(value).strip():
                raise ValidationError(
                    f"{field} cannot be empty",
                    operation="store_credentials",
                    details={"field": field},
                )

        # Determine backend
        if backend is None:
            if self.is_keychain_available():
                backend = CredentialBackend.KEYCHAIN
            else:
                backend = CredentialBackend.JSON_FILE

        # Store based on backend
        if backend == CredentialBackend.KEYCHAIN:
            return self._store_to_keychain(credentials)
        elif backend == CredentialBackend.JSON_FILE:
            return self._store_to_json(credentials)
        else:
            raise ValidationError(f"Cannot store to backend: {backend.value}")

    def _store_to_keychain(self, credentials: dict[str, str]) -> CredentialBackend:
        """Store credentials in system keychain."""
        if not self.is_keychain_available():
            raise BaseAPIError(
                "Keychain is not available. Install keyring: pip install keyring"
            )

        try:
            credential_json = json.dumps(credentials)
            keyring.set_password(
                self.get_service_name(), "credentials", credential_json
            )

            # Clear sensitive data from memory
            del credential_json
            gc.collect()

            return CredentialBackend.KEYCHAIN
        except Exception as e:
            raise BaseAPIError(
                f"Failed to store credentials in keychain: {sanitize_error_message(str(e))}"
            )

    def _store_to_json(self, credentials: dict[str, str]) -> CredentialBackend:
        """Store credentials in settings.local.json."""
        if not self._claude_dir:
            raise BaseAPIError(
                "Cannot find .claude directory. Run from project root."
            )

        local_settings = self._claude_dir / "settings.local.json"

        try:
            # Load existing config or create new
            if local_settings.exists():
                with open(local_settings) as f:
                    config = json.load(f)
            else:
                config = {}

            # Get service section name (e.g., "jira" from "jira-assistant")
            service_name = self.get_service_name().replace("-assistant", "")

            # Ensure structure exists
            if service_name not in config:
                config[service_name] = {}
            if "credentials" not in config[service_name]:
                config[service_name]["credentials"] = {}

            # Store credentials
            for field, value in credentials.items():
                config[service_name]["credentials"][field] = value

            # Write with secure permissions
            with open(local_settings, "w") as f:
                json.dump(config, f, indent=2)

            # Set restrictive permissions (owner read/write only)
            os.chmod(local_settings, stat.S_IRUSR | stat.S_IWUSR)

            return CredentialBackend.JSON_FILE
        except Exception as e:
            raise BaseAPIError(
                f"Failed to store credentials in JSON: {sanitize_error_message(str(e))}"
            )

    def delete_credentials(self) -> bool:
        """
        Delete credentials from all backends.

        Returns:
            True if any credentials were deleted, False otherwise
        """
        deleted = False

        # Delete from keychain
        if self.is_keychain_available():
            try:
                keyring.delete_password(self.get_service_name(), "credentials")
                deleted = True
            except Exception:
                pass  # May not exist

        # Delete from JSON
        if self._claude_dir:
            local_settings = self._claude_dir / "settings.local.json"
            if local_settings.exists():
                try:
                    with open(local_settings) as f:
                        config = json.load(f)

                    service_name = self.get_service_name().replace("-assistant", "")
                    if service_name in config and "credentials" in config[service_name]:
                        del config[service_name]["credentials"]
                        deleted = True

                        with open(local_settings, "w") as f:
                            json.dump(config, f, indent=2)
                except Exception:
                    pass

        return deleted
