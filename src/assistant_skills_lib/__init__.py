"""
Assistant Skills Library

Shared Python utilities for building Claude Code Assistant Skills plugins.

Modules:
    formatters - Output formatting (tables, trees, colors)
    validators - Input validation (names, URLs, paths)
    cache - Response caching with TTL
    error_handler - Exception hierarchy and decorators
    template_engine - Template loading and rendering
    project_detector - Assistant Skills project detection

Usage:
    from assistant_skills_lib import format_table, validate_url
    from assistant_skills_lib.cache import Cache, cached
    from assistant_skills_lib.error_handler import handle_errors, APIError
"""

__version__ = "0.2.1"

# Formatters - Output formatting utilities
from .formatters import (
    format_table,
    format_tree,
    format_list,
    format_json,
    format_path,
    format_file_size,
    format_count,
    print_success,
    print_error as print_error_formatted,
    print_warning,
    print_info,
    print_header,
    Colors,
    _colorize,
    truncate,
)

# Validators - Input validation utilities
from .validators import (
    validate_url,
    validate_required,
    validate_name,
    validate_topic_prefix,
    validate_path,
    validate_choice,
    validate_list,
    validate_int, # Newly added generic validator
)

# Cache - Response caching
from .cache import (
    SkillCache,
    get_skill_cache,
    invalidate,
    cached,
)

# Error Handler - Exception hierarchy
from .error_handler import (
    BaseAPIError,
    AuthenticationError,
    PermissionError,
    NotFoundError,
    RateLimitError,
    ValidationError, # Corrected from BaseValidationError
    ConflictError,
    ServerError,
    handle_errors,
    handle_api_error, 
    print_error,
    sanitize_error_message,
    ErrorContext,
)

# Backwards compatibility aliases
Cache = SkillCache
get_cache = get_skill_cache
APIError = BaseAPIError
InputValidationError = ValidationError # Alias for backwards compatibility


# Template Engine - Template loading and rendering
from .template_engine import (
    load_template,
    render_template,
    list_placeholders,
    validate_context,
    get_template_dir,
    list_template_files,
)

# Project Detector - Assistant Skills project detection
from .project_detector import (
    detect_project,
    list_skills,
    get_topic_prefix,
    get_shared_lib_modules,
    validate_structure,
    get_project_stats,
)

__all__ = [
    # Version
    "__version__",
    # Formatters
    "format_table",
    "format_tree",
    "format_list",
    "format_json",
    "format_path",
    "format_file_size",
    "format_count",
    "print_success",
    "print_error_formatted",
    "print_warning",
    "print_info",
    "print_header",
    "Colors",
    "truncate", 
    "_colorize", 
    # Validators
    "validate_url",
    "validate_required",
    "validate_name",
    "validate_topic_prefix",
    "validate_path",
    "validate_choice",
    "validate_list",
    "validate_int",
    "InputValidationError", # For BC
    # Cache (new names)
    "SkillCache",
    "get_skill_cache",
    "invalidate",
    "cached",
    # Cache (old names for BC)
    "Cache",
    "get_cache",
    # Error Handler (new names)
    "BaseAPIError",
    "AuthenticationError",
    "PermissionError",
    "NotFoundError",
    "RateLimitError",
    "ValidationError",
    "ConflictError",
    "ServerError",
    "handle_errors",
    "handle_api_error",
    "print_error",
    "sanitize_error_message",
    "ErrorContext",
    # Error Handler (old names for BC)
    "APIError",
    # Template Engine
    "load_template",
    "render_template",
    "list_placeholders",
    "validate_context",
    "get_template_dir",
    "list_template_files",
    # Project Detector
    "detect_project",
    "list_skills",
    "get_topic_prefix",
    "get_shared_lib_modules",
    "validate_structure",
    "get_project_stats",
]
