"""Tests for the CLI interface."""

from pathlib import Path

import pytest
from typer.testing import CliRunner

from bblocks.projects import __version__
from bblocks.projects.cli import app
from tests._helpers import make_bblocks_project as _make_bblocks_project

runner = CliRunner()


def test_version() -> None:
    """Test version command."""
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert __version__ in result.stdout


def test_help() -> None:
    """Test help command."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "bblocks-projects" in result.stdout.lower()


def test_create_help() -> None:
    """Test create command help."""
    result = runner.invoke(app, ["create", "--help"])
    assert result.exit_code == 0
    assert "Create a new Python project from a template" in result.stdout


def test_update_help() -> None:
    """Test update command help."""
    result = runner.invoke(app, ["update", "--help"])
    assert result.exit_code == 0
    assert "Update an existing" in result.stdout


def test_update_without_copier_answers(tmp_path: Path) -> None:
    """Test update fails gracefully without .copier-answers.yml."""
    result = runner.invoke(app, ["update", "--path", str(tmp_path)])
    assert result.exit_code == 1
    assert ".copier-answers.yml" in result.stdout


def test_create_help_shows_template_flag() -> None:
    """Test that create --help shows --template / -T flag."""
    result = runner.invoke(app, ["create", "--help"])
    assert result.exit_code == 0
    assert "--template" in result.stdout


def test_update_help_shows_template_flag() -> None:
    """Test that update --help shows --template / -T flag."""
    result = runner.invoke(app, ["update", "--help"])
    assert result.exit_code == 0
    assert "--template" in result.stdout


def test_doctor_help() -> None:
    result = runner.invoke(app, ["doctor", "--help"])
    assert result.exit_code == 0
    assert "Run health checks" in result.stdout


def test_doctor_refuses_no_pyproject(tmp_path: Path) -> None:
    result = runner.invoke(app, ["doctor", "--path", str(tmp_path)])
    assert result.exit_code == 1
    assert "Python project" in result.stdout or "pyproject.toml" in result.stdout


def test_doctor_refuses_no_answers(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "demo"\n', encoding="utf-8")
    result = runner.invoke(app, ["doctor", "--path", str(tmp_path)])
    assert result.exit_code == 1
    assert "bblocks-managed" in result.stdout or "appear to be" in result.stdout


def test_doctor_healthy_project(tmp_path: Path) -> None:
    _make_bblocks_project(tmp_path)
    result = runner.invoke(app, ["doctor", "--path", str(tmp_path)])
    assert result.exit_code == 0
    assert "Healthy" in result.stdout


def test_doctor_drift_detected(tmp_path: Path) -> None:
    p = _make_bblocks_project(tmp_path, python_version="3.11")
    answers = (p / ".copier-answers.yml").read_text()
    answers = answers.replace("python_version: '3.11'", "python_version: '3.12'")
    (p / ".copier-answers.yml").write_text(answers, encoding="utf-8")
    result = runner.invoke(app, ["doctor", "--path", str(tmp_path)])
    assert result.exit_code == 0
    assert "3.12" in result.stdout or "drift" in result.stdout.lower() or "findings" in result.stdout


def test_doctor_strict_flips_exit_code(tmp_path: Path) -> None:
    p = _make_bblocks_project(tmp_path, python_version="3.11")
    answers = (p / ".copier-answers.yml").read_text()
    answers = answers.replace("python_version: '3.11'", "python_version: '3.12'")
    (p / ".copier-answers.yml").write_text(answers, encoding="utf-8")
    result = runner.invoke(app, ["doctor", "--path", str(tmp_path), "--strict"])
    assert result.exit_code == 1


def test_doctor_missing_component_advisory(tmp_path: Path) -> None:
    _make_bblocks_project(
        tmp_path,
        with_components=("pre-commit", "ci", "pypi-publish"),
    )
    result = runner.invoke(app, ["doctor", "--path", str(tmp_path)])
    assert "pytest" in result.stdout
    assert "bblocks-projects add pytest" in result.stdout


def test_doctor_check_updates_graceful_when_subprocess_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fake_run(*args: object, **kwargs: object) -> None:
        raise FileNotFoundError("git not found")

    monkeypatch.setattr("bblocks.projects.doctor.subprocess.run", fake_run)

    _make_bblocks_project(tmp_path)
    result = runner.invoke(
        app, ["doctor", "--path", str(tmp_path), "--check-updates"]
    )
    assert result.exit_code == 0
    assert "skipped" in result.stdout.lower()
