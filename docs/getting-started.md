# Build your first project

> By the end of this tutorial, you'll have a generated, version-controlled `project` repo with a small piece of analysis code inside it that passes the linter, type checker, and pre-commit hooks.

## What you'll build

A non-package project called `donor-analysis` with this layout:

```
donor-analysis/
├── src/
│   └── donor_analysis/
│       └── __init__.py
├── data/
│   ├── raw/         (gitignored — input files go here)
│   └── processed/   (tracked — derived outputs go here)
├── .github/workflows/ci.yml
├── .pre-commit-config.yaml
├── pyproject.toml
└── README.md
```

…with one function under `src/donor_analysis/` that loads a CSV and writes a summary, plus a passing pre-commit run.

## What you'll learn

- How to generate a new project from the template.
- Where reusable code lives (`src/{slug}/`) versus where data lives (`data/`).
- How to add a dependency with `uv`.
- How the bundled quality checks (ruff, ty, pre-commit) fit into your loop.

## What you'll need

- About 15 minutes.
- Python 3.11+, [`uv`](https://docs.astral.sh/uv/), and `git` on your `PATH`. Run `uv --version && git --version` to confirm.
- A terminal in a directory where you can create a new folder.

If you'd like author info prefilled, also run `gh auth login` first. It's optional — `uvx` will ask for your name and email if it can't detect them.

## Step 1: Generate the project

Run the generator. We'll pass `--type project` so you don't have to pick at the prompt, and a one-line description as `--data` so you don't have to type it.

```bash
uvx bblocks-projects create donor-analysis \
  --type project \
  --data project_name="Donor Analysis" \
  --data project_description="Donor giving analysis"
```

`uvx` downloads `bblocks-projects` into a temporary cache, runs it, and exits. You don't need to install anything.

You'll be asked a handful of questions — confirm the project slug (suggested: `donor_analysis`), author name and email, Python version (default `3.11`), license (default `MIT`), and whether to include a `notebooks/` directory (default no). Press Enter to accept any default. After the questions:

```
✓ Project created successfully at donor-analysis

Next steps:
  cd donor-analysis
  # Review and edit README.md
  # Start coding!
```

The template also ran `git init`, created a virtualenv at `.venv/`, installed dependencies, made the initial commit, and installed the pre-commit hooks.

## Step 2: Explore what's there

```bash
cd donor-analysis
ls -la
```

You'll see the structure from "What you'll build," plus a `.git/`, `.venv/`, `uv.lock`, and `.copier-answers.yml`. The last one is important — it records which template version generated the project, so `bblocks-projects update` knows what to merge later. Don't delete it.

Open `src/donor_analysis/__init__.py`. It's nearly empty:

```python
"""donor-analysis."""
```

Reusable code goes under this package. You'll add to it in Step 4.

## Step 3: Add a dependency

You'll write a function that reads a CSV, so add `pandas`:

```bash
uv add pandas
```

`uv` resolves, downloads, and installs in a couple of seconds, then updates `pyproject.toml` and `uv.lock`:

```
Resolved 5 packages in 80ms
Installed 5 packages in 30ms
```

## Step 4: Write the analysis function

Replace the contents of `src/donor_analysis/__init__.py` with:

```python
"""donor-analysis."""

from pathlib import Path

import pandas as pd

DATA_RAW = Path(__file__).resolve().parents[2] / "data" / "raw"
DATA_PROCESSED = Path(__file__).resolve().parents[2] / "data" / "processed"


def summarise_donations(filename: str) -> pd.DataFrame:
    """Read raw donations and write per-country totals to processed/."""
    df = pd.read_csv(DATA_RAW / filename)
    summary = df.groupby("country", as_index=False)["amount_usd"].sum()
    summary.to_csv(DATA_PROCESSED / "country_totals.csv", index=False)
    return summary
```

Then drop a small CSV at `data/raw/donations.csv`:

```csv
donor_id,country,amount_usd
d_001,KEN,500
d_002,KEN,250
d_003,UGA,1200
d_004,KEN,75
```

You can create it with your editor, or:

```bash
cat > data/raw/donations.csv <<'EOF'
donor_id,country,amount_usd
d_001,KEN,500
d_002,KEN,250
d_003,UGA,1200
d_004,KEN,75
EOF
```

!!! note
    Anything under `data/raw/` is gitignored. Source data isn't yours to commit; the `.gitignore` keeps you from doing it by accident.

## Step 5: Run the function

Use `uv run` so the import resolves against the project's virtualenv:

```bash
uv run python -c "from donor_analysis import summarise_donations; print(summarise_donations('donations.csv'))"
```

You should see:

```
  country  amount_usd
0     KEN         825
1     UGA        1200
```

And `data/processed/country_totals.csv` now exists. That file *is* tracked — derived outputs are part of the repo so reviewers can see what changed without re-running anything.

## Step 6: Run the quality checks

The template ships with three of them already wired up:

```bash
uv run ruff check .                 # linting
uv run ruff format --check .        # formatting
uvx ty check src/donor_analysis     # type checking
```

All three should report no problems on the code from Step 4. If `ruff format --check` complains, run `uv run ruff format .` to apply the fix.

## Step 7: Commit your work

`pre-commit` was installed by the template, so the hooks will run automatically:

```bash
git add src/donor_analysis/__init__.py pyproject.toml uv.lock data/processed/country_totals.csv
git commit -m "Add donation summary"
```

You should see something like:

```
ruff (lint).............................................Passed
ruff format.............................................Passed
ty type check...........................................Passed
[main 8f3a1c2] Add donation summary
 4 files changed, 18 insertions(+), 1 deletion(-)
```

If a hook fails, the commit doesn't happen. Fix the issue and re-run the same `git commit` — `pre-commit` only re-runs hooks against the staged files.

## What you learned

- Generated a `project`-shaped repo with `uvx bblocks-projects create`.
- Found reusable code under `src/{slug}/` and data split across `data/raw/` (gitignored) and `data/processed/` (tracked).
- Added a dependency with `uv add` and ran code with `uv run`.
- Used `ruff`, `ty`, and `pre-commit` — the same checks CI will run.

## What's next

- **More options for `create`** — defaults, picking a template version, overriding template variables: see [Creating projects](creating-projects.md).
- **Why `project` and not `package`?** — see [Package vs project](package-vs-project.md) for the decision.
- **Pull future template improvements into this repo** — see [Updating projects](updating-projects.md).
