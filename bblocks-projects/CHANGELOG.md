# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2024-12-16

### Added

- **Interactive destination prompt**: Running `bblocks-projects create` without arguments now asks whether to create in the current directory or a new subdirectory, making the workflow more discoverable
- **`--here` flag**: Create projects directly in the current directory with `bblocks-projects create --here` or `bblocks-projects create .`
- **GitHub CLI integration**: Author information (name, email, username) is automatically prefilled from GitHub CLI (`gh`) when authenticated
- **`--no-github` flag**: Skip GitHub detection with `bblocks-projects create --no-github`

### Changed

- **Relaxed mypy settings**: Replaced `strict = true` with individual, more permissive settings:
  - `disallow_untyped_defs = false` - Allow untyped functions
  - `disallow_any_generics = false` - Allow bare `list` instead of requiring `list[int]`
  - `check_untyped_defs = true` - Still check logic inside untyped functions
  - `disallow_incomplete_defs = true` - If you start typing a function, finish it
- **Pre-commit mypy args**: Removed `--strict` flag from pre-commit hooks, now uses `pyproject.toml` settings
- **Updated hook versions**: Pre-commit hooks updated to latest versions (ruff v0.8.4, pre-commit-hooks v5.0.0)

### Fixed

- **Pre-commit installation**: Added `pre-commit>=3.0.0` to template dev dependencies so `pre-commit install` no longer fails during project setup

## [0.1.2] - 2024-12-15

### Added

- Initial public release
- `create` command for new projects
- `update` command for existing projects
- `add` command for adding components to existing projects
- Package and research project templates
- Pre-commit, ruff, CI, pytest, and pypi-publish components
