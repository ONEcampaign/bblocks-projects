"""Tests for project type detection."""

from pathlib import Path

import pytest

from bblocks.projects.project import Project


@pytest.fixture
def project_with_src(tmp_path: Path) -> Path:
    """A minimal project with pyproject.toml and a src/ dir.

    The src/ dir means the filesystem heuristic would classify this as
    "package" — useful for tests that need to verify .copier-answers.yml
    overrides the heuristic, or that fall-through to it works.
    """
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "demo"\n', encoding="utf-8"
    )
    (tmp_path / "src").mkdir()
    return tmp_path


def _write_answers(project: Path, contents: str) -> None:
    """Write `contents` to .copier-answers.yml at the project root."""
    (project / ".copier-answers.yml").write_text(contents, encoding="utf-8")


def test_detect_type_reads_copier_answers_project(project_with_src: Path) -> None:
    """detect_type() reads project_type from .copier-answers.yml first."""
    _write_answers(project_with_src, "project_type: project\nproject_name: demo\n")
    assert Project(project_with_src).detect_type() == "project"


def test_detect_type_normalizes_legacy_research_to_project(
    project_with_src: Path,
) -> None:
    """Legacy `project_type: research` normalizes to `project` on read (BC)."""
    _write_answers(project_with_src, "project_type: research\nproject_name: demo\n")
    assert Project(project_with_src).detect_type() == "project"


def test_detect_type_reads_copier_answers_package(tmp_path: Path) -> None:
    """detect_type() reads project_type=package from .copier-answers.yml."""
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "demo"\n', encoding="utf-8"
    )
    _write_answers(tmp_path, "project_type: package\nproject_name: demo\n")
    assert Project(tmp_path).detect_type() == "package"


def test_detect_type_falls_back_to_heuristic_when_no_answers(
    project_with_src: Path,
) -> None:
    """When .copier-answers.yml is missing, the heuristic still works.

    A project with src/ but no .copier-answers.yml is classified as "package"
    via the existing has_src_layout heuristic.
    """
    assert Project(project_with_src).detect_type() == "package"


def test_detect_type_falls_back_when_answers_malformed(
    project_with_src: Path,
) -> None:
    """Malformed .copier-answers.yml falls through to the heuristic."""
    _write_answers(project_with_src, ":::not valid yaml:::")
    assert Project(project_with_src).detect_type() == "package"


def test_detect_type_falls_back_when_answers_root_is_not_dict(
    project_with_src: Path,
) -> None:
    """A YAML root that isn't a dict (e.g., a list) falls through to heuristic."""
    _write_answers(project_with_src, "- not\n- a\n- dict\n")
    assert Project(project_with_src).detect_type() == "package"


def test_detect_type_falls_back_when_project_type_missing(
    project_with_src: Path,
) -> None:
    """A copier-answers dict without `project_type` falls through to heuristic."""
    _write_answers(project_with_src, "project_name: demo\nauthor_name: Test\n")
    assert Project(project_with_src).detect_type() == "package"


def test_detect_type_falls_back_when_project_type_unknown(
    project_with_src: Path,
) -> None:
    """An unrecognized `project_type` value falls through to heuristic."""
    _write_answers(project_with_src, "project_type: data_engineering\n")
    assert Project(project_with_src).detect_type() == "package"


def test_has_dev_dependency_reads_pep735_dependency_groups(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "demo"\n'
        '[dependency-groups]\ndev = ["pytest>=8", "ruff>=0.8"]\n',
        encoding="utf-8",
    )
    project = Project(tmp_path)
    assert project.has_dev_dependency("pytest")
    assert project.has_dev_dependency("ruff")
    assert not project.has_dev_dependency("mypy")


def test_has_dev_dependency_falls_back_to_optional_dependencies_dev(
    tmp_path: Path,
) -> None:
    """Pre-PEP-735 projects keep dev deps under project.optional-dependencies.dev."""
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "demo"\n'
        '[project.optional-dependencies]\ndev = ["pytest>=8", "ruff>=0.8"]\n',
        encoding="utf-8",
    )
    project = Project(tmp_path)
    assert project.has_dev_dependency("pytest")
    assert project.has_dev_dependency("ruff")
    assert not project.has_dev_dependency("mypy")
