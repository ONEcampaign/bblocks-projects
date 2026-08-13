# How to create a new project

`uvx bblocks-projects create` runs the [Copier](https://copier.readthedocs.io/) template and writes a generated project to disk.

If you've never run it before, walk through [Getting Started](getting-started.md) first.

## Before you start

- Python 3.12+, `git`, and `uv` on your `PATH`.
- (Optional) `gh auth login` so author info gets prefilled from your GitHub profile.

## Pick a destination

Three options:

```bash
# Create a new subdirectory
uvx bblocks-projects create donor-analysis

# Create in the current directory (e.g., one you've already `mkdir`d)
uvx bblocks-projects create --here
uvx bblocks-projects create .

# Ask interactively
uvx bblocks-projects create
```

If the destination exists and isn't empty, you'll get a confirmation prompt before any files are written.

## Pick a project type

Two types:

- `package` — for libraries you'll publish to PyPI (src layout, `tests/`, `py.typed`, PyPI release workflow).
- `project` — for analysis, pipelines, internal tools (src layout, `data/raw/` and `data/processed/`, optional notebooks, looser ruff/ty rules for pandas/numpy).

If you already know which one you want, pass it on the command line and skip the prompt:

```bash
uvx bblocks-projects create my-package --type package
uvx bblocks-projects create donor-analysis --type project
```

If you're not sure which one, read [Package vs project](package-vs-project.md) — it covers what each is shaped for and when to switch.

!!! note
    `--type research` is accepted as a legacy alias for `--type project`. It renders the exact same layout. Use `project` for new work.

## Skip the prompts

Use `--defaults` to accept every default answer non-interactively:

```bash
uvx bblocks-projects create my-project --type project --defaults
```

The defaults are: project type `project`, Python `3.13`, license `MIT`, no notebooks. Author name and email come from the GitHub CLI (if logged in); otherwise both default to empty strings, and Copier still prompts for them.

## Override specific values

Use `--data KEY=VALUE` (repeatable) to override one or more template variables. Combine with `--defaults` to set those values and accept the rest:

```bash
uvx bblocks-projects create my-project \
  --type package \
  --defaults \
  --data author_name="Jane Smith" \
  --data author_email="jane@one.org" \
  --data github_username=ONEcampaign \
  --data license=apache
```

The full list of variables is in the [Reference](reference.md#template-variables). Two callouts:

- `license` takes the *short codes* `mit`, `apache`, `bsd3`, or `none` — not `apache-2.0` or `bsd-3-clause`.
- `github_username` is only asked for `package` projects (it's used in the PyPI release workflow). Setting it on a `project` is harmless but ignored.

## Use a specific template version

By default `create` pulls from `main`. To pin to a tag, branch, or commit:

```bash
uvx bblocks-projects create my-project --ref v1.2.0       # tag
uvx bblocks-projects create my-project --ref experimental # branch
uvx bblocks-projects create my-project --ref abc1234      # commit
```

Pin to a tag if your team standardises on a known-good version. Use a branch when you're testing template changes before they merge to `main`.

## Use a different template entirely

`bblocks-projects` defaults to the ONE Campaign template at `https://github.com/ONEcampaign/bblocks-projects`. To run against a fork or a private template:

```bash
uvx bblocks-projects create my-project \
  --template https://github.com/your-org/your-template
```

You can also set `BBLOCKS_PROJECTS_TEMPLATE` in your environment, or put the URL in `~/.config/bblocks-projects/config.toml` under the key `template_url` — see the [Reference](reference.md#template-source). The CLI announces the resolved source whenever it isn't the default.

## Skip the GitHub prefill

`create` calls `gh auth status` and `gh api user` to prefill `author_name`, `author_email`, and `github_username`. If you'd rather it didn't:

```bash
uvx bblocks-projects create my-project --no-github
```

## Verify it worked

After `create` finishes:

```bash
cd my-project
git log --oneline       # one commit: "Initial commit from copier template"
uv run ruff check .     # no errors
uv run pytest           # for packages: empty test suite passes
```

The template ran `git init`, `uv venv`, `uv sync`, and `pre-commit install` for you. You don't need to repeat any of that.

## Troubleshooting

**`Required tool(s) not found on PATH: git, uv`**
Install whichever tool the message names: see the [`uv` install guide](https://docs.astral.sh/uv/getting-started/installation/) for `uv`, and Xcode Command Line Tools (`xcode-select --install`) or your distro's package manager for `git`.

**`project_slug must be a valid Python identifier`**
The slug is auto-generated from the project name (`My Project` → `my_project`, `my-cool-project` → `my_cool_project`), but if you override it manually with `--data project_slug=...`, it has to be a legal Python identifier — letters, digits, underscores, must start with a letter.

**Directory exists and isn't empty**
You'll be asked to confirm before anything is written. Hidden files (like `.git/`) don't count toward "non-empty," so this is safe to use after `mkdir my-project && cd my-project && git init`.

## See also

- [Reference: `create` flags and template variables](reference.md) — for the full flag list and every variable you can pass via `--data`
- [Package vs project](package-vs-project.md) — choosing between the two project types
- [Updating projects](updating-projects.md) — pulling later template changes into a project you've already created
