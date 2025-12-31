import pytest
import os
from pathlib import Path
from unittest.mock import patch

from assistant_skills_lib.validators import (
    validate_required,
    validate_name,
    validate_topic_prefix,
    validate_path,
    validate_url,
    validate_email,
    validate_choice,
    validate_list,
    validate_int,
)
from assistant_skills_lib.error_handler import ValidationError # Ensure this is the correct ValidationError

# --- Test validate_required ---
@pytest.mark.parametrize("value, field_name, expected", [
    ("test", "field", "test"),
    ("  test  ", "field", "test"),
])
def test_validate_required_success(value, field_name, expected):
    assert validate_required(value, field_name) == expected

@pytest.mark.parametrize("value, field_name, error_msg", [
    (None, "field", "field is required"),
    ("", "field", "field cannot be empty"),
    ("   ", "field", "field cannot be empty"),
])
def test_validate_required_failure(value, field_name, error_msg):
    with pytest.raises(ValidationError, match=error_msg):
        validate_required(value, field_name)

# --- Test validate_name ---
@pytest.mark.parametrize("name, expected", [
    ("ProjectName", "ProjectName"),
    ("skill-name", "skill-name"),
    ("skill_name", "skill_name"),
    ("SKILL123", "SKILL123"),
])
def test_validate_name_success(name, expected):
    assert validate_name(name) == expected

@pytest.mark.parametrize("name, kwargs, error_msg", [
    ("1invalid", {}, "name must start with a letter"),
    ("invalid name", {}, "name can only contain letters, numbers"),
    ("long" * 20, {}, "name must be at most 64 characters"),
    ("a", {"min_length": 2}, "name must be at least 2 characters"),
])
def test_validate_name_failure(name, kwargs, error_msg):
    with pytest.raises(ValidationError, match=error_msg):
        validate_name(name, **kwargs)

# --- Test validate_topic_prefix ---
@pytest.mark.parametrize("prefix, expected", [
    ("topic1", "topic1"),
    ("topic", "topic"),
    ("Topic", "topic"),  # Auto-lowercased
    ("TOPIC", "topic"),  # Auto-lowercased
])
def test_validate_topic_prefix_success(prefix, expected):
    assert validate_topic_prefix(prefix) == expected

@pytest.mark.parametrize("prefix, error_msg", [
    ("1topic", "Topic prefix must be lowercase letters/numbers, starting with a letter"),
    ("topic-name", "Topic prefix must be lowercase letters/numbers"),
    ("long" * 10, "Topic prefix should be concise"),
])
def test_validate_topic_prefix_failure(prefix, error_msg):
    with pytest.raises(ValidationError, match=error_msg):
        validate_topic_prefix(prefix)

# --- Test validate_path ---
def test_validate_path_success(tmp_path):
    test_file = tmp_path / "test.txt"
    test_file.write_text("content")
    assert validate_path(test_file, must_exist=True) == test_file

def test_validate_path_create_parents(tmp_path):
    new_path = tmp_path / "a" / "b" / "file.txt"
    validated = validate_path(new_path, create_parents=True)
    assert validated == new_path
    assert new_path.parent.exists()

@pytest.mark.parametrize("path, kwargs, error_msg", [
    ("nonexistent.txt", {"must_exist": True}, "path does not exist"),
    (__file__, {"must_be_dir": True}, "path is not a directory"),
    (os.path.dirname(__file__), {"must_be_file": True}, "path is not a file"),
])
def test_validate_path_failure(path, kwargs, error_msg):
    with pytest.raises(ValidationError, match=error_msg):
        validate_path(path, **kwargs)

# --- Test validate_url ---
@pytest.mark.parametrize("url, kwargs, expected", [
    ("http://example.com", {}, "http://example.com"),
    ("example.com", {"require_https": True}, "https://example.com"),
    ("https://example.com/", {}, "https://example.com"),
    # ftp requires explicit allowed_schemes since default is ['http', 'https']
    ("ftp://example.com", {"allowed_schemes": ["ftp", "http", "https"]}, "ftp://example.com"),
    # URLs without scheme get https:// auto-added
    ("example.com", {}, "https://example.com"),
])
def test_validate_url_success(url, kwargs, expected):
    assert validate_url(url, **kwargs) == expected

@pytest.mark.parametrize("url, kwargs, error_msg", [
    # ftp is not allowed by default (only http/https)
    ("ftp://example.com", {}, "URL must use one of: http, https"),
    ("http://example.com", {"require_https": True}, "URL must use HTTPS"),
    ("example.com", {"allowed_domains": [".test.com"]}, "URL must be from an allowed domain"),
])
def test_validate_url_failure(url, kwargs, error_msg):
    with pytest.raises(ValidationError, match=error_msg):
        validate_url(url, **kwargs)

# --- Test validate_email ---
@pytest.mark.parametrize("email, expected", [
    ("test@example.com", "test@example.com"),
    ("TEST@example.com", "test@example.com"),
])
def test_validate_email_success(email, expected):
    assert validate_email(email) == expected

@pytest.mark.parametrize("email, error_msg", [
    ("invalid-email", "is not a valid email address"),
    ("test@", "is not a valid email address"),
])
def test_validate_email_failure(email, error_msg):
    with pytest.raises(ValidationError, match=error_msg):
        validate_email(email)

# --- Test validate_choice ---
@pytest.mark.parametrize("value, choices, expected", [
    ("apple", ["apple", "banana"], "apple"),
    ("Apple", ["apple", "banana"], "apple"), # Case-insensitive match
])
def test_validate_choice_success(value, choices, expected):
    assert validate_choice(value, choices) == expected

def test_validate_choice_failure():
    with pytest.raises(ValidationError, match="Invalid value: 'grape'"):
        validate_choice("grape", ["apple", "banana"])

# --- Test validate_list ---
@pytest.mark.parametrize("value, expected", [
    ("a,b,c", ["a", "b", "c"]),
    ("a, b , c", ["a", "b", "c"]),
    ("a,,b", ["a", "b"]),
    ("", []),
])
def test_validate_list_success(value, expected):
    assert validate_list(value) == expected

@pytest.mark.parametrize("value, kwargs, error_msg", [
    ("", {"min_items": 1}, "requires at least 1 items"),
    ("a,b,c", {"max_items": 2}, "allows at most 2 items"),
])
def test_validate_list_failure(value, kwargs, error_msg):
    with pytest.raises(ValidationError, match=error_msg):
        validate_list(value, **kwargs)

# --- Test validate_int ---
@pytest.mark.parametrize("value, kwargs, expected", [
    (10, {}, 10),
    ("5", {}, 5),
    (None, {"allow_none": True}, None),
    (10, {"min_value": 5, "max_value": 15}, 10),
])
def test_validate_int_success(value, kwargs, expected):
    assert validate_int(value, **kwargs) == expected

@pytest.mark.parametrize("value, kwargs, error_msg", [
    (None, {}, "is required"),
    ("abc", {}, "must be an integer"),
    (3, {"min_value": 5}, "must be at least 5"),
    (10, {"max_value": 5}, "must be at most 5"),
])
def test_validate_int_failure(value, kwargs, error_msg):
    with pytest.raises(ValidationError, match=error_msg):
        validate_int(value, **kwargs)