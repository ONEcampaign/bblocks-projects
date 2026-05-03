"""Tests for the CLI interface."""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock

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
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "demo"\n', encoding="utf-8"
    )
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
    assert (
        "3.12" in result.stdout
        or "drift" in result.stdout.lower()
        or "findings" in result.stdout
    )


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
    result = runner.invoke(app, ["doctor", "--path", str(tmp_path), "--check-updates"])
    assert result.exit_code == 0
    assert "skipped" in result.stdout.lower()


def test_update_passes_overwrite_and_default_ref(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    mock_run_update = MagicMock()
    monkeypatch.setattr("bblocks.projects.cli.run_update", mock_run_update)
    _make_bblocks_project(tmp_path)
    result = runner.invoke(app, ["update", "--path", str(tmp_path)])
    assert result.exit_code == 0
    mock_run_update.assert_called_once()
    _, kwargs = mock_run_update.call_args
    assert kwargs["overwrite"] is True
    assert kwargs["defaults"] is True
    assert kwargs["vcs_ref"] == "main"


def test_update_uses_explicit_ref_when_provided(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    mock_run_update = MagicMock()
    monkeypatch.setattr("bblocks.projects.cli.run_update", mock_run_update)
    _make_bblocks_project(tmp_path)
    result = runner.invoke(app, ["update", "--path", str(tmp_path), "--ref", "v0.2.0"])
    assert result.exit_code == 0
    mock_run_update.assert_called_once()
    _, kwargs = mock_run_update.call_args
    assert kwargs["vcs_ref"] == "v0.2.0"


def test_create_passes_cleanup_on_error_false(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    mock_run_copy = MagicMock()
    monkeypatch.setattr("bblocks.projects.cli.run_copy", mock_run_copy)
    monkeypatch.setattr(
        "bblocks.projects.cli.subprocess.run",
        lambda *a, **kw: subprocess.CompletedProcess(a, 0),
    )
    result = runner.invoke(
        app,
        ["create", str(tmp_path / "newproj"), "--defaults", "--no-github"],
    )
    assert result.exit_code == 0
    mock_run_copy.assert_called_once()
    _, kwargs = mock_run_copy.call_args
    assert kwargs["cleanup_on_error"] is False


@pytest.mark.parametrize(
    ("failing_tool", "failure_mode"),
    [("git", "returncode_nonzero"), ("uv", "filenotfound")],
)
def test_create_preflights_missing_tool_exits_one(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failing_tool: str,
    failure_mode: str,
) -> None:
    mock_run_copy = MagicMock()
    monkeypatch.setattr("bblocks.projects.cli.run_copy", mock_run_copy)

    def fake_subprocess_run(
        cmd: list[str], **kwargs: object
    ) -> subprocess.CompletedProcess:  # type: ignore[type-arg]
        if cmd[0] == failing_tool:
            if failure_mode == "filenotfound":
                raise FileNotFoundError(f"{failing_tool} not found")
            return subprocess.CompletedProcess(cmd, returncode=1)
        return subprocess.CompletedProcess(cmd, returncode=0)

    monkeypatch.setattr("bblocks.projects.cli.subprocess.run", fake_subprocess_run)
    result = runner.invoke(
        app, ["create", str(tmp_path / "newproj"), "--defaults", "--no-github"]
    )
    assert result.exit_code == 1
    assert failing_tool in result.stdout
    mock_run_copy.assert_not_called()
    mock_run_copy.assert_not_called()


def test_help_text_does_not_leak_cwd() -> None:
    cwd_str = str(Path.cwd())
    for subcmd in ("update", "add", "doctor"):
        result = runner.invoke(app, [subcmd, "--help"])
        assert result.exit_code == 0
        assert cwd_str not in result.stdout, (
            f"{subcmd} --help leaks CWD: {cwd_str!r} found in output"
        )


def test_add_bogus_component_yes_exits_one(tmp_path: Path) -> None:
    _make_bblocks_project(tmp_path)
    result = runner.invoke(app, ["add", "bogus-name", "--yes", "--path", str(tmp_path)])
    assert result.exit_code == 1


def test_add_partial_success_exits_one(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _make_bblocks_project(tmp_path)

    import bblocks.projects.installer as _installer  # noqa: PLC0415

    def fake_install_component(
        component: object,
        project: object,
        *,
        force: bool = False,
        interactive: bool = True,
        rendered_template_dir: object = None,
    ) -> bool:
        from bblocks.projects.components import ComponentDef  # noqa: PLC0415

        assert isinstance(component, ComponentDef)
        return component.name == "pre-commit"  # type: ignore[union-attr]

    monkeypatch.setattr(_installer, "install_component", fake_install_component)

    result = runner.invoke(
        app,
        ["add", "pre-commit", "bogus-name", "--yes", "--path", str(tmp_path)],
    )
    assert result.exit_code == 1


def test_add_install_component_returns_false_exits_one(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A real component whose install_component returns False must exit 1."""
    _make_bblocks_project(tmp_path)

    import bblocks.projects.installer as _installer  # noqa: PLC0415

    monkeypatch.setattr(_installer, "install_component", lambda *a, **kw: False)

    result = runner.invoke(app, ["add", "pre-commit", "--yes", "--path", str(tmp_path)])
    assert result.exit_code == 1
