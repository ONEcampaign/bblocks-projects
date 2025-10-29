# Creating Projects

Learn how to create new Python projects with bblocks-projects, customize them, and choose the right project type for your needs.

## Basic Creation

The simplest way to create a project:

```bash
bblocks-projects create my-project
```

This starts an interactive session where you answer questions about your project. You choose the name, description, type, author info, Python version, and license.

## Project Types

You can create two types of projects:

### Package Projects

For libraries you'll publish to PyPI:

```bash
bblocks-projects create my-awesome-package --type package
```

**You get:**
- src-layout structure (`src/my_awesome_package/`)
- pytest with coverage reporting
- PyPI publishing workflow with trusted publishing
- Type hint support (py.typed marker)
- Package metadata in pyproject.toml

**Use when:**
- Building a reusable library
- Sharing code across projects
- Publishing to PyPI
- Creating tools others will import

**Example structure:**

```
my-awesome-package/
├── src/
│   └── my_awesome_package/
│       ├── __init__.py
│       ├── core.py
│       └── py.typed
├── tests/
│   ├── __init__.py
│   └── test_core.py
├── .github/
│   └── workflows/
│       ├── ci.yml
│       └── release.yml
└── pyproject.toml
```

**Common workflow:**

```bash
# Create package
bblocks-projects create data-cleaner --type package

cd data-cleaner

# Add your code
echo 'def clean(data): return data.strip()' > src/data_cleaner/core.py

# Write tests
echo 'from data_cleaner.core import clean\n\ndef test_clean():\n    assert clean(" hello ") == "hello"' > tests/test_core.py

# Run tests
uv run pytest

# Build package
uv build

# When ready, push a tag to publish
git tag v0.1.0
git push origin v0.1.0
```

### Research Projects

For data analysis and scientific computing:

```bash
bblocks-projects create climate-analysis --type research
```

**You get:**
- Organized scripts/ directory
- Paths class for consistent file references
- Configured logger for analysis scripts
- Separate raw_data/ and output/ directories
- Example analysis script

**Use when:**
- Analyzing data
- One-off research projects
- Exploratory analysis
- Scientific computing
- You won't publish to PyPI

**Example structure:**

```
climate-analysis/
├── scripts/
│   ├── config.py           # Paths configuration
│   ├── logger.py           # Logging setup
│   ├── 01_load_data.py
│   ├── 02_clean_data.py
│   └── 03_analyze.py
├── raw_data/
│   └── climate_data.csv
├── output/
│   ├── cleaned_data.csv
│   └── results.png
└── pyproject.toml
```

**Common workflow:**

```bash
# Create research project
bblocks-projects create climate-analysis --type research

cd climate-analysis

# Add your data
cp ~/Downloads/climate_data.csv raw_data/

# Write analysis script
cat > scripts/analyze_climate.py << 'EOF'
import pandas as pd
from scripts.config import Paths
from scripts.logger import logger

logger.info("Loading data...")
df = pd.read_csv(Paths.raw_data / "climate_data.csv")
logger.info(f"Loaded {len(df)} rows")

# Your analysis
summary = df.groupby("year").mean()
summary.to_csv(Paths.output / "yearly_summary.csv")

logger.info("Analysis complete!")
EOF

# Add pandas
uv add pandas

# Run analysis
uv run python scripts/analyze_climate.py
```

## Customization Options

### Use Defaults

Skip all questions by using defaults:

```bash
bblocks-projects create quick-project --defaults
```

This uses sensible defaults:
- Project type: package
- Python version: 3.11
- License: MIT
- Author: From git config

### Override Specific Values

Use `--data` to set specific values while keeping other defaults:

```bash
bblocks-projects create my-project \
  --defaults \
  --data author_name="Jane Smith" \
  --data author_email="jane@one.org" \
  --data license="apache-2.0"
```

You can override any template variable:
- `project_name` - Display name
- `project_slug` - Python package name
- `project_description` - Brief description
- `project_type` - `package` or `research`
- `author_name` - Your name
- `author_email` - Your email
- `python_version` - `3.11`, `3.12`, or `3.13`
- `license` - `mit`, `apache-2.0`, `bsd-3-clause`, or `none`
- `github_username` - GitHub username (packages only)

### Template Versions

Use a specific template version:

```bash
# Use a tagged version
bblocks-projects create my-project --ref v1.0.0

# Use a branch
bblocks-projects create my-project --ref experimental

# Use a commit
bblocks-projects create my-project --ref abc123
```

Default is `main` (latest).

**When to specify a version:**
- Your team uses a specific template version
- You need a feature from a newer version
- You want stability (pin to a tag)
- Testing template changes (use a branch)

## What's Included

Every project includes these tools, pre-configured:

### uv - Dependency Management

Fast Python package manager:

```bash
# Add dependencies
uv add requests pandas

# Add dev dependencies
uv add --dev pytest-cov

# Run commands
uv run python scripts/my_script.py
uv run pytest
```

### Ruff - Linting and Formatting

Lightning-fast code quality:

```bash
# Check code
uv run ruff check .

# Fix automatically
uv run ruff check --fix .

# Format code
uv run ruff format .
```

Configured with comprehensive rules:
- pycodestyle errors and warnings
- pyflakes
- isort (import sorting)
- flake8-bugbear (bug detection)
- flake8-comprehensions
- pyupgrade (modernization)
- Google-style docstrings

### mypy - Type Checking

Static type checking:

```bash
# Check types
uv run mypy src/  # or scripts/ for research
```

Configured in strict mode for maximum safety.

### pre-commit - Automatic Checks

Runs quality checks before each commit:

```bash
# Manual run
uv run pre-commit run --all-files

# Runs automatically on git commit
git commit -m "Add feature"
```

Configured hooks:
- Ruff linting
- Ruff formatting
- mypy type checking
- Trailing whitespace removal
- YAML/TOML validation

### GitHub Actions CI/CD

Automatic testing and deployment:

**For all projects:**
- `ci.yml` - Runs tests and quality checks on every push

**For packages:**
- `release.yml` - Publishes to PyPI when you push a tag

## Common Patterns

### Quick Prototype

```bash
bblocks-projects create prototype --defaults --type research
cd prototype
uv add pandas matplotlib
# Start coding!
```

### Team Project

```bash
bblocks-projects create team-project \
  --type package \
  --data author_name="ONE Campaign Data Team" \
  --data author_email="data@one.org" \
  --data github_username="ONEcampaign"
```

### Multiple Python Versions

For testing across Python versions, edit pyproject.toml after creation:

```toml
[project]
requires-python = ">=3.11"

# In CI, test multiple versions
[tool.pytest.ini_options]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
```

Then update `.github/workflows/ci.yml`:

```yaml
strategy:
  matrix:
    python-version: ["3.11", "3.12", "3.13"]
```

## After Creation

Once your project is created:

### 1. Review Generated Files

```bash
cd my-project
cat README.md  # Generated readme with project-specific info
cat pyproject.toml  # Project configuration
```

### 2. Initialize Git Remote

```bash
# Create repo on GitHub, then:
git remote add origin https://github.com/yourusername/my-project.git
git push -u origin main
```

### 3. Set Up PyPI Publishing (Packages Only)

For automated PyPI releases:

1. Create the project on PyPI (first release manually):
   ```bash
   uv build
   uv publish
   ```

2. Configure trusted publishing on PyPI:
   - Go to your project settings
   - Add GitHub as trusted publisher
   - Workflow: `release.yml`
   - Environment: `pypi`

3. Future releases are automatic:
   ```bash
   git tag v0.2.0
   git push origin v0.2.0
   # GitHub Actions publishes automatically
   ```

### 4. Start Coding

Add your code and commit:

```bash
# Add code
vim src/my_project/core.py  # or scripts/analysis.py

# Quality checks run automatically
git add .
git commit -m "Add core functionality"
git push
```

## Troubleshooting

### "Directory already exists"

Choose a different name or remove the existing directory:

```bash
rm -rf my-project
bblocks-projects create my-project
```

### "Invalid project slug"

Project names must be valid Python identifiers. Use underscores, not hyphens:

```bash
# Bad
bblocks-projects create my-cool-project

# Good
bblocks-projects create my_cool_project
```

Or let bblocks-projects auto-convert:
- "My Cool Project" becomes `my_cool_project`
- "my-cool-project" becomes `my_cool_project`

### "Template not found"

Check your template reference:

```bash
# Make sure the ref exists
bblocks-projects create my-project --ref main  # Use main, not master
```

### Git initialization fails

Ensure git is installed and configured:

```bash
git --version
git config --global user.name "Your Name"
git config --global user.email "you@example.com"
```

## Next Steps

- **Keep projects updated** → [Updating Projects](updating-projects.md)
- **Add features to existing projects** → [Adding Components](adding-components.md)
- **Back to basics** → [Getting Started](getting-started.md)