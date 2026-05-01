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


def test_detect_type_reads_copier_answers_research(project_with_src: Path) -> None:
    """detect_type() reads project_type from .copier-answers.yml first.

    A research project with a src/ dir (which would otherwise be classified
    as "package" by the heuristic) is correctly classified as "research"
    when .copier-answers.yml says so.
    """
    _write_answers(project_with_src, "project_type: research\nproject_name: demo\n")
    assert Project(project_with_src).detect_type() == "research"


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
