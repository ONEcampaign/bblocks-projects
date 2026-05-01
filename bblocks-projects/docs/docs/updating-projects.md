# Updating Projects

Keep your projects synchronized with the latest template improvements. This guide shows you how to update existing projects created with bblocks-projects.

## Basic Update

Update your project to the latest template:

```bash
cd my-project
bblocks-projects update
```

You'll see:

```
Updating project at: /path/to/my-project

Updating from template
    identical  .gitignore
    identical  pyproject.toml
    updated    .github/workflows/ci.yml
    updated    .pre-commit-config.yaml

✓ Project updated successfully!

Next steps:
  git diff  # Review changes
  uv sync   # Update dependencies if needed
  uv run pytest  # Run tests
  git commit -m 'Update from template'
```

The update command:
1. Reads your `.copier-answers.yml` to find the template source
2. Compares your current version with the latest
3. Applies changes to template-managed files
4. Preserves your code and customizations

## What Gets Updated

### Always Updated

These files are managed by the template and get updated:

- `.github/workflows/` - CI/CD workflows
- `.pre-commit-config.yaml` - Pre-commit configuration
- `.gitignore` - Ignore patterns
- Parts of `pyproject.toml` - Tool configurations (ruff, ty, etc.)

### Never Touched

Your code and data stay untouched:

- **Package projects:** Everything in `src/` and `tests/`
- **Research projects:** Your analysis scripts in `scripts/`
- `raw_data/` and `output/` directories
- Custom code you've added
- Git history

### Smart Merging

Some files are intelligently merged:

- `pyproject.toml` - Template sections update, your dependencies stay
- `README.md` - Usually kept as-is (you'll see conflicts if changed)
- `.copier-answers.yml` - Updated automatically

## Review Changes Before Committing

Always review what changed:

```bash
git diff
```

You'll see exactly what the update modified:

```diff
diff --git a/.github/workflows/ci.yml b/.github/workflows/ci.yml
index abc123..def456 100644
--- a/.github/workflows/ci.yml
+++ b/.github/workflows/ci.yml
@@ -10,7 +10,7 @@ jobs:
     runs-on: ubuntu-latest
     steps:
       - uses: actions/checkout@v4
-      - uses: astral-sh/setup-uv@v1
+      - uses: astral-sh/setup-uv@v3
       - run: uv sync
       - run: uv run pytest
```

If you don't like a change, you can revert it:

```bash
git checkout HEAD -- .github/workflows/ci.yml
```

## Handling Conflicts

Sometimes your changes conflict with template updates.

### Conflict Example

You customized `.pre-commit-config.yaml`, and the template also changed it:

```
Updating from template
    conflict  .pre-commit-config.yaml

Conflict! Your changes:
  - Added custom hook: check-json

Template changes:
  - Updated ruff version

Choose an option:
  1 - Keep your version
  2 - Use template version
  3 - See diff
```

### Resolution Strategies

**Keep your changes:**
```bash
# During update, choose option 1
# Or after update:
git checkout HEAD -- .pre-commit-config.yaml
```

**Use template version:**
```bash
# During update, choose option 2
# Or after update:
git checkout --theirs .pre-commit-config.yaml
```

**Merge manually:**
```bash
# See both versions
git diff HEAD .pre-commit-config.yaml

# Edit to combine them
vim .pre-commit-config.yaml

# Mark as resolved
git add .pre-commit-config.yaml
```

### Common Conflicts

**pyproject.toml dependencies:**

Your version:
```toml
dependencies = [
    "requests",
    "pandas",
]
```

Template update adds nothing, but you might see conflicts in tool config sections. Keep your dependencies, accept template tool configs.

**README.md:**

You've heavily customized your README. The template rarely changes this file, but if it does:

```bash
# Usually keep your version
git checkout HEAD -- README.md
```

## Update to Specific Version

Update to a particular template version:

```bash
# Update to tagged version
bblocks-projects update --ref v1.2.0

# Update to branch
bblocks-projects update --ref develop

# Update to specific commit
bblocks-projects update --ref abc123def
```

**Use cases:**

- **Pin to stable version:** Your team uses v1.0.0 as standard
- **Test new features:** Try the develop branch before it's released
- **Rollback:** Something broke, go back to previous version

## When to Update

### Update Regularly

Run updates monthly or quarterly:

```bash
cd my-project
bblocks-projects update
git diff  # Review
git commit -m "Update from template"
git push
```

**Benefits:**
- Get latest bug fixes
- Stay current with Python ecosystem
- Small, manageable changes
- Consistent across all your projects

### Update Before Major Changes

Before starting big features:

```bash
# Update first
bblocks-projects update

# Make sure everything works
uv run pytest
uv run ruff check .

# Now start your feature
git checkout -b feature/new-thing
```

This avoids merge conflicts later.

## Verify After Updating

Always test after updating:

```bash
# Update dependencies
uv sync

# Run tests (packages)
uv run pytest

# Check code quality
uv run ruff check .
uvx ty check src/  # or scripts/ for research

# Try pre-commit
uv run pre-commit run --all-files
```

If everything passes:

```bash
git commit -m "Update from template v1.2.0"
git push
```

## Re-answer Questions

If you want to change your original answers:

```bash
bblocks-projects update --no-skip-answered
```

This re-asks all template questions. Use it to:
- Change Python version requirement
- Update author information
- Switch licenses
- Modify project metadata

## Change Specific Answers

Change individual values without re-answering everything:

```bash
# Update author email
bblocks-projects update --data author_email="newemail@one.org"

# Update Python version
bblocks-projects update --data python_version="3.12"

# Multiple changes
bblocks-projects update \
    --data author_email="newemail@one.org" \
    --data license="apache-2.0"
```

## Troubleshooting

### "No .copier-answers.yml found"

Your project wasn't created with bblocks-projects. You have two options:

1. **Add components instead:**
   ```bash
   bblocks-projects add pre-commit ruff ci
   ```

2. **Fully adopt the template** (advanced, see adoption guide in the repo)

### "Template version not found"

The version you specified doesn't exist:

```bash
# Check available versions
git ls-remote --tags https://github.com/ONEcampaign/bblocks-projects.git

# Use a valid version
bblocks-projects update --ref v1.0.0
```

### "Conflicts after update"

You have uncommitted changes:

```bash
# Stash your changes
git stash

# Run update
bblocks-projects update

# Reapply your changes
git stash pop

# Resolve conflicts
git diff
```

### "Dependencies broken after update"

Resync dependencies:

```bash
# Delete lock file and resync
rm uv.lock
uv sync

# Or force reinstall
uv sync --reinstall
```

### "Tests fail after update"

The template update might have changed tool configurations:

```bash
# Check what changed
git diff

# Common fixes:

# Update ruff config if needed
uv run ruff check --fix .

# Re-run type checking
uvx ty check src/

# Update pre-commit
uv run pre-commit autoupdate
```

### "CI workflow fails"

GitHub Actions workflows updated:

1. Check the workflow file:
   ```bash
   git diff .github/workflows/ci.yml
   ```

2. Push and watch the run:
   ```bash
   git commit -m "Update template"
   git push
   # Go to GitHub Actions tab
   ```

3. Fix any issues and commit

## Track Template Version

Check which template version you're on:

```bash
cat .copier-answers.yml | grep _commit
```

Output:
```yaml
_commit: abc123def456
```

This is the template git commit hash.

Compare with latest:

```bash
# See template repository
cat .copier-answers.yml | grep _src_path
# _src_path: gh:ONEcampaign/bblocks-projects

# Check latest on GitHub
# https://github.com/ONEcampaign/bblocks-projects/commits/main
```

## Automate Update Checks

Add a reminder to check for updates:

```yaml
# .github/workflows/template-check.yml
name: Check Template Updates

on:
  schedule:
    - cron: '0 0 1 * *'  # Monthly on the 1st
  workflow_dispatch:

jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Check template version
        run: |
          echo "Current template commit:"
          grep _commit .copier-answers.yml
          echo ""
          echo "Check for updates at:"
          echo "https://github.com/ONEcampaign/bblocks-projects/commits/main"
```

This creates a monthly reminder to check for template updates.

## Best Practices

### 1. Update in Feature Branches

```bash
git checkout -b update-template
bblocks-projects update
git diff
git commit -m "Update from template"
# Create PR and review
```

### 2. Test Thoroughly

```bash
# After updating
uv sync
uv run pytest
uv run ruff check .
uvx ty check src/
```

### 3. Update Regularly

Don't let projects drift too far from template. 

### 4. Read Template Changelogs

Check the template repository for:
- Breaking changes
- New features
- Migration guides

### 5. Keep .copier-answers.yml

Never delete or ignore this file. It's required for updates.

## Next Steps

- **Add new features** → [Adding Components](adding-components.md)
- **Create more projects** → [Creating Projects](creating-projects.md)
- **Start fresh** → [Getting Started](getting-started.md)