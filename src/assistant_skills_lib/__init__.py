"""
Assistant Skills Library

Shared Python utilities for building Claude Code Assistant Skills plugins.

Modules:
    formatters - Output formatting (tables, trees, colors, sensitive field redaction)
    validators - Input validation (names, URLs, paths, security validators)
    cache - Response caching with TTL
    error_handler - Exception hierarchy and decorators
    template_engine - Template loading and rendering
    project_detector - Assistant Skills project detection
    credential_manager - Multi-backend credential storage (keychain, JSON, env)
    batch_processor - Batch processing with checkpoint/resume
    request_batcher - Parallel HTTP request execution

Usage:
    from assistant_skills_lib import format_table, validate_url
    from assistant_skills_lib.cache import Cache, cached
    from assistant_skills_lib.error_handler import handle_errors, APIError
    from assistant_skills_lib.credential_manager import BaseCredentialManager
    from assistant_skills_lib.batch_processor import BatchProcessor
"""

__version__ = "0.3.0"

# Formatters - Output formatting utilities
# Cache - Response caching
from .cache import (
    SkillCache,
    cached,
    get_skill_cache,
    invalidate,
)

# Error Handler - Exception hierarchy
from .error_handler import (
    AuthenticationError,
    BaseAPIError,
    ConflictError,
    ErrorContext,
    NotFoundError,
    PermissionError,
    RateLimitError,
    ServerError,
    ValidationError,  # Corrected from BaseValidationError
    handle_api_error,
    handle_errors,
    print_error,
    sanitize_error_message,
)
from .formatters import (
    SENSITIVE_FIELD_PATTERNS,
    Colors,
    _colorize,
    format_count,
    format_file_size,
    format_json,
    format_list,
    format_path,
    format_table,
    format_tree,
    is_sensitive_field,
    print_header,
    print_info,
    print_success,
    print_warning,
    redact_dict,
    redact_sensitive_value,
    truncate,
)
from .formatters import (
    print_error as print_error_formatted,
)

# Project Detector - Assistant Skills project detection
from .project_detector import (
    detect_project,
    get_project_stats,
    get_shared_lib_modules,
    get_topic_prefix,
    list_skills,
    validate_structure,
)

# Template Engine - Template loading and rendering
from .template_engine import (
    get_template_dir,
    list_placeholders,
    list_template_files,
    load_template,
    render_template,
    validate_context,
)

# Validators - Input validation utilities
from .validators import (
    validate_choice,
    validate_file_path_secure,
    validate_int,  # Newly added generic validator
    validate_list,
    validate_name,
    validate_path,
    validate_path_component,
    validate_required,
    validate_topic_prefix,
    validate_url,
)

# Credential Manager - Multi-backend credential storage
from .credential_manager import (
    BaseCredentialManager,
    CredentialBackend,
    CredentialNotFoundError,
)

# Batch Processor - Batch operations with checkpointing
from .batch_processor import (
    BatchConfig,
    BatchProcessor,
    BatchProgress,
    CheckpointManager,
    generate_operation_id,
    get_recommended_batch_size,
    list_pending_checkpoints,
)

# Request Batcher - Parallel HTTP request execution
from .request_batcher import (
    BatchError,
    BatchResult,
    RequestBatcher,
)

# Mock Client - Base classes for testing
from .mock import (
    BaseMockClient,
    create_mock_mode_checker,
)

# Backwards compatibility aliases
Cache = SkillCache
get_cache = get_skill_cache
APIError = BaseAPIError
InputValidationError = ValidationError  # Alias for backwards compatibility

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
    # Sensitive field redaction
    "SENSITIVE_FIELD_PATTERNS",
    "is_sensitive_field",
    "redact_sensitive_value",
    "redact_dict",
    # Validators
    "validate_url",
    "validate_required",
    "validate_name",
    "validate_topic_prefix",
    "validate_path",
    "validate_choice",
    "validate_list",
    "validate_int",
    # Security validators
    "validate_file_path_secure",
    "validate_path_component",
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
    # Credential Manager
    "BaseCredentialManager",
    "CredentialBackend",
    "CredentialNotFoundError",
    # Batch Processor
    "BatchConfig",
    "BatchProcessor",
    "BatchProgress",
    "CheckpointManager",
    "generate_operation_id",
    "get_recommended_batch_size",
    "list_pending_checkpoints",
    # Request Batcher
    "BatchError",
    "BatchResult",
    "RequestBatcher",
    # Mock Client
    "BaseMockClient",
    "create_mock_mode_checker",
]
