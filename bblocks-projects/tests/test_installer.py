"""Tests for component installation, focused on post-install hint substitution."""

import io
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from rich.console import Console as RichConsole

from bblocks.projects.components import COMPONENTS_REGISTRY
from bblocks.projects.installer import install_component
from bblocks.projects.project import Project


@pytest.fixture
def fake_uv_project(tmp_path: Path) -> Path:
    """Create a minimal uv-style project (pyproject + uv.lock) at tmp_path."""
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "demo"\nrequires-python = ">=3.11"\n'
        '[build-system]\nrequires = ["setuptools>=68"]\n'
        'build-backend = "setuptools.build_meta"\n',
        encoding="utf-8",
    )
    (tmp_path / "uv.lock").write_text("", encoding="utf-8")
    (tmp_path / "src").mkdir()
    return tmp_path


def _make_no_render_stub(tmp_path: Path) -> Any:
    def _no_render(**kwargs: Any) -> None:
        dst = Path(kwargs["dst_path"])
        (dst / "pyproject.toml").write_text(
            '[build-system]\nrequires = ["setuptools>=68"]\n'
            'build-backend = "setuptools.build_meta"\n',
            encoding="utf-8",
        )

    return _no_render


def test_pypi_publish_substitutes_github_username(
    fake_uv_project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (fake_uv_project / ".copier-answers.yml").write_text(
        "github_username: testuser\n", encoding="utf-8"
    )
    buf = io.StringIO()
    test_console = RichConsole(file=buf, force_terminal=False, width=200)
    monkeypatch.setattr("bblocks.projects.installer.console", test_console)

    project = Project(fake_uv_project)
    component = COMPONENTS_REGISTRY["pypi-publish"]

    with patch(
        "bblocks.projects.installer._copier_run_copy",
        side_effect=_make_no_render_stub(fake_uv_project),
    ):
        result = install_component(component, project, force=True, interactive=False)

    assert result is True
    output = buf.getvalue()
    assert "testuser/<your-repo>" in output
    assert "{github_username}" not in output
    assert "<YOUR-GITHUB-USERNAME>" not in output


def test_pypi_publish_falls_back_when_no_copier_answers(
    fake_uv_project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    buf = io.StringIO()
    test_console = RichConsole(file=buf, force_terminal=False, width=200)
    monkeypatch.setattr("bblocks.projects.installer.console", test_console)

    project = Project(fake_uv_project)
    component = COMPONENTS_REGISTRY["pypi-publish"]

    with patch(
        "bblocks.projects.installer._copier_run_copy",
        side_effect=_make_no_render_stub(fake_uv_project),
    ):
        result = install_component(component, project, force=True, interactive=False)

    assert result is True
    output = buf.getvalue()
    assert "<YOUR-GITHUB-USERNAME>/<your-repo>" in output
    assert "{github_username}" not in output
