# Reference

Every command, flag, template variable, and component. Runnable examples live in the how-tos.

As of `bblocks-projects 1.0.0`.

## CLI

Common to all commands:

- **`-v, --version`** — print the version and exit.
- **`--help`** — print Typer-generated help for any command.

### `create`

Generate a new project from the template.

```
bblocks-projects create [OPTIONS] [DESTINATION]
```

**Arguments**

- **`DESTINATION`** *(optional)* — directory for the new project. Pass `.` or `--here` for the current directory. If omitted, you'll be asked interactively.

**Options**

- **`-H, --here`** — create in the current directory.
- **`-r, --ref TEXT`** *(default: `main`)* — template branch, tag, or commit.
- **`-t, --type TEXT`** — `package` or `project` (or legacy `research`). Skips the project-type prompt.
- **`-d, --data KEY=VALUE`** *(repeatable)* — override a template variable.
- **`--defaults`** — accept every default answer non-interactively.
- **`--no-github`** — skip the `gh` profile prefill.
- **`-T, --template TEXT`** — template URL. Overrides env / config / default.

**Examples** — see [Creating projects](creating-projects.md).

**Exit codes** — `0` on success, `1` on validation error or template failure.

### `update`

Re-run the template against an already-generated project.

```
bblocks-projects update [OPTIONS]
```

Requires `.copier-answers.yml` at the project root.

**Options**

- **`-p, --path PATH`** *(default: current directory)* — project to update.
- **`-r, --ref TEXT`** *(default: `main`)* — template branch, tag, or commit.
- **`-d, --data KEY=VALUE`** *(repeatable)* — override one or more template answers.
- **`--skip-answered / --no-skip-answered`** *(default: `--skip-answered`)* — silently reuse previous answers (default), or re-prompt for all of them.
- **`-T, --template TEXT`** — template URL. Same precedence as `create`.

**Exit codes** — `0` on success, `1` if `.copier-answers.yml` is missing or Copier returns an error.

### `add`

Install one or more components into an existing Python project.

```
bblocks-projects add [OPTIONS] [COMPONENTS]...
```

The project must have a `pyproject.toml` and a `uv.lock`.

**Arguments**

- **`COMPONENTS`** — one or more of `pre-commit`, `ruff`, `ci`, `pytest`, `pypi-publish`. Required unless `--list` is passed.

**Options**

- **`-p, --path PATH`** *(default: current directory)* — target project.
- **`-f, --force`** — overwrite existing files. Config sections are still merged section-by-section.
- **`-y, --yes`** — skip confirmation prompts.
- **`-l, --list`** — print available components and exit.

**Exit codes** — `0` if every requested component installed, `1` if at least one failed.

### `doctor`

Run health checks against a managed project.

```
bblocks-projects doctor [OPTIONS]
```

Requires `pyproject.toml` and `.copier-answers.yml` at the project root.

**Options**

- **`-p, --path PATH`** *(default: current directory)* — project to diagnose.
- **`--strict`** — exit `1` on any *finding* (severity `finding` only; advisories never affect the exit code).
- **`--check-updates`** — also compare local `_commit` against the template's upstream `HEAD` (network call, 5s timeout).

**Exit codes** — `0` on a healthy project. `1` on any catastrophic finding, or — with `--strict` — any finding.

## Template variables

Source of truth: `copier.yml` in the [template repo](https://github.com/ONEcampaign/bblocks-projects/blob/main/copier.yml). Pass any of these to `create` or `update` via `--data KEY=VALUE`.

| Variable | Type | Default | Allowed values | When |
|---|---|---|---|---|
| `project_name` | `str` | — | any string | always |
| `project_slug` | `str` | derived from `project_name` | valid Python identifier | always |
| `project_description` | `str` | — | any string | always |
| `project_type` | `str` | `project` | `package`, `project`, `research` (legacy alias for `project`) | always |
| `include_notebooks` | `bool` | `false` | `true`, `false` | only when `project_type != 'package'` |
| `author_name` | `str` | `""` | any string | always |
| `author_email` | `str` | `""` | any string | always |
| `python_version` | `str` | `3.13` | `3.11`, `3.12`, `3.13`, `3.14` | always |
| `license` | `str` | `mit` | `mit`, `apache`, `bsd3`, `none` | always |
| `github_username` | `str` | — | any string | only when `project_type == 'package'` |

Notes:

- `project_slug` defaults to `project_name | lower | replace(' ', '_') | replace('-', '_')`. Override with `--data project_slug=...` if you want a non-default mapping.
- The license values are short codes (`apache`, not `apache-2.0`; `bsd3`, not `bsd-3-clause`). The full SPDX names appear only in the generated `LICENSE` file.

## Components

Source of truth: `src/bblocks/projects/components.py`.

| Name | Files written | `pyproject.toml` sections | Dev deps | Project type |
|---|---|---|---|---|
| `pre-commit` | `.pre-commit-config.yaml` | — | `pre-commit>=3.0.0` | any |
| `ruff` | — | `tool.ruff`, `tool.ruff.lint`, `tool.ruff.lint.pydocstyle`, `tool.ruff.lint.per-file-ignores`, `tool.ruff.format` | `ruff>=0.8.0` | any |
| `ci` | `.github/workflows/ci.yml` | — | — | any |
| `pytest` | — | `tool.pytest.ini_options`, `tool.coverage.run`, `tool.coverage.report` | `pytest>=8.0.0`, `pytest-cov>=4.1.0` | any |
| `pypi-publish` | `.github/workflows/release.yml` | `build-system` (only added if missing) | — | `package` only |

`pypi-publish` post-install steps include placeholders that are filled from your `.copier-answers.yml`. The `{github_username}` token is replaced with the actual value, or `<YOUR-GITHUB-USERNAME>` if absent.

## Template source

Resolution order, highest to lowest:

1. **`-T, --template URL`** on the CLI.
2. **`BBLOCKS_PROJECTS_TEMPLATE`** environment variable.
3. **`template_url`** key in `~/.config/bblocks-projects/config.toml` (or `$XDG_CONFIG_HOME/bblocks-projects/config.toml`).
4. **Default**: `gh:ONEcampaign/bblocks-projects`.

The CLI prints a `[Using template from ...]` line whenever the resolved source isn't the default.

Example config file:

```toml
# ~/.config/bblocks-projects/config.toml
template_url = "https://github.com/your-org/your-template"
```

Malformed config files emit a warning to stderr and fall through to the next layer.

## Doctor severities

From `src/bblocks/projects/doctor.py`. Used by the report renderer and the `--strict` exit-code logic.

| Severity | Meaning | Affects exit code |
|---|---|---|
| `catastrophic` | Project is unreadable (missing or malformed `pyproject.toml` / `.copier-answers.yml`). Other checks are skipped. | always exits `1` |
| `finding` | Drift from the standards. | exits `1` only with `--strict` |
| `advisory` | Informational. Currently used when a network-dependent check (e.g., `--check-updates`) couldn't reach the network. | never |

Each finding carries a `code` (e.g., `drift.project_type_mismatch`, `components.missing`, `template.stale`). The first `.`-separated segment matches one of the four report sections: `scaffolding`, `drift`, `components`, `template`.

## See also

- [Getting Started](getting-started.md) — to see these commands used together in a complete first-project workflow.
- [Package vs project](package-vs-project.md) — for the design rationale behind the two project types listed in the variables table.
