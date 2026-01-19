# Cross-Library Refactoring Plan

This document outlines a comprehensive plan for refactoring and pattern replication across the assistant-skills library ecosystem.

## Executive Summary

After analyzing all four libraries, I've identified significant opportunities to:
1. **Elevate patterns to the base library** - Reduce duplication and establish shared standards
2. **Replicate proven patterns** - Share battle-tested solutions across all service libraries
3. **Harmonize implementations** - Ensure consistent developer experience

### Library Overview

| Library | Modules | Key Strengths | Test Coverage |
|---------|---------|---------------|---------------|
| assistant-skills-lib (base) | 8 | Config, errors, validators, cache, formatters | Foundation |
| jira-assistant-skills-lib | 21 | Credential manager, batch processor, mock client | Most mature |
| confluence-assistant-skills-lib | 9 | Content format conversion, proper base extension | Good structure |
| splunk-assistant-skills-lib | 9 | Security hardening, SPL injection prevention | 62% |

---

## Phase 1: Base Library Enhancements

**Priority: HIGH**
**Effort: 2-3 days**

These patterns are fully generic and should be moved to `assistant-skills-lib` for all service libraries to inherit.

### 1.1 Credential Manager Base Class

**Source:** `jira-assistant-skills-lib/credential_manager.py`
**Target:** `assistant-skills-lib/credential_manager.py`

The JIRA library has a sophisticated multi-backend credential manager that is 100% reusable.

**Features to extract:**
- `CredentialBackend` enum (KEYCHAIN, JSON_FILE, ENVIRONMENT)
- Priority chain: Environment → Keychain → JSON file
- Optional keyring detection with graceful degradation
- Secure file permissions (0600) on JSON storage
- Credential validation hooks

**New base library interface:**
```python
# assistant_skills_lib/credential_manager.py

class CredentialBackend(Enum):
    KEYCHAIN = "keychain"
    JSON_FILE = "json_file"
    ENVIRONMENT = "environment"

class BaseCredentialManager(ABC):
    @abstractmethod
    def get_service_name(self) -> str:
        """Returns keychain service name (e.g., 'jira-assistant')"""
        pass

    @abstractmethod
    def get_credential_fields(self) -> list[str]:
        """Returns list of credential field names"""
        pass

    @abstractmethod
    def validate_credentials(self, credentials: dict) -> bool:
        """Validate credentials via test API call"""
        pass

    def get_credentials(self) -> dict[str, str]:
        """Get credentials from best available backend"""
        pass

    def store_credentials(self, credentials: dict, backend: CredentialBackend = None) -> bool:
        """Store credentials in specified backend"""
        pass
```

**Service library implementation:**
```python
# splunk_assistant_skills_lib/credential_manager.py

class SplunkCredentialManager(BaseCredentialManager):
    def get_service_name(self) -> str:
        return "splunk-assistant"

    def get_credential_fields(self) -> list[str]:
        return ["site_url", "token", "username", "password"]

    def validate_credentials(self, credentials: dict) -> bool:
        client = SplunkClient(**credentials)
        return client.test_connection()
```

**Files to create:**
- `assistant-skills-lib/src/assistant_skills_lib/credential_manager.py`

**Files to modify:**
- `assistant-skills-lib/src/assistant_skills_lib/__init__.py` (add exports)
- `jira-assistant-skills-lib/src/.../credential_manager.py` (extend base)
- `splunk-assistant-skills-lib/src/.../credential_manager.py` (new, extend base)
- `confluence-assistant-skills-lib/src/.../credential_manager.py` (new, extend base)

---

### 1.2 Batch Processor

**Source:** `jira-assistant-skills-lib/batch_processor.py`
**Target:** `assistant-skills-lib/batch_processor.py`

The batch processor is 100% service-agnostic and handles resumable batch operations.

**Features:**
- Generic `BatchProcessor[T]` with TypeVar
- Checkpoint manager for resume capability
- Progress callbacks
- Rate limiting with backoff
- Dry-run support

**New base library interface:**
```python
# assistant_skills_lib/batch_processor.py

@dataclass
class BatchProgress:
    total: int
    processed: int
    succeeded: int
    failed: int
    skipped: int

class BatchProcessor(Generic[T]):
    def __init__(
        self,
        items: list[T],
        process_item: Callable[[T], bool],
        get_key: Callable[[T], str],
        batch_size: int = 50,
        checkpoint_name: str = None,
        on_progress: Callable[[BatchProgress], None] = None,
    ): ...

    def run(self, dry_run: bool = False) -> BatchProgress: ...
    def resume(self) -> BatchProgress: ...
```

**Files to create:**
- `assistant-skills-lib/src/assistant_skills_lib/batch_processor.py`

---

### 1.3 Security Validators

**Source:** `splunk-assistant-skills-lib/validators.py`
**Target:** `assistant-skills-lib/validators.py`

The Splunk library has critical security validators that should protect all service libraries.

**Functions to add to base validators:**
```python
# assistant_skills_lib/validators.py (additions)

def validate_file_path(
    path: str,
    param_name: str,
    must_exist: bool = False,
    allow_absolute: bool = False,
    base_dir: Path = None,
) -> Path:
    """
    Validate file path for security (path traversal prevention).

    - Rejects '..' sequences
    - Rejects paths escaping base directory
    - Validates symlinks don't escape
    - Returns normalized Path
    """
    pass

def validate_path_component(
    component: str,
    param_name: str,
) -> str:
    """
    Validate a single path component for URL interpolation.

    - Rejects '..', '/', '\\'
    - URL-encodes the result
    - Returns safe string for REST API paths
    """
    pass
```

**Files to modify:**
- `assistant-skills-lib/src/assistant_skills_lib/validators.py` (add functions)
- Remove from `splunk-assistant-skills-lib/validators.py` (import from base)

---

### 1.4 Sensitive Field Redaction

**Source:** `splunk-assistant-skills-lib/formatters.py`
**Target:** `assistant-skills-lib/formatters.py`

The Splunk library automatically redacts sensitive fields in output - this should be universal.

**Functions to add:**
```python
# assistant_skills_lib/formatters.py (additions)

SENSITIVE_FIELD_PATTERNS = [
    r"password",
    r"token",
    r"secret",
    r"api_?key",
    r"credential",
    r"auth",
    r"private_?key",
    r"session_?key",
    r"bearer",
]

def is_sensitive_field(field_name: str) -> bool:
    """Check if field name matches sensitive patterns."""
    pass

def redact_sensitive_value(field_name: str, value: Any) -> Any:
    """Redact value if field is sensitive."""
    pass

def format_results_with_redaction(
    results: list[dict],
    output_format: str = "table",
) -> str:
    """Format results with automatic sensitive field redaction."""
    pass
```

**Files to modify:**
- `assistant-skills-lib/src/assistant_skills_lib/formatters.py` (add functions)
- `splunk-assistant-skills-lib/formatters.py` (import from base, extend if needed)

---

### 1.5 Request Batcher

**Source:** `jira-assistant-skills-lib/request_batcher.py`
**Target:** `assistant-skills-lib/request_batcher.py`

Async batch execution with semaphore-based concurrency limits.

**Features:**
- Async/sync interfaces
- Semaphore-based concurrency control
- Partial failure handling
- Progress callbacks
- Request ID mapping

**Interface:**
```python
# assistant_skills_lib/request_batcher.py

@dataclass
class BatchResult:
    request_id: str
    success: bool
    data: Optional[dict]
    error: Optional[str]
    duration_ms: float

class RequestBatcher:
    def __init__(self, client, max_concurrent: int = 10): ...
    def add_request(self, request_id: str, method: str, endpoint: str, **kwargs): ...
    async def execute(self) -> dict[str, BatchResult]: ...
    def execute_sync(self) -> dict[str, BatchResult]: ...
```

---

## Phase 2: Pattern Replication

**Priority: MEDIUM-HIGH**
**Effort: 3-5 days**

### 2.1 Mock Client Architecture

**Source:** `jira-assistant-skills-lib/mock/`
**Target:** All service libraries

The JIRA library has a sophisticated mock client architecture using mixins for modular testing.

**Architecture to replicate:**
```
mock/
├── base.py          # MockClientBase with seed data
├── clients.py       # Composed client classes
├── protocol.py      # MockClientProtocol
└── mixins/
    ├── __init__.py
    ├── admin.py     # AdminMixin
    ├── search.py    # SearchMixin
    └── ...
```

**For Splunk:**
```python
# splunk_assistant_skills_lib/mock/base.py

class MockSplunkClientBase:
    INDEXES = ["main", "security", "_internal", "_audit"]
    USERS = [{"name": "admin", "roles": ["admin"]}]
    JOBS = {}  # sid -> job state

    def create_search_job(self, spl: str) -> dict: ...
    def get_job_status(self, sid: str) -> dict: ...
    def get_job_results(self, sid: str) -> list[dict]: ...
```

**For Confluence:**
```python
# confluence_assistant_skills/mock/base.py

class MockConfluenceClientBase:
    SPACES = [{"key": "TEST", "name": "Test Space"}]
    PAGES = {}  # page_id -> page data

    def get_page(self, page_id: str) -> dict: ...
    def create_page(self, space_key: str, title: str, body: str) -> dict: ...
```

**Files to create:**
- `splunk-assistant-skills-lib/src/.../mock/__init__.py`
- `splunk-assistant-skills-lib/src/.../mock/base.py`
- `splunk-assistant-skills-lib/src/.../mock/clients.py`
- `splunk-assistant-skills-lib/src/.../mock/mixins/` (as needed)
- `confluence-assistant-skills-lib/src/.../mock/` (same structure)

---

### 2.2 Pre-commit Hooks and CI Configuration

**Source:** `splunk-assistant-skills-lib/.pre-commit-config.yaml`
**Target:** All libraries

Standardize code quality tooling across all libraries.

**Files to replicate:**
```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v5.0.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-json
      - id: check-toml
      - id: detect-private-key
  - repo: https://github.com/psf/black
    rev: 24.10.0
    hooks:
      - id: black
  - repo: https://github.com/pycqa/isort
    rev: 5.13.2
    hooks:
      - id: isort
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.13.0
    hooks:
      - id: mypy
  - repo: https://github.com/PyCQA/bandit
    rev: 1.8.0
    hooks:
      - id: bandit
        args: ["-c", "pyproject.toml"]
```

**Files to create/update:**
- `assistant-skills-lib/.pre-commit-config.yaml`
- `jira-assistant-skills-lib/.pre-commit-config.yaml`
- `confluence-assistant-skills-lib/.pre-commit-config.yaml`

---

### 2.3 Dependabot Configuration

**Source:** `splunk-assistant-skills-lib/.github/dependabot.yml`
**Target:** All libraries

```yaml
# .github/dependabot.yml
version: 2
updates:
  - package-ecosystem: "pip"
    directory: "/"
    schedule:
      interval: "weekly"
      day: "monday"
    groups:
      dev-dependencies:
        patterns:
          - "pytest*"
          - "black"
          - "isort"
          - "mypy"
  - package-ecosystem: "github-actions"
    directory: "/"
    schedule:
      interval: "weekly"
```

---

### 2.4 Project Context Pattern

**Source:** `jira-assistant-skills-lib/project_context.py`
**Target:** Splunk and Confluence libraries

Layered configuration loading from skill directories.

**For Splunk:**
```python
# splunk_assistant_skills_lib/search_context.py

@dataclass
class SearchContext:
    index: str
    earliest_time: str
    latest_time: str
    app: Optional[str]
    owner: Optional[str]
    defaults: dict

def load_search_context(index: str = None) -> SearchContext:
    """
    Load search context from:
    1. .claude/skills/splunk-index-{name}/defaults.json
    2. .claude/settings.local.json → splunk.indexes.{name}
    3. Environment variables
    """
    pass
```

---

## Phase 3: Consistency Improvements

**Priority: MEDIUM**
**Effort: 2-3 days**

### 3.1 Harmonize Error Handlers

All three service libraries extend `BaseAPIError` but with slight variations. Standardize:

**Consistent pattern:**
```python
# error_handler.py (all service libraries)

class ServiceError(BaseAPIError):
    """Base exception for service-specific errors."""
    pass

class AuthenticationError(BaseAuthenticationError, ServiceError):
    """Service-specific authentication hints."""

    def __init__(self, message: str = None, **kwargs):
        message = message or f"{SERVICE_NAME} authentication failed"
        hints = [
            f"Check {SERVICE_PREFIX}_API_TOKEN environment variable",
            f"Verify token at: {TOKEN_MANAGEMENT_URL}",
        ]
        super().__init__(message, hints=hints, **kwargs)
```

**Files to modify:**
- Ensure all three libraries follow same inheritance pattern
- Add service-specific hints consistently
- Use `sanitize_error_message()` universally

---

### 3.2 Standardize CLI Structure

All three libraries have Click-based CLIs. Standardize command group organization:

**Recommended structure:**
```
cli/
├── main.py              # Entry point with @click.group()
├── cli_utils.py         # Shared utilities
└── commands/
    ├── __init__.py
    ├── search.py        # Core operations
    ├── job.py           # Background job management
    ├── export.py        # Data export
    ├── metadata.py      # Discovery commands
    ├── admin.py         # Administration
    └── ...
```

**Shared CLI utilities to standardize:**
```python
# cli_utils.py (all libraries)

def get_client_from_context(ctx) -> ServiceClient:
    """Get or create client from Click context."""
    pass

def handle_cli_errors(func):
    """Decorator for consistent error handling."""
    pass

def output_results(data, output_format: str, columns: list = None):
    """Unified output formatting."""
    pass
```

---

### 3.3 Test Infrastructure Standardization

**Source:** `confluence-assistant-skills-lib/tests/conftest.py`

Standardize pytest configuration and fixtures:

```python
# conftest.py (all libraries)

def pytest_addoption(parser):
    parser.addoption("--live", action="store_true", help="Run live API tests")

def pytest_configure(config):
    config.addinivalue_line("markers", "slow: slow running tests")
    config.addinivalue_line("markers", "live: requires live API")
    config.addinivalue_line("markers", "destructive: modifies data")

def pytest_collection_modifyitems(config, items):
    if not config.getoption("--live"):
        skip_live = pytest.mark.skip(reason="Need --live option")
        for item in items:
            if "live" in item.keywords:
                item.add_marker(skip_live)

@pytest.fixture
def mock_client():
    """Return mock client instance."""
    return MockServiceClient()

@pytest.fixture
def temp_config_dir(tmp_path):
    """Create temporary .claude config directory."""
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir()
    return claude_dir
```

---

## Phase 4: Documentation Alignment

**Priority: LOW-MEDIUM**
**Effort: 1-2 days**

### 4.1 README Structure

Standardize README.md structure across all libraries:

```markdown
# {Service} Assistant Skills Library

[![PyPI version](badge)]
[![Python Versions](badge)]
[![License: MIT](badge)]
[![CI](badge)]
[![Security: bandit](badge)]
[![Code style: black](badge)]
[![pre-commit](badge)]

Brief description.

## Installation
## Quick Start
## CLI
## Features
### HTTP Client
### Configuration Management
### Error Handling
### Input Validators
### Security Validators (if applicable)
## API Reference
## Security
## Development
## License
## Contributing
```

### 4.2 CLAUDE.md Structure

Standardize CLAUDE.md for consistent AI assistance:

```markdown
# CLAUDE.md

## Build & Test Commands
## Architecture
### CLI Module
### Core Modules
### Utility Modules
### Key Patterns
### Test Markers
## Coding Patterns
### CLI Commands
### Thread Safety
### Security Considerations
### Error Handling
```

---

## Implementation Sequence

### Week 1: Base Library Enhancements
| Day | Task | Library |
|-----|------|---------|
| 1 | Add security validators to base | assistant-skills-lib |
| 1 | Add sensitive field redaction to base | assistant-skills-lib |
| 2 | Extract credential manager base class | assistant-skills-lib |
| 2 | Update JIRA to extend base credential manager | jira-assistant-skills-lib |
| 3 | Extract batch processor to base | assistant-skills-lib |
| 3 | Update JIRA to import from base | jira-assistant-skills-lib |
| 4 | Extract request batcher to base | assistant-skills-lib |
| 5 | Tests and documentation | all |

### Week 2: Pattern Replication
| Day | Task | Library |
|-----|------|---------|
| 1 | Add credential manager | splunk-assistant-skills-lib |
| 1 | Add credential manager | confluence-assistant-skills-lib |
| 2 | Create mock client structure | splunk-assistant-skills-lib |
| 3 | Create mock client structure | confluence-assistant-skills-lib |
| 4 | Add pre-commit and dependabot | assistant-skills-lib, jira, confluence |
| 5 | Tests and documentation | all |

### Week 3: Consistency and Polish
| Day | Task | Library |
|-----|------|---------|
| 1 | Harmonize error handlers | all |
| 2 | Standardize CLI structure | all |
| 3 | Standardize test infrastructure | all |
| 4 | Documentation alignment | all |
| 5 | Final review and release | all |

---

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| Breaking changes in base library | HIGH | Semantic versioning, deprecation warnings |
| Import cycles with new base classes | MEDIUM | Careful module organization, lazy imports |
| Inconsistent behavior after refactor | MEDIUM | Comprehensive test coverage before/after |
| Migration complexity for existing users | LOW | Maintain backward compatibility aliases |

---

## Success Metrics

1. **Code Reuse**: ≥80% of common patterns in base library
2. **Test Coverage**: ≥80% in all libraries
3. **Consistency**: Same CLI structure, error handling, config loading
4. **Security**: All libraries have path traversal and injection prevention
5. **DX**: Unified developer experience across all service libraries

---

## Appendix: File Checklist

### Base Library Additions
- [ ] `src/assistant_skills_lib/credential_manager.py`
- [ ] `src/assistant_skills_lib/batch_processor.py`
- [ ] `src/assistant_skills_lib/request_batcher.py`
- [ ] Update `src/assistant_skills_lib/validators.py`
- [ ] Update `src/assistant_skills_lib/formatters.py`
- [ ] Update `src/assistant_skills_lib/__init__.py`

### Service Library Updates
- [ ] `jira-assistant-skills-lib` - Extend base credential manager
- [ ] `jira-assistant-skills-lib` - Import batch processor from base
- [ ] `splunk-assistant-skills-lib` - Add credential manager
- [ ] `splunk-assistant-skills-lib` - Add mock client
- [ ] `splunk-assistant-skills-lib` - Import security validators from base
- [ ] `confluence-assistant-skills-lib` - Add credential manager
- [ ] `confluence-assistant-skills-lib` - Add mock client

### Configuration Files
- [ ] `.pre-commit-config.yaml` - All libraries
- [ ] `.github/dependabot.yml` - All libraries
- [ ] `pyproject.toml` - bandit config - All libraries

### Documentation
- [ ] README.md structure alignment
- [ ] CLAUDE.md structure alignment
- [ ] CHANGELOG.md updates
