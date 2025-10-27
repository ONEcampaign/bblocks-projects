# Updating Projects from Template

This guide explains how to update existing projects that were created from this template to get the latest improvements, bug fixes, and best practices.

## Why Update?

The template is continuously improved with:
- 🔧 Bug fixes and security updates
- 📦 New dependency versions
- ✨ New features and best practices
- 🚀 Performance improvements
- 📝 Better documentation

Copier makes it easy to apply these updates to your existing projects while preserving your custom changes.

## Prerequisites

- Your project was created with Copier (has `.copier-answers.yml`)
- You have committed all local changes (clean working directory)
- Copier is installed (`uv tool install copier`)

## How It Works

Copier's update feature:
1. ✅ Compares your project with the latest template
2. ✅ Applies changes intelligently
3. ✅ Preserves your customizations
4. ✅ Marks conflicts for manual resolution
5. ✅ Updates `.copier-answers.yml` with the new template version

## Basic Update

### Step 1: Commit Your Work

Ensure you have a clean working directory:

```bash
git status
# If you have uncommitted changes:
git add .
git commit -m "Work in progress before template update"
```

### Step 2: Run Copier Update

```bash
cd your-project
copier update
```

This will:
- Fetch the latest template
- Ask if you want to update any answers
- Apply changes to your project

### Step 3: Review Changes

```bash
# See what changed
git diff

# See which files were modified
git status
```

### Step 4: Resolve Conflicts (if any)

If there are conflicts, Copier will mark them in your files:

```python
<<<<<<< before updating
# Your old code
def old_function():
    pass
=======
# New template code
def new_function():
    pass
>>>>>>> after updating
```

Manually edit these files to resolve conflicts, then:

```bash
git add .
git commit -m "Update from template vX.Y.Z"
```

### Step 5: Test Everything

```bash
# For packages
uv sync
uv run pytest
uv run ruff check .
uv run mypy src/

# For research projects
uv sync
uv run ruff check .
uv run mypy scripts/
```

## Update from Specific Version

Update to a specific template version:

```bash
# Update to version 1.2.0
copier update --vcs-ref=v1.2.0

# Update to a specific commit
copier update --vcs-ref=abc123def

# Update to a branch (useful for testing)
copier update --vcs-ref=feature-branch
```

## Change Answers During Update

You can change your original answers during an update:

```bash
copier update --data project_name="New Project Name"
```

Or answer interactively:

```bash
copier update --trust
```

Copier will re-ask all questions, pre-filled with your previous answers.

## Common Update Scenarios

### Scenario 1: No Conflicts

**Best case!** Everything merges cleanly.

```bash
$ copier update
✨ Project "my-project" updated successfully!
...

$ git status
On branch main
Changes not staged for commit:
  modified:   pyproject.toml
  modified:   .github/workflows/ci.yml
  modified:   .pre-commit-config.yaml

$ git diff  # Review changes
$ git add .
$ git commit -m "Update from template v1.2.0"
```

### Scenario 2: Minor Conflicts

Some files have conflicts that need manual resolution.

```bash
$ copier update

⚠️  Conflicts found in:
  - pyproject.toml
  - README.md

$ # Edit files to resolve conflicts
$ git add .
$ git commit -m "Update from template v1.2.0, resolved conflicts"
```

### Scenario 3: Major Conflicts

Many conflicts or structural changes.

```bash
# Option 1: Resolve manually
copier update
# ... resolve conflicts ...
git add .
git commit -m "Update from template v1.2.0"

# Option 2: Review on a branch first
git checkout -b template-update
copier update
# ... review all changes ...
git add .
git commit -m "Update from template v1.2.0"
git checkout main
git merge template-update
```

### Scenario 4: You Modified Template Files

If you heavily customized files that the template also changed:

```bash
$ copier update

# Copier will show conflicts
# You can choose to:
# 1. Keep your changes
# 2. Accept template changes
# 3. Merge both manually

# For each conflict, edit the file and remove conflict markers
$ vim pyproject.toml  # or your editor

# When done:
$ git add .
$ git commit -m "Update from template v1.2.0, preserved customizations"
```

## Skipping Files

If you've heavily customized certain files and don't want them updated:

**Option 1: Use `.copier-answers.yml`**

Add to your `.copier-answers.yml`:

```yaml
_skip_if_exists:
  - pyproject.toml  # Never overwrite this file
  - README.md       # Keep my custom README
```

**Option 2: Use `--skip` flag**

```bash
copier update --skip="pyproject.toml" --skip="README.md"
```

## Checking Template Version

See which template version your project uses:

```bash
# Check .copier-answers.yml
cat .copier-answers.yml | grep _commit

# Or use copier
copier --help-all  # Shows template info
```

See available template versions:

```bash
# If using GitHub
git ls-remote --tags https://github.com/ONEcampaign/repo-templates.git

# If using local path
cd /path/to/repo-templates
git tag
```

## Best Practices

### 1. Update Regularly

Update often to avoid large divergences:

```bash
# Good: Update monthly or after major template releases
copier update

# Bad: Wait a year, face massive conflicts
```

### 2. Review Before Committing

Always review changes before committing:

```bash
copier update
git diff  # Review ALL changes
git diff pyproject.toml  # Review specific files
uv run pytest  # Run tests
git add .
git commit -m "Update from template"
```

### 3. Use Branches for Large Updates

For major template version jumps:

```bash
git checkout -b template-update-v2
copier update --vcs-ref=v2.0.0
# Test thoroughly
uv run pytest
# If good:
git checkout main
git merge template-update-v2
```

### 4. Document Customizations

Keep notes about intentional deviations:

```markdown
# docs/template-customizations.md

## Deviations from Template

- **pyproject.toml**: Added extra dependencies for ML
- **ci.yml**: Added GPU testing job
- **README.md**: Completely custom for our use case
```

### 5. Keep .copier-answers.yml Clean

Don't edit `.copier-answers.yml` manually:
- ❌ Manual edits may break updates
- ✅ Use `copier update --data key=value` instead

## Troubleshooting

### "No .copier-answers.yml found"

Your project wasn't created with Copier. See [Adopting Existing Projects](./adopting-existing.md).

### "Cannot update, working directory is dirty"

You have uncommitted changes:

```bash
git status
git add .
git commit -m "Save work before template update"
copier update
```

### "Too many conflicts"

If conflicts are overwhelming:

```bash
# Abort and try a different approach
git reset --hard HEAD

# Try updating to intermediate version first
copier update --vcs-ref=v1.5.0  # Middle version
# Resolve conflicts
git add . && git commit -m "Update to v1.5.0"

# Then update to latest
copier update
```

### Update Broke Tests

```bash
# Revert the update
git reset --hard HEAD

# Review what changed
copier update --vcs-ref=vX.Y.Z --pretend

# Update again and fix tests before committing
copier update
uv run pytest  # Fix failing tests
git add .
git commit -m "Update from template, fixed tests"
```

### Want to See Changes Before Applying

Use `--pretend` flag:

```bash
# Dry run - shows what would change
copier update --pretend

# Shows differences without modifying files
copier update --pretend | less
```

## Automation

### Update Check in CI

Add a workflow to check for template updates:

```yaml
# .github/workflows/template-check.yml
name: Check Template Updates

on:
  schedule:
    - cron: '0 0 * * 0'  # Weekly on Sunday
  workflow_dispatch:

jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install Copier
        run: pip install copier

      - name: Check for updates
        run: |
          copier update --pretend || echo "Updates available"
```

### Pre-commit Hook

Add a hook to remind you to update:

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: check-template-age
        name: Check template age
        entry: bash -c 'if [ -f .copier-answers.yml ]; then echo "Remember to update template periodically with: copier update"; fi'
        language: system
        pass_filenames: false
```

## Migration Between Major Versions

For major template version updates (e.g., v1 → v2):

1. **Read the CHANGELOG** in the template repository
2. **Check migration notes** for breaking changes
3. **Update on a branch first**:
   ```bash
   git checkout -b upgrade-to-v2
   copier update --vcs-ref=v2.0.0
   ```
4. **Run full test suite**
5. **Update custom configurations** to match new conventions
6. **Merge to main** after thorough testing

## Summary

- ✅ **Update regularly** to avoid large conflicts
- ✅ **Always commit before updating**
- ✅ **Review all changes** before committing
- ✅ **Test after updating**
- ✅ **Use branches for major updates**
- ✅ **Document your customizations**

Next: [Adopting in Existing Projects](./adopting-existing.md)
