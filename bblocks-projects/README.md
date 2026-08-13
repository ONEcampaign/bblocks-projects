# bblocks-projects

> A CLI for creating, updating, and auditing Python projects against a shared [Copier](https://copier.readthedocs.io/) template.

[![PyPI](https://img.shields.io/pypi/v/bblocks-projects.svg)](https://pypi.org/project/bblocks-projects/)
[![Python](https://img.shields.io/pypi/pyversions/bblocks-projects.svg)](https://pypi.org/project/bblocks-projects/)
[![License](https://img.shields.io/pypi/l/bblocks-projects.svg)](https://github.com/ONEcampaign/bblocks-projects/blob/main/LICENSE)

`bblocks-projects` is the ONE Campaign's tool for keeping its Python projects consistent. It scaffolds new repos, pulls template improvements into existing ones, and adds individual pieces (pre-commit, CI, ruff config) to projects that didn't start from the template.

## Why this exists

Every Python project starts with the same decisions and boilerplate: which linter, which type checker, how to wire CI, where tests live, how publishing works. `bblocks-projects` keeps the choices in one place ([the template repo](https://github.com/ONEcampaign/bblocks-projects)) and gives you four commands to apply them: `create`, `update`, `add`, and `doctor`.

## Install

Requires Python 3.12+, `git`, and [`uv`](https://docs.astral.sh/uv/) on `PATH`.

```bash
# One-off, no install (recommended)
uvx bblocks-projects create my-project

# Install with uv
uv tool install bblocks-projects

# Or pipx / pip
pipx install bblocks-projects
pip install bblocks-projects
```

If you're signed into the GitHub CLI (`gh auth login`), `create` prefills your name, email, and username from your GitHub profile.

## Usage

**Create a new project.** Interactive by default — answer a handful of questions about name, license, and project type:

```bash
bblocks-projects create my-analysis        # new subdirectory
bblocks-projects create --here             # current directory
```

You'll be asked to pick `package` (publishable to PyPI; src layout, pytest, `py.typed`) or `project` (analysis, pipeline, internal tool — adds `data/raw/`, `data/processed/`, optional notebooks, and ruff/ty configs that tolerate pandas/numpy stub gaps). To skip the prompts:

```bash
bblocks-projects create my-package --type package --defaults
```

**Update an existing project** when the template changes upstream:

```bash
cd my-analysis
uvx bblocks-projects update
git diff       # review what changed
uv sync
```

Previously-answered questions are reused silently. Pass `--no-skip-answered` to re-prompt for any of them, or `--ref v1.2.0` to update to a specific template version instead of `main`.

**Add a single component** to any Python project — including ones that didn't start from the template:

```bash
uvx bblocks-projects add --list             # see what's available
uvx bblocks-projects add pre-commit         # one component
uvx bblocks-projects add ruff ci pytest     # several at once
```

Available components: `pre-commit`, `ruff`, `ci`, `pytest`, and `pypi-publish` (packages only). `add` merges into your existing `pyproject.toml` rather than overwriting it, and shows the diff before applying.

**Run the doctor** to check a project against the current standards:

```bash
uvx bblocks-projects doctor                 # diagnose the current directory
uvx bblocks-projects doctor --strict        # exit non-zero on findings (CI-friendly)
uvx bblocks-projects doctor --check-updates # is the template newer upstream?
```

## When not to use this

- **You're not at ONE Data.** The template encodes our specific choices (uv, ruff, ty, GitHub Actions, src-layout). If your team has different ones, fork the template repo — don't fight ours.
- **You don't want a Copier-managed project.** `create` and `update` rely on `.copier-answers.yml` to track which template version generated the project. If you'd rather not have that file, use `add` to take a one-shot copy of the components you want and walk away.
- **Your project predates Copier and you want full template adoption.** `update` requires `.copier-answers.yml`. Either start from `add` for the pieces you need, or follow the [adoption guide](https://github.com/ONEcampaign/bblocks-projects/blob/main/docs/adopting-an-existing-project.md).

## What you get

Every generated project includes [uv](https://docs.astral.sh/uv/), [ruff](https://docs.astral.sh/ruff/), [ty](https://docs.astral.sh/ty/), pre-commit, and a GitHub Actions CI workflow. Packages also get pytest with coverage, a `py.typed` marker, and a PyPI trusted-publishing workflow. Projects also get a `data/` tree (`raw/` gitignored, `processed/` tracked) and an optional `notebooks/` directory.

## Next

- [Getting Started](https://github.com/ONEcampaign/bblocks-projects/blob/main/docs/getting-started.md) — a 15-minute walkthrough from zero to a generated project you've made a real change to.

---

[Source](https://github.com/ONEcampaign/bblocks-projects) · [Issues](https://github.com/ONEcampaign/bblocks-projects/issues) · MIT — see [LICENSE](https://github.com/ONEcampaign/bblocks-projects/blob/main/LICENSE).
