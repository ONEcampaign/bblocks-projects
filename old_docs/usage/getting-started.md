# Getting Started Guide

This guide covers how to use this template to create a new Python project from scratch.

## Prerequisites

- Python 3.11 or higher
- [uv](https://github.com/astral-sh/uv) installed (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
- [Copier](https://copier.readthedocs.io/) installed (`uv tool install copier`)
- Git installed

## Creating a New Project

### Step 1: Run Copier

Navigate to where you want to create your project and run:

```bash
# Using HTTPS (recommended for most users)
copier copy https://github.com/ONEcampaign/repo-templates.git my-new-project

# Or using local path if you've cloned the template
copier copy /path/to/repo-templates my-new-project
```

### Step 2: Answer the Questions

Copier will ask you a series of questions:

```
🎤 What is your project name?
   Example: "My Awesome Project"

🎤 Python-compatible project name
   Default: my_awesome_project (auto-generated from project name)

🎤 Brief project description
   Example: "A library for doing awesome things"

🎤 What type of project?
   [1] Package (library to publish on PyPI)
   [2] Research/Analysis (data analysis scripts)

🎤 Author name
   Example: "Jane Smith"

🎤 Author email
   Example: "jane@example.com"

🎤 Minimum Python version
   [1] 3.11 (default)
   [2] 3.12
   [3] 3.13

🎤 License
   [1] MIT (default)
   [2] Apache-2.0
   [3] BSD-3-Clause
   [4] None

🎤 GitHub username or organization (only for packages)
   Example: "janesmith" or "my-org"
```

### Step 3: Automatic Setup

After you answer the questions, Copier will automatically:

1. ✅ Generate all project files
2. ✅ Initialize a git repository
3. ✅ Create a virtual environment with `uv venv`
4. ✅ Install dependencies and create `uv.lock` with `uv sync`
5. ✅ Install pre-commit hooks
6. ✅ Create initial git commit

You'll see output like:

```
Copying from template version 0.1.0
    create  .
    create  .copier-answers.yml
    create  .github
    create  .github/workflows
    create  .github/workflows/ci.yml
    ...

 > Running task 1 of 6: git init
 > Running task 2 of 6: uv venv
 > Running task 3 of 6: uv sync
 > Running task 4 of 6: git add .
 > Running task 5 of 6: git commit -m "Initial commit from copier template"
 > Running task 6 of 6: pre-commit install

🎉 Project "My Awesome Project" created successfully!

Next steps:
1. Change directory to the project root:
   $ cd my-new-project

2. Review and edit README.md with project-specific information
...
```

## Project Structure

### For Package Projects

```
my-new-project/
├── .github/
│   └── workflows/
│       ├── ci.yml           # Runs tests and linting
│       └── release.yml      # Publishes to PyPI on tags
├── src/
│   └── my_new_project/
│       ├── __init__.py      # Package initialization
│       └── py.typed         # PEP 561 marker
├── tests/
│   ├── __init__.py
│   └── test_example.py      # Example test
├── .copier-answers.yml      # Copier config (don't edit manually)
├── .gitignore
├── .pre-commit-config.yaml  # Pre-commit hooks config
├── CHANGELOG.md             # Change log (Keep a Changelog format)
├── LICENSE                  # Your chosen license
├── README.md                # Project documentation
├── pyproject.toml           # Project configuration
└── uv.lock                  # Locked dependencies
```

### For Research Projects

```
my-new-project/
├── scripts/
│   ├── config.py            # Paths configuration
│   ├── logger.py            # Logging setup
│   └── example_analysis.py  # Example analysis script
├── raw_data/                # Put your raw data here
├── output/                  # Analysis outputs go here
├── .copier-answers.yml      # Copier config (don't edit manually)
├── .gitignore
├── .pre-commit-config.yaml  # Pre-commit hooks config
├── LICENSE                  # Your chosen license
├── README.md                # Project documentation
├── pyproject.toml           # Project configuration
└── uv.lock                  # Locked dependencies
```

## Next Steps

### For Package Projects

1. **Review the generated README.md** and add specific details about your project

2. **Run the tests** to verify everything works:
   ```bash
   cd my-new-project
   uv run pytest
   ```

3. **Start developing** by editing files in `src/my_new_project/`

4. **Add dependencies** as needed:
   ```bash
   uv add requests  # Add a runtime dependency
   uv add --dev pytest-mock  # Add a dev dependency
   ```

5. **Build your package**:
   ```bash
   uv build
   ```

6. **When ready to publish**:
   - Set up [PyPI Trusted Publishing](https://docs.pypi.org/trusted-publishers/)
   - Create and push a git tag:
     ```bash
     git tag v0.1.0
     git push origin v0.1.0
     ```
   - GitHub Actions will automatically build and publish to PyPI

### For Research Projects

1. **Review the generated README.md** and document your research

2. **Try the example script**:
   ```bash
   cd my-new-project
   uv run python scripts/example_analysis.py
   ```

3. **Add your data**:
   - Place raw data files in `raw_data/`
   - Results will be saved to `output/`

4. **Write analysis scripts** in `scripts/`:
   ```python
   # scripts/my_analysis.py
   from scripts.config import Paths
   from scripts.logger import logger

   logger.info("Starting analysis...")

   # Your analysis code here
   input_file = Paths.raw_data / "data.csv"
   output_file = Paths.output / "results.csv"
   ```

5. **Run quality checks**:
   ```bash
   uv run ruff check .
   uv run mypy scripts/
   ```

## Common Tasks

### Adding Dependencies

```bash
# Add a runtime dependency
uv add pandas

# Add a development dependency
uv add --dev jupyter

# Add a specific version
uv add "requests>=2.30.0,<3.0.0"
```

### Running Code

```bash
# Run a Python script
uv run python scripts/my_script.py

# Run tests (packages only)
uv run pytest

# Run with coverage (packages only)
uv run pytest --cov

# Run linting
uv run ruff check .

# Run type checking
uv run mypy src/my_project/  # or scripts/ for research
```

### Pre-commit Hooks

Pre-commit hooks run automatically before each commit:

```bash
# Run manually on all files
uv run pre-commit run --all-files

# Update hook versions
uv run pre-commit autoupdate
```

### Updating Python Version

Edit `pyproject.toml`:

```toml
requires-python = ">=3.12"  # Change from 3.11 to 3.12
```

Then reinstall:

```bash
uv python install 3.12
uv sync
```

## GitHub Setup

After creating your project locally:

1. **Create a GitHub repository** (don't initialize it)

2. **Add the remote and push**:
   ```bash
   cd my-new-project
   git remote add origin https://github.com/YOUR_USERNAME/my-new-project.git
   git push -u origin main
   ```

3. **For packages**, set up PyPI trusted publishing:
   - Go to your PyPI project settings
   - Add GitHub as a trusted publisher
   - Specify your repo name and workflow file: `release.yml`
   - See [PyPI docs](https://docs.pypi.org/trusted-publishers/) for details

## Troubleshooting

### "uv: command not found"

Install uv:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### "copier: command not found"

Install Copier with uv:
```bash
uv tool install copier
```

### Pre-commit hooks fail

Update the hooks:
```bash
uv run pre-commit autoupdate
uv run pre-commit run --all-files
```

### Tests fail on fresh project

This shouldn't happen! If it does, it's a template bug. Please report it.

### CI/CD workflows not running

Make sure you've pushed your repository to GitHub and that workflows are enabled in Settings → Actions.

## What's Included

Your project comes with:

- ✅ **uv**: Fast Python package manager and build backend
- ✅ **ruff**: Lightning-fast linter and formatter
- ✅ **mypy**: Static type checking
- ✅ **pytest** (packages): Testing framework with coverage
- ✅ **pre-commit**: Automatic code quality checks
- ✅ **GitHub Actions**: CI/CD pipelines
- ✅ **uv.lock**: Reproducible dependency locking
- ✅ **Modern project structure**: src-layout (packages) or scripts (research)

## Next Steps

- Read the [Updating Guide](./updating.md) to learn about keeping your project in sync with template updates
- Read the [Adopting Guide](./adopting-existing.md) to learn about using this template with existing projects
