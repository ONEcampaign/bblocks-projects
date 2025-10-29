# PyPI Trusted Publishing Setup

This guide explains how to set up PyPI trusted publishing for automated releases.

## What is Trusted Publishing?

Trusted publishing uses OpenID Connect (OIDC) to authenticate GitHub Actions to PyPI without requiring API tokens. It's more secure and easier to manage.

## Prerequisites

- A GitHub repository with your package
- A PyPI account

## First-Time Setup

### 1. Create PyPI Project (First Release)

For the first release, you need to manually upload to create the project:

```bash
# Bump version (choose one)
uv version 0.1.0                    # Set specific version
# OR
vi pyproject.toml                   # Edit manually

# Commit version change
git add pyproject.toml
git commit -m "chore: bump version to 0.1.0"

# Create version tag
git tag v0.1.0
git push origin main --tags

# Build locally
uv build

# Upload to PyPI (requires PyPI account)
uv publish
```

### 2. Configure Trusted Publishing

After the first release, set up trusted publishing on PyPI:

1. Go to https://pypi.org/manage/project/YOUR-PROJECT/settings/publishing/
2. Click "Add a new publisher"
3. Fill in the form:
   - **Owner**: your-github-username or org-name
   - **Repository name**: your-repo-name
   - **Workflow name**: release.yml
   - **Environment name**: pypi
4. Click "Add"

### 3. Configure GitHub Environment

In your GitHub repository:

1. Go to Settings → Environments
2. Create environment named `pypi`
3. (Optional) Add protection rules:
   - Required reviewers
   - Restrict to main branch

### 4. Future Releases (Automated)

After setup, releases are automatic:

```bash
# 1. Update version (choose one method)
uv version --bump patch              # Bump patch: 0.1.0 → 0.1.1
uv version --bump minor              # Bump minor: 0.1.0 → 0.2.0
uv version --bump major              # Bump major: 0.1.0 → 1.0.0
uv version 1.2.3                     # Set specific version

# OR edit manually
vi pyproject.toml

# 2. Commit changes
git add pyproject.toml
git commit -m "chore: bump version to 1.2.3"

# 3. Create and push tag
git tag v1.2.3
git push origin main --tags

# GitHub Actions automatically builds and publishes!
```

## Version Bumping Strategies

### Using uv version (Recommended)

```bash
# Preview change
uv version --bump patch --dry-run

# Apply change
uv version --bump patch
```

### Manual Editing

Edit `pyproject.toml`:
```toml
[project]
version = "1.2.3"  # Update this
```

## Semantic Versioning

Follow [semver](https://semver.org/):

- **MAJOR** (1.0.0 → 2.0.0): Breaking changes
- **MINOR** (1.0.0 → 1.1.0): New features (backward compatible)
- **PATCH** (1.0.0 → 1.0.1): Bug fixes (backward compatible)

## Troubleshooting

### "No trusted publisher configured"

- Verify environment name matches: `pypi`
- Check workflow name: `release.yml`
- Ensure repository and owner are correct

### "Permission denied"

- Verify `id-token: write` permission in workflow
- Check GitHub environment protection rules

### "Version already exists"

- You can't re-upload the same version
- Bump version and try again

## Additional Resources

- [PyPI Trusted Publishing Guide](https://docs.pypi.org/trusted-publishers/)
- [GitHub Actions OIDC](https://docs.github.com/en/actions/deployment/security-hardening-your-deployments/about-security-hardening-with-openid-connect)
- [uv publish docs](https://docs.astral.sh/uv/guides/publish/)
