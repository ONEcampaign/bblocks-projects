"""Component definitions for template features."""

from dataclasses import dataclass, field
from typing import Literal


@dataclass(frozen=True)
class ComponentDef:
    """Declarative definition of an installable template component."""

    name: str
    description: str
    template_files: list[str] = field(default_factory=list)
    pyproject_sections: list[str] = field(default_factory=list)
    dev_deps: list[str] = field(default_factory=list)
    post_install_steps: list[str] = field(default_factory=list)
    requires_project_type: Literal["package", "research"] | None = None


COMPONENTS_REGISTRY: dict[str, ComponentDef] = {
    "pre-commit": ComponentDef(
        name="pre-commit",
        description="Pre-commit hooks with ruff and ty",
        template_files=[".pre-commit-config.yaml.jinja"],
        dev_deps=["pre-commit>=3.0.0"],
        post_install_steps=[
            "Run: uv sync",
            "Run: uv run pre-commit install",
            "Test: uv run pre-commit run --all-files",
        ],
    ),
    "ruff": ComponentDef(
        name="ruff",
        description="Ruff linter and formatter with comprehensive rules",
        pyproject_sections=[
            "tool.ruff",
            "tool.ruff.lint",
            "tool.ruff.lint.pydocstyle",
            "tool.ruff.lint.per-file-ignores",
            "tool.ruff.format",
        ],
        dev_deps=["ruff>=0.8.0"],
        post_install_steps=[
            "Run: uv sync",
            "Check code: uv run ruff check .",
            "Format code: uv run ruff format .",
            "Fix issues: uv run ruff check --fix .",
        ],
    ),
    "ci": ComponentDef(
        name="ci",
        description="GitHub Actions CI workflow",
        template_files=[".github/workflows/ci.yml.jinja"],
        post_install_steps=[
            "Commit .github/workflows/ci.yml to git",
            "Push to GitHub to trigger first CI run",
            "Check the Actions tab in your GitHub repo",
            "Consider adding a status badge to your README",
        ],
    ),
    "pytest": ComponentDef(
        name="pytest",
        description="Pytest with coverage reporting",
        pyproject_sections=[
            "tool.pytest.ini_options",
            "tool.coverage.run",
            "tool.coverage.report",
        ],
        dev_deps=["pytest>=8.0.0", "pytest-cov>=4.1.0"],
        post_install_steps=[
            "Run: uv sync",
            "Run tests: uv run pytest",
            "View coverage: uv run pytest --cov",
        ],
        requires_project_type=None,
    ),
    "pypi-publish": ComponentDef(
        name="pypi-publish",
        description="GitHub Actions workflow for PyPI publishing",
        template_files=[".github/workflows/release.yml.jinja"],
        pyproject_sections=["build-system"],
        post_install_steps=[
            "Register project on PyPI: https://pypi.org/manage/projects/",
            "Set up PyPI trusted publishing in project settings",
            "Add GitHub as trusted publisher: {github_username}/<your-repo>",
            "Specify workflow: release.yml",
            "Create a tag to publish: git tag v0.1.0 && git push origin v0.1.0",
        ],
        requires_project_type="package",
    ),
}


def get_component(name: str) -> ComponentDef | None:
    """Get a component by name.

    Args:
        name: Component name

    Returns:
        ComponentDef instance or None if not found
    """
    return COMPONENTS_REGISTRY.get(name)


def list_components() -> list[ComponentDef]:
    """Get list of all available components.

    Returns:
        List of ComponentDef instances
    """
    return list(COMPONENTS_REGISTRY.values())
