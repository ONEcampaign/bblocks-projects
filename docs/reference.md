# Reference

Every command, flag, template variable, and component. Runnable examples live in the how-tos.

As of `bblocks-projects 1.1.0`.

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

- **`DESTINATION`** _(optional)_ — directory for the new project. Pass `.` or `--here` for the current directory. If omitted, you'll be asked interactively.

**Options**

- **`-H, --here`** — create in the current directory.
- **`-r, --ref TEXT`** _(default: `main`)_ — template branch, tag, or commit.
- **`-t, --type TEXT`** — `package` or `project` (or legacy `research`). Skips the project-type prompt.
- **`-d, --data KEY=VALUE`** _(repeatable)_ — override a template variable.
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

- **`-p, --path PATH`** _(default: current directory)_ — project to update.
- **`-r, --ref TEXT`** _(default: `main`)_ — template branch, tag, or commit.
- **`-d, --data KEY=VALUE`** _(repeatable)_ — override one or more template answers.
- **`--skip-answered / --no-skip-answered`** _(default: `--skip-answered`)_ — silently reuse previous answers (default), or re-prompt for all of them.
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

- **`-p, --path PATH`** _(default: current directory)_ — target project.
- **`-f, --force`** — overwrite existing files. Config sections are still merged section-by-section.
- **`-y, --yes`** — skip confirmation prompts.
- **`-l, --list`** — print available components and exit.

**Exit codes** — `0` if every requested component installed, `1` if at least one failed.

### `doctor`

Run health checks against a managed project.

```
bblocks-projects doctor [OPTIONS]
```

Requires `pyproject.toml` at the project root. Also requires `.copier-answers.yml`, unless `--family` is passed — that flag is the escape hatch for family repos that were never generated from the template and so have no answers file at all.

**Options**

- **`-p, --path PATH`** _(default: current directory)_ — project to diagnose.
- **`--strict`** — exit `1` on any _finding_ (severity `finding` only; advisories never affect the exit code).
- **`--check-updates`** — also compare local `_commit` against the template's upstream `HEAD` (network call, 5s timeout).
- **`--family`** — run the [family contract](the-family-contract.md) checks, even without a `preset: family` answer (also implied automatically when `.copier-answers.yml` records `preset: family`).
- **`--check-remote`** — also run the two family-contract checks that hit the network (branch protection via `gh api`, the conda-forge feedstock via `api.anaconda.org`; 8s timeout each). No effect without `--family` or `preset: family`.

**Exit codes** — `0` on a healthy project (or, without `--strict`, one with findings/advisories but nothing catastrophic). `1` with `--strict` when any finding is present. `2` on a catastrophic finding — the project couldn't be checked at all, distinct from checked-and-non-compliant.

## Template variables

Source of truth: `copier.yml` in the [template repo](https://github.com/ONEcampaign/bblocks-projects/blob/main/copier.yml). Pass any of these to `create` or `update` via `--data KEY=VALUE`.

| Variable              | Type   | Default                                    | Allowed values                                                | When                                  |
| --------------------- | ------ | ------------------------------------------ | ------------------------------------------------------------- | ------------------------------------- |
| `project_name`        | `str`  | —                                          | any string                                                    | always                                |
| `project_slug`        | `str`  | derived from `project_name`                | valid Python identifier                                       | always                                |
| `project_description` | `str`  | —                                          | any string                                                    | always                                |
| `project_type`        | `str`  | `project`                                  | `package`, `project`, `research` (legacy alias for `project`) | always                                |
| `preset`              | `str`  | `standalone`                               | `standalone`, `family`                                        | always                                |
| `include_notebooks`   | `bool` | `false`                                    | `true`, `false`                                               | only when `project_type != 'package'` |
| `include_pytest`      | `bool` | `false`                                    | `true`, `false`                                               | only when `project_type != 'package'` |
| `author_name`         | `str`  | `""`                                       | any string                                                    | always                                |
| `author_email`        | `str`  | `""`                                       | any string                                                    | always                                |
| `python_version`      | `str`  | `3.12` if `preset == 'family'` else `3.13` | `3.11`, `3.12`, `3.13`, `3.14`                                | always                                |
| `license`             | `str`  | `mit`                                      | `mit`, `apache`, `bsd3`, `none`                               | always                                |
| `github_username`     | `str`  | —                                          | any string                                                    | only when `project_type == 'package'` |

Notes:

- `project_slug` defaults to `project_name | lower | replace(' ', '_') | replace('-', '_')`. Override with `--data project_slug=...` if you want a non-default mapping.
- The license values are short codes (`apache`, not `apache-2.0`; `bsd3`, not `bsd-3-clause`). The full SPDX names appear only in the generated `LICENSE` file.
- `preset: family` doesn't change anything else in the rendered output — no dependency is injected, no CI step is added. It's a durable, offline signal `doctor --family` reads from `.copier-answers.yml`. See [The bblocks family contract](the-family-contract.md).
- `preset: family` also narrows `python_version` in effect, not in the choice list: `3.11` is still selectable, but the question's validator rejects it when `preset == 'family'`, with the message _"The family preset requires a Python floor of 3.12 or higher."_ The same validator runs on every later `copier update`, so a family repo still on `3.11` fails `update` outright, not just `doctor`.

## Components

Source of truth: `src/bblocks/projects/components.py`.

| Name           | Files written                   | `pyproject.toml` sections                                                                                         | Dev deps                             | Project type   |
| -------------- | ------------------------------- | ----------------------------------------------------------------------------------------------------------------- | ------------------------------------ | -------------- |
| `pre-commit`   | `.pre-commit-config.yaml`       | —                                                                                                                 | `pre-commit>=4.6.0`                  | any            |
| `ruff`         | —                               | `tool.ruff`, `tool.ruff.lint`, `tool.ruff.lint.pydocstyle`, `tool.ruff.lint.per-file-ignores`, `tool.ruff.format` | `ruff>=0.15.0`                       | any            |
| `ci`           | `.github/workflows/ci.yml`      | —                                                                                                                 | —                                    | any            |
| `pytest`       | —                               | `tool.pytest.ini_options`, `tool.coverage.run`, `tool.coverage.report`                                            | `pytest>=9.1.0`, `pytest-cov>=7.1.0` | any            |
| `pypi-publish` | `.github/workflows/release.yml` | `build-system` (only added if missing)                                                                            | —                                    | `package` only |

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

| Severity       | Meaning                                                                                                                                                                                                                                                                             | Affects exit code              |
| -------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------ |
| `catastrophic` | Project is unreadable (missing, malformed, or unreadable `pyproject.toml` / `.copier-answers.yml`). Other checks are skipped.                                                                                                                                                       | always exits `2`               |
| `finding`      | Drift from the standards, or (under `--family`) a family-contract item failing outright.                                                                                                                                                                                            | exits `1` only with `--strict` |
| `advisory`     | Informational. Used when a network-dependent check (`--check-updates`, `--check-remote`) couldn't reach the network, when a family-contract source scan couldn't run or couldn't attribute what it found to a job or module (items 6, 7, 8, 10), or for the item-5 floor and item-6 readerkit exemptions. | never                          |

`–` (not applicable) isn't a severity — it's the family-contract renderer's third glyph, printed for items 6 and 7 when the package doesn't fetch or doesn't cache at all. When the source scan can't establish that either way — no package found under `src/`, or a module it needed to read failed to parse — the item reports a `*_skipped` advisory instead of guessing at the `–`. See [The family contract](#the-family-contract) below.

`?` (not checked) is a fourth glyph, printed for every item when a catastrophic finding stops the contract checks from running at all — the project couldn't be read, so there's nothing to report as passing, failing, or n/a.

Each finding carries a `code` (e.g., `scaffolding.pyproject_missing`, `drift.project_type_mismatch`, `components.missing`, `template.stale`, `contract.readerkit`). The first `.`-separated segment matches one of the five report sections: `scaffolding`, `drift`, `components`, `contract`, `template`.

## Scaffolding codes

From `_check_pyproject_parseable` and `_check_copier_answers_parseable` in `doctor.py`. All `catastrophic` — any one of these stops the rest of `doctor`'s checks from running.

| Code                                | Fires when                                                         |
| ----------------------------------- | ------------------------------------------------------------------ |
| `scaffolding.pyproject_missing`     | no `pyproject.toml` at the project root                            |
| `scaffolding.pyproject_unparseable` | `pyproject.toml` exists but isn't valid TOML                       |
| `scaffolding.pyproject_unreadable`  | `pyproject.toml` exists but can't be read (e.g. permission denied) |
| `scaffolding.answers_missing`       | `.copier-answers.yml` is missing, or exists but can't be read      |
| `scaffolding.answers_unparseable`   | `.copier-answers.yml` exists but isn't valid YAML                  |
| `scaffolding.answers_not_dict`      | `.copier-answers.yml` parses, but its root isn't a mapping         |

## The family contract

From `src/bblocks/projects/contract.py`. Runs under `--family` (or automatically when `.copier-answers.yml` records `preset: family`) — see [The bblocks family contract](the-family-contract.md) for what each item means, the exemptions, and the checks' known false negatives and false positives.

| #   | Item                               | Code(s)                                                                                                                         | Severity                                                                      | What it reads                                                                                                                                                                                                                                  |
| --- | ---------------------------------- | ------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | uv build backend                   | `contract.build_backend`                                                                                                        | finding                                                                       | `[build-system].build-backend` in `pyproject.toml`                                                                                                                                                                                             |
| 2   | ruff                               | `contract.ruff`                                                                                                                 | finding                                                                       | `tool.ruff*` sections and the `ruff` dev dependency                                                                                                                                                                                            |
| 3   | ty                                 | `contract.ty`                                                                                                                   | finding                                                                       | the `ty` dev dependency and `[tool.ty.src]` / `[tool.ty.environment]`                                                                                                                                                                          |
| 4   | pre-commit                         | `contract.pre_commit`                                                                                                           | finding                                                                       | `.pre-commit-config.yaml` at the git root and the `pre-commit` dev dependency                                                                                                                                                                  |
| 5   | Python floor 3.12                  | `contract.python_floor`, `contract.python_floor_exempt`                                                                         | finding (advisory if exempt)                                                  | the `requires-python` lower bound                                                                                                                                                                                                              |
| 6   | readerkit for HTTP and caching     | `contract.readerkit`, `contract.readerkit_exempt`, `contract.readerkit_skipped`                                                 | finding (advisory if exempt or when the scan can't tell), n/a if the package doesn't fetch | runtime dependencies and first-party imports of `requests`/`httpx`/`httpx2`/`aiohttp`/`urllib.request`/`http.client`, and whether `readerkit` is declared and imported                                                                   |
| 7   | Cache redirectable and disableable | `contract.cache_redirect`, `contract.cache_env_var`, `contract.cache_disable`, `contract.cache_skipped`                         | finding (advisory when the scan can't tell), n/a if the package doesn't cache | the package's public surface (`__all__`, top-level names), string literals, and function keyword arguments                                                                                                                                     |
| 8   | No import-time side effects        | `contract.import_io` (finding), `contract.import_opaque`, `contract.import_unreadable`, `contract.import_no_package` (advisory) | mixed                                                                         | an AST walk of the package's import-time-reachable modules, including decorators, parameter defaults, parameter/return annotations, class bases, and metaclass keywords                                                                        |
| 9   | No upper-bound pins                | `contract.dependency_cap`, `contract.dependency_cap_exempt`                                                                     | finding (advisory if exempt)                                                  | `[project].dependencies` and every `[project.optional-dependencies]` list                                                                                                                                                                      |
| 10  | OIDC publishing                    | `contract.oidc_publish`, `contract.oidc_publish_unscoped`                                                                       | finding, packages only (advisory when a workflow can't be scoped to a job)    | workflows under the git root's `.github/workflows/`: the publishing job's own `permissions:` (or the workflow-level default it inherits) plus its `env`/`with`/`run` text; falls back to whole-file text when the workflow can't be parsed as YAML or the publish step can't be attributed to a job |
| 11  | Branch protection                  | `contract.branch_protection`, `contract.branch_protection_skipped`                                                              | finding (advisory without `--check-remote` or on a skip)                      | `gh api repos/<slug>/branches/main/protection`, falling back to `gh api repos/<slug>/rulesets` — network, `--check-remote` only                                                                                                                |
| 12  | conda-forge feedstock              | `contract.conda_forge`, `contract.conda_forge_skipped`                                                                          | finding (advisory without `--check-remote` or on a skip), packages only       | `https://api.anaconda.org/package/conda-forge/<name>` — network, `--check-remote` only                                                                                                                                                         |

`contract.not_adopted` is not a numbered item — it's an advisory printed when `--family` runs against a project with no `.copier-answers.yml`, naming that scaffolding, drift, and component checks were skipped.

## See also

- [Getting Started](getting-started.md) — to see these commands used together in a complete first-project workflow.
- [Package vs project](package-vs-project.md) — for the design rationale behind the two project types listed in the variables table.
- [The bblocks family contract](the-family-contract.md) — the full explanation behind the table above.
