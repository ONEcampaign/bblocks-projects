"""Tests for the doctor check engine."""

import shutil
import subprocess
from pathlib import Path

import pytest

from bblocks.projects.components import COMPONENTS_REGISTRY
from bblocks.projects.doctor import Finding, _component_installed, run_checks
from bblocks.projects.project import Project
from tests._helpers import make_bblocks_project as _make_bblocks_project


def test_finding_dataclass_is_frozen() -> None:
    f = Finding("test.code", "finding", "msg")
    with pytest.raises((AttributeError, TypeError)):
        f.code = "other"  # type: ignore[misc]


def test_run_checks_returns_empty_for_healthy_project(tmp_path: Path) -> None:
    p = _make_bblocks_project(tmp_path)
    project = Project(p)
    findings = run_checks(project, check_updates=False)
    assert findings == []


def test_run_checks_short_circuits_on_catastrophic_pyproject(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("not valid toml [[[", encoding="utf-8")
    (tmp_path / ".copier-answers.yml").write_text(
        "project_type: package\n", encoding="utf-8"
    )
    project = Project(tmp_path)
    findings = run_checks(project, check_updates=False)
    assert len(findings) >= 1
    assert all(f.severity == "catastrophic" for f in findings)
    codes = [f.code for f in findings]
    assert "scaffolding.pyproject_unparseable" in codes


def test_run_checks_short_circuits_on_catastrophic_answers(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "demo"\n', encoding="utf-8")
    (tmp_path / ".copier-answers.yml").write_text("{ bad yaml", encoding="utf-8")
    project = Project(tmp_path)
    findings = run_checks(project, check_updates=False)
    assert len(findings) >= 1
    assert all(f.severity == "catastrophic" for f in findings)
    codes = [f.code for f in findings]
    assert "scaffolding.answers_unparseable" in codes


def test_check_drift_project_type_research_missing_data(tmp_path: Path) -> None:
    p = _make_bblocks_project(tmp_path, project_type="research")
    shutil.rmtree(p / "data")
    project = Project(p)
    findings = run_checks(project, check_updates=False)
    drift_findings = [f for f in findings if f.code == "drift.project_type_mismatch"]
    assert len(drift_findings) == 1
    assert "data" in drift_findings[0].message


def test_check_drift_project_type_package_missing_src(tmp_path: Path) -> None:
    p = _make_bblocks_project(tmp_path)
    shutil.rmtree(p / "src" / "demo")
    project = Project(p)
    findings = run_checks(project, check_updates=False)
    drift_findings = [f for f in findings if f.code == "drift.project_type_mismatch"]
    assert len(drift_findings) == 1
    assert "demo" in drift_findings[0].message


def test_check_drift_project_slug_mismatch(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "bar-baz"\nrequires-python = ">=3.11"\n', encoding="utf-8"
    )
    (tmp_path / ".copier-answers.yml").write_text(
        "project_type: package\nproject_slug: foo\npython_version: '3.11'\n",
        encoding="utf-8",
    )
    (tmp_path / "src" / "foo").mkdir(parents=True)
    project = Project(tmp_path)
    findings = run_checks(project, check_updates=False)
    slug_findings = [f for f in findings if f.code == "drift.project_slug_mismatch"]
    assert len(slug_findings) == 1
    assert "foo" in slug_findings[0].message
    assert "bar_baz" in slug_findings[0].message


def test_check_drift_python_version_mismatch(tmp_path: Path) -> None:
    p = _make_bblocks_project(tmp_path, python_version="3.11")
    answers = (p / ".copier-answers.yml").read_text()
    answers = answers.replace("python_version: '3.11'", "python_version: '3.12'")
    (p / ".copier-answers.yml").write_text(answers, encoding="utf-8")
    project = Project(p)
    findings = run_checks(project, check_updates=False)
    version_findings = [f for f in findings if f.code == "drift.python_version_mismatch"]
    assert len(version_findings) == 1
    assert "3.12" in version_findings[0].message
    assert "3.11" in version_findings[0].message


def test_component_installed_detects_template_file(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "demo"\n', encoding="utf-8")
    (tmp_path / ".pre-commit-config.yaml").touch()
    project = Project(tmp_path)
    comp = COMPONENTS_REGISTRY["pre-commit"]
    assert _component_installed(comp, project) is True


def test_component_installed_detects_pyproject_section(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "demo"\n[tool.ruff]\n', encoding="utf-8"
    )
    project = Project(tmp_path)
    comp = COMPONENTS_REGISTRY["ruff"]
    assert _component_installed(comp, project) is True


def test_component_installed_detects_dev_dep(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "demo"\n[dependency-groups]\ndev = ["pre-commit>=3.0.0"]\n',
        encoding="utf-8",
    )
    project = Project(tmp_path)
    comp = COMPONENTS_REGISTRY["pre-commit"]
    assert _component_installed(comp, project) is True


def test_check_components_skips_wrong_project_type(tmp_path: Path) -> None:
    p = _make_bblocks_project(
        tmp_path,
        project_type="research",
        with_components=("pre-commit", "ruff", "ci", "pytest"),
    )
    project = Project(p)
    findings = run_checks(project, check_updates=False)
    missing_names = [f.message for f in findings if f.code == "components.missing"]
    assert not any("pypi-publish" in msg for msg in missing_names)


def test_check_components_reports_missing_with_remediation(tmp_path: Path) -> None:
    p = _make_bblocks_project(
        tmp_path,
        project_type="package",
        with_components=("pre-commit", "ci", "pytest", "pypi-publish"),
    )
    project = Project(p)
    findings = run_checks(project, check_updates=False)
    ruff_findings = [
        f for f in findings if f.code == "components.missing" and "ruff" in f.message
    ]
    assert len(ruff_findings) == 1
    assert ruff_findings[0].remediation == "bblocks-projects add ruff"


def test_check_template_version_skips_when_commit_absent(tmp_path: Path) -> None:
    p = _make_bblocks_project(tmp_path, commit=None)
    project = Project(p)
    findings = run_checks(project, check_updates=True)
    template_findings = [f for f in findings if f.code == "template.skipped"]
    assert len(template_findings) == 1
    assert template_findings[0].severity == "advisory"


def test_check_template_version_skips_on_subprocess_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fake_run(*args: object, **kwargs: object) -> None:
        raise FileNotFoundError("git not found")

    monkeypatch.setattr("bblocks.projects.doctor.subprocess.run", fake_run)

    p = _make_bblocks_project(tmp_path)
    project = Project(p)
    findings = run_checks(project, check_updates=True)
    template_findings = [f for f in findings if f.code == "template.skipped"]
    assert len(template_findings) == 1
    assert template_findings[0].severity == "advisory"
    assert "FileNotFoundError" in template_findings[0].message


def test_check_template_version_skips_on_timeout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fake_run(*args: object, **kwargs: object) -> None:
        raise subprocess.TimeoutExpired(cmd="git", timeout=5)

    monkeypatch.setattr("bblocks.projects.doctor.subprocess.run", fake_run)

    p = _make_bblocks_project(tmp_path)
    project = Project(p)
    findings = run_checks(project, check_updates=True)
    template_findings = [f for f in findings if f.code == "template.skipped"]
    assert len(template_findings) == 1
    assert template_findings[0].severity == "advisory"
    assert "TimeoutExpired" in template_findings[0].message


def test_check_template_version_reports_stale(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    local_sha = "0123456789abcdef0123456789abcdef01234567"
    remote_sha = "fedcba9876543210fedcba9876543210fedcba98"

    fake_result = subprocess.CompletedProcess(
        args=["git", "ls-remote"],
        returncode=0,
        stdout=f"{remote_sha}\tHEAD\n",
        stderr="",
    )
    monkeypatch.setattr(
        "bblocks.projects.doctor.subprocess.run", lambda *a, **kw: fake_result
    )

    p = _make_bblocks_project(tmp_path, commit=local_sha)
    project = Project(p)
    findings = run_checks(project, check_updates=True)
    stale_findings = [f for f in findings if f.code == "template.stale"]
    assert len(stale_findings) == 1
    assert stale_findings[0].severity == "finding"
    assert stale_findings[0].remediation == "bblocks-projects update"


def test_check_template_version_healthy_when_match(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    sha = "0123456789abcdef0123456789abcdef01234567"

    fake_result = subprocess.CompletedProcess(
        args=["git", "ls-remote"],
        returncode=0,
        stdout=f"{sha}\tHEAD\n",
        stderr="",
    )
    monkeypatch.setattr(
        "bblocks.projects.doctor.subprocess.run", lambda *a, **kw: fake_result
    )

    p = _make_bblocks_project(tmp_path, commit=sha)
    project = Project(p)
    findings = run_checks(project, check_updates=True)
    template_findings = [f for f in findings if f.code.startswith("template.")]
    assert template_findings == []


def test_check_template_version_handles_describe_style_commit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    local_describe = "v0.2.2-3-gabcdef0"
    remote_sha = "abcdef0123456789abcdef0123456789abcdef01"

    fake_result = subprocess.CompletedProcess(
        args=["git", "ls-remote"],
        returncode=0,
        stdout=f"{remote_sha}\tHEAD\n",
        stderr="",
    )
    monkeypatch.setattr(
        "bblocks.projects.doctor.subprocess.run", lambda *a, **kw: fake_result
    )

    p = _make_bblocks_project(tmp_path, commit=local_describe)
    project = Project(p)
    findings = run_checks(project, check_updates=True)
    # remote_sha.startswith("abcdef0") → True → no finding
    template_findings = [f for f in findings if f.code.startswith("template.")]
    assert template_findings == []


def test_check_template_version_handles_short_remote_sha(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    local_sha = "0123456789abcdef0123456789abcdef01234567"
    short_remote = "01234567"

    fake_result = subprocess.CompletedProcess(
        args=["git", "ls-remote"],
        returncode=0,
        stdout=f"{short_remote}\tHEAD\n",
        stderr="",
    )
    monkeypatch.setattr(
        "bblocks.projects.doctor.subprocess.run", lambda *a, **kw: fake_result
    )

    p = _make_bblocks_project(tmp_path, commit=local_sha)
    project = Project(p)
    findings = run_checks(project, check_updates=True)
    # local_sha.startswith(short_remote) → True → no finding
    template_findings = [f for f in findings if f.code.startswith("template.")]
    assert template_findings == []
