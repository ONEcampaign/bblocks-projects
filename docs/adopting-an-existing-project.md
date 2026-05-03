# How to adopt an existing project

You have a Python project that wasn't created from the template, and you want to bring it under the standards. Two paths:

1. **Cherry-pick.** Use `bblocks-projects add` to install one or two pieces (pre-commit, ruff, ci) and stop. The project stays unmanaged.
2. **Full adoption.** Write a `.copier-answers.yml` by hand, then run `bblocks-projects update` to back-fill the rest of the template.

Path 1 is enough for most projects. Path 2 is required only if `update` needs to keep the project synced with future template changes.

## Path 1: Cherry-pick components

Use when you want pre-commit, ruff, or CI in the project, but not the full template-managed layout.

```bash
cd my-existing-project

# Make sure uv is set up (add creates a uv-based project)
uv sync                                    # or `uv init` if no pyproject.toml

uvx bblocks-projects add pre-commit ruff ci
```

`add` merges configs into your existing `pyproject.toml`, copies file templates, and runs `uv add --dev` for any dev deps. Conflicts are flagged with a y/n prompt; `--force` overwrites.

Verify it worked:

```bash
git status                            # see what was added/modified
uv sync                               # install any new dev deps
uv run pre-commit install             # if you added pre-commit
uv run pre-commit run --all-files     # confirm hooks pass on the existing tree
```

There's no `.copier-answers.yml`, so `update` won't work against this project. Path 1 stops here.

See [Adding components](adding-components.md) for the full list of components and flags.

## Path 2: Full adoption

Use when the project should pull future template updates through `bblocks-projects update`. Setup runs once.

### Decide the project type

Pick `package` (PyPI library) or `project` (analysis, pipeline, internal tool). See [Package vs project](package-vs-project.md) if you're not sure.

### Reshape the layout

The template expects a specific layout. Your project probably matches some of it already. Check what it expects:

| | `package` | `project` |
|---|---|---|
| `src/{slug}/__init__.py` | required | required |
| `tests/` | required | absent |
| `data/raw/`, `data/processed/` | absent | required |
| `notebooks/` | absent | optional |
| `pyproject.toml` | required | required |
| `.pre-commit-config.yaml` | created by template | created by template |
| `.github/workflows/ci.yml` | created by template | created by template |

`{slug}` is the Python-identifier form of your project name (`my-tool` → `my_tool`). Move your code into `src/{slug}/` if it isn't there already, and create empty placeholder directories for the data tree if you're going `project`.

### Write `.copier-answers.yml`

Create the file at the project root with the answers the template would have asked for if you'd run `create`. A minimal one for a `project`-type repo:

```yaml
# Copier-answers file
# Changes here will be overwritten by Copier; do not edit manually.
_commit: main
_src_path: gh:ONEcampaign/bblocks-projects

project_name: my-existing-project
project_slug: my_existing_project
project_description: What this project does
project_type: project
include_notebooks: false
author_name: Your Name
author_email: you@one.org
python_version: "3.11"
license: mit
```

For a `package`, also include `github_username`. The license value is one of `mit`, `apache`, `bsd3`, or `none` — see [Reference: template variables](reference.md#template-variables) for all the variables.

`_commit: main` tells Copier you've never run an update; the next `update` will rewrite this to the actual commit hash.

### Run update

```bash
uvx bblocks-projects update
```

This treats your project as if it were rendered from `main` with no template-managed files yet. Expect a lot of file additions and likely a few conflicts in `pyproject.toml` and `README.md`. Resolve conflicts the same way you would for a normal update — see [Updating projects](updating-projects.md).

### Verify and commit

```bash
git status                          # review what was added
uv sync                             # refresh lock with any new dev deps
uv run pre-commit install
uv run pre-commit run --all-files   # fix any new lint findings
uv run pytest                       # for packages
uvx bblocks-projects doctor         # confirms scaffolding/components/drift
git commit -m "Adopt bblocks template"
```

If `doctor` is green, the project is now managed. Future template changes can be pulled with `bblocks-projects update`.

## Troubleshooting

**`update` rewrites the whole `pyproject.toml`**
Expected on the first update: the template owns several `[tool.X]` sections that didn't exist in your file. Review the diff and keep your `[project.dependencies]` and any custom sections.

**Tests fail after adoption**
The template's CI matrix and tool configs are stricter than most ad-hoc setups. Run `uv run ruff check --fix .` and the type checker, then iterate.

**You picked the wrong project type**
Edit `project_type` in `.copier-answers.yml` and re-run `update --no-skip-answered`. You'll need to also reshape the layout (e.g., add `data/` for `project`, or `tests/` for `package`) — `doctor`'s drift section will tell you what's missing.

## See also

- [Adding components](adding-components.md) — the path-1 detail
- [Updating projects](updating-projects.md) — how the merge works under the hood
- [Reference: template variables](reference.md#template-variables) — the full set of `.copier-answers.yml` keys
