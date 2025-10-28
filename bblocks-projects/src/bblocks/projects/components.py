"""Component definitions for template features."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from rich.console import Console

from bblocks.projects.project import Project

console = Console()


@dataclass
class ComponentFile:
    """Represents a file to be installed by a component."""

    source_template: str  # Template content
    destination: str  # Relative path in target project
    create_dirs: bool = True  # Create parent directories if needed


class Component(ABC):
    """Base class for installable template components."""

    def __init__(self) -> None:
        """Initialize component."""
        self.name = ""
        self.description = ""

    @abstractmethod
    def get_files(self, project: Project) -> list[ComponentFile]:
        """Get list of files to install.

        Args:
            project: Target project

        Returns:
            List of files to install
        """

    @abstractmethod
    def get_config_updates(self, project: Project) -> dict[str, Any]:
        """Get pyproject.toml configuration updates.

        Args:
            project: Target project

        Returns:
            Dictionary of config sections to merge
        """

    @abstractmethod
    def get_dependencies(self, project: Project) -> list[str]:
        """Get runtime dependencies to add.

        Args:
            project: Target project

        Returns:
            List of package specifications
        """

    @abstractmethod
    def get_dev_dependencies(self, project: Project) -> list[str]:
        """Get dev dependencies to add.

        Args:
            project: Target project

        Returns:
            List of package specifications
        """

    @abstractmethod
    def get_post_install_steps(self, project: Project) -> list[str]:
        """Get commands to run after installation.

        Args:
            project: Target project

        Returns:
            List of human-readable instructions
        """

    def can_install(self, project: Project) -> tuple[bool, str]:
        """Check if component can be installed.

        Args:
            project: Target project

        Returns:
            Tuple of (can_install, reason)
        """
        return True, ""

    def get_conflicts(self, project: Project) -> list[str]:
        """Get list of conflicting files/configs.

        Args:
            project: Target project

        Returns:
            List of conflict descriptions
        """
        conflicts = []
        for file in self.get_files(project):
            if project.has_file(file.destination):
                conflicts.append(f"File exists: {file.destination}")

        for section in self.get_config_updates(project):
            if project.has_config_section(section):
                conflicts.append(f"Config section exists: {section}")

        return conflicts


class PreCommitComponent(Component):
    """Pre-commit hooks configuration."""

    def __init__(self) -> None:
        """Initialize pre-commit component."""
        super().__init__()
        self.name = "pre-commit"
        self.description = "Pre-commit hooks with ruff and mypy"

    def get_files(self, project: Project) -> list[ComponentFile]:
        """Get pre-commit config file."""
        template = """repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
      - id: check-merge-conflict

  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.3.0
    hooks:
      - id: ruff
        args: [--fix, --exit-non-zero-on-fix]
      - id: ruff-format

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.8.0
    hooks:
      - id: mypy
        additional_dependencies: []
"""
        return [
            ComponentFile(
                source_template=template,
                destination=".pre-commit-config.yaml",
            )
        ]

    def get_config_updates(self, project: Project) -> dict[str, Any]:
        """No pyproject.toml updates needed."""
        return {}

    def get_dependencies(self, project: Project) -> list[str]:
        """No runtime dependencies."""
        return []

    def get_dev_dependencies(self, project: Project) -> list[str]:
        """Add pre-commit as dev dependency."""
        return ["pre-commit>=3.0.0"]

    def get_post_install_steps(self, project: Project) -> list[str]:
        """Return installation steps."""
        return [
            "Run: uv sync",
            "Run: uv run pre-commit install",
            "Test: uv run pre-commit run --all-files",
        ]


class RuffComponent(Component):
    """Ruff linter and formatter configuration."""

    def __init__(self) -> None:
        """Initialize ruff component."""
        super().__init__()
        self.name = "ruff"
        self.description = "Ruff linter and formatter with comprehensive rules"

    def get_files(self, project: Project) -> list[ComponentFile]:
        """No files to install (config in pyproject.toml)."""
        return []

    def get_config_updates(self, project: Project) -> dict[str, Any]:
        """Get ruff configuration."""
        python_version = project.pyproject_data.get("project", {}).get(
            "requires-python", ">=3.11"
        )
        # Extract version number (e.g., ">=3.11" -> "311")
        py_version = python_version.replace(">=", "").replace(".", "")

        return {
            "tool.ruff": {
                "line-length": 88,
                "target-version": f"py{py_version}",
            },
            "tool.ruff.lint": {
                "select": ["ALL"],
                "ignore": [
                    "COM812",  # conflicts with formatter
                    "ISC001",  # conflicts with formatter
                ],
            },
            "tool.ruff.lint.pydocstyle": {
                "convention": "google",
            },
        }

    def get_dependencies(self, project: Project) -> list[str]:
        """No runtime dependencies."""
        return []

    def get_dev_dependencies(self, project: Project) -> list[str]:
        """Add ruff as dev dependency."""
        return ["ruff>=0.3.0"]

    def get_post_install_steps(self, project: Project) -> list[str]:
        """Return usage steps."""
        return [
            "Run: uv sync",
            "Check code: uv run ruff check .",
            "Format code: uv run ruff format .",
            "Fix issues: uv run ruff check --fix .",
        ]


class CIComponent(Component):
    """GitHub Actions CI workflow."""

    def __init__(self) -> None:
        """Initialize CI component."""
        super().__init__()
        self.name = "ci"
        self.description = "GitHub Actions CI workflow"

    def get_files(self, project: Project) -> list[ComponentFile]:
        """Get CI workflow file."""
        project_type = project.detect_type()
        project_name = project.get_project_name() or "project"

        # Build test command based on project type
        if project_type == "package":
            test_cmd = "uv run pytest"
            lint_paths = f"src/{project_name.replace('-', '_')} tests"
        else:
            test_cmd = "echo 'No tests configured'"
            lint_paths = "scripts"

        template = f"""name: CI

on:
  push:
    branches: [main]
  pull_request:

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ['3.11', '3.12', '3.13']

    steps:
      - uses: actions/checkout@v4

      - name: Install uv
        uses: astral-sh/setup-uv@v5
        with:
          enable-cache: true

      - name: Set up Python ${{{{ matrix.python-version }}}}
        uses: actions/setup-python@v5
        with:
          python-version: ${{{{ matrix.python-version }}}}

      - name: Install dependencies
        run: uv sync --all-extras --dev

      - name: Run tests
        run: {test_cmd}

      - name: Run linting
        run: uv run ruff check {lint_paths}

      - name: Run type checking
        run: uv run mypy {lint_paths}
"""
        return [
            ComponentFile(
                source_template=template,
                destination=".github/workflows/ci.yml",
            )
        ]

    def get_config_updates(self, project: Project) -> dict[str, Any]:
        """No pyproject.toml updates needed."""
        return {}

    def get_dependencies(self, project: Project) -> list[str]:
        """No runtime dependencies."""
        return []

    def get_dev_dependencies(self, project: Project) -> list[str]:
        """No dev dependencies (assumes ruff/mypy already added)."""
        return []

    def get_post_install_steps(self, project: Project) -> list[str]:
        """Return next steps."""
        return [
            "Commit .github/workflows/ci.yml to git",
            "Push to GitHub to trigger first CI run",
            "Check the Actions tab in your GitHub repo",
            "Consider adding a status badge to your README",
        ]


class PytestComponent(Component):
    """Pytest testing framework configuration."""

    def __init__(self) -> None:
        """Initialize pytest component."""
        super().__init__()
        self.name = "pytest"
        self.description = "Pytest with coverage reporting"

    def can_install(self, project: Project) -> tuple[bool, str]:
        """Check if this is a package project."""
        if project.detect_type() != "package":
            return False, "pytest component is only for package projects"
        return True, ""

    def get_files(self, project: Project) -> list[ComponentFile]:
        """No files (config in pyproject.toml)."""
        return []

    def get_config_updates(self, project: Project) -> dict[str, Any]:
        """Get pytest and coverage configuration."""
        project_name = project.get_project_name() or "project"
        package_name = project_name.replace("-", "_")

        return {
            "tool.pytest.ini_options": {
                "testpaths": ["tests"],
                "python_files": ["test_*.py"],
                "addopts": (
                    f"-v --cov=src/{package_name} --cov-report=term "
                    "--cov-report=xml"
                ),
            },
            "tool.coverage.run": {
                "source": ["src"],
                "branch": True,
                "omit": [
                    "*/tests/*",
                    "*/__pycache__/*",
                ],
            },
            "tool.coverage.report": {
                "exclude_lines": [
                    "pragma: no cover",
                    "def __repr__",
                    "def __str__",
                    "raise AssertionError",
                    "raise NotImplementedError",
                    "if __name__ == .__main__.:",
                    "if TYPE_CHECKING:",
                ],
                "show_missing": True,
                "precision": 2,
            },
        }

    def get_dependencies(self, project: Project) -> list[str]:
        """No runtime dependencies."""
        return []

    def get_dev_dependencies(self, project: Project) -> list[str]:
        """Add pytest and coverage."""
        return ["pytest>=8.0.0", "pytest-cov>=4.1.0"]

    def get_post_install_steps(self, project: Project) -> list[str]:
        """Return testing steps."""
        return [
            "Run: uv sync",
            "Run tests: uv run pytest",
            "View coverage: uv run pytest --cov",
        ]


class PyPIPublishComponent(Component):
    """PyPI publishing workflow with trusted publishing."""

    def __init__(self) -> None:
        """Initialize PyPI publish component."""
        super().__init__()
        self.name = "pypi-publish"
        self.description = "GitHub Actions workflow for PyPI publishing"

    def can_install(self, project: Project) -> tuple[bool, str]:
        """Check if this is a package project."""
        if project.detect_type() != "package":
            return False, "pypi-publish component is only for package projects"
        return True, ""

    def get_files(self, project: Project) -> list[ComponentFile]:
        """Get release workflow file."""
        template = """name: Publish to PyPI

on:
  push:
    tags:
      - 'v*'
  workflow_dispatch:

jobs:
  publish:
    runs-on: ubuntu-latest
    permissions:
      id-token: write  # Required for PyPI trusted publishing
      contents: read

    steps:
      - uses: actions/checkout@v4

      - name: Install uv
        uses: astral-sh/setup-uv@v5
        with:
          enable-cache: true

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Build package
        run: uv build

      - name: Publish to PyPI
        uses: pypa/gh-action-pypi-publish@release/v1
"""
        return [
            ComponentFile(
                source_template=template,
                destination=".github/workflows/release.yml",
            )
        ]

    def get_config_updates(self, project: Project) -> dict[str, Any]:
        """Check if build-system is configured."""
        if not project.has_config_section("build-system"):
            return {
                "build-system": {
                    "requires": ["hatchling"],
                    "build-backend": "hatchling.build",
                }
            }
        return {}

    def get_dependencies(self, project: Project) -> list[str]:
        """No runtime dependencies."""
        return []

    def get_dev_dependencies(self, project: Project) -> list[str]:
        """No dev dependencies."""
        return []

    def get_post_install_steps(self, project: Project) -> list[str]:
        """Return publishing setup steps."""
        return [
            "Register project on PyPI: https://pypi.org/manage/projects/",
            "Set up PyPI trusted publishing in project settings",
            "Add GitHub as trusted publisher: ONEcampaign/<your-repo>",
            "Specify workflow: release.yml",
            "Create a tag to publish: git tag v0.1.0 && git push origin v0.1.0",
        ]


# Registry of all available components
COMPONENTS: dict[str, type[Component]] = {
    "pre-commit": PreCommitComponent,
    "ruff": RuffComponent,
    "ci": CIComponent,
    "pytest": PytestComponent,
    "pypi-publish": PyPIPublishComponent,
}


def get_component(name: str) -> Component | None:
    """Get a component by name.

    Args:
        name: Component name

    Returns:
        Component instance or None if not found
    """
    component_class = COMPONENTS.get(name)
    if component_class:
        return component_class()
    return None


def list_components() -> list[Component]:
    """Get list of all available components.

    Returns:
        List of component instances
    """
    return [cls() for cls in COMPONENTS.values()]
