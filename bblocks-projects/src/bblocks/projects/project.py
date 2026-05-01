"""Project analysis and detection utilities."""

import re
import tomllib
from pathlib import Path
from typing import Any, Literal

import yaml
from rich.console import Console

console = Console()

ProjectType = Literal["package", "research", "unknown"]


class Project:
    """Represents a Python project for component installation."""

    def __init__(self, path: Path) -> None:
        """Initialize project analyzer.

        Args:
            path: Path to the project directory
        """
        self.path = path.resolve()
        self.pyproject_path = self.path / "pyproject.toml"
        self._pyproject_data: dict[str, Any] | None = None
        self._copier_answers: dict[str, Any] | None = None

    @property
    def pyproject_data(self) -> dict[str, Any]:
        """Load and cache pyproject.toml data."""
        if self._pyproject_data is None:
            if self.pyproject_path.exists():
                with open(self.pyproject_path, "rb") as f:
                    self._pyproject_data = tomllib.load(f)
            else:
                self._pyproject_data = {}
        return self._pyproject_data

    def reload_pyproject(self) -> None:
        """Drop the cached pyproject.toml so the next access re-reads from disk."""
        self._pyproject_data = None

    def has_pyproject(self) -> bool:
        """Check if project has pyproject.toml."""
        return self.pyproject_path.exists()

    def uses_uv(self) -> bool:
        """Check if project uses uv."""
        return (self.path / "uv.lock").exists()

    def has_src_layout(self) -> bool:
        """Check if project uses src/ layout."""
        return (self.path / "src").is_dir()

    def has_tests(self) -> bool:
        """Check if project has tests/ directory."""
        return (self.path / "tests").is_dir()

    def has_github_workflows(self) -> bool:
        """Check if project has .github/workflows/ directory."""
        return (self.path / ".github" / "workflows").is_dir()

    @property
    def copier_answers(self) -> dict[str, Any]:
        """Load and cache `.copier-answers.yml` as a dict.

        Returns an empty dict when the file is missing, unreadable, malformed,
        or has a non-dict root. Cached for the lifetime of the Project, so
        repeated callers (`detect_type`, `get_github_username`, plus the
        `add` hot-path) only pay one stat + read + parse.
        """
        if self._copier_answers is None:
            try:
                data = yaml.safe_load(
                    (self.path / ".copier-answers.yml").read_text(encoding="utf-8")
                )
            except (OSError, yaml.YAMLError):
                data = None
            self._copier_answers = data if isinstance(data, dict) else {}
        return self._copier_answers

    def detect_type(self) -> ProjectType:
        """Detect project type (package or research).

        Consults .copier-answers.yml first (authoritative for bblocks-managed
        projects). Falls back to filesystem heuristics if the file is missing
        or malformed.
        """
        pt = self.copier_answers.get("project_type")
        if pt in ("package", "research"):
            return pt

        if not self.has_pyproject():
            return "unknown"

        # Check for package indicators
        if self.has_src_layout() or self.has_tests():
            return "package"

        # Check for research indicators
        if (self.path / "scripts").is_dir():
            return "research"

        # Check build system in pyproject.toml
        if "build-system" in self.pyproject_data:
            return "package"

        return "unknown"

    def get_project_name(self) -> str | None:
        """Get project name from pyproject.toml."""
        project_data = self.pyproject_data.get("project", {})
        name = project_data.get("name") if isinstance(project_data, dict) else None
        return name if isinstance(name, str) else None

    def get_project_slug(self) -> str:
        """Get Python-identifier form of project name (hyphens → underscores)."""
        return (self.get_project_name() or "project").replace("-", "_")

    def get_python_version(self) -> str:
        """Get minimum Python version from requires-python (e.g., '3.11')."""
        requires = self.pyproject_data.get("project", {}).get(
            "requires-python", ">=3.11"
        )
        match = re.search(r"(\d+)\.(\d+)", requires)
        return f"{match.group(1)}.{match.group(2)}" if match else "3.11"

    def has_dependency(self, name: str) -> bool:
        """Check if project has a dependency."""
        deps = self.pyproject_data.get("project", {}).get("dependencies", [])
        return any(name in dep for dep in deps)

    def has_dev_dependency(self, name: str) -> bool:
        """Check if project has a dev dependency."""
        dev_deps = self.pyproject_data.get("dependency-groups", {}).get("dev", [])
        return any(name in dep for dep in dev_deps)

    def has_file(self, relative_path: str) -> bool:
        """Check if project has a file at relative path."""
        return (self.path / relative_path).exists()

    def has_config_section(self, section: str) -> bool:
        """Check if pyproject.toml has a config section."""
        parts = section.split(".")
        data = self.pyproject_data
        for part in parts:
            if part not in data:
                return False
            data = data[part]
        return True

    def get_github_username(self) -> str | None:
        """Read `github_username` from the project's .copier-answers.yml."""
        value = self.copier_answers.get("github_username")
        return value if isinstance(value, str) and value else None

    def validate_for_component(self) -> tuple[bool, list[str]]:
        """Validate project is ready for component installation.

        Returns:
            Tuple of (is_valid, list of error messages)
        """
        errors = []

        if not self.has_pyproject():
            errors.append(
                "No pyproject.toml found. This doesn't appear to be a Python project."
            )

        if not self.uses_uv():
            errors.append(
                "No uv.lock found. This tool currently only supports uv projects. "
                "Initialize with 'uv init' first."
            )

        return len(errors) == 0, errors

    def summary(self) -> str:
        """Get a summary of the project."""
        lines = [
            f"Project: {self.get_project_name() or 'Unknown'}",
            f"Path: {self.path}",
            f"Type: {self.detect_type()}",
            f"Uses uv: {'Yes' if self.uses_uv() else 'No'}",
            f"Has pyproject.toml: {'Yes' if self.has_pyproject() else 'No'}",
        ]
        return "\n".join(lines)
