"""Tests for component installation, focused on post-install hint substitution."""

import io
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from rich.console import Console as RichConsole

from bblocks.projects.components import COMPONENTS_REGISTRY
from bblocks.projects.installer import (
    _parse_dep_name,
    can_install_component,
    get_conflicts,
    install_component,
    rendered_template_for,
)
from bblocks.projects.project import Project
from tests._helpers import make_bblocks_project


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


def test_rendered_template_for_renders_once_for_multiple_installs(
    fake_uv_project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Hoisting the render context manager around a batch of installs causes a
    single render call even when multiple components are installed."""
    buf = io.StringIO()
    test_console = RichConsole(file=buf, force_terminal=False, width=200)
    monkeypatch.setattr("bblocks.projects.installer.console", test_console)

    project = Project(fake_uv_project)
    components = [
        COMPONENTS_REGISTRY["ruff"],
        COMPONENTS_REGISTRY["pre-commit"],
        COMPONENTS_REGISTRY["pytest"],
    ]

    with (
        patch(
            "bblocks.projects.installer._copier_run_copy",
            side_effect=_make_no_render_stub(fake_uv_project),
        ) as mock_render,
        rendered_template_for(project) as rendered_dir,
    ):
        for comp in components:
            install_component(
                comp,
                project,
                force=True,
                interactive=False,
                rendered_template_dir=rendered_dir,
            )

    assert mock_render.call_count == 1


@pytest.mark.parametrize(
    ("spec", "expected"),
    [
        ("ruff", "ruff"),
        ("ruff>=0.8.0", "ruff"),
        ("ruff==0.8.0", "ruff"),
        ("pkg~=1.0", "pkg"),
        ("pkg!=1.5", "pkg"),
        ("pkg<2", "pkg"),
        ("pkg<=2", "pkg"),
        ("pkg>1", "pkg"),
        ("pkg[extra]", "pkg"),
        ("pkg[extra]>=1.0", "pkg"),
        ("pkg ; python_version>='3.10'", "pkg"),
        ("  pkg>=1  ", "pkg"),
    ],
)
def test_parse_dep_name(spec: str, expected: str) -> None:
    assert _parse_dep_name(spec) == expected


def test_install_component_renders_internally_when_no_dir_passed(
    fake_uv_project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When no rendered_template_dir is passed, install_component renders for itself."""
    buf = io.StringIO()
    test_console = RichConsole(file=buf, force_terminal=False, width=200)
    monkeypatch.setattr("bblocks.projects.installer.console", test_console)

    project = Project(fake_uv_project)
    component = COMPONENTS_REGISTRY["ruff"]

    with patch(
        "bblocks.projects.installer._copier_run_copy",
        side_effect=_make_no_render_stub(fake_uv_project),
    ) as mock_render:
        install_component(component, project, force=True, interactive=False)

    assert mock_render.call_count == 1


def _patch_rendered_template_for(
    monkeypatch: pytest.MonkeyPatch, files: dict[str, str]
) -> None:
    """Replace `rendered_template_for` with a stub that yields a temp dir holding `files`."""

    @contextmanager
    def _fake(_project: Any) -> Iterator[Path]:
        with tempfile.TemporaryDirectory(prefix="bblocks-test-") as d:
            td = Path(d)
            for relpath, content in files.items():
                target = td / relpath
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content, encoding="utf-8")
            yield td

    monkeypatch.setattr("bblocks.projects.installer.rendered_template_for", _fake)


def test_install_component_yes_installs_dev_deps(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Non-interactive install must call _add_dependencies with the component's dev_deps."""
    make_bblocks_project(tmp_path, with_components=())

    buf = io.StringIO()
    test_console = RichConsole(file=buf, force_terminal=False, width=200)
    monkeypatch.setattr("bblocks.projects.installer.console", test_console)

    project = Project(tmp_path)
    comp = COMPONENTS_REGISTRY["pre-commit"]

    add_deps_mock = MagicMock()
    monkeypatch.setattr("bblocks.projects.installer._add_dependencies", add_deps_mock)
    _patch_rendered_template_for(monkeypatch, {".pre-commit-config.yaml": ""})

    result = install_component(comp, project, interactive=False)

    assert result is True
    add_deps_mock.assert_called_once_with(project, comp.dev_deps, dev=True)


def test_install_component_message_renders_build_system_literal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """[build-system] must appear literally in console output, not as a Rich tag."""
    make_bblocks_project(
        tmp_path,
        with_components=(),
        project_type="package",
        github_username="testuser",
    )

    buf = io.StringIO()
    test_console = RichConsole(file=buf, force_terminal=False, width=200)
    monkeypatch.setattr("bblocks.projects.installer.console", test_console)

    project = Project(tmp_path)
    comp = COMPONENTS_REGISTRY["pypi-publish"]

    monkeypatch.setattr("bblocks.projects.installer._add_dependencies", MagicMock())
    _patch_rendered_template_for(
        monkeypatch,
        {
            ".github/workflows/release.yml": "",
            "pyproject.toml": (
                '[build-system]\nrequires = ["uv_build"]\nbuild-backend = "uv_build"\n'
            ),
        },
    )

    install_component(comp, project, interactive=False, force=True)

    output = buf.getvalue()
    assert "[build-system]" in output
    assert "  section" not in output


@pytest.fixture
def package_in_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Project:
    """A package in `python/` of a git work tree, with a silenced console."""
    (tmp_path / ".git").mkdir()
    package = tmp_path / "python"
    package.mkdir()
    make_bblocks_project(package, with_components=())
    monkeypatch.setattr(
        "bblocks.projects.installer.console",
        RichConsole(file=io.StringIO(), force_terminal=False, width=200),
    )
    monkeypatch.setattr("bblocks.projects.installer._add_dependencies", MagicMock())
    return Project(package)


_REPO_LEVEL_COMPONENTS = [
    ("pre-commit", ".pre-commit-config.yaml"),
    ("ci", ".github/workflows/ci.yml"),
    ("pypi-publish", ".github/workflows/release.yml"),
]


def _snapshot(root: Path) -> dict[str, str | None]:
    """Every path under `root`, with the text of each file."""
    return {
        path.relative_to(root).as_posix(): path.read_text() if path.is_file() else None
        for path in sorted(root.rglob("*"))
    }


def _capture_console(monkeypatch: pytest.MonkeyPatch) -> io.StringIO:
    buf = io.StringIO()
    monkeypatch.setattr(
        "bblocks.projects.installer.console",
        RichConsole(file=buf, force_terminal=False, width=500),
    )
    return buf


@pytest.mark.parametrize(("component", "relpath"), _REPO_LEVEL_COMPONENTS)
@pytest.mark.parametrize("force", [False, True])
@pytest.mark.parametrize("root_file_exists", [False, True])
def test_install_component_installs_the_package_part_below_the_git_root(
    package_in_repo: Project,
    monkeypatch: pytest.MonkeyPatch,
    component: str,
    relpath: str,
    force: bool,
    root_file_exists: bool,
) -> None:
    """A repo-level file is shared by every language, so `add` never writes it."""
    comp = COMPONENTS_REGISTRY[component]
    _patch_rendered_template_for(
        monkeypatch,
        {
            relpath: "rendered\n",
            "pyproject.toml": '[build-system]\nrequires = ["uv_build"]\n',
        },
    )
    buf = _capture_console(monkeypatch)
    add_dependencies = MagicMock()
    monkeypatch.setattr(
        "bblocks.projects.installer._add_dependencies", add_dependencies
    )
    root_file = package_in_repo.repo_root / relpath
    if root_file_exists:
        root_file.parent.mkdir(parents=True, exist_ok=True)
        root_file.write_text("root\n")
    before = _snapshot(package_in_repo.repo_root)

    installed = install_component(comp, package_in_repo, interactive=False, force=force)

    assert installed is True
    assert _snapshot(package_in_repo.repo_root) == before
    if comp.dev_deps:
        add_dependencies.assert_called_once_with(
            package_in_repo, comp.dev_deps, dev=True
        )
    else:
        add_dependencies.assert_not_called()
    output = buf.getvalue()
    assert f"Skipped {relpath}" in output
    assert ("where it exists" in output) is root_file_exists
    assert ("by hand" in output) is not root_file_exists
    assert ("a-package-in-a-multi-language-repo" in output) is not root_file_exists


def test_install_component_installs_several_components_below_the_git_root(
    package_in_repo: Project, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`add ruff pre-commit` installs the package-side part of both."""
    _patch_rendered_template_for(
        monkeypatch,
        {
            ".pre-commit-config.yaml": "rendered\n",
            "pyproject.toml": "[tool.ruff]\nline-length = 88\n",
        },
    )
    _capture_console(monkeypatch)
    add_dependencies = MagicMock()
    monkeypatch.setattr(
        "bblocks.projects.installer._add_dependencies", add_dependencies
    )
    ruff = COMPONENTS_REGISTRY["ruff"]
    pre_commit = COMPONENTS_REGISTRY["pre-commit"]

    with rendered_template_for(package_in_repo) as rendered:
        results = [
            install_component(
                comp,
                package_in_repo,
                interactive=False,
                rendered_template_dir=rendered,
            )
            for comp in (ruff, pre_commit)
        ]

    assert results == [True, True]
    assert [call.args[1] for call in add_dependencies.call_args_list] == [
        ruff.dev_deps,
        pre_commit.dev_deps,
    ]
    assert package_in_repo.has_config_section("tool.ruff")
    assert not (package_in_repo.repo_root / ".pre-commit-config.yaml").exists()
    assert not (package_in_repo.path / ".pre-commit-config.yaml").exists()


def test_install_component_installs_a_non_repo_level_component_below_the_git_root(
    package_in_repo: Project,
) -> None:
    ok, _ = can_install_component(COMPONENTS_REGISTRY["ruff"], package_in_repo)
    assert ok is True


@pytest.mark.parametrize(("component", "relpath"), _REPO_LEVEL_COMPONENTS)
def test_install_component_writes_repo_level_files_for_a_package_at_the_git_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    component: str,
    relpath: str,
) -> None:
    (tmp_path / ".git").mkdir()
    make_bblocks_project(tmp_path, with_components=(), github_username="octo")
    buf = io.StringIO()
    monkeypatch.setattr(
        "bblocks.projects.installer.console",
        RichConsole(file=buf, force_terminal=False, width=200),
    )
    monkeypatch.setattr("bblocks.projects.installer._add_dependencies", MagicMock())
    _patch_rendered_template_for(monkeypatch, {relpath: "rendered\n"})

    installed = install_component(
        COMPONENTS_REGISTRY[component], Project(tmp_path), interactive=False
    )

    assert installed is True
    assert (tmp_path / relpath).read_text() == "rendered\n"
    assert f"Created: {relpath}" in buf.getvalue()
    assert "../" not in buf.getvalue()


def test_get_conflicts_ignores_repo_level_files_below_the_git_root(
    package_in_repo: Project,
) -> None:
    """`add` writes no repo-level file there, so none can conflict."""
    comp = COMPONENTS_REGISTRY["pre-commit"]
    (package_in_repo.repo_root / ".pre-commit-config.yaml").write_text("root\n")
    (package_in_repo.path / ".pre-commit-config.yaml").write_text("stray\n")
    assert get_conflicts(comp, package_in_repo) == []


def test_install_component_places_tooling_in_a_package_outside_git(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    make_bblocks_project(tmp_path, with_components=())
    monkeypatch.setattr("bblocks.projects.installer._add_dependencies", MagicMock())
    monkeypatch.setattr(
        "bblocks.projects.installer.console",
        RichConsole(file=io.StringIO(), force_terminal=False, width=200),
    )
    project = Project(tmp_path)
    comp = COMPONENTS_REGISTRY["pre-commit"]
    assert get_conflicts(comp, project) == []
    _patch_rendered_template_for(monkeypatch, {".pre-commit-config.yaml": "x\n"})

    install_component(comp, project, interactive=False)

    assert (tmp_path / ".pre-commit-config.yaml").read_text() == "x\n"
    assert get_conflicts(comp, project) == ["File exists: .pre-commit-config.yaml"]


def test_render_passes_the_module_name_to_the_template(
    fake_uv_project: Path,
) -> None:
    """`[tool.uv.build-backend] module-name` reaches copier, and the slug does when it is unset."""
    pyproject = fake_uv_project / "pyproject.toml"
    pyproject.write_text(
        pyproject.read_text() + '[tool.uv.build-backend]\nmodule-name = "dfo"\n'
    )
    seen: list[dict[str, Any]] = []

    def _capture(**kwargs: Any) -> None:
        seen.append(kwargs["data"])

    with patch("bblocks.projects.installer._copier_run_copy", side_effect=_capture):
        with rendered_template_for(Project(fake_uv_project)):
            pass
        pyproject.write_text(pyproject.read_text().split("[tool.uv")[0])
        with rendered_template_for(Project(fake_uv_project)):
            pass

    assert [data["module_name"] for data in seen] == ["dfo", "demo"]
