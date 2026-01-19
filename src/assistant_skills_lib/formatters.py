"""
Generic Output Formatters for Assistant Skills

Provides consistent CLI output utilities, including:
- ANSI colorization
- Generic print functions (success, error, warning, info, header)
- Table formatting (using tabulate if available, with a fallback)
- JSON formatting
- List formatting
- Path formatting
- File size formatting
- Count pluralization
- Timestamp formatting
- CSV export/string generation
- Sensitive field detection and redaction
"""

import csv
import json
import re
import sys
from collections.abc import Sequence
from datetime import datetime
from io import StringIO
from pathlib import Path
from typing import Any, Optional, Union


# =============================================================================
# Sensitive Field Detection and Redaction
# =============================================================================

# Patterns to match sensitive field names (case-insensitive)
SENSITIVE_FIELD_PATTERNS: frozenset[str] = frozenset({
    "password",
    "passwd",
    "token",
    "api_key",
    "apikey",
    "secret",
    "auth",
    "authorization",
    "credential",
    "credentials",
    "private_key",
    "privatekey",
    "access_token",
    "refresh_token",
    "session_key",
    "sessionkey",
    "bearer",
})


def is_sensitive_field(field_name: str) -> bool:
    """
    Check if a field name matches sensitive data patterns.

    This function performs case-insensitive substring matching against
    known sensitive field patterns like 'password', 'token', 'secret', etc.

    Args:
        field_name: The field name to check

    Returns:
        True if the field appears to contain sensitive data
    """
    field_lower = field_name.lower()
    return any(pattern in field_lower for pattern in SENSITIVE_FIELD_PATTERNS)


def redact_sensitive_value(field_name: str, value: Any) -> Any:
    """
    Redact value if the field name indicates sensitive data.

    Args:
        field_name: The field/key name
        value: The field value

    Returns:
        The original value if field is not sensitive, or "[REDACTED]" if sensitive
    """
    if is_sensitive_field(field_name):
        return "[REDACTED]"
    return value


def redact_dict(data: dict[str, Any]) -> dict[str, Any]:
    """
    Create a copy of a dictionary with sensitive fields redacted.

    Args:
        data: Dictionary to redact

    Returns:
        New dictionary with sensitive values replaced with "[REDACTED]"
    """
    return {k: redact_sensitive_value(k, v) for k, v in data.items()}

# Try to import tabulate for advanced table formatting
try:
    from tabulate import tabulate
    HAS_TABULATE = True
except ImportError:
    HAS_TABULATE = False


# ANSI color codes
class Colors:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    RESET = '\033[0m'


def _supports_color() -> bool:
    """Check if terminal supports color."""
    return hasattr(sys.stdout, 'isatty') and sys.stdout.isatty()


def _colorize(text: str, color: str) -> str:
    """Apply color to text if terminal supports it."""
    if _supports_color():
        return f"{color}{text}{Colors.RESET}"
    return text


def format_table(
    data: Sequence[dict[str, Any]],
    columns: Optional[list[str]] = None,
    headers: Optional[list[str]] = None,
    tablefmt: str = 'simple', # default format for tabulate
    max_col_width: int = 50, # For fallback table
    truncate_long_values: bool = True,
) -> str:
    """
    Format data as an ASCII table. Uses 'tabulate' if available, otherwise a basic fallback.

    Args:
        data: List of dictionaries to format
        columns: Optional list of keys to include from each dictionary. If None, uses all keys from the first item.
        headers: Optional list of header labels. If None, uses `columns` values as headers.
        tablefmt: Format string for `tabulate` (e.g., 'plain', 'simple', 'grid', 'fancy_grid', 'pipe', 'org', 'psql').
        max_col_width: Maximum width for columns in the fallback table.
        truncate_long_values: If True, truncate long cell values in the fallback table.

    Returns:
        Formatted table string
    """
    if not data:
        return "(no data)"

    if columns is None:
        columns = list(data[0].keys())

    if headers is None:
        headers = columns

    # Use tabulate if available
    if HAS_TABULATE:
        # Prepare rows, ensuring all items are strings for tabulate
        rows = []
        for row_dict in data:
            row_list = []
            for col_key in columns:
                value = row_dict.get(col_key, '')
                if isinstance(value, (list, tuple)):
                    value = ', '.join(map(str, value))
                elif isinstance(value, dict):
                    # Try to get a 'name' or 'title' from dict, otherwise stringify
                    value = value.get('name', value.get('title', str(value)))
                row_list.append(str(value))
            rows.append(row_list)
        return tabulate(rows, headers=headers, tablefmt=tablefmt)
    else:
        # Fallback to basic table formatting logic
        return _format_basic_table_fallback(data, columns, headers, max_col_width, truncate_long_values)


def _format_basic_table_fallback(
    data: Sequence[dict[str, Any]],
    columns: list[str],
    headers: list[str],
    max_col_width: int,
    truncate_long_values: bool,
) -> str:
    """
    Basic ASCII table formatting fallback when 'tabulate' is not installed.
    """
    lines = []

    # Calculate column widths
    widths = [len(str(h)) for h in headers]
    for row in data:
        for i, key in enumerate(columns):
            val = str(row.get(key, ''))
            if truncate_long_values and len(val) > max_col_width:
                val = val[:max_col_width - 3] + "..."
            widths[i] = max(widths[i], len(val))

    # Apply max_col_width to calculated widths
    widths = [min(w, max_col_width) for w in widths]

    # Header row
    header_row = ' | '.join(str(h).ljust(widths[i]) for i, h in enumerate(headers))
    lines.append(header_row)

    # Separator
    separator = '-+-'.join('-' * w for w in widths)
    lines.append(separator)

    # Data rows
    for row_dict in data:
        row_str = ' | '.join(
            (str(row_dict.get(key, ''))[:widths[i]] if truncate_long_values else str(row_dict.get(key, ''))).ljust(widths[i])
            for i, key in enumerate(columns)
        )
        lines.append(row_str)

    return '\n'.join(lines)


def format_tree(
    root: str,
    items: list[dict[str, Any]],
    name_key: str = 'name',
    children_key: str = 'children'
) -> str:
    """
    Format data as a tree structure.

    Args:
        root: Root node name
        items: List of items (can be nested with children_key)
        name_key: Key for item name
        children_key: Key for nested children

    Returns:
        Formatted tree string
    """
    lines = [root]

    def add_items(current_items: list, prefix: str = '', is_last_parent: bool = True):
        for i, item in enumerate(current_items):
            is_last = i == len(current_items) - 1

            # Determine branch character
            if is_last:
                branch = '└── '
                next_prefix = prefix + '    '
            else:
                branch = '├── '
                next_prefix = prefix + '│   '

            # Get name
            name = item.get(name_key, str(item)) if isinstance(item, dict) else str(item)
            lines.append(f"{prefix}{branch}{name}")

            # Process children
            if isinstance(item, dict) and children_key in item:
                add_items(item[children_key], next_prefix, is_last)

    add_items(items)
    return '\n'.join(lines)


def format_json(data: Any, indent: int = 2, ensure_ascii: bool = False) -> str:
    """
    Format data as pretty-printed JSON.

    Args:
        data: Data to format
        indent: Indentation level
        ensure_ascii: If False, allow non-ASCII characters to be output directly.

    Returns:
        JSON string
    """
    return json.dumps(data, indent=indent, default=str, ensure_ascii=ensure_ascii)


def format_list(
    items: Sequence[str],
    bullet: str = '•',
    numbered: bool = False,
    max_items: Optional[int] = None,
    truncate_message: str = " ... and {remaining} more"
) -> str:
    """
    Format items as a bulleted or numbered list.

    Args:
        items: List of strings
        bullet: Bullet character (for non-numbered lists)
        numbered: If True, format as a numbered list.
        max_items: Maximum number of items to display before truncating.
        truncate_message: Message to show if items are truncated.
                          Use {remaining} placeholder for count.

    Returns:
        Formatted list string
    """
    if not items:
        return "(no items)"

    display_items = items
    truncated = False
    if max_items is not None and len(items) > max_items:
        display_items = items[:max_items]
        truncated = True

    lines = []
    for i, item in enumerate(display_items, 1):
        prefix = f"{i}." if numbered else bullet
        lines.append(f" {prefix} {item}")

    if truncated:
        remaining = len(items) - max_items
        lines.append(truncate_message.format(remaining=remaining))

    return '\n'.join(lines)


def print_success(message: str) -> None:
    """Print a success message in green."""
    prefix = _colorize("✓", Colors.GREEN)
    print(f"{prefix} {message}")


def print_error(message: str) -> None:
    """Print an error message in red to stderr."""
    prefix = _colorize("✗", Colors.RED)
    print(f"{prefix} {message}", file=sys.stderr)


def print_warning(message: str) -> None:
    """Print a warning message in yellow."""
    prefix = _colorize("!", Colors.YELLOW)
    print(f"{prefix} {message}")


def print_info(message: str) -> None:
    """Print an info message in blue."""
    prefix = _colorize("→", Colors.BLUE)
    print(f"{prefix} {message}")


def print_header(title: str) -> None:
    """Print a section header."""
    if _supports_color():
        print(f"\n{Colors.BOLD}{title}{Colors.RESET}")
        print('=' * len(title))
    else:
        print(f"\n{title}")
        print('=' * len(title))


def format_path(path: str, relative_to: Optional[Union[str, Path]] = None) -> str:
    """
    Format a path for display.

    Args:
        path: Absolute path string or Path object
        relative_to: Optional base path to make relative to.

    Returns:
        Formatted path string (e.g., "~/path/to/file" or "relative/path")
    """
    p = Path(path)

    if relative_to:
        try:
            return str(p.relative_to(relative_to))
        except ValueError:
            pass # Not relative to base, fall through to home or absolute

    # Use ~ for home directory if applicable
    home = Path.home()
    try:
        return '~/' + str(p.relative_to(home))
    except ValueError:
        return str(p) # Return absolute path if not relative to home


def format_file_size(size_bytes: Union[int, float]) -> str:
    """Format file size in human-readable format."""
    if size_bytes < 0:
        return "N/A"

    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} PB"


def format_count(count: int, singular: str, plural: Optional[str] = None) -> str:
    """
    Format a count with proper pluralization.

    Args:
        count: Number to format
        singular: Singular form of word
        plural: Plural form (defaults to singular + 's')

    Returns:
        Formatted string like "1 file" or "5 files"
    """
    if plural is None:
        plural = singular + 's'

    word = singular if count == 1 else plural
    return f"{count} {word}"


def format_large_number(count: int) -> str:
    """
    Format large count with K/M/B suffix.

    Args:
        count: Count to format

    Returns:
        Formatted count string
    """
    if count < 1000:
        return str(count)
    elif count < 1_000_000:
        return f"{count / 1000:.1f}K"
    elif count < 1_000_000_000:
        return f"{count / 1_000_000:.1f}M"
    else:
        return f"{count / 1_000_000_000:.1f}B"


def format_timestamp(timestamp: Optional[str], format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """
    Format an ISO timestamp for display.
    Handles various ISO-like formats and provides a consistent output.

    Args:
        timestamp: ISO format timestamp string
        format_str: Output format string (strftime-compatible)

    Returns:
        Formatted date/time string, or original timestamp if parsing fails
    """
    if not timestamp:
        return "N/A"

    try:
        # Handle various ISO formats, including fractional seconds and timezone info
        # datetime.fromisoformat requires exact format, so try to clean/adapt
        if timestamp.endswith('Z'):
            timestamp = timestamp[:-1] + '+00:00'

        # Split at '+' or '-' for timezone to remove it if not needed for fromisoformat
        dt_part = timestamp.split('+')[0].split('-')[0] # get only date-time part

        # Try parsing with microsecond precision, then without
        try:
            dt = datetime.fromisoformat(dt_part)
        except ValueError:
            # Try without microseconds if the first attempt fails
            dt = datetime.strptime(dt_part.split('.')[0], "%Y-%m-%dT%H:%M:%S")

        return dt.strftime(format_str)
    except (ValueError, TypeError):
        return timestamp # Return original string if parsing fails


def export_csv(
    data: list[dict[str, Any]],
    file_path: Union[str, Path],
    columns: Optional[list[str]] = None,
    headers: Optional[list[str]] = None,
) -> Path:
    """
    Export a list of dictionaries to a CSV file.

    Args:
        data: List of dictionaries to export.
        file_path: Output file path.
        columns: Keys to include from each dictionary. If None, uses all keys from the first item.
        headers: Custom headers for the CSV file. If None, uses `columns` values as headers.

    Returns:
        Path to the created CSV file.

    Raises:
        ValueError: If no data is provided.
    """
    file_path = Path(file_path).expanduser().resolve()

    if not data:
        raise ValueError("No data to export to CSV.")

    if columns is None:
        columns = list(data[0].keys())

    if headers is None:
        headers = columns

    with open(file_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=columns, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(data)

    return file_path


def get_csv_string(
    data: list[dict[str, Any]],
    columns: Optional[list[str]] = None,
    headers: Optional[list[str]] = None,
) -> str:
    """
    Generate a CSV formatted string from a list of dictionaries.

    Args:
        data: List of dictionaries to convert.
        columns: Keys to include from each dictionary. If None, uses all keys from the first item.
        headers: Custom headers for the CSV string. If None, uses `columns` values as headers.

    Returns:
        CSV formatted string.

    Raises:
        ValueError: If no data is provided.
    """
    if not data:
        return "" # Return empty string for no data, not an error

    if columns is None:
        columns = list(data[0].keys())

    if headers is None:
        headers = columns

    output_buffer = StringIO()
    writer = csv.DictWriter(output_buffer, fieldnames=columns, extrasaction='ignore')
    writer.writeheader()
    writer.writerows(data)

    return output_buffer.getvalue()


def truncate(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    Truncate text to a maximum length.

    Args:
        text: Text to truncate
        max_length: Maximum length including suffix
        suffix: Suffix to add when truncated

    Returns:
        Truncated text
    """
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix
