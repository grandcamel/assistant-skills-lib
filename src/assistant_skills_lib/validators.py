"""
Generic Input Validators for Assistant Skills

Provides common input validation utilities for user inputs, paths, URLs, etc.

Security validators:
- validate_file_path_secure: Prevents directory traversal attacks
- validate_path_component: Prevents URL path injection
"""

import re
from pathlib import Path
from typing import Any, Optional, Union
from urllib.parse import quote

# Import ValidationError from the base error_handler
from assistant_skills_lib.error_handler import ValidationError


def validate_required(value: Optional[Any], field_name: str = "value") -> str:
    """
    Validate that a value is provided and not empty.

    Args:
        value: Value to validate
        field_name: Name of field for error message

    Returns:
        Stripped value string

    Raises:
        ValidationError: If value is None or empty
    """
    if value is None:
        raise ValidationError(f"{field_name} is required", operation="validation", details={"field": field_name})

    stripped = str(value).strip()
    if not stripped:
        raise ValidationError(f"{field_name} cannot be empty", operation="validation", details={"field": field_name})

    return stripped


def validate_name(
    name: str,
    field_name: str = "name",
    allow_dashes: bool = True,
    allow_underscores: bool = True,
    min_length: int = 1,
    max_length: int = 64
) -> str:
    """
    Validate a name (project name, skill name, etc).

    Args:
        name: Name to validate
        field_name: Field name for error messages
        allow_dashes: Allow hyphens in name
        allow_underscores: Allow underscores in name
        min_length: Minimum name length
        max_length: Maximum name length

    Returns:
        Validated name string

    Raises:
        ValidationError: If name is invalid
    """
    name = validate_required(name, field_name)

    # Check length
    if len(name) < min_length:
        raise ValidationError(
            f"{field_name} must be at least {min_length} characters",
            operation="validation", details={"field": field_name, "value": name}
        )

    if len(name) > max_length:
        raise ValidationError(
            f"{field_name} must be at most {max_length} characters",
            operation="validation", details={"field": field_name, "value": name}
        )

    # Build allowed pattern
    allowed = r'a-zA-Z0-9'
    if allow_dashes:
        allowed += r'\-'
    if allow_underscores:
        allowed += r'_'

    pattern = f'^[{allowed}]+$'

    if not re.match(pattern, name):
        allowed_desc = "letters, numbers"
        if allow_dashes:
            allowed_desc += ", dashes"
        if allow_underscores:
            allowed_desc += ", underscores"

        raise ValidationError(
            f"{field_name} can only contain {allowed_desc}",
            operation="validation",
            details={"field": field_name, "value": name, "suggestion": f"Try: {re.sub(r'[^a-zA-Z0-9_-]', '-', name)}"}
        )

    # Must start with letter
    if not name[0].isalpha():
        raise ValidationError(
            f"{field_name} must start with a letter",
            operation="validation", details={"field": field_name, "value": name}
        )

    return name


def validate_topic_prefix(prefix: str) -> str:
    """
    Validate a topic prefix (lowercase, no special chars).

    Args:
        prefix: Prefix to validate

    Returns:
        Validated lowercase prefix

    Raises:
        ValidationError: If prefix is invalid
    """
    prefix = validate_required(prefix, "topic prefix")
    prefix = prefix.lower()

    if not re.match(r'^[a-z][a-z0-9]*$', prefix):
        raise ValidationError(
            "Topic prefix must be lowercase letters/numbers, starting with a letter",
            operation="validation",
            details={"field": "topic prefix", "value": prefix, "suggestion": f"Try: {re.sub(r'[^a-z0-9]', '', prefix.lower())}"}
        )

    if len(prefix) > 20:
        raise ValidationError(
            "Topic prefix should be concise (max 20 characters)",
            operation="validation", details={"field": "topic prefix", "value": prefix}
        )

    return prefix


def validate_path(
    path: Union[str, Path],
    field_name: str = "path",
    must_exist: bool = False,
    must_be_dir: bool = False,
    must_be_file: bool = False,
    create_parents: bool = False
) -> Path:
    """
    Validate a file system path.

    Args:
        path: Path to validate
        field_name: Name of the field for error messages
        must_exist: Require path to exist
        must_be_dir: Require path to be a directory
        must_be_file: Require path to be a file
        create_parents: Create parent directories if needed

    Returns:
        Resolved Path object

    Raises:
        ValidationError: If path is invalid
    """
    if not path:
        raise ValidationError(f"{field_name} is required", operation="validation", details={"field": field_name})

    resolved = Path(path).expanduser().resolve()

    if must_exist and not resolved.exists():
        raise ValidationError(
            f"{field_name} does not exist: {resolved}",
            operation="validation", details={"field": field_name, "value": str(resolved)}
        )

    if must_be_dir:
        if resolved.exists() and not resolved.is_dir():
            raise ValidationError(
                f"{field_name} is not a directory: {resolved}",
                operation="validation", details={"field": field_name, "value": str(resolved)}
            )

    if must_be_file:
        if resolved.exists() and not resolved.is_file():
            raise ValidationError(
                f"{field_name} is not a file: {resolved}",
                operation="validation", details={"field": field_name, "value": str(resolved)}
            )

    if create_parents and not resolved.parent.exists():
        resolved.parent.mkdir(parents=True, exist_ok=True)

    return resolved


def validate_url(
    url: str,
    field_name: str = "URL",
    require_https: bool = False,
    allowed_schemes: Optional[list[str]] = None,
    allowed_domains: Optional[list[str]] = None
) -> str:
    """
    Validate a URL format. This version is more robust, combining features from service libs.

    Args:
        url: URL to validate
        field_name: Field name for error messages
        require_https: If True, only HTTPS protocol is allowed.
        allowed_schemes: List of allowed URL schemes (e.g., ['http', 'https']). Defaults to ['http', 'https'].
        allowed_domains: List of allowed domain suffixes (e.g., ['.atlassian.net', '.splunkcloud.com']).

    Returns:
        Validated URL string (normalized, no trailing slash).

    Raises:
        ValidationError: If URL is invalid
    """
    from urllib.parse import urlparse

    url = validate_required(url, field_name)

    if allowed_schemes is None:
        allowed_schemes = ['http', 'https']

    # Add scheme if missing (e.g., "example.com" -> "https://example.com" if require_https)
    if '://' not in url:
        if require_https:
            url = f"https://{url}"
        elif 'https' in allowed_schemes: # Default to https if allowed
             url = f"https://{url}"
        elif 'http' in allowed_schemes: # Fallback to http if allowed
             url = f"http://{url}"
        else:
             raise ValidationError(
                f"{field_name} must include a valid scheme (e.g., http:// or https://)",
                operation="validation", details={"field": field_name, "value": url}
            )

    try:
        parsed = urlparse(url)
    except Exception as e:
        raise ValidationError(
            f"Invalid {field_name} format: {e}",
            operation="validation", details={"field": field_name, "value": url}
        ) from e

    if not parsed.scheme or parsed.scheme not in allowed_schemes:
        raise ValidationError(
            f"{field_name} must use one of: {', '.join(allowed_schemes)} (got: {parsed.scheme})",
            operation="validation", details={"field": field_name, "value": url}
        )

    if require_https and parsed.scheme != 'https':
        raise ValidationError(
            f"{field_name} must use HTTPS",
            operation="validation", details={"field": field_name, "value": url}
        )

    if not parsed.netloc:
        raise ValidationError(
            f"{field_name} must include a host",
            operation="validation", details={"field": field_name, "value": url}
        )

    if allowed_domains:
        domain_match = False
        for domain_suffix in allowed_domains:
            if parsed.netloc.endswith(domain_suffix):
                domain_match = True
                break
        if not domain_match:
            raise ValidationError(
                f"{field_name} must be from an allowed domain: {', '.join(allowed_domains)}",
                operation="validation", details={"field": field_name, "value": url}
            )

    # Basic hostname pattern (optional for very generic URL validation, parsed.netloc covers most)
    # pattern = r'^[a-zA-Z0-9][-a-zA-Z0-9.]*[a-zA-Z0-9](:[0-9]+)?$'
    # if not re.match(pattern, parsed.netloc.split(':')[0]):
    #     raise ValidationError(f"Invalid {field_name} hostname format", field=field_name, value=url)

    return url.rstrip('/') # Normalize: remove trailing slash


def validate_email(
    email: str,
    field_name: str = "email",
) -> str:
    """
    Validate an email address.

    Args:
        email: The email address to validate
        field_name: Name of the field for error messages

    Returns:
        Validated email (lowercase)

    Raises:
        ValidationError: If the email is invalid
    """
    email = validate_required(email, field_name)

    email = email.strip().lower()

    # Basic email pattern - more comprehensive than just existence
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_pattern, email):
        raise ValidationError(
            f"{field_name} is not a valid email address",
            operation="validation", details={"field": field_name, "value": email}
        )

    return email


def validate_choice(
    value: str,
    choices: list[str],
    field_name: str = "value"
) -> str:
    """
    Validate that value is one of allowed choices.

    Args:
        value: Value to validate
        choices: List of allowed values
        field_name: Field name for error messages

    Returns:
        Validated value (case-normalized to match choice)

    Raises:
        ValidationError: If value not in choices
    """
    value = validate_required(value, field_name)

    # Try exact match first
    if value in choices:
        return value

    # Try case-insensitive match
    lower_value = value.lower()
    for choice in choices:
        if choice.lower() == lower_value:
            return choice

    raise ValidationError(
        f"Invalid {field_name}: '{value}'. Choose from: {', '.join(choices)}",
        operation="validation",
        details={"field": field_name, "value": value, "valid_choices": choices}
    )


def validate_list(
    value: str,
    field_name: str = "list",
    separator: str = ",",
    min_items: int = 0,
    max_items: Optional[int] = None
) -> list[str]:
    """
    Validate and parse a separator-separated list.

    Args:
        value: Separator-separated string
        field_name: Field name for error messages
        separator: List separator character
        min_items: Minimum number of items required
        max_items: Maximum number of items allowed

    Returns:
        List of stripped strings

    Raises:
        ValidationError: If list is invalid
    """
    if not value or not value.strip():
        if min_items > 0:
            raise ValidationError(
                f"{field_name} requires at least {min_items} items",
                operation="validation", details={"field": field_name}
            )
        return []

    items = [item.strip() for item in value.split(separator)]
    items = [item for item in items if item]  # Remove empty strings

    if len(items) < min_items:
        raise ValidationError(
            f"{field_name} requires at least {min_items} items, got {len(items)}",
            operation="validation", details={"field": field_name, "value": value}
        )

    if max_items and len(items) > max_items:
        raise ValidationError(
            f"{field_name} allows at most {max_items} items, got {len(items)}",
            operation="validation", details={"field": field_name, "value": value}
        )

    return items


def validate_int(
    value: Union[str, int],
    field_name: str = "value",
    min_value: Optional[int] = None,
    max_value: Optional[int] = None,
    allow_none: bool = False
) -> Optional[int]:
    """
    Validate that a value is an integer within an optional range.

    Args:
        value: Value to validate.
        field_name: Name of the field for error messages.
        min_value: Minimum allowed integer value (inclusive).
        max_value: Maximum allowed integer value (inclusive).
        allow_none: If True, None is allowed and returned as None.

    Returns:
        Validated integer, or None if allow_none is True and value is None.

    Raises:
        ValidationError: If value is not an integer or outside the range.
    """
    if value is None:
        if allow_none:
            return None
        raise ValidationError(f"{field_name} is required", operation="validation", details={"field": field_name})

    try:
        int_value = int(value)
    except (ValueError, TypeError) as e:
        raise ValidationError(
            f"{field_name} must be an integer (got: {value})",
            operation="validation", details={"field": field_name, "value": str(value)}
        ) from e

    if min_value is not None and int_value < min_value:
        raise ValidationError(
            f"{field_name} must be at least {min_value} (got: {int_value})",
            operation="validation", details={"field": field_name, "value": str(int_value)}
        )

    if max_value is not None and int_value > max_value:
        raise ValidationError(
            f"{field_name} must be at most {max_value} (got: {int_value})",
            operation="validation", details={"field": field_name, "value": str(int_value)}
        )

    return int_value


# =============================================================================
# Security Validators
# =============================================================================


def validate_file_path_secure(
    file_path: str,
    param_name: str = "file_path",
    base_dir: Optional[Path] = None,
    allow_absolute: bool = False,
) -> Path:
    """
    Validate file path to prevent directory traversal attacks.

    This is a security-focused validator that prevents:
    - Path traversal via '..' sequences
    - Symlink-based traversal attacks
    - Escaping the base directory (defaults to current working directory)

    Args:
        file_path: Path to validate
        param_name: Parameter name for error messages
        base_dir: Base directory paths must be relative to (defaults to cwd)
        allow_absolute: If True, allow absolute paths (still validates no '..')

    Returns:
        Validated Path object

    Raises:
        ValidationError: If path contains traversal attempts or escapes base_dir
    """
    file_path = validate_required(file_path, param_name)

    # Check for explicit path traversal patterns
    if ".." in file_path:
        raise ValidationError(
            f"Path traversal detected in {param_name}: '..' not allowed",
            operation="validation",
            details={"field": param_name},
        )

    path = Path(file_path)

    # Reject symlinks to prevent symlink-based path traversal
    if path.exists() and path.is_symlink():
        raise ValidationError(
            f"Symlinks not allowed in {param_name}",
            operation="validation",
            details={"field": param_name},
        )

    if path.is_absolute():
        if not allow_absolute:
            raise ValidationError(
                f"Absolute paths not allowed in {param_name}",
                operation="validation",
                details={"field": param_name},
            )
        # For absolute paths, check no .. components
        for part in path.parts:
            if part == "..":
                raise ValidationError(
                    f"Path traversal detected in {param_name}",
                    operation="validation",
                    details={"field": param_name},
                )
        return path
    else:
        # For relative paths, ensure it doesn't escape base directory
        if base_dir is None:
            base_dir = Path.cwd()
        base_dir = base_dir.resolve()

        try:
            resolved = (base_dir / path).resolve()
            # Check the resolved path is within or at base_dir
            resolved.relative_to(base_dir)
        except ValueError:
            raise ValidationError(
                f"Path {param_name} would escape base directory",
                operation="validation",
                details={"field": param_name},
            )

        return resolved


def validate_path_component(
    component: str,
    param_name: str = "name",
) -> str:
    """
    Validate and sanitize a path component for use in URLs.

    Prevents path injection by rejecting components with path separators
    or traversal patterns. Returns URL-encoded component for safe
    interpolation into REST API endpoints.

    Args:
        component: Path component to validate (e.g., app name, collection name)
        param_name: Parameter name for error messages

    Returns:
        URL-encoded path component safe for REST API paths

    Raises:
        ValidationError: If component contains disallowed characters
    """
    component = validate_required(component, param_name)

    # Reject path traversal
    if ".." in component:
        raise ValidationError(
            f"Path traversal detected in {param_name}: '..' not allowed",
            operation="validation",
            details={"field": param_name},
        )

    # Reject path separators
    if "/" in component or "\\" in component:
        raise ValidationError(
            f"Path separators not allowed in {param_name}",
            operation="validation",
            details={"field": param_name},
        )

    # URL-encode to prevent any special character issues
    return quote(component, safe="")
