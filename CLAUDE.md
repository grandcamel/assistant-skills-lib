# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is `assistant-skills-lib`, a shared Python library published to PyPI that provides utilities for building Claude Code Assistant Skills plugins. It offers formatters, validators, caching, error handling, template rendering, and project detection.

## Commands

### Install Dependencies
```bash
pip install -e ".[dev]"
```

### Run Tests
```bash
pytest
```

### Run Single Test
```bash
pytest tests/test_cache.py::test_cache_set_get -v
```

### Run Tests with Coverage
```bash
pytest --cov=assistant_skills_lib --cov-report=xml
```

### Run Linting
```bash
ruff check src/
```

### Type Checking
```bash
mypy src/ --ignore-missing-imports
```

## Architecture

### Module Structure

The library is organized into six core modules in `src/assistant_skills_lib/`:

| Module | Purpose |
|--------|---------|
| `formatters.py` | Output formatting (tables, trees, colors, truncation) |
| `validators.py` | Input validation with clear error messages |
| `cache.py` | SQLite-based caching with TTL, LRU eviction, pattern invalidation |
| `error_handler.py` | Exception hierarchy, `@handle_errors` decorator, error sanitization |
| `config_manager.py` | Multi-source config loading (env vars, `.claude/settings*.json`) |
| `template_engine.py` | Template loading and placeholder rendering |
| `project_detector.py` | Assistant Skills project structure detection |

### Public API

All public exports are defined in `__init__.py`. The library maintains backwards compatibility through aliases:
- `Cache` → `SkillCache`
- `get_cache` → `get_skill_cache`
- `APIError` → `BaseAPIError`
- `InputValidationError` → `ValidationError`

### Error Hierarchy

```
BaseAPIError
├── AuthenticationError (401)
├── PermissionError (403)
│   └── AuthorizationError
├── ValidationError (400)
├── NotFoundError (404)
├── RateLimitError (429)
├── ConflictError (409)
└── ServerError (5xx)
```

### Cache System

`SkillCache` uses SQLite with:
- Category-based TTL defaults
- LRU eviction when size limit reached
- Glob pattern invalidation (optimized to SQL LIKE where possible)
- Thread-safe access via `threading.RLock`

### Config Manager Pattern

`BaseConfigManager` is an abstract base class. Service-specific managers inherit from it and implement:
- `get_service_name()` - returns service identifier (e.g., 'jira')
- `get_default_config()` - returns default configuration dict

Config sources (highest to lowest priority):
1. Environment variables (`{SERVICE}_*`)
2. `.claude/settings.local.json` (gitignored)
3. `.claude/settings.json` (committed)
4. Hardcoded defaults

## Testing

Tests are in `tests/` with one test file per module. The `pyproject.toml` configures pytest with:
- `testpaths = ["tests"]`
- `pythonpath = ["src"]`
- `addopts = "-v --tb=short"`

CI runs tests against Python 3.9-3.12.

## Backwards Compatibility

When renaming internal methods that downstream packages may use, always add an alias:

```python
def _merge_config(self, base, override):
    # Implementation
    ...

# Backwards compatibility alias
_deep_merge = _merge_config
```

Current aliases in `config_manager.py`:
- `_deep_merge` → `_merge_config` (used by splunk-as, jira-as)

Current aliases in `__init__.py`:
- `Cache` → `SkillCache`
- `get_cache` → `get_skill_cache`
- `APIError` → `BaseAPIError`
- `InputValidationError` → `ValidationError`
