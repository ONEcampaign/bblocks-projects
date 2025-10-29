# Understanding .copier-answers.yml

## What Is This File?

`.copier-answers.yml` is Copier's "memory" file that stores:

- 📝 Your template answers (project name, type, Python version, etc.)
- 🏷️ Template metadata (source URL, version/commit hash)
- 📅 Update history

**Example:**
```yaml
# Changes here will be overwritten by Copier; NEVER EDIT MANUALLY
_commit: abc123def456789
_src_path: gh:yourusername/repo-templates
project_name: My Awesome Project
project_slug: my_awesome_project
project_type: package
python_version: '3.11'
author_name: Jane Smith
author_email: jane@example.com
license: mit
```

## Why Does This File Exist?

### 1. Enables Template Updates

Without this file, `copier update` cannot work:

```bash
# Without .copier-answers.yml
$ copier update
❌ Error: Cannot find .copier-answers.yml
❌ Cannot determine template source or version

# With .copier-answers.yml
$ copier update
✅ Fetching from gh:yourusername/repo-templates
✅ Updating from v1.0.0 to v1.2.0
✅ Pre-filling your previous answers
```

### 2. Documents Project Origin

Anyone can see:
- What template generated this project
- What configuration was used
- When it was last updated

```bash
# Check template version
$ grep _commit .copier-answers.yml
_commit: abc123def456789

# Check template source
$ grep _src_path .copier-answers.yml
_src_path: gh:yourusername/repo-templates

# Check your project configuration
$ grep project_type .copier-answers.yml
project_type: package
```

### 3. Maintains Consistency

On updates, Copier:
- ✅ Pre-fills questions with your previous answers
- ✅ Only changes what you explicitly change
- ✅ Keeps your project consistent

Without this, you'd re-answer all questions on every update.

### 4. Tracks Template History

You can see your template update history in git:

```bash
$ git log --oneline .copier-answers.yml
def456 Update from template v1.2.0
abc123 Update from template v1.1.0
789xyz Initial commit from copier template

$ git diff abc123..def456 .copier-answers.yml
# Shows what template answers changed between versions
```

## Should I Commit This File?

### ✅ YES - Always Track It

**Reasons:**

1. **Team collaboration**: All team members can update from template
2. **Reproducibility**: Documents exact template version used
3. **CI/CD**: Can automate template update checks
4. **History**: Track when template was updated

**Status in git:**

```bash
$ git status
On branch main
Changes not staged for commit:
  modified:   .copier-answers.yml  # ← Should be committed!

$ git add .copier-answers.yml
$ git commit -m "Update template to v1.2.0"
```

### ❌ Don't Ignore It

**Never add to `.gitignore`:**

```bash
# ❌ Bad - breaks updates for team
echo ".copier-answers.yml" >> .gitignore

# ✅ Good - file is tracked by default
```

## The "NEVER EDIT MANUALLY" Warning

The file includes this warning:

```yaml
# Changes here will be overwritten by Copier; NEVER EDIT MANUALLY
```

### Why This Warning?

Copier **regenerates** this file on every operation:
- On `copier copy` - Initial generation
- On `copier update` - Every update
- Manual edits are lost

### How to Change Answers

**❌ Wrong Way:**
```bash
# Manual editing gets overwritten
vim .copier-answers.yml
# Change: project_name: Old Name
# To:     project_name: New Name
# Next copier operation will overwrite this!
```

**✅ Right Way:**
```bash
# Option 1: Change during update
copier update --data project_name="New Name"

# Option 2: Interactive update
copier update
# Copier will ask questions again
# Accept defaults or change answers

# Option 3: Recopy with new answers (advanced)
copier copy --force --data project_name="New Name" template-url .
```

## What Information Is Stored?

### Template Metadata

```yaml
_commit: abc123def            # Template git commit hash
_src_path: gh:user/repo      # Where template came from
```

### Your Answers

All the questions you answered during generation:

```yaml
project_name: My Awesome Project
project_slug: my_awesome_project
project_description: A brief description
project_type: package         # or 'research'
author_name: Jane Smith
author_email: jane@example.com
python_version: '3.11'
license: mit
github_username: janesmith    # only for packages
```

### Copier Internal Data

```yaml
_commit: abc123def
_src_path: gh:user/repo
```

These are used internally by Copier for updates.

## Common Scenarios

### New Team Member Joins

```bash
# They clone your repo
git clone https://github.com/you/your-project.git
cd your-project

# .copier-answers.yml is there
ls -la .copier-answers.yml
# -rw-r--r-- 1 user user 245 Jan 15 10:30 .copier-answers.yml

# They can update from template
copier update
# ✅ Works! Uses committed .copier-answers.yml
```

### Checking Template Version

```bash
# What template version am I on?
cat .copier-answers.yml | grep _commit

# What's the latest template version?
git ls-remote --tags https://github.com/you/repo-templates.git

# Am I behind?
# Compare your _commit with latest tag
```

### Template Source Changed

If the template moves:

```bash
# Old source
_src_path: gh:olduser/old-templates

# Update to new source
copier update --vcs-ref HEAD gh:newuser/new-templates
# Copier will update _src_path automatically
```

### Conflicting Answers

If two branches have different answers:

```bash
git checkout main
# .copier-answers.yml has python_version: '3.11'

git checkout feature-branch
# .copier-answers.yml has python_version: '3.12'

git merge feature-branch
# Git will show conflict in .copier-answers.yml
# Resolve manually, choose one version

# After merge, optionally re-run:
copier update  # Syncs with chosen answers
```

## Automation Examples

### Check for Template Updates in CI

```yaml
# .github/workflows/template-check.yml
name: Check Template Updates

on:
  schedule:
    - cron: '0 0 * * 0'  # Weekly

jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Check template version
        run: |
          CURRENT=$(grep _commit .copier-answers.yml | cut -d' ' -f2)
          LATEST=$(git ls-remote --tags https://github.com/you/repo-templates.git | tail -1)

          if [ "$CURRENT" != "$LATEST" ]; then
            echo "⚠️ Template update available!"
            echo "Current: $CURRENT"
            echo "Latest: $LATEST"
            exit 1
          fi
```

### Pre-commit Hook Reminder

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: check-template-age
        name: Check template age
        entry: bash -c 'echo "💡 Remember to update template: copier update"'
        language: system
        stages: [commit]
        pass_filenames: false
```

## Troubleshooting

### "No .copier-answers.yml found"

**Problem:** File is missing or not tracked

**Solutions:**

1. Check if it exists:
   ```bash
   ls -la .copier-answers.yml
   ```

2. Check if it's ignored:
   ```bash
   git check-ignore .copier-answers.yml
   # Should output nothing
   ```

3. If missing, project wasn't created with Copier:
   - See [Adopting Guide](usage/adopting-existing.md)
   - Can't use `copier update` without this file

### File Changed Unexpectedly

**Problem:** `.copier-answers.yml` shows in git diff

**This is normal after:**
- ✅ Running `copier update` - Updates `_commit` hash
- ✅ Changing answers during update - Updates answer values
- ✅ Template changes - May add/remove answer fields

**Commit it:**
```bash
git add .copier-answers.yml
git commit -m "Update template to vX.Y.Z"
```

### Accidentally Edited Manually

**Problem:** Edited file directly, now `copier update` gives errors

**Solution:**

```bash
# Revert manual changes
git checkout HEAD -- .copier-answers.yml

# Or if you want to keep changes:
# Run copier update with new values
copier update --data key="new value"
```

### Merge Conflicts

**Problem:** Git merge conflict in `.copier-answers.yml`

**Solution:**

```bash
# 1. Resolve conflict manually (choose one version)
vim .copier-answers.yml
# Remove conflict markers <<<<<<, =======, >>>>>>>

# 2. Commit resolution
git add .copier-answers.yml
git commit -m "Resolve .copier-answers.yml conflict"

# 3. Optionally re-sync with template
copier update  # Ensures consistency
```

## Comparison to Other Tools

| Tool | Config File | Purpose |
|------|-------------|---------|
| Copier | `.copier-answers.yml` | Template version tracking |
| npm | `package.json` | Package dependencies |
| pip | `requirements.txt` | Python dependencies |
| uv | `uv.lock` | Locked Python dependencies |
| git | `.git/config` | Repository configuration |

`.copier-answers.yml` is like `package.json` - it documents your template dependency.

## Summary

- ✅ **Always commit** `.copier-answers.yml`
- ✅ **Never edit manually** - use `copier update --data`
- ✅ **Track in version control** - enables team updates
- ✅ **Check regularly** - to stay current with template
- ❌ **Don't ignore** in `.gitignore`
- ❌ **Don't delete** unless abandoning template updates

**Key Insight:** This file is the "link" between your project and the template. Without it, you lose the ability to get template updates.

## Further Reading

- [Copier Documentation: Answers File](https://copier.readthedocs.io/en/stable/configuring/#the-answers-file)
- [Updating Guide](usage/updating.md) - How to update from template
- [Getting Started](usage/getting-started.md) - Initial project setup
