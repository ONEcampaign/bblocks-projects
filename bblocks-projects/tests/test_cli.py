"""Tests for the CLI interface."""

from pathlib import Path

from typer.testing import CliRunner

from bblocks.projects import __version__
from bblocks.projects.cli import app

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
    assert "Create a new ONE Campaign Python project" in result.stdout


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
