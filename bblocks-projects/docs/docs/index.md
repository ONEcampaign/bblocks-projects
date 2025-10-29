# bblocks-projects

**ONE Campaign Python project utilities** - Create, update, and enhance Python projects with standardized templates and tools.

## The Problem

Setting up a new Python project means answering the same questions every time: Which linter? How to configure CI/CD? Where do tests go? What about type checking? You spend hours cobbling together configs from different projects, copying GitHub workflows, and tweaking pyproject.toml files.

Worse, keeping multiple projects consistent is nearly impossible. When you improve the CI workflow in one project, you manually copy it to others. When Ruff releases a new version with better rules, you update each project individually. Your projects drift apart, each with slightly different configurations.

And if you didn't start with a template? Adopting best practices means rewriting configs and restructuring directories. Most teams give up and live with inconsistency.

## The Solution

bblocks-projects gives you three simple commands to create, update, and enhance Python projects:

```bash
# Create a new project with everything configured
uvx bblocks-projects my-awesome-project

# Update an existing project to the latest template
bblocks-projects update

# Add specific features to any Python project
bblocks-projects add pre-commit ruff ci
```

One tool. Three commands. All your projects stay consistent and current.

## Key Features

### Create Projects in Seconds

Start a new Python project with one command. No configuration needed:

```bash
uvx bblocks-projects my-data-analysis
```

You get a complete project structure with uv, Ruff, mypy, pre-commit hooks, and GitHub Actions CI/CD - all configured and ready to use.

Choose between:
- **Package projects** - For libraries you'll publish to PyPI
- **Research projects** - For data analysis and scientific computing

### Keep Projects Current

Update all your projects when the template improves:

```bash
cd my-project
bblocks-projects update
```

Get new features, updated dependencies, and improved configurations automatically. Your customizations stay intact.

### Enhance Existing Projects

Add ONE Campaign standards to any Python project without full adoption:

```bash
# Add pre-commit hooks
bblocks-projects add pre-commit

# Add multiple components at once
bblocks-projects add ruff ci pytest
```

Available components:
- **pre-commit** - Pre-commit hooks with Ruff and mypy
- **ruff** - Linter and formatter with comprehensive rules
- **ci** - GitHub Actions CI workflow
- **pytest** - Testing with coverage reporting
- **pypi-publish** - Automated PyPI publishing workflow

Each component integrates intelligently with your existing configuration.

## What You Get

Every project includes:

- **[uv](https://docs.astral.sh/uv/)** - Fast dependency management (10-100x faster than pip)
- **[Ruff](https://docs.astral.sh/ruff/)** - Lightning-fast linting and formatting
- **[mypy](https://mypy.readthedocs.io/)** - Static type checking
- **[pre-commit](https://pre-commit.com/)** - Automatic quality checks before commits
- **[GitHub Actions](https://github.com/features/actions)** - CI/CD pipelines

**For packages:**
- src-layout structure
- pytest with coverage
- PyPI publishing with trusted publishing
- Type hint support (py.typed)

**For research projects:**
- Organized scripts/ structure
- Paths class for consistent directory references
- Configured logger
- Separate raw_data/ and output/ directories

## Quick Start

### No Installation Required

Use uvx to run without installing:

```bash
uvx bblocks-projects my-project
```

### Or Install Persistently

```bash
# With uv (recommended)
uv tool install bblocks-projects

# With pipx
pipx install bblocks-projects

# With pip
pip install bblocks-projects
```

## Next Steps

- **New to bblocks-projects?** → [Getting Started](getting-started.md)
- **Creating a new project?** → [Creating Projects](creating-projects.md)
- **Have an existing project?** → [Updating Projects](updating-projects.md)
- **Want to add specific features?** → [Adding Components](adding-components.md)

## Support

- [Report Issues](https://github.com/ONEcampaign/bblocks-projects/issues)
- [View Source](https://github.com/ONEcampaign/bblocks-projects)
- [Template Repository](https://github.com/ONEcampaign/repo-templates)