"""Characterization tests for the copier template."""

import shutil
from pathlib import Path

import copier
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
assert (REPO_ROOT / "copier.yml").exists(), (
    f"REPO_ROOT={REPO_ROOT} is not the bblocks-projects template root; "
    "test fixture must point at the directory containing copier.yml"
)

_BASE_DATA = {
    "project_name": "Test Project",
    "project_slug": "test_project",
    "project_description": "x",
    "author_name": "T",
    "author_email": "t@example.com",
    "python_version": "3.11",
    "license": "mit",
    "github_username": "testuser",
}


@pytest.fixture(scope="session")
def template_src(tmp_path_factory: pytest.TempPathFactory) -> Path:
    # Copy without .git so copier reads working-tree files, not last git commit.
    src = tmp_path_factory.mktemp("template_src")
    shutil.copytree(
        REPO_ROOT,
        src,
        dirs_exist_ok=True,
        ignore=shutil.ignore_patterns(
            ".git", "__pycache__", "*.pyc", ".venv", ".pytest_cache", ".ruff_cache"
        ),
    )
    return src


def _render(template_src: Path, dst: Path, project_type: str, **overrides: str) -> Path:
    copier.run_copy(
        src_path=str(template_src),
        dst_path=str(dst),
        data={**_BASE_DATA, "project_type": project_type, **overrides},
        defaults=True,
        skip_tasks=True,
        unsafe=True,
        quiet=True,
    )
    return dst


def test_project_has_lint_only_ci_no_release(
    template_src: Path, tmp_path: Path
) -> None:
    rendered = _render(template_src, tmp_path / "rendered", "project")
    ci = (rendered / ".github" / "workflows" / "ci.yml").read_text()
    assert "lint:" in ci
    assert "test:" not in ci
    assert not (rendered / ".github" / "workflows" / "release.yml").exists()


def test_legacy_research_value_still_renders_project_layout(
    template_src: Path, tmp_path: Path
) -> None:
    """`project_type: research` (legacy) renders the same non-package layout.

    Old projects re-rendered via `copier update` still have `research` in
    their answers file; the template's `!= 'package'` conditionals must
    keep treating that as the project layout.
    """
    rendered = _render(template_src, tmp_path / "rendered", "research")
    assert (rendered / "src" / "test_project").is_dir()
    assert (rendered / "data" / "raw" / ".gitkeep").exists()
    assert (rendered / "data" / "processed" / ".gitkeep").exists()
    assert not (rendered / "tests").exists()
    assert not (rendered / ".github" / "workflows" / "release.yml").exists()


def test_package_has_full_ci_and_release(template_src: Path, tmp_path: Path) -> None:
    rendered = _render(template_src, tmp_path / "rendered", "package")
    ci_path = rendered / ".github" / "workflows" / "ci.yml"
    release_path = rendered / ".github" / "workflows" / "release.yml"
    ci = ci_path.read_text()
    assert "lint:" in ci
    assert "test:" in ci
    assert release_path.exists()


def test_ci_quotes_project_slug_in_run_lines(
    template_src: Path, tmp_path: Path
) -> None:
    rendered = _render(template_src, tmp_path / "rendered", "package")
    ci = (rendered / ".github" / "workflows" / "ci.yml").read_text()
    assert "uvx ty check 'src/test_project'" in ci
    assert "--cov='src/test_project'" in ci


def test_ci_quotes_python_version_in_run_lines(
    template_src: Path, tmp_path: Path
) -> None:
    rendered = _render(template_src, tmp_path / "rendered", "package")
    ci = (rendered / ".github" / "workflows" / "ci.yml").read_text()
    release = (rendered / ".github" / "workflows" / "release.yml").read_text()
    assert "uv python install '3.11'" in ci
    assert "uv python install '3.11'" in release


def test_validator_rejects_bad_project_slug(template_src: Path, tmp_path: Path) -> None:
    """Copier validator must reject non-identifier slugs to prevent shell injection."""
    with pytest.raises(ValueError, match="valid Python identifier"):
        _render(
            template_src,
            tmp_path / "bad",
            "package",
            project_slug="bad-slug; rm -rf /",
        )
