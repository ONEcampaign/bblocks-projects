# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **Packages in a subdirectory of a multi-language repo.** `doctor` reads `.pre-commit-config.yaml` and `.github/workflows/` from the root of the git work tree that contains `--path`, so `doctor --family --path python` passes items 4 and 10 on the repo's root files. See [A package in a multi-language repo](../docs/the-family-contract.md#a-package-in-a-multi-language-repo).
- **Item 6 exemption for `development-finance`**, the DFO client, reported as the `contract.readerkit_exempt` advisory. Item 7 still applies to it.
- Item 6 counts `httpx2`, as a dependency or an import, as a fetch signal.

### Fixed

- `drift.project_slug_mismatch` compares `project_slug` against `[tool.uv.build-backend] module-name` when it is set, so a distribution whose import package differs from its name passes.

## [1.1.1] - 2026-08-13

### Fixed

- **`copier update` could destroy real source and tests.** The template's post-generation `_tasks` (`git init`, `uv venv`, `uv sync`, `git add .`, `git commit`, installing the pre-commit hook) ran unconditionally on both `copier copy` and `copier update`. On update, copier's `_apply_update()` runs those tasks against the _real_ subproject — and does so before it replays the diff that restores local edits, not after. If any task failed on that second run (`uv venv` errors outright when `.venv` already exists; `git commit` fails when a pre-commit hook reformats a file mid-commit; `uv sync` can fail on a network hiccup or a dependency floor the subproject can't satisfy), the failure aborted the update immediately after the working tree had already been overwritten with fresh template scaffold, but before copier ever reapplied the subproject's real content. The result: hand-written source and tests silently replaced with placeholder boilerplate, already staged, with no conflict markers or `.rej` files to signal that anything had gone wrong. Initial `copier copy` was never affected — a failed task there triggers copier's own cleanup of the half-built directory instead.

  Every task in `_tasks` is now guarded to run only on the initial `copy` — including `uv sync`, even though it's the most "idempotent-looking" of the six. The point isn't that each task is individually unsafe to repeat; it's that a task failing mid-update is categorically worse than a task simply not running, so no task runs on update at all, and `_message_after_update` now tells you which of these to run by hand (`uv sync`, `uv run pre-commit install` if the hook config changed, then commit). (Installing the hook has to be guarded for a second, independent reason: `copier update` also runs `_tasks` inside the throwaway template renders it diffs internally, and those only become git repos _after_ `_tasks` runs, so an unguarded `pre-commit install` fails there once `git init` is skipped.)

  **Why not `skip_if_exists` instead (or as well)?** It doesn't address the actual failure mode — the diff/merge itself already preserves hand-written content correctly once nothing aborts it mid-update — and it would permanently stop the template from ever evolving `src/{project_slug}/__init__.py` or `tests/`, which are exactly the files every generated project immediately overwrites with real code. The task guard fixes the actual defect without giving up template evolution of those files.

  **One-time consequence of this fix: your first `copier update` onto 1.1.1 or later will delete `uv.lock`.** `uv.lock` isn't a template file — it only exists because `uv sync` used to create it. Copier's update mechanism renders your project's _previous_ template version into a scratch copy to compute what changed; if that previous version still had `uv sync` unguarded, the scratch copy gets a `uv.lock` and the new (1.1.1+) scratch copy doesn't, and copier's own cleanup step — which recursively deletes anything present in the "old" scratch render but absent from the "new" one, with no way to exempt a path from it — reads that as "the template stopped shipping this file" and removes it from your real project. It's a one-time side effect of the transition, not a recurring one: once a project is fully on 1.1.1+, both renders agree `uv sync` doesn't run, and further updates leave `uv.lock` alone. The fix is exactly `_message_after_update`'s first recommended step: run `uv sync` after updating and it's back.

## [1.1.0] - 2026-08-13

### Added

- **`preset` template question.** New `create`/`update` question, `standalone` (default) or `family`. `family` opts a repo into the bblocks family contract — a Python 3.12 floor, `readerkit` for HTTP and caching, no upper-bound pins, OIDC publishing, branch protection, and a conda-forge feedstock — and is recorded in `.copier-answers.yml` so `doctor` can read it without the network. Choosing `family` also changes `python_version`'s default to `3.12` (was `3.13`) and rejects `3.11` at the prompt.
- **`doctor --family`** — runs the twelve family-contract checks against a project, reported in a new "Family contract" section. Runs automatically when `.copier-answers.yml` records `preset: family`; pass the flag explicitly for a `standalone` repo or one that predates the `preset` question and has no answers file at all. See [the family contract docs](../docs/the-family-contract.md).
- **`doctor --check-remote`** — also runs the two contract checks that hit the network (branch protection via `gh api`, the conda-forge feedstock via `api.anaconda.org`). Without it, both report a `not checked (pass --check-remote)` advisory instead of a false pass.

### Changed

- **Raised `bblocks-projects`' own Python floor to 3.12** (was 3.11) and dropped the 3.11 classifier. `target-version`, `[tool.ty.environment]`, the CI matrix (now `3.12`–`3.14`), and the publish workflow's Python version all moved with it. No source changes were needed — there were no 3.11-only compatibility shims.
- **The `doctor` summary line now counts findings and advisories separately.** It previously printed `f"{n} findings"` for `n` findings-plus-advisories combined, so a run with one real finding and ten advisories read "11 findings" — overstating what `--strict` would actually fail on. It now reads `"1 finding, 10 advisories (use --strict to fail)"`, with correct singular/plural on both nouns.

## [1.0.3] - 2026-07-16

### Fixed

- **Generated `project`-type projects now define `__version__`.** The
  non-package `src/{slug}/__init__.py` shipped with only a docstring, but
  the generated `test_version` asserts `__version__ == "0.1.0"` — so the
  first CI run of a fresh `project` scaffold with pytest failed. The init
  now defines `__version__`, matching the package template.
- **Generated CI uploads coverage with the `files:` input.** The upload
  step passed `file:` (singular) to `codecov/codecov-action`, an input
  dropped in the action's v4+ rewrite — so `actionlint` failed on every
  generated project and the coverage path was mis-named. Now uses
  `files:` with `codecov/codecov-action@v7`.

### Changed

- **Refreshed the dependency floors scaffolded into new projects** —
  pytest `>=9.1.0`, pytest-cov `>=7.1.0`, ruff `>=0.15.0`, ty `>=0.0.59`,
  pre-commit `>=4.6.0`, and the `uv_build` backend `>=0.11.29,<0.12`.
- **Updated the pinned pre-commit hooks in new projects** —
  ruff-pre-commit `v0.15.21` and codespell `v2.4.3`, and pinned
  `mdformat-gfm` / `mdformat-frontmatter` for compatibility with
  mdformat 1.0's plugin interface.
- **Updated the GitHub Actions in generated CI and release workflows** —
  `actions/checkout@v7`, `astral-sh/setup-uv@v8.3.2`, `actions/cache@v6`,
  and `codecov/codecov-action@v7`.
- **Bumped the CLI's own dependencies** — copier `>=9.17.0`, rich
  `>=15.0.0`, tomlkit `>=0.15.0`, typer `>=0.26.0`, and the dev toolchain
  (pytest, ruff, ty, mkdocs-material).

## [1.0.2] - 2026-05-03

### Added

- **`include_pytest` template variable for `project`-type repos.** Asks at
  creation time whether to scaffold pytest (config sections, dev deps,
  `tests/` directory, CI test job). Default `false` — opt-in. Packages
  always include pytest, unchanged.

### Changed

- **`project`-type repos no longer ship dead pytest config sections.**
  Previously, `[tool.pytest.ini_options]`, `[tool.coverage.run]`, and
  `[tool.coverage.report]` were rendered for every project type, even
  when pytest itself wasn't installed — which caused `bblocks-projects
add pytest` to flag spurious "Conflicts detected" against
  byte-identical config. Now those sections render only when pytest is
  actually present.
- **`doctor` no longer flags pytest as missing for `project`-type repos
  that opted out.** When `include_pytest: false` (or absent) in
  `.copier-answers.yml`, the pytest component check is skipped.

## [1.0.1] - 2026-05-03

### Changed

- Generated project default Python version is now `3.13` (was `3.11`).
  3.11 entered security-only support in October 2024.
- Generated `pyproject.toml`, CI workflow, pre-commit hook, and README use
  `uv run ty` instead of `uvx ty`, picking up the version pin from the
  dev-dep group.

### Added

- Python `3.14` is now selectable as the minimum version.
- Generated `.gitignore` ignores `.env` files (with a `!.env.example` carve-out).

### Fixed

- CI test matrix no longer emits duplicate versions for projects pinned to
  `3.12` or `3.13`.
- `.claude/` entry in generated `.gitignore` is now directory-only.

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
