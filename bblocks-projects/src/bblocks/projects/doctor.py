"""Health-check engine for bblocks-managed projects."""

import subprocess
import tomllib
from dataclasses import dataclass
from typing import Literal

import yaml

from bblocks.projects.components import COMPONENTS_REGISTRY, ComponentDef
from bblocks.projects.config import resolve_template_url
from bblocks.projects.installer import _parse_dep_name
from bblocks.projects.project import Project

Severity = Literal["catastrophic", "finding", "advisory"]

# Section prefixes for Finding.code. Renderer groups findings by the
# substring before the first ".". Keep this tuple in sync with any new
# section a future check author introduces.
SECTIONS: tuple[tuple[str, str], ...] = (
    ("scaffolding", "Scaffolding"),
    ("drift", "Drift"),
    ("components", "Components"),
    ("template", "Template version"),
)


@dataclass(frozen=True)
class Finding:
    """A single health-check observation about a project."""

    code: str
    severity: Severity
    message: str
    remediation: str | None = None


def _template_skipped(message: str) -> Finding:
    return Finding("template.skipped", "advisory", message, None)


def run_checks(project: Project, *, check_updates: bool) -> list[Finding]:
    """Run all health checks against a bblocks-managed project.

    Catastrophic findings short-circuit further checks. The caller is
    responsible for refusing non-bblocks-managed projects (no
    `.copier-answers.yml` or `pyproject.toml`) before invoking this
    function — those refusals are not modeled as findings.
    """
    findings: list[Finding] = []
    findings += _check_pyproject_parseable(project)
    findings += _check_copier_answers_parseable(project)
    if any(f.severity == "catastrophic" for f in findings):
        return findings
    findings += _check_drift_project_type(project)
    findings += _check_drift_project_slug(project)
    findings += _check_drift_python_version(project)
    findings += _check_components(project)
    if check_updates:
        findings += _check_template_version(project)
    return findings


def _check_pyproject_parseable(project: Project) -> list[Finding]:
    if not project.has_pyproject():
        return [
            Finding(
                "scaffolding.pyproject_missing",
                "catastrophic",
                "pyproject.toml is missing",
                "Ensure pyproject.toml exists at the project root",
            )
        ]
    try:
        # Triggers a single tomllib.load via Project's cached property; later
        # checks (drift, components) reuse the cache instead of re-parsing.
        _ = project.pyproject_data
    except tomllib.TOMLDecodeError as e:
        return [
            Finding(
                "scaffolding.pyproject_unparseable",
                "catastrophic",
                f"pyproject.toml is malformed: {e}",
                "Fix the TOML syntax",
            )
        ]
    return []


def _check_copier_answers_parseable(project: Project) -> list[Finding]:
    answers_path = project.path / ".copier-answers.yml"
    try:
        data = yaml.safe_load(answers_path.read_text(encoding="utf-8"))
    except OSError as e:
        return [
            Finding(
                "scaffolding.answers_missing",
                "catastrophic",
                f".copier-answers.yml could not be read: {e}",
                "Ensure .copier-answers.yml exists and is readable",
            )
        ]
    except yaml.YAMLError as e:
        return [
            Finding(
                "scaffolding.answers_unparseable",
                "catastrophic",
                f".copier-answers.yml is malformed: {e}",
                "Fix the YAML syntax",
            )
        ]
    if not isinstance(data, dict):
        return [
            Finding(
                "scaffolding.answers_not_dict",
                "catastrophic",
                ".copier-answers.yml root is not a mapping",
                "Ensure .copier-answers.yml contains a YAML mapping at the root",
            )
        ]
    return []


def _check_drift_project_type(project: Project) -> list[Finding]:
    answer = project.copier_answers.get("project_type")
    if answer not in ("package", "research"):
        return []
    slug = project.copier_answers.get("project_slug") or project.get_project_slug()
    if answer == "research":
        expected_dirs = [project.path / "src" / slug, project.path / "data"]
    else:
        expected_dirs = [project.path / "src" / slug]
    missing = [d.name for d in expected_dirs if not d.is_dir()]
    if missing:
        return [
            Finding(
                "drift.project_type_mismatch",
                "finding",
                f"project_type={answer} but missing expected dirs: {', '.join(missing)}",
                "Run `bblocks-projects update` or restore the directories",
            )
        ]
    return []


def _check_drift_project_slug(project: Project) -> list[Finding]:
    answer_slug = project.copier_answers.get("project_slug")
    if not isinstance(answer_slug, str):
        return []
    actual_slug = project.get_project_slug()
    if answer_slug != actual_slug:
        return [
            Finding(
                "drift.project_slug_mismatch",
                "finding",
                f"project_slug={answer_slug!r} but pyproject name slugifies to {actual_slug!r}",
                "Update either .copier-answers.yml or [project].name in pyproject.toml",
            )
        ]
    return []


def _check_drift_python_version(project: Project) -> list[Finding]:
    answer_version = project.copier_answers.get("python_version")
    if not isinstance(answer_version, str):
        return []
    actual_version = project.get_python_version()
    if answer_version != actual_version:
        return [
            Finding(
                "drift.python_version_mismatch",
                "finding",
                f"python_version={answer_version} but pyproject requires-python lower bound is {actual_version}",
                "Align requires-python in pyproject.toml or re-run `bblocks-projects update`",
            )
        ]
    return []


def _component_installed(comp: ComponentDef, project: Project) -> bool:
    for relpath in comp.template_files:
        if project.has_file(relpath.removesuffix(".jinja")):
            return True
    for section in comp.pyproject_sections:
        if project.has_config_section(section):
            return True
    for dep in comp.dev_deps:
        if project.has_dev_dependency(_parse_dep_name(dep)):
            return True
    return False


def _check_components(project: Project) -> list[Finding]:
    findings: list[Finding] = []
    project_type = project.detect_type()
    for comp in COMPONENTS_REGISTRY.values():
        if comp.requires_project_type and comp.requires_project_type != project_type:
            continue
        if not _component_installed(comp, project):
            findings.append(
                Finding(
                    "components.missing",
                    "finding",
                    f"Component not installed: {comp.name} ({comp.description})",
                    f"bblocks-projects add {comp.name}",
                )
            )
    return findings


def _check_template_version(project: Project) -> list[Finding]:
    commit = project.copier_answers.get("_commit")
    if not isinstance(commit, str) or not commit:
        return [_template_skipped("_commit field absent from .copier-answers.yml")]
    template_url = resolve_template_url()
    try:
        result = subprocess.run(
            ["git", "ls-remote", template_url, "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        return [_template_skipped(f"template-version check skipped: {type(e).__name__}")]
    if result.returncode != 0:
        return [_template_skipped(
            f"template-version check skipped: git ls-remote failed (exit {result.returncode})"
        )]
    line = result.stdout.strip().splitlines()[0] if result.stdout.strip() else ""
    remote_sha = line.split("\t", 1)[0] if line else ""
    if not remote_sha:
        return [_template_skipped(
            "template-version check skipped: could not parse git ls-remote output"
        )]
    local_sha = commit.rsplit("-g", 1)[-1] if "-g" in commit else commit
    if not remote_sha.startswith(local_sha) and not local_sha.startswith(remote_sha):
        return [
            Finding(
                "template.stale",
                "finding",
                f"Local template at {local_sha[:8]} but remote main is at {remote_sha[:8]}",
                "bblocks-projects update",
            )
        ]
    return []
