"""Shared test helpers."""

from pathlib import Path

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
) -> Path:
    """Build a synthetic bblocks-managed project at `tmp_path`.

    Default args produce a fully-installed package project that yields zero
    doctor findings — the baseline for healthy-path tests and the starting
    point for drift tests, which mutate one field.
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

    # build-system is already in the base template below; skip to avoid duplicate header.
    section_toml_parts = [
        f"[{section}]\n" for section in pyproject_sections if section != "build-system"
    ]

    dev_deps_toml = ", ".join(dev_deps) if dev_deps else ""
    pyproject_content = (
        f'[project]\nname = "{name}"\nrequires-python = ">={python_version}"\n\n'
        f'[build-system]\nrequires = ["uv_build"]\nbuild-backend = "uv_build"\n\n'
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
    if github_username is not None:
        answers_lines.append(f"github_username: {github_username}")
    if commit is not None:
        answers_lines.append(f"_commit: {commit}")
    (tmp_path / ".copier-answers.yml").write_text(
        "\n".join(answers_lines) + "\n", encoding="utf-8"
    )

    (tmp_path / "src" / slug).mkdir(parents=True, exist_ok=True)
    if project_type == "research":
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

    return tmp_path
