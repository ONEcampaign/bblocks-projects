"""Shared test helpers."""

from pathlib import Path
from typing import Any

from bblocks.projects.components import COMPONENTS_REGISTRY


def make_bblocks_project(
    tmp_path: Path,
    *,
    project_type: str = "package",
    slug: str = "demo",
    python_version: str = "3.11",
    with_components: tuple[str, ...] = (
        "pre-commit",
        "ruff",
        "ci",
        "pytest",
        "pypi-publish",
    ),
    commit: str | None = "abc123def456abc123def456abc123def4567890",
    github_username: str | None = None,
    preset: str | None = None,
    build_backend: str = "uv_build",
    dependencies: tuple[str, ...] = (),
    package_modules: dict[str, str] | None = None,
    workflows: dict[str, str] | None = None,
    ty_configured: bool = True,
) -> Path:
    """Build a synthetic bblocks-managed project at `tmp_path`.

    Default args produce a fully-installed package project that yields zero
    doctor findings — the baseline for healthy-path tests and the starting
    point for drift tests, which mutate one field. The keyword-only
    parameters below (`preset` onward) extend the project for `contract.py`
    tests; all default to values that keep the zero-finding baseline zero.
    """
    name = slug.replace("_", "-")

    pyproject_sections: list[str] = [
        section
        for comp_name in with_components
        if (comp := COMPONENTS_REGISTRY.get(comp_name)) is not None
        for section in comp.pyproject_sections
    ]
    dev_deps: list[str] = [
        f'"{dep}"'
        for comp_name in with_components
        if (comp := COMPONENTS_REGISTRY.get(comp_name)) is not None
        for dep in comp.dev_deps
    ]
    if ty_configured:
        pyproject_sections.append("tool.ty.src")
        dev_deps.append('"ty>=0.0.59"')

    # build-system is already in the base template below; skip to avoid duplicate header.
    # tool.ty.src needs a real `include` value, not an empty table.
    section_toml_parts = [
        (
            f'[{section}]\ninclude = ["src/{slug}"]\n'
            if section == "tool.ty.src"
            else f"[{section}]\n"
        )
        for section in pyproject_sections
        if section != "build-system"
    ]

    dev_deps_toml = ", ".join(dev_deps) if dev_deps else ""
    deps_toml = ", ".join(f'"{d}"' for d in dependencies)
    pyproject_content = (
        f'[project]\nname = "{name}"\n'
        f'requires-python = ">={python_version}"\n'
        f"dependencies = [{deps_toml}]\n\n"
        f'[build-system]\nrequires = ["uv_build"]\nbuild-backend = "{build_backend}"\n\n'
        f"[dependency-groups]\ndev = [{dev_deps_toml}]\n\n"
        + "".join(section_toml_parts)
    )
    (tmp_path / "pyproject.toml").write_text(pyproject_content, encoding="utf-8")

    answers_lines = [
        f"project_type: {project_type}",
        f"project_name: {name}",
        f"project_slug: {slug}",
        f"python_version: '{python_version}'",
    ]
    if preset is not None:
        answers_lines.append(f"preset: {preset}")
    if github_username is not None:
        answers_lines.append(f"github_username: {github_username}")
    if commit is not None:
        answers_lines.append(f"_commit: {commit}")
    (tmp_path / ".copier-answers.yml").write_text(
        "\n".join(answers_lines) + "\n", encoding="utf-8"
    )

    (tmp_path / "src" / slug).mkdir(parents=True, exist_ok=True)
    if project_type in ("project", "research"):
        (tmp_path / "data" / "raw").mkdir(parents=True, exist_ok=True)
        (tmp_path / "data" / "processed").mkdir(parents=True, exist_ok=True)

    for comp_name in with_components:
        if comp_name == "pre-commit":
            (tmp_path / ".pre-commit-config.yaml").touch()
        elif comp_name == "ci":
            (tmp_path / ".github" / "workflows").mkdir(parents=True, exist_ok=True)
            (tmp_path / ".github" / "workflows" / "ci.yml").touch()
        elif comp_name == "pypi-publish":
            (tmp_path / ".github" / "workflows").mkdir(parents=True, exist_ok=True)
            (tmp_path / ".github" / "workflows" / "release.yml").touch()

    if package_modules is not None:
        pkg_dir = tmp_path / "src" / slug
        if "__init__.py" not in package_modules:
            (pkg_dir / "__init__.py").touch()
        for relpath, text in package_modules.items():
            module_path = pkg_dir / relpath
            module_path.parent.mkdir(parents=True, exist_ok=True)
            module_path.write_text(text, encoding="utf-8")

    if workflows is not None:
        workflows_dir = tmp_path / ".github" / "workflows"
        workflows_dir.mkdir(parents=True, exist_ok=True)
        for filename, text in workflows.items():
            (workflows_dir / filename).write_text(text, encoding="utf-8")

    return tmp_path


def _family_init_py(slug: str) -> str:
    """A readerkit-shaped `__init__.py` that also owns items 7a/7b/7c honestly.

    `readerkit` in dependencies is itself a cache indicator (see
    `_source_scan._CACHE_DEP_NAMES`), so declaring it opens item 7's gate —
    "does this package cache" — without exposing any of the redirect/env-
    var/disable surface item 7 actually checks for. A `__init__.py` that
    only imports `build_session` satisfies item 6 but then fails 7a and 7b
    on an otherwise-clean fixture. `set_cache_dir` and `disable_cache`
    satisfy 7a and 7c by name; the `<SLUG>_CACHE_DIR` literal satisfies 7b.
    """
    env_var = f"{slug.upper()}_CACHE_DIR"
    return (
        "from readerkit import build_session\n\n"
        f'{env_var} = "{env_var}"\n\n\n'
        "def set_cache_dir(path):\n"
        '    """Redirect the on-disk cache to `path`."""\n\n\n'
        "def disable_cache():\n"
        '    """Turn caching off entirely."""\n\n\n'
        "__all__ = ['build_session', 'set_cache_dir', 'disable_cache']\n"
    )


def make_family_project(tmp_path: Path, **kwargs: Any) -> Path:
    """Build a family-preset project clean enough to pass every implemented item.

    Wraps `make_bblocks_project` with `preset="family"`, a Python 3.12
    floor, uncapped runtime dependencies, a readerkit-shaped `__init__.py`
    that also honestly satisfies the cache contract (items 7a-7c — see
    `_family_init_py`), and an OIDC-clean release workflow. This is the
    fixture the pass-path contract tests assert against; callers override
    one field at a time (via `kwargs`) to produce a single finding.
    """
    kwargs.setdefault("preset", "family")
    kwargs.setdefault("python_version", "3.12")
    kwargs.setdefault("dependencies", ("readerkit>=0.1.0", "httpx>=0.27"))
    kwargs.setdefault(
        "package_modules",
        {"__init__.py": _family_init_py(str(kwargs.get("slug", "demo")))},
    )
    kwargs.setdefault(
        "workflows",
        {
            "release.yml": (
                "name: Release\n"
                "on:\n"
                "  push:\n"
                "    tags: ['v*']\n"
                "permissions:\n"
                "  id-token: write\n"
                "jobs:\n"
                "  publish:\n"
                "    runs-on: ubuntu-latest\n"
                "    steps:\n"
                "      - run: uv build\n"
                "      - run: uv publish\n"
            )
        },
    )
    return make_bblocks_project(tmp_path, **kwargs)
