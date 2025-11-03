# Python Project Templates

This repository contains:

1. **bblocks-projects** - A CLI tool for creating, updating, and enhancing Python projects
2. **template/** - Copier templates for Python packages and research projects

## Repository Structure

```
bblocks-projects/
├── bblocks-projects/       # CLI tool (installable via pip/uv)
│   ├── src/                # Source code
│   ├── docs/               # User documentation (MkDocs)
│   └── pyproject.toml      # Package configuration
│
├── template/               # Copier template files
│   ├── copier.yml          # Template questions and configuration
│   ├── {% if ... %}/       # Conditional directories for project types
│   └── [template files]    # Files copied to generated projects
│
└── README.md               # This file
```

## bblocks-projects CLI Tool

A command-line tool that makes it easy to work with these templates.

**Features:**
- Create new Python projects (packages or research)
- Update existing projects when templates improve
- Add individual components (pre-commit, ruff, CI, etc.) to any project

**Installation:**
```bash
# Use without installing
uvx bblocks-projects create my-project

# Or install persistently
uv tool install bblocks-projects
```

**Documentation:**

Full documentation is available at [bblocks-projects/docs/](bblocks-projects/docs/):

- [Getting Started](bblocks-projects/docs/docs/getting-started.md) - Installation and first project
- [Creating Projects](bblocks-projects/docs/docs/creating-projects.md) - Package vs research projects
- [Updating Projects](bblocks-projects/docs/docs/updating-projects.md) - Keeping projects in sync
- [Adding Components](bblocks-projects/docs/docs/adding-components.md) - Enhance existing projects


## Template Directory

The `template/` directory contains [Copier](https://copier.readthedocs.io/) template files that define what gets generated when you create a new project.

### How It Works

Copier is a library for rendering project templates. When you run `bblocks-projects create` or `copier copy`, it:

1. Reads `template/copier.yml` for configuration and questions
2. Asks you questions (project name, type, Python version, etc.)
3. Renders template files with your answers using Jinja2
4. Copies the rendered files to your new project directory

### Template Types

The template supports two project types:

**Python Package** - For libraries to publish on PyPI:
- src-layout structure
- pytest with coverage
- PyPI publishing workflow
- Type hint support

**Research/Analysis** - For data analysis projects:
- Organized scripts/ directory
- Paths configuration
- Logger setup
- raw_data/ and output/ directories

### Template Features

All projects include:
- **uv** for fast dependency management
- **Ruff** for linting and formatting
- **mypy** for type checking
- **pre-commit** hooks
- **GitHub Actions** CI/CD workflows

### Conditional Content

The template uses Jinja2 conditionals to include different files based on project type:

```
template/
├── {% if project_type == 'package' %}src{% endif %}/
│   └── [package files]
├── {% if project_type == 'research' %}scripts{% endif %}/
│   └── [analysis files]
└── pyproject.toml.jinja  # Different configs per type
```

See the [Copier documentation](https://copier.readthedocs.io/) for more on template syntax.

## Quick Start

**Create a new project:**
```bash
uvx bblocks-projects create my-project
```

**Update an existing project:**
```bash
cd my-project
uvx bblocks-projects update
```

**Add features to existing projects:**
```bash
cd existing-project
uvx bblocks-projects add ruff ci pre-commit
```

## Using Copier Directly

If you prefer to use Copier without the bblocks-projects CLI:

```bash
# Install Copier
uv tool install copier

# Create project from this template
copier copy gh:ONEcampaign/bblocks-projects my-project

# Update existing project
cd my-project
copier update
```

The bblocks-projects CLI is a wrapper around Copier with a nicer interface and additional features like component installation.

## Development

### Working on bblocks-projects

```bash
cd bblocks-projects
uv sync
uv run pytest
uv run ruff check .
```

### Modifying the Template

1. Edit files in `template/`
2. Test by creating a project:
   ```bash
   copier copy . /tmp/test-project
   ```
3. Verify the generated project works

### Template Testing Best Practices

- Test both package and research project types
- Verify generated projects pass their CI checks
- Check that `uv sync` and `uv run pytest` work in generated packages
- Ensure `.copier-answers.yml` is created (needed for updates)

## Requirements

- Python 3.11+
- [uv](https://docs.astral.sh/uv/)
- [Copier](https://copier.readthedocs.io/) 9.0+ (if using directly)

## License

MIT License - see LICENSE file for details.