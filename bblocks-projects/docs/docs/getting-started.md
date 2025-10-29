# Getting Started

This guide walks you through installing bblocks-projects and creating your first project.

## Installation

You have three options for using bblocks-projects:

### Option 1: Use with uvx (Recommended)

No installation required. Run directly with uvx:

```bash
uvx bblocks-projects create my-research-project
```

This downloads and runs bblocks-projects automatically. Perfect for trying it out or occasional use.

### Option 2: Install with uv tool

Install persistently for regular use:

```bash
uv tool install bblocks-projects
```

Now you can run it anytime:

```bash
bblocks-projects create my-project
```

### Option 3: Install with pip/pipx

If you prefer traditional installation:

```bash
# With pipx (isolated)
pipx install bblocks-projects

# With pip
pip install bblocks-projects
```

## Create Your First Project

Let's create a simple data analysis project:

```bash
uvx bblocks-projects create my-data-analysis
```

You'll see a series of questions to customize your project:

```
🎤 What is your project name?
   my-data-analysis

🎤 Brief project description
   Analysis of climate data

🎤 What type of project?
   1 - Package (for libraries to publish on PyPI)
   2 - Research/Analysis (for data analysis and scripts)
   [2]

🎤 Author name
   Jane Smith

🎤 Author email
   jane@one.org

🎤 Minimum Python version
   1 - 3.11
   2 - 3.12
   3 - 3.13
   [1]

🎤 License
   1 - MIT
   2 - Apache-2.0
   3 - BSD-3-Clause
   4 - None
   [1]
```

After you answer the questions, bblocks-projects automatically:

1. Generates all project files
2. Initialises a git repository
3. Creates a virtual environment
4. Installs dependencies
5. Sets up pre-commit hooks
6. Makes the initial commit

You'll see output like:

```
ONE Campaign Python project utilities
Creating project at: my-data-analysis

Copying from template
    create  .
    create  .copier-answers.yml
    create  .github
    create  .github/workflows/ci.yml
    ...

✓ Project created successfully at my-data-analysis

Next steps:
  cd my-data-analysis
  # Review and edit README.md
  # Start coding!
```

## Explore Your Project

Let's see what was created:

```bash
cd my-data-analysis
ls -la
```

You'll see:

```
.
├── .github/
│   └── workflows/
│       └── ci.yml              # GitHub Actions CI
├── scripts/
│   ├── config.py               # Path configuration
│   ├── logger.py               # Logging setup
│   └── example_analysis.py     # Example script
├── raw_data/                   # Put your data here
├── output/                     # Results go here
├── .copier-answers.yml         # Template configuration
├── .gitignore
├── .pre-commit-config.yaml     # Pre-commit hooks
├── LICENSE
├── README.md
├── pyproject.toml              # Project config
└── uv.lock                     # Locked dependencies
```

## Run Your First Script

Try the example analysis script:

```bash
uv run python scripts/example_analysis.py
```

You'll see:

```
2024-03-15 10:30:45 | INFO | Starting example analysis
2024-03-15 10:30:45 | INFO | Raw data directory: /path/to/my-data-analysis/raw_data
2024-03-15 10:30:45 | INFO | Output directory: /path/to/my-data-analysis/output
2024-03-15 10:30:45 | INFO | Analysis complete
```

The script demonstrates:
- Using the configured logger
- Accessing data paths consistently
- Basic project structure

## Add Your First Dependency

Let's add pandas for data analysis:

```bash
uv add pandas
```

Output:

```
Resolved 21 packages in 111ms
Prepared 1 package in 326ms
Installed 7 packages in 155ms
 + numpy==2.3.4
 + pandas==2.3.3
 + python-dateutil==2.9.0.post0
 + pytz==2025.2
 + six==1.17.0
 + tzdata==2025.2
```

Now use it in your script:

```python
# scripts/my_analysis.py
import pandas as pd
from scripts.config import Paths
from scripts.logger import logger

logger.info("Loading data...")
df = pd.read_csv(Paths.raw_data / "data.csv")
logger.info(f"Loaded {len(df)} rows")

# Your analysis here
results = df.describe()

# Save results
results.to_csv(Paths.output / "summary.csv")
logger.info("Analysis complete!")
```

Run it:

```bash
uv run python scripts/my_analysis.py
```

## Quality Checks

Your project comes with automatic code quality tools.

### Check Code Style

```bash
uv run ruff check .
```

If everything looks good:

```
All checks passed!
```

### Fix Issues Automatically

```bash
uv run ruff check --fix .
```

### Type Checking

```bash
uv run mypy scripts/
```

### Pre-commit Hooks

These checks run automatically before each commit:

```bash
git add .
git commit -m "Add my first analysis"
```

You'll see:

```
ruff.................................................Passed
ruff-format..........................................Passed
mypy.................................................Passed
[main abc123] Add my first analysis
 1 file changed, 15 insertions(+)
```

If checks fail, the commit is blocked until you fix them.

## Next Steps

You've created your first project! Now you can:

- **Learn more about creating projects** → [Creating Projects](creating-projects.md)
- **Keep projects up to date** → [Updating Projects](updating-projects.md)
- **Add features to existing projects** → [Adding Components](adding-components.md)

## Skip the Questions

If you want to create projects faster, use defaults:

```bash
uvx bblocks-projects create my-project --type research --defaults
```

This uses default answers for all questions. You can override specific values:

```bash
uvx bblocks-projects create my-project \
  --type research \
  --defaults \
  --data author_name="Jane Smith" \
  --data author_email="jane@one.org"
```

## Troubleshooting

### "command not found: uvx"

Install uv first:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Then restart your terminal.

### "copier: command not found"

bblocks-projects includes Copier as a dependency, so this shouldn't happen. If it does, your installation may have failed. Try reinstalling:

```bash
uv tool install --force bblocks-projects
```

### Pre-commit hooks fail

Update the hooks:

```bash
uv run pre-commit autoupdate
uv run pre-commit run --all-files
```

### "No module named 'scripts'"

Make sure you're running commands from the project root directory:

```bash
cd my-data-analysis
uv run python scripts/my_script.py
```