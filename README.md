# Python Project Templates

Modern Python project templates using Copier, with uv for dependency management.

## Available Templates

- **Python Package**: Full package with tests, CI/CD, and PyPI publishing
- **Research/Analysis**: Script-based analysis repos with organized structure

## Quick Start

### Prerequisites

- Python 3.11+
- [copier](https://copier.readthedocs.io/) installed: `uv tool install copier`
- [uv](https://docs.astral.sh/uv/) installed

### Generate a New Project

```bash
copier copy gh:{{ github_username if github_username else 'yourusername' }}/repo-templates my-new-project
cd my-new-project
```

Copier will ask questions to customize your project.

## What You Get

### All Projects

- ✅ uv for fast dependency management
- ✅ Ruff for linting and formatting (comprehensive rules, Google docstrings)
- ✅ mypy for type checking (strict mode)
- ✅ pre-commit hooks configured
- ✅ GitHub Actions CI

### Python Packages

- ✅ src-layout structure
- ✅ pytest with coverage
- ✅ PyPI publishing workflow with trusted publishing
- ✅ Type hint support (py.typed)

### Research Projects

- ✅ Organized scripts/ structure
- ✅ Paths class for consistent directory references
- ✅ Configured logger for analysis scripts
- ✅ Separate raw_data/ and output/ directories

## Post-Generation

After generating a project:

1. Review and update the generated README.md
2. For packages: Set up PyPI trusted publishing (see docs/pypi-setup.md)
3. Pre-commit hooks are installed automatically
4. Start coding!

## Documentation

📚 **Comprehensive guides for all use cases:**

- **[Getting Started](docs/usage/getting-started.md)** - Create a new project from scratch
- **[Updating Projects](docs/usage/updating.md)** - Keep your project in sync with template updates
- **[Adopting in Existing Projects](docs/usage/adopting-existing.md)** - Use the template with existing code
- **[Understanding .copier-answers.yml](docs/understanding-copier-answers.md)** - Why this file is critical and must be committed

### Quick Reference

**Create new project:**
```bash
copier copy gh:ONEcampaign/repo-templates my-new-project
```

**Update existing project:**
```bash
cd your-project
copier update
```

**Adopt in existing project (cherry-pick approach):**
```bash
# Generate template elsewhere, then copy what you need
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
