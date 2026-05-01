# Adding Components

Add ONE Data template features to any Python project—even if it wasn't created with bblocks-projects. This lets you adopt best practices incrementally without restructuring your entire project.

## Available Components

List all components:

```bash
bblocks-projects add --list
```

Output:

```
Available components:

  • pre-commit - Pre-commit hooks with ruff and ty
  • ruff - Ruff linter and formatter with comprehensive rules
  • ci - GitHub Actions CI workflow
  • pytest - Pytest with coverage reporting (packages only)
  • pypi-publish - GitHub Actions workflow for PyPI publishing (packages only)
```

## How It Works

When you add a component, bblocks-projects:

1. **Analyses your project** - Detects project type and structure
2. **Shows what will change** - Displays files to create and configs to update
3. **Asks for confirmation** - You review before anything happens
4. **Installs the component** - Copies files and merges configurations
5. **Adds dependencies** - Updates pyproject.toml with required packages
6. **Shows next steps** - Tells you what to do after installation

Everything is interactive by default. You see exactly what happens before it happens.

## Basic Usage

Add a single component:

```bash
bblocks-projects add pre-commit
```

You'll see:

```
Project Analysis:
  Path: /Users/you/my-project
  Name: my-project
  Type: package
  Uses uv: Yes

Component: pre-commit
Pre-commit hooks with ruff and ty

Will create:
  • .pre-commit-config.yaml

Will add dev dependencies:
  • pre-commit>=3.0.0

Continue? [y/N]: y

✓ Created .pre-commit-config.yaml
✓ Added pre-commit>=3.0.0 to dev dependencies

Next steps:
  • Run: uv sync
  • Run: uv run pre-commit install
  • Test: uv run pre-commit run --all-files

✓ Component 'pre-commit' installed successfully
```

## Add Multiple Components

Add several components at once:

```bash
bblocks-projects add ruff ci pytest
```

Each component installs sequentially. You see the progress for all of them:

```
Installing component 1/3: ruff
✓ ruff installed

Installing component 2/3: ci
✓ ci installed

Installing component 3/3: pytest
✓ pytest installed

Summary: Installed 3/3 components
```

## Component Details

### pre-commit

Pre-commit hooks that run before each commit.

**What it does:**
- Creates `.pre-commit-config.yaml`
- Adds pre-commit to dev dependencies
- Configures hooks for ruff, ty, and common checks

**Hooks included:**
- Ruff linting with auto-fix
- Ruff formatting
- ty type checking
- Trailing whitespace removal
- YAML/TOML validation
- Large file detection

**After installation:**

```bash
# Install hooks
uv sync
uv run pre-commit install

# Test hooks
uv run pre-commit run --all-files
```

Now hooks run automatically on commit:

```bash
git add .
git commit -m "Add feature"

# Hooks run automatically:
ruff...............................................Passed
ruff-format........................................Passed
ty.................................................Passed
```

**When to use:**
- You want automatic code quality checks
- Team members should follow consistent standards
- Catching issues before CI saves time

### ruff

Fast Python linter and formatter.

**What it does:**
- Adds ruff configuration to pyproject.toml
- Adds ruff to dev dependencies
- Configures comprehensive rules

**Rules included:**
- All Ruff rules enabled by default
- Excludes rules that conflict with formatter
- Google-style docstring convention
- Line length: 88 characters

**After installation:**

```bash
# Sync dependencies
uv sync

# Check code
uv run ruff check .

# Fix automatically
uv run ruff check --fix .

# Format code
uv run ruff format .
```

**Example output:**

```bash
$ uv run ruff check .
src/my_project/core.py:10:1: E501 Line too long (92 > 88)
src/my_project/core.py:15:5: F841 Local variable `x` is assigned to but never used
Found 2 errors.

$ uv run ruff check --fix .
Fixed 2 errors.
```

**When to use:**
- You want fast linting (100x faster than pylint)
- Replacing black + flake8 + isort
- Need comprehensive code quality rules

### ci

GitHub Actions CI workflow.

**What it does:**
- Creates `.github/workflows/ci.yml`
- Runs on push and pull requests
- Tests across Python 3.11, 3.12, and 3.13

**Workflow includes:**
- Running tests (pytest for packages)
- Linting with ruff
- Type checking with ty
- Uses GitHub's uv caching for speed

**After installation:**

```bash
# Commit the workflow
git add .github/workflows/ci.yml
git commit -m "Add CI workflow"

# Push to GitHub
git push origin main

# Watch it run
# Go to: https://github.com/your-username/your-repo/actions
```

**Example CI run:**

```
✓ Install dependencies (12s)
✓ Run tests (5s)
✓ Run linting (2s)
✓ Run type checking (8s)

All checks passed!
```

**Customizing:**

Edit `.github/workflows/ci.yml` to:
- Change Python versions
- Add more test commands
- Modify lint paths
- Add deployment steps

**When to use:**
- Automatic testing on every push
- Enforce quality checks in pull requests
- Test across multiple Python versions

### pytest

Testing framework with coverage.

**Package projects only** - Research projects typically don't need structured testing.

**What it does:**
- Adds pytest configuration to pyproject.toml
- Configures coverage reporting
- Adds pytest and pytest-cov to dev dependencies

**Configuration includes:**
- Test directory: `tests/`
- Coverage for `src/` directory
- XML and terminal coverage reports
- Excludes common untestable lines

**After installation:**

```bash
# Sync dependencies
uv sync

# Run tests
uv run pytest

# With coverage
uv run pytest --cov
```

**Example output:**

```bash
$ uv run pytest --cov

============================= test session starts ==============================
platform darwin -- Python 3.12.3, pytest-8.4.2, pluggy-1.6.0
collecting ... collected 2 items

tests/test_package.py::test_version PASSED                              [ 50%]
tests/test_package.py::test_placeholder PASSED                          [100%]

================================ tests coverage ================================
Name                           Stmts   Miss  Cover
--------------------------------------------------
src/my_package/__init__.py         2      0   100%
--------------------------------------------------
TOTAL                              2      0   100%
============================== 2 passed in 0.03s ===============================
```

**When to use:**
- Building a library
- Need test coverage metrics
- Want to enforce testing standards

### pypi-publish

Automated PyPI publishing workflow.

**Package projects only** - Only packages get published to PyPI.

**What it does:**
- Creates `.github/workflows/release.yml`
- Uses PyPI trusted publishing (no API tokens!)
- Builds and publishes on git tags

**Workflow triggered by:**
- Pushing a tag: `git push origin v1.0.0`
- Manual workflow dispatch

**After installation:**

1. **Register project on PyPI:**
   - Go to https://pypi.org/manage/projects/
   - Create your project

2. **Set up trusted publishing:**
   - Project Settings → Publishing
   - Add GitHub as trusted publisher
   - Repository: `ONEcampaign/your-repo`
   - Workflow: `release.yml`
   - Environment: Leave blank

3. **Publish by pushing tags:**
   ```bash
   # Update version in pyproject.toml
   # Then:
   git tag v0.1.0
   git push origin v0.1.0

   # GitHub Actions builds and publishes automatically!
   ```

**When to use:**
- Publishing packages to PyPI
- Want secure, automated releases
- No API tokens to manage

## Common Workflows

### Starting an Existing Project

You have a Python project without modern tooling:

```bash
cd my-existing-project

# Add pre-commit for automatic quality checks
bblocks-projects add pre-commit

# Add ruff for linting
bblocks-projects add ruff

# Add CI for automated testing
bblocks-projects add ci

# Install and test
uv sync
uv run pre-commit run --all-files
git add .
git commit -m "Add ONE Campaign tooling"
git push
```

### Modernizing an Old Package

You have an old package with setuptools and pylint:

```bash
cd old-package

# Add modern tooling
bblocks-projects add ruff pytest ci

# Migrate from old tools:
# Remove: setup.py, setup.cfg, .pylintrc
# Keep: pyproject.toml (merged with new config)

# Update and test
uv sync
uv run pytest
uv run ruff check .
```

### Adding CI to Research Project

You have scripts but want CI:

```bash
cd climate-analysis

# Add ruff for code quality
bblocks-projects add ruff

# Add CI (automatically detects research type)
bblocks-projects add ci

# CI will:
# - Lint scripts/ directory
# - Run ty on scripts/
# - Skip tests (research projects don't have them)

git add .github/workflows/ci.yml
git commit -m "Add CI"
git push
```

## Skip Confirmations

For scripting or when you're sure:

```bash
bblocks-projects add ruff --yes
```

This skips the confirmation prompt and installs immediately.

## Force Overwrite

If a file already exists and you want to replace it:

```bash
bblocks-projects add pre-commit --force
```

**Warning:** This overwrites without asking. Use carefully.

## Handling Conflicts

When a file or configuration already exists:

```bash
bblocks-projects add ruff
```

You'll see:

```
Conflicts detected:
  • Config section exists: tool.ruff

The component wants to add [tool.ruff] but it already exists.

Options:
  1. Skip this component
  2. Merge configurations (advanced)
  3. Overwrite existing config

Choice [1]: 1

Skipping ruff due to conflicts.
```

### Resolving Conflicts

**Option 1: Manual merge**

```bash
# See what the component would add
bblocks-projects add ruff --yes

# Review the changes
git diff pyproject.toml

# Keep what you want
vim pyproject.toml

# Commit
git add pyproject.toml
git commit -m "Add ruff config"
```

**Option 2: Backup and overwrite**

```bash
# Backup existing config
cp pyproject.toml pyproject.toml.bak

# Overwrite
bblocks-projects add ruff --force

# Compare and merge manually
diff pyproject.toml.bak pyproject.toml
```

**Option 3: Use different component**

If one component conflicts, try others:

```bash
# ruff conflicts? Try just pre-commit
bblocks-projects add pre-commit ci
```

## Add to Specific Project

Add components to a project in a different directory:

```bash
bblocks-projects add pre-commit --path /path/to/other-project
```

Useful for:
- Managing multiple projects
- Scripting updates across projects
- Working from a different directory

## Check Before Installing

See what will happen without installing:

```bash
# Dry-run (show analysis but don't install)
# Use --yes to see the plan, then cancel when asked

bblocks-projects add ruff
# Review what it shows
# Press Ctrl+C before confirming
```

## Requirements

To use `bblocks-projects add`, your project must:

1. **Have pyproject.toml** - For dependency management
2. **Use uv** - With uv.lock file present
3. **Be valid Python project** - Importable package or scripts

**Check your project:**

```bash
# Both should exist
ls pyproject.toml
ls uv.lock

# If you don't have uv.lock, initialize:
uv sync  # This creates uv.lock

# Now components will work
bblocks-projects add ruff
```

## Limitations

**What components DON'T do:**

- Don't restructure your code (your src/ or scripts/ stay untouched)
- Don't modify existing functions/classes
- Don't change git history
- Don't run tests (you do that afterward)

**When NOT to use components:**

- Project has no pyproject.toml (convert first)
- Not using uv (migrate first)
- Need full template adoption (use `bblocks-projects create` instead)

## Troubleshooting

### "Project validation failed: No pyproject.toml"

Your project needs a pyproject.toml:

```bash
# Create minimal pyproject.toml
cat > pyproject.toml << 'EOF'
[project]
name = "my-project"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = []

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
EOF

# Now try adding components
bblocks-projects add pre-commit
```

### "Component is only for package projects"

Some components only work with package projects:

```bash
# Fails for research projects
bblocks-projects add pytest

# Error: pytest component is only for package projects
```

**Solution:** Use appropriate components for your project type.

### "File exists: .pre-commit-config.yaml"

You already have this file:

```bash
# Option 1: Keep yours
# Just cancel the installation

# Option 2: Overwrite with template version
bblocks-projects add pre-commit --force

# Option 3: Merge manually
mv .pre-commit-config.yaml .pre-commit-config.yaml.bak
bblocks-projects add pre-commit
# Merge the two files
```

### Dependencies not installing

Make sure uv is working:

```bash
# Check uv
uv --version

# Try manually
uv sync

# If that works, try component again
bblocks-projects add ruff
```

### CI workflow not running

After adding CI:

1. **Commit and push the workflow:**
   ```bash
   git add .github/workflows/ci.yml
   git commit -m "Add CI"
   git push
   ```

2. **Check GitHub Actions tab:**
   - Go to your repo on GitHub
   - Click "Actions" tab
   - You should see a workflow run

3. **Enable workflows if needed:**
   - Settings → Actions → General
   - Allow all actions

## Best Practices

### 1. Start Small

Add components incrementally:

```bash
# Week 1: Add pre-commit
bblocks-projects add pre-commit

# Week 2: Add ruff
bblocks-projects add ruff

# Week 3: Add CI
bblocks-projects add ci
```

This lets your team adapt gradually.

### 2. Test Each Component

After adding each component, verify it works:

```bash
bblocks-projects add pytest
uv sync
uv run pytest  # Make sure it works
git commit -m "Add pytest"
```

### 3. Document Changes

Tell your team what you added:

```bash
git commit -m "Add pre-commit hooks

- Runs ruff and ty before commits
- Catches issues before CI
- Run: pre-commit install after pulling"
```

### 4. Keep Components Updated

When template updates:

```bash
# Re-add components to get latest versions
bblocks-projects add pre-commit --force
bblocks-projects add ci --force
```

## Next Steps

- **Create new projects** → [Creating Projects](creating-projects.md)
- **Update existing projects** → [Updating Projects](updating-projects.md)
- **Learn the basics** → [Getting Started](getting-started.md)