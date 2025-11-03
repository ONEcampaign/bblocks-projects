# bblocks.projects

ONE Campaign Python project utilities - create, update, and enhance Python projects with standardized templates and tools.

## Installation

### Use with uvx (recommended for one-off usage)

No installation required! Just use `uvx`:

```bash
uvx bblocks-projects my-awesome-project
```

### Install persistently with uv

```bash
uv tool install bblocks-projects
bblocks-projects my-awesome-project
```

### Install with pip/pipx

```bash
pipx install bblocks-projects
# or
pip install bblocks-projects
```

## Usage

### Create a New Project

**Interactive (recommended):**
```bash
bblocks-projects my-project
```

The tool will ask you questions to customize your project:
- Project name and description
- Project type (package or research)
- Author information
- License choice
- etc.

**With options:**
```bash
# Create a package project with defaults
bblocks-projects my-package --type package --defaults

# Create using a specific template version
bblocks-projects my-project --ref v1.0.0

# Override specific values
bblocks-projects my-project --data author_name="Jane Doe" --data author_email="jane@one.org"
```

### Update an Existing Project

Keep your project in sync with the latest template improvements:

```bash
# Update from within your project directory
cd my-project
bblocks-projects update

# Or specify the path
bblocks-projects update --path /path/to/my-project

# Update to a specific template version
bblocks-projects update --ref v1.2.0
```

### Add Components to Existing Projects

Add specific template features to your existing Python projects without full template adoption:

```bash
# List available components
bblocks-projects add --list

# Add pre-commit hooks
bblocks-projects add pre-commit

# Add multiple components at once
bblocks-projects add ruff ci pytest

# Add to a specific project
bblocks-projects add pre-commit --path /path/to/project

# Skip confirmation prompts
bblocks-projects add ruff --yes

# Force overwrite existing files
bblocks-projects add ci --force
```

**Available Components:**
- **pre-commit** - Pre-commit hooks with ruff and mypy
- **ruff** - Ruff linter and formatter with comprehensive rules
- **ci** - GitHub Actions CI workflow
- **pytest** - Pytest with coverage reporting (packages only)
- **pypi-publish** - GitHub Actions workflow for PyPI publishing (packages only)

**What it does:**
- Copies template files to your project
- Merges configurations intelligently into pyproject.toml
- Adds required dependencies
- Shows you exactly what will change before applying

**Example workflow:**
```bash
# You have an existing Python project
cd my-existing-project

# Add pre-commit hooks from ONE template
bblocks-projects add pre-commit
# ✓ Creates .pre-commit-config.yaml
# ✓ Adds pre-commit to dev dependencies
# Shows next steps: uv sync, pre-commit install

# Add CI workflows
bblocks-projects add ci
# ✓ Creates .github/workflows/ci.yml
# Shows next steps: commit and push to GitHub

# Add ruff configuration
bblocks-projects add ruff
# ✓ Adds [tool.ruff] config to pyproject.toml
# ✓ Adds ruff to dev dependencies
# Shows next steps: uv sync, ruff check
```

## Available Commands

### `create`

Create a new ONE Campaign Python project.

**Arguments:**
- `DESTINATION` - Directory where the project will be created (required)

**Options:**
- `--ref, -r` - Template version (branch, tag, or commit). Defaults to 'main'
- `--type, -t` - Project type: 'package' or 'research'
- `--data, -d` - Override template variables in KEY=VALUE format (can be used multiple times)
- `--defaults` - Use default answers for all questions

**Examples:**
```bash
bblocks-projects my-project
bblocks-projects my-package --type package
bblocks-projects my-project --ref v1.0.0
bblocks-projects my-project --data author_name="John Doe"
```

### `update`

Update an existing project to the latest template version.

**Options:**
- `--path, -p` - Path to the project to update (defaults to current directory)
- `--ref, -r` - Update to specific template version
- `--data, -d` - Override template variables in KEY=VALUE format
- `--skip-answered/--no-skip-answered` - Skip or re-answer previously answered questions

**Examples:**
```bash
bblocks-projects update
bblocks-projects update --ref v1.2.0
bblocks-projects update --path ../my-other-project
bblocks-projects update --no-skip-answered  # Re-answer all questions
```

### `add`

Add specific template components to an existing project.

**Arguments:**
- `COMPONENTS` - One or more component names to add

**Options:**
- `--path, -p` - Path to the project (defaults to current directory)
- `--force, -f` - Force overwrite existing files
- `--yes, -y` - Skip confirmation prompts
- `--list, -l` - List available components and exit

**Available Components:**
- `pre-commit` - Pre-commit hooks configuration
- `ruff` - Ruff linter/formatter configuration
- `ci` - GitHub Actions CI workflow
- `pytest` - Pytest testing configuration (packages only)
- `pypi-publish` - PyPI publishing workflow (packages only)

**Examples:**
```bash
bblocks-projects add --list
bblocks-projects add pre-commit
bblocks-projects add ruff ci pytest
bblocks-projects add pre-commit --path /path/to/project
bblocks-projects add ruff --yes  # Skip confirmations
```

**Features:**
- Interactive by default - shows what will change before applying
- Intelligent config merging for pyproject.toml
- Conflict detection - warns if files/configs already exist
- Automatic dependency management
- Post-install guidance for each component

## What You Get

The template creates a modern Python project with:

### For All Projects
-  **uv** for fast dependency management
-  **Ruff** for linting and formatting
-  **mypy** for type checking
-  **pre-commit** hooks configured
-  **GitHub Actions** CI/CD

### For Package Projects
-  **src-layout** structure
-  **pytest** with coverage
-  **PyPI publishing** workflow with trusted publishing
-  Type hint support (py.typed)

### For Research Projects
-  Organized **scripts/** structure
-  **Paths** class for consistent directory references
-  Configured **logger** for analysis scripts
-  Separate **raw_data/** and **output/** directories


## Documentation

For detailed documentation about the templates and best practices:

- [Getting Started Guide](../docs/usage/getting-started.md)
- [Updating Projects](../docs/usage/updating.md)
- [Template Repository](https://github.com/ONEcampaign/bblocks-projects)

## Support

- [Report Issues](https://github.com/ONEcampaign/bblocks-projects/issues)
- [Discussions](https://github.com/ONEcampaign/bblocks-projects/discussions)

## License

MIT License - see [LICENSE](../LICENSE) file for details.
