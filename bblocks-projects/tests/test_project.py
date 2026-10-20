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


def test_iter_runtime_dependencies_excludes_dev_optional_group(
    tmp_path: Path,
) -> None:
    """The dev-named optional-dependencies group is dev tooling, not a
    runtime extra — consistent with has_dev_dependency's own reading of it."""
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "demo"\ndependencies = ["httpx>=0.27"]\n\n'
        "[project.optional-dependencies]\n"
        'dev = ["ruff~=0.15.0"]\n'
        'extra = ["pandas>=2.0"]\n',
        encoding="utf-8",
    )
    deps = Project(tmp_path).iter_runtime_dependencies()
    assert deps == ["httpx>=0.27", "pandas>=2.0"]


# --- package_root -----------------------------------------------------------


def test_package_root_none_when_no_src_dir(tmp_path: Path) -> None:
    assert Project(tmp_path).package_root() is None


def test_package_root_none_when_src_has_no_package(tmp_path: Path) -> None:
    """A src/ dir that never bottoms out at an __init__.py anywhere must
    return None only once the whole tree has been searched, not because
    the first directory with no subdirs ended the walk early."""
    (tmp_path / "src" / "_vendor").mkdir(parents=True)
    (tmp_path / "src" / "_data").mkdir(parents=True)
    assert Project(tmp_path).package_root() is None


def test_package_root_skips_non_package_sibling_that_sorts_first(
    tmp_path: Path,
) -> None:
    """An empty sibling directory that sorts alphabetically before the real
    package must not make package_root() give up early."""
    (tmp_path / "src" / "_vendor").mkdir(parents=True)
    (tmp_path / "src" / "demo").mkdir(parents=True)
    (tmp_path / "src" / "demo" / "__init__.py").touch()
    assert Project(tmp_path).package_root() == tmp_path / "src" / "demo"


def test_package_root_descends_through_namespace_package(tmp_path: Path) -> None:
    (tmp_path / "src" / "bblocks" / "projects").mkdir(parents=True)
    (tmp_path / "src" / "bblocks" / "projects" / "__init__.py").touch()
    assert Project(tmp_path).package_root() == tmp_path / "src" / "bblocks" / "projects"


def test_package_root_multi_package_src_returns_first_alphabetically(
    tmp_path: Path,
) -> None:
    """A flat multi-package src/ layout (several real repos on disk ship
    this shape) has no single "correct" answer; package_root() documents
    returning the first genuine package in breadth-first, alphabetical
    order rather than crashing or giving up."""
    for name in ("zeta_pkg", "alpha_pkg"):
        pkg_dir = tmp_path / "src" / name
        pkg_dir.mkdir(parents=True)
        (pkg_dir / "__init__.py").touch()
    assert Project(tmp_path).package_root() == tmp_path / "src" / "alpha_pkg"


# --- package_roots -----------------------------------------------------------


def test_package_roots_empty_when_no_src_dir(tmp_path: Path) -> None:
    assert Project(tmp_path).package_roots() == []


def test_package_roots_empty_when_src_has_no_package(tmp_path: Path) -> None:
    (tmp_path / "src" / "_vendor").mkdir(parents=True)
    (tmp_path / "src" / "_data").mkdir(parents=True)
    assert Project(tmp_path).package_roots() == []


def test_package_roots_single_package(tmp_path: Path) -> None:
    (tmp_path / "src" / "_vendor").mkdir(parents=True)
    (tmp_path / "src" / "demo").mkdir(parents=True)
    (tmp_path / "src" / "demo" / "__init__.py").touch()
    assert Project(tmp_path).package_roots() == [tmp_path / "src" / "demo"]


def test_package_roots_returns_every_package_alphabetically(tmp_path: Path) -> None:
    """The defect this guards: a caller that only looks at package_root()
    (the first hit) never sees the other packages in a flat multi-package
    src/ layout — a clean first package must not hide a violation living
    in a second one."""
    for name in ("zeta_pkg", "alpha_pkg"):
        pkg_dir = tmp_path / "src" / name
        pkg_dir.mkdir(parents=True)
        (pkg_dir / "__init__.py").touch()
    assert Project(tmp_path).package_roots() == [
        tmp_path / "src" / "alpha_pkg",
        tmp_path / "src" / "zeta_pkg",
    ]


def test_package_roots_does_not_descend_into_a_found_package(tmp_path: Path) -> None:
    """Once a directory is a package, its own subpackages are part of it,
    not siblings to discover separately — package_roots() must not also
    report `demo.sub` as a second root."""
    pkg_dir = tmp_path / "src" / "demo"
    (pkg_dir / "sub").mkdir(parents=True)
    (pkg_dir / "__init__.py").touch()
    (pkg_dir / "sub" / "__init__.py").touch()
    assert Project(tmp_path).package_roots() == [pkg_dir]


@pytest.mark.parametrize("git_entry", ["dir", "file"])
def test_tooling_path_resolves_repo_level_files_from_git_root(
    tmp_path: Path, git_entry: str
) -> None:
    """A `.git` file marks a linked worktree or submodule root."""
    if git_entry == "dir":
        (tmp_path / ".git").mkdir()
    else:
        (tmp_path / ".git").write_text("gitdir: elsewhere\n", encoding="utf-8")
    package = tmp_path / "python"
    package.mkdir()
    project = Project(package)
    assert project.repo_root == tmp_path
    assert project.tooling_path(".pre-commit-config.yaml") == (
        tmp_path / ".pre-commit-config.yaml"
    )
    assert project.tooling_path(".github/workflows/ci.yml") == (
        tmp_path / ".github" / "workflows" / "ci.yml"
    )
    assert project.tooling_path("pyproject.toml") == package / "pyproject.toml"


def test_repo_root_is_the_project_outside_a_git_work_tree(tmp_path: Path) -> None:
    package = tmp_path / "python"
    package.mkdir()
    project = Project(package)
    assert project.repo_root == package
    assert (
        project.tooling_path(".github/workflows") == package / ".github" / "workflows"
    )


def test_read_workflows_reads_the_git_root(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()
    workflows = tmp_path / ".github" / "workflows"
    workflows.mkdir(parents=True)
    (workflows / "release.yml").write_text("name: release\n", encoding="utf-8")
    package = tmp_path / "python"
    (package / ".github" / "workflows").mkdir(parents=True)
    (package / ".github" / "workflows" / "ignored.yml").write_text(
        "name: ignored\n", encoding="utf-8"
    )
    assert Project(package).read_workflows() == {"release.yml": "name: release\n"}
