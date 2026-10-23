# Why we have `package` and `project`

> As of `bblocks-projects 1.0.0`. Last reviewed 2026-05.

## The question this page answers

`bblocks-projects create` prompts for `package` or `project`. The two layouts overlap, which makes the choice non-obvious. This page covers what each is shaped for and how to pick.

## The short answer

Pick `package` if the artifact is a Python library that someone will `pip install`. Pick `project` for everything else: an analysis, a pipeline, an internal tool, a one-off script worth a repo. Most ONE Campaign work is `project`.

When in doubt, choose `project`. Switching to `package` later is additive work — move code into `src/{slug}/`, add `tests/`. The reverse is harder: a `package` carries `tests/`, `py.typed`, and a release workflow that have to be removed.

## Background

Both types share the same skeleton: `uv` for dependencies, `ruff` for lint and format, `ty` for type checking, pre-commit hooks, GitHub Actions CI, src layout. What differs is the parts of the layout that exist *because* the artifact has a particular shape.

| | `package` | `project` |
|---|---|---|
| `src/{slug}/` | yes | yes |
| `tests/` | yes | no |
| `data/raw/` (gitignored) | no | yes |
| `data/processed/` (tracked) | no | yes |
| `notebooks/` | no | optional |
| `py.typed` marker | yes | no |
| PyPI release workflow | yes | no |
| Stricter ruff/ty rule set | yes | no — looser, pandas/numpy-tolerant |

The two project types are conditionals in `copier.yml` and the template directory tree. Once a project is generated, the type is recorded in `.copier-answers.yml` so `update` and `doctor` can do the right thing.

## The reasoning

### What `package` is shaped for

A library that other code imports. The reader is a downstream developer; the contract is the public API. The shape optimises for that contract:

- `src/{slug}/` makes the test suite import the *installed* package, not the development tree. With a flat layout, a missing entry in `pyproject.toml` can be invisible during local development and only break when a downstream user installs the package.
- `tests/` is mandatory. Without a test suite, downstream users have no signal that an upgrade is safe to take.
- `py.typed` opts the package into PEP 561, so type checkers in downstream projects use the inline annotations.
- The PyPI release workflow ships on every tag push, so cutting a release is `git tag` + `git push --tags`.
- The ruff and ty rule set is stricter than for `project`. Library code is read by people who don't have the original author available.

### What `project` is shaped for

Code that consumes data and produces results. The reader is whoever picks the analysis up next, frequently the original author months later. The contract is the path from raw inputs to processed outputs. The shape optimises for that:

- `data/raw/` is gitignored. Source data isn't ours to commit, and accidental commits of raw donor records can violate data-protection commitments. The directory exists (with a `.gitkeep`) so the path is stable across clones.
- `data/processed/` is tracked. Derived outputs are reviewable — a reader sees the new summary file in the diff instead of re-running a script to find out what changed.
- `notebooks/` is opt-in. Some `project` repos use notebooks heavily, others don't use them at all; making it a `--data` answer keeps both paths clean.
- The ruff and ty rule set is looser than for `package`. Analysis code reaches into pandas DataFrames whose stub coverage is incomplete; strict rules in that environment produce noise that gets blanket-ignored, which is worse than tuning the rules to flag the issues that matter.

### Why `tests/` isn't required for `project`

We considered making `tests/` mandatory for both types and rejected it. Analysis code is usually validated against the data it produces, not against unit tests, and most `project` repos are either retired or rewritten before a test suite would have paid back the cost of writing it. Projects that do warrant tests can install `bblocks-projects add pytest`; the configuration is identical to what `package` ships with. Shipping an empty `tests/` to every analysis would create a directory that day-one users delete, which trains the team to delete template defaults rather than read them.

## Alternatives we considered

**A single project type with everything turned on.** Rejected. The merged layout would carry `tests/`, `data/`, a release workflow, and stricter lint rules into every repo — wrong for both audiences. The PyPI workflow has nothing to publish in analyses; the `data/` tree has nothing to hold in libraries.

**A finer taxonomy** (e.g., `package`, `analysis`, `pipeline`, `tool`). Rejected. Each additional type adds conditionals to the template, sections to the docs, and cases to the tests. Two types cover most work; sub-cases are addressed by combining `project` with the right components or editing the generated config.

**Calling it `research` instead of `project`.** The template originally did. We renamed it once the type started being used for ETL pipelines and internal CLIs as well as research code. `project` is the broader, more accurate name. The `research` value still works as an alias on `update` and `create` for back-compat — see [Reference: template variables](reference.md#template-variables).

## Consequences

- **Switching after generation is manual.** `update` won't reshape the tree. Going `project` → `package` means: add `tests/`, add `py.typed`, swap the looser ruff config for the stricter one, run `bblocks-projects add pypi-publish`. Going `package` → `project` means: add a `data/` tree — and the existing `tests/` directory becomes orphaned, since `update` won't remove it.
- **`doctor` enforces the type's expected layout.** A `project` missing `data/`, or a `package` missing `src/{slug}/`, produces a `drift` finding. Drift here usually means someone deleted a directory by accident.
- **One repo, one type.** A single repo that's both isn't supported. Monorepo-style "library + analysis using it" cases should be two repos, with the analysis depending on the library through normal `uv add`. A multi-language package repo, one library shipped in Python and another language, keeps one package per language directory (`python/`, `typescript/`), and the Python package is a `package` in its own right. See [A package in a multi-language repo](the-family-contract.md#a-package-in-a-multi-language-repo).

## When this might change

The split would be revisited if:

- A third archetype emerges that's badly served by both — e.g., a pure data-engineering project type with materially different scaffolding (Airflow / dbt / Dagster integration, parquet-first conventions). The signal to watch is how often existing `project` repos require heavy customisation for ETL work; if that frequency rises, a third type becomes worth the maintenance cost.
- Type checker tooling matures to where the looser-rules concession isn't necessary, at which point both types could converge on the same lint/type config.

## Related

- [Creating projects](creating-projects.md) — how to pass `--type` and pick at the prompt
- [Reference: template variables](reference.md#template-variables) — including the `research` alias
- [Adding components](adding-components.md) — turning on package-shaped pieces inside a `project` repo, and vice versa
