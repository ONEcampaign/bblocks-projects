# How to add components to an existing project

`uvx bblocks-projects add` installs one or more template features (pre-commit, ruff, CI, pytest, PyPI publishing) into a Python project, including projects that weren't created from the template. Use this for projects that need individual pieces of the template's tooling but not the full Copier-managed layout.

To bring an unmanaged project under full template management, see [Adopting an existing project](adopting-an-existing-project.md) instead.

## Before you start

- The project must have a `pyproject.toml` and use [`uv`](https://docs.astral.sh/uv/) for dependency management. If `uv.lock` doesn't exist yet, run `uv sync` first.
- Run from inside the project directory, or pass `--path /path/to/project`.

## What's available

```bash
uvx bblocks-projects add --list
```

| Component | What it installs | Project types |
|---|---|---|
| `pre-commit` | `.pre-commit-config.yaml` + `pre-commit` dev dep | any |
| `ruff` | `[tool.ruff]` and friends in `pyproject.toml` + `ruff` dev dep | any |
| `ci` | `.github/workflows/ci.yml` | any |
| `pytest` | `[tool.pytest.ini_options]`, `[tool.coverage.*]` + `pytest`, `pytest-cov` dev deps | any |
| `pypi-publish` | `.github/workflows/release.yml` + ensures `[build-system]` exists | `package` only |

`.pre-commit-config.yaml` and everything under `.github/` belong at the root of the git work tree, the place Git and GitHub read them from. For a package in `python/` of a multi-language repo, that root holds the tooling of every language, so `add pre-commit`, `add ci`, and `add pypi-publish` refuse there, name the root file to edit, and change nothing, with or without `--force`. Edit the root file by hand; [A package in a multi-language repo](the-family-contract.md#a-package-in-a-multi-language-repo) says what each file needs. `add ruff` and `add pytest` write only inside the package and work as usual. A package at its git root, or outside a git work tree, gets all five components in its own directory.

Component definitions live in `src/bblocks/projects/components.py` if you want the precise list of files and config keys each one writes.

## Add one component

```bash
uvx bblocks-projects add pre-commit
```

You'll get a project summary, a list of what will change, and a confirmation prompt before anything is written:

```
Project Analysis:
  Path: /Users/you/donor-analysis
  Name: donor-analysis
  Type: project
  Uses uv: Yes

Installing component: pre-commit
Pre-commit hooks with ruff and ty

✓ Created: .pre-commit-config.yaml

Dev dependencies to add:
  • pre-commit>=3.0.0

Add these dependencies now? [y/n]:
```

Accepting writes the file, runs `uv add --dev pre-commit`, and prints next steps:

```
✓ Component installed successfully!

Next steps:
  1. Run: uv sync
  2. Run: uv run pre-commit install
  3. Test: uv run pre-commit run --all-files
```

## Add several at once

```bash
uvx bblocks-projects add ruff ci pytest
```

Components install sequentially, with the same prompt-and-confirm flow for each. The template is rendered once per invocation, so this is faster than running `add` once per component.

## Skip prompts in scripts

```bash
uvx bblocks-projects add ruff --yes
```

`--yes` accepts the confirmation prompts. It does *not* overwrite existing files — for that, see the next section.

## Handle conflicts (file or config already exists)

When a target file already exists or a `[tool.X]` section is already in `pyproject.toml`, `add` warns:

```
Conflicts detected:
  • File exists: .pre-commit-config.yaml
  • Config section exists: tool.ruff

Continue anyway? (will merge configs, skip existing files) [y/n]:
```

By default, **continuing merges configs and skips existing files**: your settings stay, and the template's settings are added where they don't collide.

To overwrite a conflicting file with the template's version:

```bash
uvx bblocks-projects add pre-commit --force
```

`--force` only affects files. Config sections are still merged section-by-section: if you have `[tool.ruff]` with rules the template would also add, the template's rules win on per-key collision but your other rules stay.

!!! warning "Heads up"
    `--force` skips the conflict prompt. Use it when you've already reviewed the diff or when scripting against projects you control.

## Add to a project elsewhere on disk

```bash
uvx bblocks-projects add ci --path /path/to/other-project
```

Useful when you're applying the same component across several projects from a single working directory.

## Verify it worked

```bash
git status                     # see what was added/modified
git diff pyproject.toml        # review merged config sections
uv sync                        # install any new dev deps
uv run ruff check .            # if you added ruff
uv run pre-commit run --all-files   # if you added pre-commit
```

If you added `ci`, commit and push to trigger the first run:

```bash
git add .github/workflows/ci.yml
git commit -m "Add CI workflow"
git push
```

If you added `pypi-publish`, the [components reference](reference.md#components) lists the PyPI trusted-publishing setup steps.

## Troubleshooting

**`pypi-publish component is only for package projects`**
The component requires `project_type=package` in `.copier-answers.yml`, or — for unmanaged projects — `bblocks-projects` infers `package` from the presence of a `src/{slug}/` and `tests/` layout. If the project is meant to be a package but the layout isn't there yet, set it up first or run `bblocks-projects create` to start fresh.

**`Type mismatch at tool.ruff.lint.select`**
You have a key in `pyproject.toml` whose type doesn't match the template's (e.g., a string where the template expects a list). Fix the key by hand and rerun.

**`No pyproject.toml found` or `No uv.lock found`**
The project isn't using `uv` yet. Run `uv init --no-readme` (for a fresh project) or `uv sync` (if `pyproject.toml` already exists) first.

## See also

- [Reference: components and `add` flags](reference.md#components)
- [Adopting an existing project](adopting-an-existing-project.md) — if you eventually want full template management
- [Running the doctor](running-the-doctor.md) — `doctor` reports any standard component that's missing
