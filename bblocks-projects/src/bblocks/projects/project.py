"""Project analysis and detection utilities."""

import re
import subprocess
import tomllib
from functools import cached_property
from pathlib import Path
from typing import Any, Literal

import yaml
from rich.console import Console

console = Console()

ProjectType = Literal["package", "project", "unknown"]

# Legacy values that resolve to a current ProjectType. The template was
# renamed from `research` to `project` (the broader name better fits
# analysis, pipelines, and internal tooling) but old projects still have
# `project_type: research` in their .copier-answers.yml. Normalize on read.
_PROJECT_TYPE_ALIASES: dict[str, ProjectType] = {"research": "project"}

# Top-level names that git tooling reads from the work-tree root, wherever
# pyproject.toml sits: pre-commit loads `.pre-commit-config.yaml` from the
# root, and GitHub runs only the workflows under the root's `.github/`.
_REPO_LEVEL_NAMES = frozenset({".pre-commit-config.yaml", ".github"})


def is_repo_level(relative_path: str) -> bool:
    """Whether git tooling reads `relative_path` from the git work-tree root."""
    return Path(relative_path).parts[0] in _REPO_LEVEL_NAMES


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

    @cached_property
    def repo_root(self) -> Path:
        """Get the root of the git work tree that contains the project.

        The nearest directory, the project's own included, holding a `.git`
        entry (a directory, or a file in a linked worktree or submodule).
        Falls back to the project directory outside a git work tree, so a
        package in `python/` of a multi-language repo resolves to the repo
        root and a standalone package resolves to itself.
        """
        for candidate in (self.path, *self.path.parents):
            if (candidate / ".git").exists():
                return candidate
        return self.path

    @property
    def below_repo_root(self) -> bool:
        """Whether the project directory sits below the root of its git work tree."""
        return self.repo_root != self.path

    def tooling_path(self, relative_path: str) -> Path:
        """Get where git tooling reads `relative_path` from.

        `.pre-commit-config.yaml` and anything under `.github/` resolve
        against `repo_root`. Every other path resolves against the project
        directory.
        """
        base = self.repo_root if is_repo_level(relative_path) else self.path
        return base / relative_path

    def has_github_workflows(self) -> bool:
        """Check if the repo has a .github/workflows/ directory."""
        return self.tooling_path(".github/workflows").is_dir()

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
        """Detect project type (package or project).

        Consults .copier-answers.yml first (authoritative for bblocks-managed
        projects). Falls back to filesystem heuristics if the file is missing
        or malformed. Legacy `research` answers normalize to `project`.
        """
        pt = self.copier_answers.get("project_type")
        if isinstance(pt, str):
            pt = _PROJECT_TYPE_ALIASES.get(pt, pt)
            if pt in ("package", "project"):
                return pt

        if not self.has_pyproject():
            return "unknown"

        # Strongest layout markers: tests/ ⇒ package; data/ ⇒ project.
        if self.has_tests():
            return "package"
        if (self.path / "data").is_dir():
            return "project"

        # Fallback: src/ or [build-system] without disambiguating dirs leans
        # package (the historical default).
        if self.has_src_layout() or "build-system" in self.pyproject_data:
            return "package"

        return "unknown"

    def get_project_name(self) -> str | None:
        """Get project name from pyproject.toml."""
        project_data = self.pyproject_data.get("project", {})
        name = project_data.get("name") if isinstance(project_data, dict) else None
        return name if isinstance(name, str) else None

    def get_module_name(self) -> str | None:
        """Get `[tool.uv.build-backend].module-name`, or None when unset."""
        module = (
            self.pyproject_data.get("tool", {})
            .get("uv", {})
            .get("build-backend", {})
            .get("module-name")
        )
        return module if isinstance(module, str) else None

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

    def get_requires_python(self) -> str | None:
        """Get the raw `requires-python` string, or None when unset.

        Unlike `get_python_version()`, this does not default to "3.11" —
        callers that need to know whether the field is genuinely absent
        (the family contract's Python-floor check) want the raw value.
        """
        requires = self.pyproject_data.get("project", {}).get("requires-python")
        return requires if isinstance(requires, str) else None

    def get_build_backend(self) -> str | None:
        """Get `[build-system].build-backend`, or None when unset."""
        backend = self.pyproject_data.get("build-system", {}).get("build-backend")
        return backend if isinstance(backend, str) else None

    def get_preset(self) -> str | None:
        """Get the `preset` answer from `.copier-answers.yml` ("family" or "standalone")."""
        value = self.copier_answers.get("preset")
        return value if isinstance(value, str) else None

    def has_dependency(self, name: str) -> bool:
        """Check if project has a dependency."""
        deps = self.pyproject_data.get("project", {}).get("dependencies", [])
        return any(name in dep for dep in deps)

    def has_dev_dependency(self, name: str) -> bool:
        """Check if project has a dev dependency.

        Reads PEP-735 `dependency-groups.dev` first, then falls back to the
        older `project.optional-dependencies.dev` location used by pre-PEP-735
        uv projects.
        """
        pep735 = self.pyproject_data.get("dependency-groups", {}).get("dev", [])
        if any(name in dep for dep in pep735):
            return True
        legacy = (
            self.pyproject_data.get("project", {})
            .get("optional-dependencies", {})
            .get("dev", [])
        )
        return any(name in dep for dep in legacy)

    def has_config_section(self, section: str) -> bool:
        """Check if pyproject.toml has a config section."""
        parts = section.split(".")
        data = self.pyproject_data
        for part in parts:
            if part not in data:
                return False
            data = data[part]
        return True

    def iter_runtime_dependencies(self) -> list[str]:
        """Get every runtime dependency spec.

        `[project].dependencies` plus every list under
        `[project].optional-dependencies` except `dev` — `dev` is the
        pre-PEP-735 location for dev tooling (see `has_dev_dependency`),
        not a runtime extra a consumer resolves against. `[dependency-groups]`
        is dev-only by construction and is deliberately excluded too.
        """
        project_data = self.pyproject_data.get("project", {})
        deps: list[str] = [
            d for d in project_data.get("dependencies", []) if isinstance(d, str)
        ]
        optional = project_data.get("optional-dependencies", {})
        if isinstance(optional, dict):
            for group_name, group in optional.items():
                if group_name == "dev" or not isinstance(group, list):
                    continue
                deps.extend(d for d in group if isinstance(d, str))
        return deps

    def package_roots(self) -> list[Path]:
        """Get every genuine package directory under `src/`.

        Walks the tree under `src/` breadth-first — each level sorted by
        name, `__pycache__` excluded — collecting every directory that
        has an `__init__.py`. A directory without one is treated as a
        namespace-package layer and its children are queued for the same
        search, so a non-package sibling that sorts first (`_vendor/`,
        `_data/`, an empty `assets/`) gets skipped instead of aborting
        the whole search. Once a directory IS a package, its children
        are not queued — a subpackage belongs to its parent, it is not a
        sibling root to discover separately.

        A flat multi-package `src/` (`src/alpha_pkg/`, `src/zeta_pkg/`)
        is real: several repos on this machine ship this shape, and
        every one of those packages is a distinct root a caller like
        `_source_scan` needs to inspect — a clean `alpha_pkg` must not
        hide a violation living in `zeta_pkg`.

        A directory that can't be listed (permission error, or it
        disappears mid-walk) is skipped rather than aborting the whole
        search, mirroring `read_workflows`. Any packages under it are
        invisible to this scan — a known gap, not a crash.

        Returns an empty list when there is no `src/` layout, or no
        package is found anywhere under it.
        """
        src = self.path / "src"
        if not src.is_dir():
            return []
        roots: list[Path] = []
        queue: list[Path] = [src]
        while queue:
            current = queue.pop(0)
            try:
                entries = list(current.iterdir())
            except OSError:
                continue
            subdirs = sorted(
                (
                    d
                    for d in entries
                    if d.is_dir()
                    and not d.name.startswith(".")
                    and d.name != "__pycache__"
                ),
                key=lambda d: d.name,
            )
            for d in subdirs:
                if (d / "__init__.py").is_file():
                    roots.append(d)
                else:
                    queue.append(d)
        return roots

    def package_root(self) -> Path | None:
        """Get the first genuine package directory under `src/`.

        A thin convenience wrapper over `package_roots()` for callers that
        only care whether a package exists at all. When `src/` holds more
        than one genuine package (a flat multi-package layout), this
        returns the first one found in `package_roots()`'s breadth-first,
        alphabetical order: deterministic, but arbitrary among equals.
        Callers that need every package under `src/` — `_source_scan`'s
        `scan_package` and `public_surface` among them — use
        `package_roots()` directly instead.

        Returns None when there is no `src/` layout, or no package is
        found anywhere under it.
        """
        roots = self.package_roots()
        return roots[0] if roots else None

    def read_workflows(self) -> dict[str, str]:
        """Get every GitHub Actions workflow as raw text, filename -> text.

        Globs `.github/workflows/*.yml` and `*.yaml` under `repo_root`, the
        only workflows GitHub runs. Unreadable files are skipped rather than
        raising.
        """
        workflows_dir = self.tooling_path(".github/workflows")
        if not workflows_dir.is_dir():
            return {}
        result: dict[str, str] = {}
        for pattern in ("*.yml", "*.yaml"):
            for file in sorted(workflows_dir.glob(pattern)):
                try:
                    result[file.name] = file.read_text(encoding="utf-8")
                except OSError:
                    continue
        return result

    def get_git_remote_slug(self) -> str | None:
        """Get `owner/repo` from the `origin` remote, or None when unavailable."""
        try:
            result = subprocess.run(
                ["git", "-C", str(self.path), "remote", "get-url", "origin"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return None
        if result.returncode != 0:
            return None
        match = re.search(
            r"github\.com[:/ ]([^/\s]+)/([^/\s]+?)(?:\.git)?/?$", result.stdout.strip()
        )
        if not match:
            return None
        return f"{match.group(1)}/{match.group(2)}"

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
