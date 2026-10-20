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
    ("contract", "Family contract"),
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


def is_family_project(project: Project, *, force: bool = False) -> bool:
    """True when the family contract applies to this project.

    True when `.copier-answers.yml` records `preset: family`, or when
    `force` is set (the CLI's `--family` escape hatch, for family repos
    that predate the preset question and so have no answers file at all).
    """
    return force or project.get_preset() == "family"


def run_checks(
    project: Project,
    *,
    check_updates: bool,
    family: bool = False,
    check_remote: bool = False,
) -> list[Finding]:
    """Run all health checks against a bblocks-managed project.

    Catastrophic findings short-circuit further checks. The caller is
    responsible for refusing non-bblocks-managed projects (no pyproject.toml,
    or no `.copier-answers.yml` unless `family` is set) before invoking this
    function — those refusals are not modeled as findings.

    `family` runs the family-contract checks (see `contract.py`) in addition
    to the usual scaffolding/drift/components/template checks. When
    `.copier-answers.yml` is absent, the scaffolding/drift/components checks
    that compare against it are skipped rather than treated as catastrophic;
    under `family`, a `contract.not_adopted` advisory names the gap.
    `check_remote` additionally runs the two contract checks that hit the
    network (branch protection, conda-forge); without it, both degrade to a
    `*_skipped` advisory.
    """
    findings: list[Finding] = []
    findings += _check_pyproject_parseable(project)
    answers_present = (project.path / ".copier-answers.yml").exists()
    if answers_present:
        findings += _check_copier_answers_parseable(project)
    if any(f.severity == "catastrophic" for f in findings):
        return findings
    if answers_present:
        findings += _check_drift_project_type(project)
        findings += _check_drift_project_slug(project)
        findings += _check_drift_python_version(project)
        findings += _check_components(project)
        if check_updates:
            findings += _check_template_version(project)
    elif family:
        findings.append(
            Finding(
                "contract.not_adopted",
                "advisory",
                "Not generated from the bblocks template (no .copier-answers.yml); "
                "scaffolding, drift and component checks skipped",
                "See docs/adopting-an-existing-project.md",
            )
        )
    if family:
        from bblocks.projects.contract import run_contract_checks  # noqa: PLC0415

        findings += run_contract_checks(project, check_remote=check_remote)
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
    except OSError as e:
        # Same treatment as _check_copier_answers_parseable's read below: a
        # pyproject.toml that exists but can't be opened (permission denied,
        # a broken symlink) is exactly as unable to proceed as a malformed
        # one, not a doctor crash.
        return [
            Finding(
                "scaffolding.pyproject_unreadable",
                "catastrophic",
                f"pyproject.toml could not be read: {e}",
                "Ensure pyproject.toml exists and is readable",
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
    if answer not in ("package", "project", "research"):
        return []
    slug = project.copier_answers.get("project_slug") or project.get_project_slug()
    # `research` is a legacy alias for `project` (template was renamed); both
    # share the same expected layout.
    if answer in ("project", "research"):
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
    # `project_slug` names the import package (`src/<slug>/`). uv_build's
    # `module-name` sets that package when it differs from the distribution
    # name, as `development-finance` does with module `dfo`.
    module_name = project.get_module_name()
    actual_slug = module_name or project.get_project_slug()
    if answer_slug == actual_slug:
        return []
    if module_name:
        actual = f"pyproject module-name is {module_name!r}"
        field = "[tool.uv.build-backend] module-name"
    else:
        actual = f"pyproject name slugifies to {actual_slug!r}"
        field = "[project].name"
    return [
        Finding(
            "drift.project_slug_mismatch",
            "finding",
            f"project_slug={answer_slug!r} but {actual}",
            f"Update either .copier-answers.yml or {field} in pyproject.toml",
        )
    ]


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
    categories = (
        (
            comp.template_files,
            lambda r: project.tooling_path(r.removesuffix(".jinja")).exists(),
        ),
        (comp.pyproject_sections, project.has_config_section),
        (comp.dev_deps, lambda d: project.has_dev_dependency(_parse_dep_name(d))),
    )
    checks = [any(pred(item) for item in items) for items, pred in categories if items]
    return all(checks) if checks else False


def _check_components(project: Project) -> list[Finding]:
    findings: list[Finding] = []
    project_type = project.detect_type()
    include_pytest = bool(project.copier_answers.get("include_pytest", False))
    for comp in COMPONENTS_REGISTRY.values():
        if comp.requires_project_type and comp.requires_project_type != project_type:
            continue
        # Pytest is opt-in for project-type repos; skip when the user opted out.
        if comp.name == "pytest" and project_type != "package" and not include_pytest:
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
        return [
            _template_skipped(f"template-version check skipped: {type(e).__name__}")
        ]
    if result.returncode != 0:
        return [
            _template_skipped(
                f"template-version check skipped: git ls-remote failed (exit {result.returncode})"
            )
        ]
    line = result.stdout.strip().splitlines()[0] if result.stdout.strip() else ""
    remote_sha = line.split("\t", 1)[0] if line else ""
    if not remote_sha:
        return [
            _template_skipped(
                "template-version check skipped: could not parse git ls-remote output"
            )
        ]
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
