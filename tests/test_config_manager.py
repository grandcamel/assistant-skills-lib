import pytest
import os
import json
from pathlib import Path
from typing import Dict, Any
from unittest.mock import patch, mock_open

from assistant_skills_lib.config_manager import BaseConfigManager
from assistant_skills_lib.error_handler import ValidationError # Assuming ValidationError is imported or aliased correctly


def create_test_config_manager_class():
    """Factory to create a fresh TestConfigManager class for each test."""
    class _TestConfigManager(BaseConfigManager):
        def get_service_name(self) -> str:
            return "testservice"

        def get_default_config(self) -> Dict[str, Any]:
            return {
                "url": "http://default.com",
                "api_key": "default_key",
                "api": {
                    "timeout": 10
                }
            }
    return _TestConfigManager

@pytest.fixture
def mock_claude_dir(tmp_path):
    """Fixture to create a mock .claude directory."""
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir()
    return claude_dir

@pytest.fixture
def create_settings_files(mock_claude_dir):
    """Helper to create settings.json and settings.local.json."""
    def _create(settings_content=None, local_content=None):
        if settings_content:
            (mock_claude_dir / "settings.json").write_text(json.dumps(settings_content))
        if local_content:
            (mock_claude_dir / "settings.local.json").write_text(json.dumps(local_content))
    return _create

@patch.dict(os.environ, {}, clear=True)
@patch('assistant_skills_lib.config_manager.BaseConfigManager._find_claude_dir', return_value=None)
def test_init_basic(mock_find_dir):
    TestConfigManager = create_test_config_manager_class()
    manager = TestConfigManager()
    assert manager.service_name == "testservice"
    assert manager.env_prefix == "TESTSERVICE"


def test_find_claude_dir_success(mock_claude_dir):
    TestConfigManager = create_test_config_manager_class()
    with patch('pathlib.Path.cwd', return_value=mock_claude_dir / "subdir"):
        (mock_claude_dir / "subdir").mkdir()
        manager = TestConfigManager()
        assert manager._find_claude_dir() == mock_claude_dir

def test_find_claude_dir_none(tmp_path):
    TestConfigManager = create_test_config_manager_class()
    # Patch home to be tmp_path so we don't find any .claude dirs
    with patch('pathlib.Path.cwd', return_value=tmp_path), \
         patch('pathlib.Path.home', return_value=tmp_path):
        manager = TestConfigManager()
        assert manager._find_claude_dir() is None

@patch('assistant_skills_lib.config_manager.BaseConfigManager._find_claude_dir', return_value=None)
def test_load_config_no_files(mock_find_dir):
    TestConfigManager = create_test_config_manager_class()
    manager = TestConfigManager()
    config = manager._load_config()
    assert config == {"testservice": manager.get_default_config()}

def test_load_config_settings_json(mock_claude_dir, create_settings_files):
    TestConfigManager = create_test_config_manager_class()
    create_settings_files(settings_content={
        "testservice": {"url": "http://settings.com", "extra_key": "extra_value"}
    })
    with patch.object(TestConfigManager, '_find_claude_dir', return_value=mock_claude_dir):
        manager = TestConfigManager()
        config = manager._load_config()
        assert config["testservice"]["url"] == "http://settings.com"
        assert config["testservice"]["extra_key"] == "extra_value"
        assert config["testservice"]["api_key"] == "default_key"  # Default is still there


def test_load_config_local_overrides(mock_claude_dir, create_settings_files):
    TestConfigManager = create_test_config_manager_class()
    create_settings_files(
        settings_content={
            "testservice": {"url": "http://global.com"}
        },
        local_content={
            "testservice": {"url": "http://local.com", "api_key": "local_key"}
        }
    )
    with patch.object(TestConfigManager, '_find_claude_dir', return_value=mock_claude_dir):
        manager = TestConfigManager()
        config = manager._load_config()
        assert config["testservice"]["url"] == "http://local.com"
        assert config["testservice"]["api_key"] == "local_key"


def test_load_config_malformed_json(mock_claude_dir):
    TestConfigManager = create_test_config_manager_class()
    (mock_claude_dir / "settings.json").write_text("{invalid json")
    with patch.object(TestConfigManager, '_find_claude_dir', return_value=mock_claude_dir):
        manager = TestConfigManager()
        config = manager._load_config()
        assert config == {"testservice": manager.get_default_config()}  # Should fallback to default


@patch('assistant_skills_lib.config_manager.BaseConfigManager._find_claude_dir', return_value=None)
def test_get_api_config(mock_find_dir):
    TestConfigManager = create_test_config_manager_class()
    manager = TestConfigManager()
    api_config = manager.get_api_config()
    assert api_config["timeout"] == 10
    assert api_config["max_retries"] == 3  # Default from BaseConfigManager

@patch.dict(os.environ, {"TESTSERVICE_API_KEY": "env_key"}, clear=True)
@patch('assistant_skills_lib.config_manager.BaseConfigManager._find_claude_dir', return_value=None)
def test_get_credential_from_env_service_specific(mock_find_dir):
    TestConfigManager = create_test_config_manager_class()
    manager = TestConfigManager()
    assert manager.get_credential_from_env("API_KEY") == "env_key"

@patch.dict(os.environ, {"API_KEY": "generic_key"}, clear=True)
@patch('assistant_skills_lib.config_manager.BaseConfigManager._find_claude_dir', return_value=None)
def test_get_credential_from_env_generic(mock_find_dir):
    TestConfigManager = create_test_config_manager_class()
    manager = TestConfigManager()
    assert manager.get_credential_from_env("API_KEY") == "generic_key"

@patch.dict(os.environ, {"TESTSERVICE_API_KEY": "service_key", "API_KEY": "generic_key_should_not_be_used"}, clear=True)
@patch('assistant_skills_lib.config_manager.BaseConfigManager._find_claude_dir', return_value=None)
def test_get_credential_from_env_priority(mock_find_dir):
    TestConfigManager = create_test_config_manager_class()
    manager = TestConfigManager()
    assert manager.get_credential_from_env("API_KEY") == "service_key"

@patch('assistant_skills_lib.config_manager.BaseConfigManager._find_claude_dir', return_value=None)
def test_get_instance(mock_find_dir):
    TestConfigManager = create_test_config_manager_class()
    instance = TestConfigManager.get_instance()
    assert isinstance(instance, TestConfigManager)
    assert instance.service_name == "testservice"
