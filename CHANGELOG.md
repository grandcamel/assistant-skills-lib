# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-01-20

### Changed
- **BREAKING**: Removed profile feature from `BaseConfigManager`
  - Removed `profile` parameter from `__init__()`
  - Removed `get_profile_config()` method
  - Removed `list_profiles()` method
  - Configuration now uses flat structure instead of profile-based hierarchy

### Migration
To upgrade from 0.3.0:
- Remove `profile=` parameter from `BaseConfigManager` subclass constructors
- Update config files from profile-based to flat structure
- Remove calls to `get_profile_config()` and `list_profiles()`

## [0.3.0] - 2025-01-18

### Added
- Batch processing utilities (`BatchProcessor`, `BatchConfig`, `CheckpointManager`)
- Keychain credential management support
- Autocomplete cache functionality
- Request batching utilities

## [0.2.1] - 2025-01-15

### Fixed
- Thread-safe singleton access in `BaseConfigManager`

## [0.2.0] - 2025-01-14

### Added
- `BaseConfigManager` with profile support
- `Cache` module for response caching
- Base formatters and validators

## [0.1.0] - 2025-01-10

### Added
- Initial release
- Base HTTP client utilities
- Common error handling patterns
- Shared formatter functions

[1.0.0]: https://github.com/grandcamel/assistant-skills-lib/compare/v0.3.0...v1.0.0
[0.3.0]: https://github.com/grandcamel/assistant-skills-lib/compare/v0.2.1...v0.3.0
[0.2.1]: https://github.com/grandcamel/assistant-skills-lib/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/grandcamel/assistant-skills-lib/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/grandcamel/assistant-skills-lib/releases/tag/v0.1.0
