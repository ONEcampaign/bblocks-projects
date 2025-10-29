# Adopting the Template in Existing Projects

This guide explains how to adopt this template in an existing Python project that wasn't originally created with Copier.

## ⚠️ Important Considerations

**This is more complex than creating a new project or updating.** Consider:

- 🎯 **Best for**: Projects that roughly match the template structure
- ⚠️ **Challenging for**: Projects with very different structures or tooling
- 💡 **Alternative**: Manually adopt best practices instead of full template adoption

## Decision Tree: Should You Adopt?

### ✅ Good Candidates

Your project is a **good candidate** if:
- Uses Python 3.11+
- Has a `pyproject.toml` (or willing to migrate)
- Uses standard project layout (src/ or flat structure)
- You're willing to migrate tooling (poetry → uv, black → ruff)
- You want automated updates from the template

### ⚠️ Consider Alternatives

**Manual adoption** might be better if:
- You have complex custom tooling
- Your project structure is highly customized
- You prefer full control over configuration

In these cases, consider **cherry-picking** best practices from the template instead of full adoption.

## Approaches

There are three main approaches, from easiest to most comprehensive:

1. **Cherry-pick approach**: Manually copy useful configs
2. **Parallel approach**: Generate a template project and merge selectively
3. **Full adoption**: Use Copier to adopt the template

## Approach 1: Cherry-Pick (Recommended for Most)

Copy specific configs from the template without full adoption.

### What to Cherry-Pick

**High Value, Low Risk:**
- `.github/workflows/` - CI/CD workflows
- `.pre-commit-config.yaml` - Pre-commit hooks
- `ruff` configuration from `pyproject.toml`
- `mypy` configuration from `pyproject.toml`

**Medium Value, Medium Risk:**
- Dependency management (migrate poetry → uv)
- Project structure (flat → src layout)
- Test configuration (pytest settings)

**Low Value for Existing Projects:**
- README structure (yours is probably better)
- Project metadata (already established)
- LICENSE (don't change this lightly)

### Step-by-Step: Cherry-Pick CI/CD

**Goal**: Add template's GitHub Actions workflows

```bash
# 1. Generate template in temp directory
cd /tmp
copier copy https://github.com/ONEcampaign/repo-templates.git temp-template
# Answer questions (doesn't matter much, we're just copying files)

# 2. Copy workflows to your project
cd /path/to/your-project
mkdir -p .github/workflows

# Copy and customize
cp /tmp/temp-template/.github/workflows/ci.yml .github/workflows/

# 3. Edit to match your project structure
# For example, if your package is in 'mylib/' instead of 'src/mylib/':
vim .github/workflows/ci.yml
# Change: --cov=src/package_name
# To:     --cov=mylib

# 4. Test locally first
uv run pytest  # Make sure tests work

# 5. Commit and push
git add .github/workflows/ci.yml
git commit -m "Add CI workflow from template"
git push
```

### Step-by-Step: Add Pre-commit Hooks

```bash
# 1. Copy pre-commit config
cp /tmp/temp-template/.pre-commit-config.yaml .

# 2. Install pre-commit
uv add --dev pre-commit

# 3. Install hooks
uv run pre-commit install

# 4. Run on existing code
uv run pre-commit run --all-files

# 5. Fix issues, then commit
git add .
git commit -m "Add pre-commit hooks from template"
```

### Step-by-Step: Migrate to uv

**Current**: Using poetry, pip-tools, or similar

**Goal**: Migrate to uv for faster dependency management

```bash
# 1. Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. Generate uv.lock from existing requirements
uv pip compile pyproject.toml -o requirements.txt
uv lock

# 3. Create uv venv
uv venv

# 4. Test that it works
uv sync
uv run pytest

# 5. Update pyproject.toml build system
# Add to pyproject.toml:
[build-system]
requires = ["uv_build>=0.9.2,<0.10.0"]
build-backend = "uv_build"

# 6. Convert dev dependencies
# If you had poetry dev-dependencies:
[tool.poetry.group.dev.dependencies]
pytest = "^8.0.0"

# Change to:
[dependency-groups]
dev = ["pytest>=8.0.0"]

# 7. Clean up old files
rm poetry.lock requirements*.txt requirements*.in

# 8. Commit
git add pyproject.toml uv.lock
git commit -m "Migrate to uv for dependency management"
```

## Approach 2: Parallel Adoption (Selective Merge)

Generate a fresh template project and merge what you want.

### Step 1: Generate Template

```bash
cd /tmp
copier copy https://github.com/ONEcampaign/repo-templates.git my-project-new
# Answer questions matching your existing project
```

### Step 2: Compare Projects

```bash
# Use diff to compare
diff -r /path/to/your-project /tmp/my-project-new

# Or use a visual diff tool
meld /path/to/your-project /tmp/my-project-new
# OR
code --diff /path/to/your-project /tmp/my-project-new
```

### Step 3: Selectively Merge

**Recommended merge order:**

1. **CI/CD** (`.github/workflows/`)
   - Copy workflows
   - Adjust paths to match your structure

2. **Quality tooling** (`.pre-commit-config.yaml`, ruff/mypy configs)
   - Copy configs
   - Run and fix issues

3. **Dependency management** (move to uv if desired)
   - Convert `pyproject.toml` deps
   - Create `uv.lock`

4. **Project structure** (optional, only if beneficial)
   - Migrate to src-layout
   - This is the most disruptive

### Step 4: Test Thoroughly

```bash
cd /path/to/your-project
uv sync
uv run pytest
uv run ruff check .
uv run mypy your_package/
```

## Approach 3: Full Template Adoption

Make your existing project Copier-managed. **Most complex but enables future updates.**

### ⚠️ Warning

This approach:
- Requires your project to closely match template structure
- May cause many conflicts
- Is irreversible (well, with `git reset`)
- Best done on a branch first

### Prerequisites Check

Before attempting full adoption, verify:

```bash
# ✅ Python version compatible?
python --version  # Should be 3.11+

# ✅ Has pyproject.toml?
ls pyproject.toml

# ✅ Project structure matches?
# For packages: Do you have src/your_package/ or just your_package/?
# For research: Do you have a scripts/ directory?

# ✅ Clean working directory?
git status  # Should be clean

# ✅ All changes committed?
git log -1  # Check latest commit
```

### Step 1: Create Backup Branch

```bash
git checkout -b backup-before-template
git push origin backup-before-template
git checkout main
git checkout -b adopt-template
```

### Step 2: Prepare Project Structure

If needed, restructure to match template:

```bash
# If you have flat layout and want src-layout:
mkdir -p src
mv your_package src/

# Update imports in tests, if needed
find tests -name "*.py" -exec sed -i 's/from your_package/from src.your_package/g' {} \;

# Test that it still works
uv run pytest
```

### Step 3: Run Copier Copy (Force Mode)

```bash
# This will apply the template to your existing directory
copier copy --force https://github.com/ONEcampaign/repo-templates.git .

# Answer questions to match your current project:
# - Project name: Your Project
# - Project slug: your_project
# - Type: package (or research)
# etc.
```

### Step 4: Resolve Conflicts

Copier will overwrite or create files. You'll need to:

```bash
# 1. Check what changed
git status

# 2. Review each file
git diff pyproject.toml  # Merge your custom settings
git diff README.md       # Keep your original content
git diff src/your_project/__init__.py  # Keep your code

# 3. Keep your custom files
git checkout HEAD -- README.md  # Restore your README
git checkout HEAD -- src/your_project/  # Restore your code

# 4. Selectively merge configs
# Edit pyproject.toml to merge:
# - Your custom dependencies
# - Your custom metadata
# - Template's tool configs (ruff, mypy, etc.)
vim pyproject.toml
```

### Step 5: Critical Files to Review

**Must preserve your customizations:**
- `README.md` - Your project description
- `src/your_package/` - Your actual code
- `tests/` - Your existing tests
- Custom scripts or tools

**Can accept from template (usually):**
- `.github/workflows/`
- `.pre-commit-config.yaml`
- Tool configurations in `pyproject.toml` (ruff, mypy)

**Must merge carefully:**
- `pyproject.toml` - Mix your deps with template config
- `.gitignore` - Combine both
- `LICENSE` - Keep yours unless changing

### Step 6: Update Dependencies

```bash
# Sync with uv
uv sync

# If there are issues:
uv pip install -e .  # Install your package
uv run pytest  # Test
```

### Step 7: Test Everything

```bash
# Run all checks
uv run pytest
uv run ruff check .
uv run mypy src/your_package/

# Try building (if package)
uv build

# Run your actual application
# ... your commands ...
```

### Step 8: Fix Issues

Common issues and fixes:

**Import errors:**
```bash
# If you migrated to src-layout, update imports
# Old: import your_package
# New: import your_package (same, but installed differently)

# Make sure package is installed in dev mode:
uv pip install -e .
```

**Test failures:**
```bash
# Check test configuration in pyproject.toml
# Make sure paths match your structure

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-v --cov=src/your_package"  # Adjust path
```

**Dependency conflicts:**
```bash
# Review pyproject.toml [project] dependencies
# Merge your original dependencies with template structure

# If you had:
dependencies = ["requests", "pandas", "your-custom-lib"]

# Keep them!
```

### Step 9: Commit or Rollback

```bash
# If successful:
git add .
git commit -m "Adopt template structure"
git push origin adopt-template

# Create PR for review
gh pr create --title "Adopt template structure"

# If failed:
git checkout main
git branch -D adopt-template
# Start over with cherry-pick approach
```

## Migration Checklists

### From Poetry to uv

- [ ] Install uv
- [ ] Copy dependencies from `[tool.poetry.dependencies]` to `[project] dependencies`
- [ ] Copy dev dependencies from `[tool.poetry.group.dev.dependencies]` to `[dependency-groups] dev`
- [ ] Change build system to `uv_build`
- [ ] Run `uv sync` to generate `uv.lock`
- [ ] Update CI workflows to use `uv` commands
- [ ] Delete `poetry.lock`
- [ ] Update documentation

### From Black/Flake8 to Ruff

- [ ] Add ruff configuration to `pyproject.toml`
- [ ] Remove `[tool.black]` and `[tool.flake8]` sections
- [ ] Update pre-commit hooks to use ruff
- [ ] Run `uv run ruff check . --fix` to auto-fix issues
- [ ] Update CI workflows to use ruff
- [ ] Remove black and flake8 from dependencies

### To src-layout

- [ ] Create `src/` directory
- [ ] Move `your_package/` to `src/your_package/`
- [ ] Update `pyproject.toml` to include `src` in paths
- [ ] Update test imports if needed
- [ ] Update `mypy` files path
- [ ] Update coverage source path
- [ ] Test that everything still works
- [ ] Update documentation

## Special Cases

### Existing Project Uses Setup.py

```bash
# 1. Convert setup.py to pyproject.toml
# Use a converter tool:
pip install setup-py-upgrade
setup-py-upgrade setup.py

# 2. Or manually create pyproject.toml
# Copy structure from template, add your dependencies

# 3. Remove setup.py after migration
git rm setup.py setup.cfg
```

### Complex Custom Tooling

If you have custom tools that conflict:

```bash
# Option 1: Keep both
# Use template for new conventions, keep your tools
# Edit .copier-answers.yml to skip conflicting files

# Option 2: Integrate custom tools
# Add your tools to the template's workflow
# Edit .github/workflows/ci.yml to include your steps

# Option 3: Don't adopt template
# Just cherry-pick the parts that help
```

### Monorepo or Workspace

Templates work best with single projects. For monorepos:

```bash
# Option 1: Apply template to each subproject
cd packages/project-a
copier copy ...

cd ../project-b
copier copy ...

# Option 2: Use template for common configs only
# Cherry-pick .github/workflows/ to root
# Each subproject keeps its own structure
```

## Troubleshooting

### "Too many conflicts"

The project is too different. Use cherry-pick approach instead.

### "Tests break after adoption"

```bash
# Check import paths
# Check pyproject.toml tool.pytest.ini_options
# Make sure package is installed: uv pip install -e .
```

### "CI workflow fails"

```bash
# Check paths in workflow files
# Make sure they match your project structure
# Test locally first: uv run pytest
```

### "Don't want to use uv"

You can use the template with other tools:

```bash
# Keep using poetry
# Just copy the configs you want (.github/, .pre-commit, etc.)
# Ignore the uv-specific parts
```

### "Want to keep some old behavior"

Edit `.copier-answers.yml` to skip certain files:

```yaml
_skip_if_exists:
  - custom-config.yaml
  - special-script.py
```

## Success Stories

### Example: Small Library

**Before:**
- Flat layout: `mylib/`
- poetry for deps
- no CI/CD
- manual testing

**After:**
- src layout: `src/mylib/`
- uv for deps
- GitHub Actions CI/CD
- pre-commit hooks
- 100% test coverage tracked

**Migration time:** 2 hours
**Approach:** Full adoption on a branch

### Example: Data Science Project

**Before:**
- Jupyter notebooks
- pip install -r requirements.txt
- No structure

**After:**
- `scripts/` for analysis
- `raw_data/` and `output/` organized
- uv for dependencies
- pre-commit for code quality
- Still use Jupyter, but organized

**Migration time:** 1 hour
**Approach:** Cherry-pick + manual reorganization

## Recommendations

| Project Type | Recommended Approach | Difficulty |
|-------------|---------------------|------------|
| Small, new-ish (< 6 months) | Full adoption | Medium |
| Well-established library | Cherry-pick | Easy |
| Complex monorepo | Cherry-pick | Easy |
| Data science/research | Parallel, selective merge | Medium |
| Company with strict rules | Cherry-pick only | Easy |

## Summary

- ✅ **Cherry-pick**: Easiest, lowest risk, good for most cases
- ⚠️ **Parallel**: More work, good control, one-time effort
- 🚨 **Full adoption**: Enables updates, but risky and complex

**Best practice**: Start with cherry-picking. If you like it and want automatic updates, consider full adoption later.

---

**Next Steps:**
- Start with [Getting Started Guide](./getting-started.md) to understand the template
- Try cherry-picking one feature (CI/CD) first
- If successful, expand adoption gradually
