# Usage Documentation

Complete guides for using this Python project template with Copier.

## Quick Links

- **New project?** → [Getting Started Guide](./getting-started.md)
- **Have a project from this template?** → [Updating Guide](./updating.md)
- **Want to use with existing project?** → [Adopting Guide](./adopting-existing.md)

## What's This Template?

A modern, opinionated Python project template that supports two types of projects:

1. **📦 Python Packages**: Libraries to publish on PyPI with full CI/CD
2. **🔬 Research/Analysis**: Data science and analysis projects with organized structure

### What's Included

- **[uv](https://github.com/astral-sh/uv)**: Fast Python package manager and build backend (10-100x faster than pip)
- **[Ruff](https://github.com/astral-sh/ruff)**: Lightning-fast linter and formatter (100x faster than pylint)
- **[mypy](https://mypy.readthedocs.io/)**: Static type checking for Python
- **[pytest](https://docs.pytest.org/)**: Testing framework with coverage reporting (packages only)
- **[pre-commit](https://pre-commit.com/)**: Automatic code quality checks before each commit
- **[GitHub Actions](https://github.com/features/actions)**: CI/CD pipelines for testing and releasing
- **Modern project structure**: src-layout (packages) or organized scripts (research)
- **Lock files**: `uv.lock` for reproducible builds

## Important: .copier-answers.yml

⚠️ **This file is critical** - it enables template updates and should always be committed to git.

📖 See [Understanding .copier-answers.yml](../understanding-copier-answers.md) for detailed explanation of:
- What it is and why it exists
- Why you must commit it to git
- How Copier uses it for updates
- What happens if you edit it manually

**TL;DR:** It's like `package.json` for templates - documents your template version and answers.

## Guides Overview

### [Getting Started Guide](./getting-started.md)

**For: Creating a brand new project**

Learn how to:
- Install prerequisites (uv, Copier)
- Generate a new project with `copier copy`
- Understand project structure
- Add dependencies
- Run tests and quality checks
- Set up GitHub and PyPI publishing

**Time:** 15 minutes to working project

### [Updating Guide](./updating.md)

**For: Projects created from this template**

Learn how to:
- Update your project to latest template version
- Handle conflicts during updates
- Preserve your customizations
- Test after updating
- Automate update checks
- Migrate between major versions

**Time:** 10-30 minutes depending on conflicts

### [Adopting Guide](./adopting-existing.md)

**For: Existing projects not created with this template**

Learn how to:
- Decide if you should adopt the template
- Cherry-pick useful features (CI/CD, pre-commit)
- Migrate from poetry to uv
- Migrate from black/flake8 to ruff
- Fully adopt the template (advanced)
- Handle edge cases and special scenarios

**Time:** 1-4 hours depending on approach

## Decision Flow

```
┌─────────────────────────────────────────┐
│   Do you have an existing project?      │
└──────────────┬──────────────────────────┘
               │
        ┌──────┴──────┐
        NO            YES
        │             │
        ▼             ▼
  ┌─────────┐   ┌─────────────────────────────────┐
  │  START  │   │  Was it created with Copier?    │
  │  HERE   │   │  (has .copier-answers.yml)      │
  └────┬────┘   └───────────┬────────────────────┘
       │                    │
       │             ┌──────┴──────┐
       │            YES            NO
       │             │             │
       ▼             ▼             ▼
  [Getting    [Updating    [Adopting
   Started]    Guide]       Guide]
       │             │             │
       │             │             │
       └─────────────┴─────────────┘
                     │
                     ▼
          ┌──────────────────┐
          │  Happy coding!   │
          └──────────────────┘
```

## Common Tasks Quick Reference

### New Project

```bash
# Create project
copier copy https://github.com/ONEcampaign/repo-templates.git my-project
cd my-project

# Add dependency
uv add requests

# Run tests (packages)
uv run pytest

# Run quality checks
uv run ruff check .
uv run mypy src/
```

### Update Existing Project

```bash
# Update to latest
cd my-project
copier update

# Review and test
git diff
uv run pytest
git commit -m "Update from template"
```

### Adopt in Existing Project (Cherry-pick)

```bash
# Generate template to copy from
cd /tmp
copier copy https://github.com/ONEcampaign/repo-templates.git temp

# Copy what you want
cd /path/to/your-project
cp /tmp/temp/.github/workflows/ci.yml .github/workflows/
cp /tmp/temp/.pre-commit-config.yaml .

# Test and commit
git add .
git commit -m "Add CI and pre-commit from template"
```

## What Should I Use?

### For New Projects

**Always start fresh with the template:**
- ✅ Fastest path to production-ready project
- ✅ All best practices built in
- ✅ Automatic updates available
- ✅ Consistent structure across projects

→ [Getting Started Guide](./getting-started.md)

### For Template-Based Projects

**Update regularly:**
- ✅ Get latest bug fixes and improvements
- ✅ Stay current with Python ecosystem
- ✅ Small, manageable changes
- ✅ 10-minute maintenance

→ [Updating Guide](./updating.md)

### For Existing Projects

**It depends on your situation:**

| Your Situation | Recommended Approach |
|---------------|---------------------|
| Simple project, want continuous updates | Full adoption |
| Complex project, want some features | Cherry-pick |
| Just need CI/CD | Cherry-pick workflows |
| Want to migrate from poetry | Follow migration checklist |
| Have company-mandated tooling | Cherry-pick configs only |

→ [Adopting Guide](./adopting-existing.md)

## Template Philosophy

### Opinionated Choices

This template makes specific choices:

1. **uv over poetry/pipenv**: For speed (10-100x faster)
2. **ruff over black/flake8/pylint**: For speed and simplicity
3. **src-layout over flat**: For better packaging (packages only)
4. **uv_build over setuptools/hatchling**: For integration
5. **Trusted publishing over API tokens**: For security
6. **Pre-commit over manual checks**: For consistency
7. **pytest over unittest**: For features and ecosystem

### Not Opinionated About

You're free to change:

- Testing strategy (TDD, integration tests, etc.)
- Documentation approach (Sphinx, MkDocs, etc.)
- Deployment targets (PyPI, private registry, etc.)
- Code style preferences (within ruff rules)
- Project-specific tooling

### When NOT to Use This Template

❌ Don't use if you:
- Must use specific tools (company policy)
- Need Python < 3.11 support
- Have very unique project structure
- Prefer other build backends (setuptools, poetry-core)

In these cases, cherry-pick what helps and ignore the rest.

## Support and Contributing

### Getting Help

1. **Check the guides** in this directory first
2. **Search issues** in the template repository
3. **Ask questions** by opening a discussion
4. **Report bugs** via issues

### Contributing

Found a bug or have an improvement?

1. Check existing issues/PRs
2. Open an issue to discuss
3. Submit a PR with changes
4. Update documentation

See main CONTRIBUTING.md for details.

## FAQ

### Q: Can I use this without GitHub?

**A:** Yes! Remove `.github/` directory or adapt workflows for GitLab CI, etc.

### Q: Can I change the license?

**A:** Yes. Choose during generation or edit LICENSE file afterward.

### Q: Do I have to use uv?

**A:** For new projects, yes (it's integral). For adoption, you can cherry-pick configs and use your own tools.

### Q: Will updates overwrite my code?

**A:** No! Updates only touch template-managed files (configs, workflows). Your code in `src/` or `scripts/` is safe.

### Q: Can I use this for private packages?

**A:** Yes. Change repository URLs and registry settings in workflows.

### Q: What if I need additional tools?

**A:** Add them! Edit `pyproject.toml`, `.pre-commit-config.yaml`, and workflows as needed.

### Q: How do I add a new dependency?

```bash
# Runtime dependency
uv add package-name

# Development dependency
uv add --dev package-name
```

### Q: How do I change Python version?

Edit `pyproject.toml`:
```toml
requires-python = ">=3.12"
```

Then reinstall:
```bash
uv python install 3.12
uv sync
```

### Q: Can I use conda?

**A:** This template assumes uv for environment management. For conda, you'd need to adapt the workflows and not use `uv venv`.

## Resources

### Template Resources
- [Template Repository](https://github.com/ONEcampaign/repo-templates)
- [Issue Tracker](https://github.com/ONEcampaign/repo-templates/issues)
- [Discussions](https://github.com/ONEcampaign/repo-templates/discussions)

### Tool Documentation
- [uv documentation](https://docs.astral.sh/uv/)
- [Ruff documentation](https://docs.astral.sh/ruff/)
- [Copier documentation](https://copier.readthedocs.io/)
- [pytest documentation](https://docs.pytest.org/)
- [mypy documentation](https://mypy.readthedocs.io/)

### Python Packaging
- [Python Packaging Guide](https://packaging.python.org/)
- [PyPI Trusted Publishing](https://docs.pypi.org/trusted-publishers/)
- [PEP 621 (pyproject.toml metadata)](https://peps.python.org/pep-0621/)

## Next Steps

1. Choose your guide:
   - **New project** → [Getting Started](./getting-started.md)
   - **Update project** → [Updating](./updating.md)
   - **Existing project** → [Adopting](./adopting-existing.md)

2. Follow the guide step-by-step

3. Check out template features in the main README

4. Star the repository if you find it useful! ⭐
