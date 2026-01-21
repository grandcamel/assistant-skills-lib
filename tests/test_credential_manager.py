"""Tests for credential_manager module."""

import json
import os
import pytest
from pathlib import Path
from typing import Any
from unittest.mock import patch, MagicMock

from assistant_skills_lib.credential_manager import (
    BaseCredentialManager,
    CredentialBackend,
    CredentialNotFoundError,
    KEYRING_AVAILABLE,
)


class ConcreteCredentialManager(BaseCredentialManager):
    """Concrete implementation for testing BaseCredentialManager."""

    def get_service_name(self) -> str:
        return "test-assistant"

    def get_env_prefix(self) -> str:
        return "TEST"

    def get_credential_fields(self) -> list[str]:
        return ["api_url", "username", "api_token"]

    def validate_credentials(self, credentials: dict[str, str]) -> dict[str, Any]:
        return {"valid": True}


class TestCredentialBackendEnum:
    """Tests for CredentialBackend enum."""

    def test_backend_values(self):
        """Test credential backend enum values."""
        assert CredentialBackend.KEYCHAIN.value == "keychain"
        assert CredentialBackend.JSON_FILE.value == "json_file"
        assert CredentialBackend.ENVIRONMENT.value == "environment"


class TestCredentialNotFoundError:
    """Tests for CredentialNotFoundError."""

    def test_error_message(self):
        """Test error message format."""
        error = CredentialNotFoundError("test-service")
        assert "test-service" in str(error)
        assert "No" in str(error) and "credentials found" in str(error)

    def test_error_message_with_hint(self):
        """Test error message includes hint."""
        error = CredentialNotFoundError("test-service", hint="Run setup first")
        message = str(error)
        assert "test-service" in message
        assert "Run setup first" in message


class TestIsKeychainAvailable:
    """Tests for is_keychain_available static method."""

    def test_returns_false_when_keyring_not_installed(self):
        """Test returns False when keyring not available."""
        with patch(
            "assistant_skills_lib.credential_manager.KEYRING_AVAILABLE", False
        ):
            assert BaseCredentialManager.is_keychain_available() is False

    def test_returns_true_when_keyring_works(self):
        """Test returns True when keyring is functional."""
        if not KEYRING_AVAILABLE:
            pytest.skip("keyring not installed")

        with patch("assistant_skills_lib.credential_manager.keyring") as mock_keyring:
            mock_keyring.get_keyring.return_value = MagicMock()
            with patch(
                "assistant_skills_lib.credential_manager.KEYRING_AVAILABLE", True
            ):
                assert BaseCredentialManager.is_keychain_available() is True

    def test_returns_false_when_keyring_raises(self):
        """Test returns False when keyring raises exception."""
        if not KEYRING_AVAILABLE:
            pytest.skip("keyring not installed")

        with patch("assistant_skills_lib.credential_manager.keyring") as mock_keyring:
            mock_keyring.get_keyring.side_effect = Exception("Keyring error")
            with patch(
                "assistant_skills_lib.credential_manager.KEYRING_AVAILABLE", True
            ):
                assert BaseCredentialManager.is_keychain_available() is False


class TestFindClaudeDir:
    """Tests for _find_claude_dir method."""

    def test_finds_claude_dir_in_current(self, tmp_path, monkeypatch):
        """Test finding .claude in current directory."""
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        monkeypatch.chdir(tmp_path)

        mgr = ConcreteCredentialManager()

        assert mgr._claude_dir == claude_dir

    def test_finds_claude_dir_in_parent(self, tmp_path, monkeypatch):
        """Test finding .claude in parent directory."""
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        subdir = tmp_path / "subdir" / "deep"
        subdir.mkdir(parents=True)
        monkeypatch.chdir(subdir)

        mgr = ConcreteCredentialManager()

        assert mgr._claude_dir == claude_dir

    def test_returns_none_when_not_found(self, tmp_path, monkeypatch):
        """Test returns None when .claude not found."""
        # Create a directory without .claude
        workdir = tmp_path / "workdir"
        workdir.mkdir()
        monkeypatch.chdir(workdir)

        mgr = ConcreteCredentialManager()

        assert mgr._claude_dir is None


class TestGetCredentialNotFoundHint:
    """Tests for get_credential_not_found_hint method."""

    def test_includes_env_vars(self, tmp_path, monkeypatch):
        """Test hint includes environment variable instructions."""
        monkeypatch.chdir(tmp_path)
        mgr = ConcreteCredentialManager()
        hint = mgr.get_credential_not_found_hint()

        assert "TEST_API_URL" in hint
        assert "TEST_USERNAME" in hint
        assert "TEST_API_TOKEN" in hint
        assert "export" in hint

    def test_format_structure(self, tmp_path, monkeypatch):
        """Test hint has proper structure."""
        monkeypatch.chdir(tmp_path)
        mgr = ConcreteCredentialManager()
        hint = mgr.get_credential_not_found_hint()

        # Should have one line per field
        lines = [l for l in hint.split("\n") if l.strip()]
        assert len(lines) >= 3  # Header + 3 fields


class TestGetCredentialsFromEnv:
    """Tests for get_credentials_from_env method."""

    def test_gets_env_vars(self, tmp_path, monkeypatch):
        """Test getting credentials from environment."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("TEST_API_URL", "https://example.com")
        monkeypatch.setenv("TEST_USERNAME", "testuser")
        monkeypatch.setenv("TEST_API_TOKEN", "secret123")

        mgr = ConcreteCredentialManager()
        creds = mgr.get_credentials_from_env()

        assert creds["api_url"] == "https://example.com"
        assert creds["username"] == "testuser"
        assert creds["api_token"] == "secret123"

    def test_returns_none_for_missing(self, tmp_path, monkeypatch):
        """Test returns None for missing env vars."""
        monkeypatch.chdir(tmp_path)
        # Ensure env vars are not set
        monkeypatch.delenv("TEST_API_URL", raising=False)
        monkeypatch.delenv("TEST_USERNAME", raising=False)
        monkeypatch.delenv("TEST_API_TOKEN", raising=False)

        mgr = ConcreteCredentialManager()
        creds = mgr.get_credentials_from_env()

        assert creds["api_url"] is None
        assert creds["username"] is None
        assert creds["api_token"] is None

    def test_partial_env_vars(self, tmp_path, monkeypatch):
        """Test with some env vars set, some missing."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("TEST_API_URL", "https://example.com")
        monkeypatch.delenv("TEST_USERNAME", raising=False)
        monkeypatch.delenv("TEST_API_TOKEN", raising=False)

        mgr = ConcreteCredentialManager()
        creds = mgr.get_credentials_from_env()

        assert creds["api_url"] == "https://example.com"
        assert creds["username"] is None
        assert creds["api_token"] is None


class TestGetCredentialsFromJson:
    """Tests for get_credentials_from_json method."""

    def test_reads_from_settings_local(self, tmp_path, monkeypatch):
        """Test reading credentials from settings.local.json."""
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        settings_file = claude_dir / "settings.local.json"
        settings_file.write_text(
            json.dumps(
                {
                    "test": {
                        "credentials": {
                            "api_url": "https://json.example.com",
                            "username": "jsonuser",
                            "api_token": "jsonsecret",
                        }
                    }
                }
            )
        )
        monkeypatch.chdir(tmp_path)

        mgr = ConcreteCredentialManager()
        creds = mgr.get_credentials_from_json()

        assert creds["api_url"] == "https://json.example.com"
        assert creds["username"] == "jsonuser"
        assert creds["api_token"] == "jsonsecret"

    def test_returns_none_when_no_claude_dir(self, tmp_path, monkeypatch):
        """Test returns None when .claude directory not found."""
        workdir = tmp_path / "workdir"
        workdir.mkdir()
        monkeypatch.chdir(workdir)

        mgr = ConcreteCredentialManager()
        creds = mgr.get_credentials_from_json()

        assert all(v is None for v in creds.values())

    def test_returns_none_when_file_missing(self, tmp_path, monkeypatch):
        """Test returns None when settings.local.json missing."""
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        monkeypatch.chdir(tmp_path)

        mgr = ConcreteCredentialManager()
        creds = mgr.get_credentials_from_json()

        assert all(v is None for v in creds.values())

    def test_returns_none_for_invalid_json(self, tmp_path, monkeypatch):
        """Test returns None for invalid JSON."""
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        settings_file = claude_dir / "settings.local.json"
        settings_file.write_text("invalid json {{{")
        monkeypatch.chdir(tmp_path)

        mgr = ConcreteCredentialManager()
        creds = mgr.get_credentials_from_json()

        assert all(v is None for v in creds.values())

    def test_returns_none_for_missing_section(self, tmp_path, monkeypatch):
        """Test returns None when service section missing."""
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        settings_file = claude_dir / "settings.local.json"
        settings_file.write_text(json.dumps({"other_service": {}}))
        monkeypatch.chdir(tmp_path)

        mgr = ConcreteCredentialManager()
        creds = mgr.get_credentials_from_json()

        assert all(v is None for v in creds.values())


class TestGetCredentials:
    """Tests for get_credentials method."""

    def test_prefers_env_over_json(self, tmp_path, monkeypatch):
        """Test environment variables take priority over JSON."""
        # Setup JSON
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        settings_file = claude_dir / "settings.local.json"
        settings_file.write_text(
            json.dumps(
                {
                    "test": {
                        "credentials": {
                            "api_url": "https://json.example.com",
                            "username": "jsonuser",
                            "api_token": "jsonsecret",
                        }
                    }
                }
            )
        )
        monkeypatch.chdir(tmp_path)

        # Setup env (overrides JSON)
        monkeypatch.setenv("TEST_API_URL", "https://env.example.com")
        monkeypatch.setenv("TEST_USERNAME", "envuser")
        monkeypatch.setenv("TEST_API_TOKEN", "envsecret")

        mgr = ConcreteCredentialManager()
        # Disable keychain to avoid interference
        with patch.object(mgr, "is_keychain_available", return_value=False):
            creds = mgr.get_credentials()

        assert creds["api_url"] == "https://env.example.com"
        assert creds["username"] == "envuser"
        assert creds["api_token"] == "envsecret"

    def test_raises_when_missing(self, tmp_path, monkeypatch):
        """Test raises CredentialNotFoundError when credentials missing."""
        monkeypatch.chdir(tmp_path)
        # Ensure env vars are not set
        monkeypatch.delenv("TEST_API_URL", raising=False)
        monkeypatch.delenv("TEST_USERNAME", raising=False)
        monkeypatch.delenv("TEST_API_TOKEN", raising=False)

        mgr = ConcreteCredentialManager()
        with patch.object(mgr, "is_keychain_available", return_value=False):
            with pytest.raises(CredentialNotFoundError) as exc_info:
                mgr.get_credentials()

        assert "test-assistant" in str(exc_info.value)

    def test_merges_sources(self, tmp_path, monkeypatch):
        """Test merges credentials from multiple sources."""
        # Setup JSON with partial credentials
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        settings_file = claude_dir / "settings.local.json"
        settings_file.write_text(
            json.dumps(
                {
                    "test": {
                        "credentials": {
                            "api_url": "https://json.example.com",
                            "username": "jsonuser",
                            "api_token": "jsonsecret",
                        }
                    }
                }
            )
        )
        monkeypatch.chdir(tmp_path)

        # Only set one env var
        monkeypatch.setenv("TEST_API_TOKEN", "env_override_token")
        monkeypatch.delenv("TEST_API_URL", raising=False)
        monkeypatch.delenv("TEST_USERNAME", raising=False)

        mgr = ConcreteCredentialManager()
        with patch.object(mgr, "is_keychain_available", return_value=False):
            creds = mgr.get_credentials()

        # ENV overrides for api_token, JSON for others
        assert creds["api_url"] == "https://json.example.com"
        assert creds["username"] == "jsonuser"
        assert creds["api_token"] == "env_override_token"


class TestStoreCredentials:
    """Tests for store_credentials method."""

    def test_stores_to_json_file(self, tmp_path, monkeypatch):
        """Test storing credentials to JSON file."""
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        monkeypatch.chdir(tmp_path)

        mgr = ConcreteCredentialManager()
        with patch.object(mgr, "is_keychain_available", return_value=False):
            backend = mgr.store_credentials(
                {
                    "api_url": "https://store.example.com",
                    "username": "storeuser",
                    "api_token": "storesecret",
                }
            )

        assert backend == CredentialBackend.JSON_FILE

        # Verify file was created
        settings_file = claude_dir / "settings.local.json"
        assert settings_file.exists()

        # Verify contents
        with open(settings_file) as f:
            config = json.load(f)
        assert config["test"]["credentials"]["api_url"] == "https://store.example.com"

    def test_validates_empty_fields(self, tmp_path, monkeypatch):
        """Test raises ValidationError for empty fields."""
        from assistant_skills_lib.error_handler import ValidationError

        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        monkeypatch.chdir(tmp_path)

        mgr = ConcreteCredentialManager()
        with pytest.raises(ValidationError):
            mgr.store_credentials(
                {
                    "api_url": "https://example.com",
                    "username": "",  # Empty
                    "api_token": "secret",
                }
            )


class TestDeleteCredentials:
    """Tests for delete_credentials method."""

    def test_deletes_from_json(self, tmp_path, monkeypatch):
        """Test deleting credentials from JSON file."""
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        settings_file = claude_dir / "settings.local.json"
        settings_file.write_text(
            json.dumps(
                {
                    "test": {
                        "credentials": {
                            "api_url": "https://example.com",
                            "username": "user",
                            "api_token": "token",
                        }
                    }
                }
            )
        )
        monkeypatch.chdir(tmp_path)

        mgr = ConcreteCredentialManager()
        with patch.object(mgr, "is_keychain_available", return_value=False):
            result = mgr.delete_credentials()

        assert result is True

        # Verify credentials removed
        with open(settings_file) as f:
            config = json.load(f)
        assert "credentials" not in config.get("test", {})

    def test_returns_false_when_nothing_to_delete(self, tmp_path, monkeypatch):
        """Test returns False when no credentials to delete."""
        workdir = tmp_path / "workdir"
        workdir.mkdir()
        monkeypatch.chdir(workdir)

        mgr = ConcreteCredentialManager()
        with patch.object(mgr, "is_keychain_available", return_value=False):
            result = mgr.delete_credentials()

        assert result is False
