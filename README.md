# bblocks-projects

> A Copier template for ONE Campaign Python projects, plus a CLI for working with it.

This repo holds two things:

- **`bblocks-projects/`** — the [`bblocks-projects`](bblocks-projects/README.md) CLI (`create`, `update`, `add`, `doctor`).
- **`template/`** — the [Copier](https://copier.readthedocs.io/) template the CLI renders.

If you just want to use the CLI to scaffold or maintain a project, jump to the [package README](bblocks-projects/README.md). The rest of this file is for people working on the template or the CLI itself.

## Repository layout

```
bblocks-projects/
├── bblocks-projects/       # CLI tool (published to PyPI)
│   ├── src/bblocks/projects/
│   ├── tests/
│   └── pyproject.toml
├── template/               # Copier template files
│   ├── copier.yml          # questions and post-generation tasks
│   ├── {% if ... %}/       # conditional directories per project type
│   └── ...                 # files rendered into generated projects
├── docs/                   # MkDocs site source (rendered at the repo root)
├── mkdocs.yml
└── README.md               # this file
```

## Quick start

```bash
# Create a new project (no install needed)
uvx bblocks-projects create my-project

# Update an existing one
cd my-project && uvx bblocks-projects update

# Add a single component to any Python project
uvx bblocks-projects add pre-commit ruff ci

# Health-check a managed project
uvx bblocks-projects doctor
```

Full usage and flag reference: [docs/](docs/index.md).

## Using Copier directly

The CLI is a wrapper around Copier. If you'd rather drive Copier yourself:

```bash
uv tool install copier

copier copy gh:ONEcampaign/bblocks-projects my-project   # create
cd my-project && copier update                           # update
```

The CLI adds the GitHub-profile prefill, the `add` component flow, and `doctor` on top of plain Copier.

## Working on this repo

```bash
# CLI tests, lint, type-check
cd bblocks-projects
uv sync
uv run pytest
uv run ruff check .
uv run ty check src/bblocks/projects

# Docs site (run from the repo root)
uv run --project bblocks-projects mkdocs serve
```

When changing the template:

1. Edit files under `template/`.
2. Render into a scratch directory: `copier copy . /tmp/test-project`.
3. Verify the generated project's CI checks pass.
4. Test both `package` and `project` types (and that the legacy `research` answer still resolves to `project`).

`.copier-answers.yml` must be present in the generated project for `update` to work — verify it's there before merging template changes.

## Requirements

- Python 3.12+
- [`uv`](https://docs.astral.sh/uv/) and `git` on `PATH`
- [Copier](https://copier.readthedocs.io/) 9.0+ if invoking Copier directly

---

[Issues](https://github.com/ONEcampaign/bblocks-projects/issues) · MIT — see [LICENSE](LICENSE).
