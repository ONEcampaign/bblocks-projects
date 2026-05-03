# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-05-02

This release marks the first stable version. The four-command surface
(`create` / `update` / `add` / `doctor`) is now considered the public API —
future 1.x releases will keep flag names, exit-code semantics, and template
variable names backwards-compatible.

### Added

- **`doctor` command** — a health check that reports how a managed project
  has drifted from the current standards. Groups findings into four
  sections (scaffolding, drift, components, template version) and three
  severities (catastrophic, finding, advisory). Pass `--strict` to fail
  CI on any finding, or `--check-updates` to also compare your local
  template commit against the upstream `HEAD`.
- **Configurable template URL** — point the CLI at a fork or private
  template via `--template/-T` on any command, the
  `BBLOCKS_PROJECTS_TEMPLATE` environment variable, or a
  `template_url` key in `~/.config/bblocks-projects/config.toml`. The
  CLI announces the resolved source whenever it isn't the default.

### Changed

- **Renamed project type `research` → `project`.** The non-package type
  now has a name that covers analysis, data pipelines, internal tools,
  and ad-hoc scripts. The rename is fully backwards-compatible: existing
  projects with `project_type: research` in `.copier-answers.yml` keep
  working without changes, and `--type research` still renders the same
  layout. New projects pick `project` (the new default at the prompt).
- **Cleaner `project` layout.** Generated projects now ship with a
  minimal `src/{slug}/__init__.py` plus a `data/raw/` (gitignored) and
  `data/processed/` (tracked) tree, instead of the previous
  `scripts/config.py`, `scripts/logger.py`, and `scripts/example_analysis.py`
  scaffolding. The result is closer to what teams actually keep.
- **Looser ruff and ty rules for `project`-type repos.** Analysis code
  legitimately reaches into pandas / numpy whose type stubs are
  incomplete. The non-package config now tolerates those stub gaps
  instead of producing noise that gets globally ignored.
- **Smarter `add` merging.** Adding a component now merges into your
  existing `pyproject.toml` section-by-section instead of overwriting.
  Adding several components in one invocation renders the template
  once and shares it across them.
- **Better project-type detection.** `bblocks-projects` reads
  `.copier-answers.yml` first; for unmanaged projects, the presence of
  `tests/` signals a package and `data/` signals a project. The old
  rule of "any `src/` layout means package" no longer applies (both
  types use `src/`).
- **Documentation rewritten and moved.** The MkDocs site lives at the
  repo root (`/docs/`), restructured into a tutorial, how-tos for each
  command, a reference, and an explanation page on `package` vs
  `project`. The content is now accurate against the current code —
  several pages of the previous docs described file paths and prompts
  that no longer exist.

### Fixed

- **`pyproject.toml` config merge no longer corrupts mixed types.** A
  type mismatch at a leaf key (e.g., a string where the template
  expects a list) now raises a clear error during `add` instead of
  silently producing an invalid file.
- **Component installer no longer leaves stale renders on disk.** The
  template tempdir is cleaned up via context manager whether or not
  the install succeeds.

## [0.2.2] - 2024-12-16

### Fixed

- **Mypy fails in CI on untyped third-party packages**: Added `ignore_missing_imports = true` to mypy config. Third-party packages without type stubs (e.g., `oda_data`, `pydeflate`) no longer cause `[import-untyped]` errors in GitHub Actions.

## [0.2.1] - 2024-12-16

### Fixed

- **Pre-commit mypy `--install-types` removed**: Removed `--install-types` and `--non-interactive` flags from mypy pre-commit hook. Type stubs should be declared as explicit dev dependencies in `pyproject.toml` rather than auto-installed on every commit, which caused slow commits, network failures when offline, and non-deterministic behavior.

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
