# Python Project Templates

Modern Python project templates using Copier, with uv for dependency management.

## Available Templates

- **Python Package**: Full package with tests, CI/CD, and PyPI publishing
- **Research/Analysis**: Script-based analysis repos with organized structure

## Quick Start

### Option 1: Using bblocks-projects (Recommended)

The easiest way to use these templates:

```bash
# Create a new project (no installation required)
uvx bblocks-projects my-new-project

# Or install persistently
uv tool install bblocks-projects
bblocks-projects my-new-project

# Add components to existing projects
bblocks-projects add pre-commit ruff ci
```

**New!** You can now add individual template components (pre-commit hooks, CI workflows, ruff config, etc.) to your existing projects without full template adoption.

See [bblocks-projects](bblocks-projects/) for full documentation.

### Option 2: Using Copier Directly

If you prefer to use Copier directly:

**Prerequisites:**
- Python 3.11+
- [copier](https://copier.readthedocs.io/) installed: `uv tool install copier`
- [uv](https://docs.astral.sh/uv/) installed

```bash
copier copy gh:ONEcampaign/repo-templates my-new-project
cd my-new-project
```

Copier will ask questions to customize your project.

## What You Get

### All Projects

-  uv for fast dependency management
-  Ruff for linting and formatting (comprehensive rules, Google docstrings)
-  mypy for type checking (strict mode)
-  pre-commit hooks configured
-  GitHub Actions CI

### Python Packages

-  src-layout structure
-  pytest with coverage
-  PyPI publishing workflow with trusted publishing
-  Type hint support (py.typed)

### Research Projects

-  Organized scripts/ structure
-  Paths class for consistent directory references
-  Configured logger for analysis scripts
-  Separate raw_data/ and output/ directories

## Post-Generation

After generating a project:

1. Review and update the generated README.md
2. For packages: Set up PyPI trusted publishing (see docs/pypi-setup.md)
3. Pre-commit hooks are installed automatically
4. Start coding!

## Documentation

 **Comprehensive guides for all use cases:**

- **[Getting Started](docs/usage/getting-started.md)** - Create a new project from scratch
- **[Updating Projects](docs/usage/updating.md)** - Keep your project in sync with template updates
- **[Adopting in Existing Projects](docs/usage/adopting-existing.md)** - Use the template with existing code
- **[Understanding .copier-answers.yml](docs/understanding-copier-answers.md)** - Why this file is critical and must be committed

### Quick Reference

**Using bblocks-projects (recommended):**
```bash
# Create new project
uvx bblocks-projects my-new-project

# Update existing project
cd my-project
bblocks-projects update

# Add components to existing project
bblocks-projects add pre-commit ruff ci
```

**Using Copier directly:**
```bash
# Create new project
copier copy gh:ONEcampaign/repo-templates my-new-project

# Update existing project
cd your-project
copier update

# Adopt in existing project (cherry-pick approach)
copier copy gh:ONEcampaign/repo-templates /tmp/template-ref
cp /tmp/template-ref/.github/workflows/* .github/workflows/
```

## Extending

See [docs/adding-project-types.md](docs/adding-project-types.md) for how to add new project types to this template.

## Requirements

- Copier 9.0+
- Python 3.11+
- uv

## License

MIT License - see LICENSE file for details.
