# Assistant Skills Library

Shared Python utilities for building Claude Code Assistant Skills plugins.

[![PyPI version](https://badge.fury.io/py/assistant-skills-lib.svg)](https://badge.fury.io/py/assistant-skills-lib)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Installation

```bash
pip install assistant-skills-lib

# With HTTP support (for requests-based error handling)
pip install assistant-skills-lib[http]
```

## Quick Start

```python
from assistant_skills_lib import (
    format_table,
    validate_url,
    Cache,
    handle_errors,
    APIError,
)

# Format data as a table
data = [
    {"name": "Alice", "role": "Admin"},
    {"name": "Bob", "role": "User"},
]
print(format_table(data, headers=["name", "role"]))

# Validate input
url = validate_url("https://api.example.com")

# Cache API responses
cache = Cache(app_name="my-skill")
cache.set("user:123", {"name": "Alice"}, ttl=300)
user = cache.get("user:123")

# Handle errors with decorator
@handle_errors
def main():
    # Your code here - errors are caught and formatted
    pass
```

## Modules

### Formatters

Output formatting utilities for tables, trees, and colored text.

```python
from assistant_skills_lib import (
    format_table,
    format_tree,
    format_list,
    format_json,
    print_success,
    print_error_formatted,
    print_warning,
    Colors,
)

# Table formatting
data = [{"id": 1, "name": "Item 1"}, {"id": 2, "name": "Item 2"}]
print(format_table(data, headers=["id", "name"]))

# Tree formatting
tree = {"root": {"child1": {}, "child2": {"grandchild": {}}}}
print(format_tree(tree))

# Colored output
print_success("Operation completed!")
print_warning("Check your configuration")
```

### Validators

Input validation utilities with clear error messages.

```python
from assistant_skills_lib import (
    validate_url,
    validate_required,
    validate_name,
    validate_path,
    validate_choice,
    InputValidationError,
)

# URL validation
url = validate_url("https://api.example.com")

# Required field validation
name = validate_required(user_input, "username")

# Name validation (alphanumeric, hyphens, underscores)
skill_name = validate_name("my-skill", field_name="skill name")

# Choice validation
status = validate_choice(value, choices=["active", "inactive"], field_name="status")
```

### Cache

File-based response caching with TTL support.

```python
from assistant_skills_lib import Cache, cached, get_cache, invalidate

# Direct cache usage
cache = Cache(app_name="my-skill", default_ttl=300)
cache.set("key", {"data": "value"})
value = cache.get("key")

# Decorator usage
@cached(ttl=600, app_name="my-skill")
def fetch_user(user_id):
    return api.get_user(user_id)

# Global cache access
cache = get_cache("my-skill")
cache.clear()

# Invalidate by pattern
invalidate("user:", app_name="my-skill")
```

### Error Handler

Exception hierarchy and error handling utilities.

```python
from assistant_skills_lib import (
    handle_errors,
    handle_api_error,
    APIError,
    AuthenticationError,
    NotFoundError,
    RateLimitError,
    print_error,
    ErrorContext,
)

# Decorator for main functions
@handle_errors
def main():
    # Exceptions are caught, formatted, and exit with appropriate code
    pass

# Handle API response errors
def make_request():
    response = requests.get(url)
    if not response.ok:
        handle_api_error(response, operation="fetch user")

# Context manager for detailed error context
with ErrorContext("creating resource", resource_id=123):
    client.post("/api/resources", data=data)

# Raise specific errors
raise NotFoundError("User not found", status_code=404)
raise RateLimitError("Too many requests", retry_after=60)
```

### Template Engine

Template loading and rendering with placeholder support.

```python
from assistant_skills_lib import (
    load_template,
    render_template,
    list_placeholders,
    list_template_files,
)

# Load and render templates
template = load_template("templates/skill.md")
content = render_template(template, {
    "SKILL_NAME": "my-skill",
    "DESCRIPTION": "A helpful skill",
})

# List placeholders in a template
placeholders = list_placeholders(template)
# Returns: ["SKILL_NAME", "DESCRIPTION", ...]
```

### Project Detector

Detect and analyze Assistant Skills project structure.

```python
from assistant_skills_lib import (
    detect_project,
    list_skills,
    validate_structure,
    get_project_stats,
)

# Detect project type
project = detect_project("/path/to/project")
# Returns: {"name": "Jira-Assistant-Skills", "type": "assistant-skills", ...}

# List skills in a project
skills = list_skills("/path/to/project")
# Returns: [{"name": "search", "path": "...", "has_scripts": True}, ...]

# Validate project structure
result = validate_structure("/path/to/project")
# Returns: {"valid": True, "errors": [], "warnings": [...]}

# Get project statistics
stats = get_project_stats("/path/to/project")
# Returns: {"skills": 5, "scripts": 12, "templates": 8, ...}
```

## Development

```bash
# Clone the repository
git clone https://github.com/grandcamel/assistant-skills-lib.git
cd assistant-skills-lib

# Install in development mode
pip install -e ".[dev]"

# Run tests
pytest

# Run linting
ruff check src/

# Type checking
mypy src/
```

## License

MIT License - see [LICENSE](LICENSE) for details.
