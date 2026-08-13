"""The bblocks family contract — twelve checks `doctor` runs under `--family`.

See docs/the-family-contract.md for what each item means and why. Items 6,
7, and 8 are source-inspection heuristics; the import-graph BFS, the
denylist/allowlist tables, and the public-surface reader they share live in
`_source_scan.py`, along with the stated false negatives and false
positives for those three items. Items 11 and 12 hit the network — `gh api`
via `subprocess` and `api.anaconda.org` via `urlopen` — and only run under
`--check-remote`; every failure mode (missing `gh`, a timeout, a 403 that
means "cannot tell" rather than "unprotected", an unreachable host) degrades
to a `*_skipped` advisory rather than a false finding, mirroring
`doctor._template_skipped`.

No check reaches into `project.pyproject_data` directly — every check goes
through a `Project` accessor, so the parsing stays in one place.
"""

import json
import re
import subprocess
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from typing import Literal
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

import yaml

from bblocks.projects import _source_scan
from bblocks.projects.components import COMPONENTS_REGISTRY
from bblocks.projects.doctor import Finding, _component_installed
from bblocks.projects.installer import _parse_dep_name
from bblocks.projects.project import Project

# Shared timeout for both network checks. `gh api` and `urlopen` are given
# the same budget so neither item can stall `doctor` noticeably longer
# than the other.
_NETWORK_TIMEOUT = 8


@dataclass(frozen=True)
class ContractItem:
    """One numbered item of the bblocks family contract."""

    number: int
    key: str
    title: str
    codes: tuple[str, ...]  # every Finding.code this item can emit
    requires_project_type: Literal["package", "project"] | None = None
    needs_network: bool = False


FAMILY_CONTRACT: tuple[ContractItem, ...] = (
    ContractItem(1, "build_backend", "uv build backend", ("contract.build_backend",)),
    ContractItem(2, "ruff", "ruff", ("contract.ruff",)),
    ContractItem(3, "ty", "ty", ("contract.ty",)),
    ContractItem(4, "pre_commit", "pre-commit", ("contract.pre_commit",)),
    ContractItem(
        5,
        "python_floor",
        "Python floor 3.12",
        ("contract.python_floor", "contract.python_floor_exempt"),
    ),
    ContractItem(
        6,
        "readerkit",
        "readerkit for HTTP and caching",
        ("contract.readerkit", "contract.readerkit_skipped"),
    ),
    ContractItem(
        7,
        "cache",
        "Cache redirectable and disableable",
        (
            "contract.cache_redirect",
            "contract.cache_env_var",
            "contract.cache_disable",
            "contract.cache_skipped",
        ),
    ),
    ContractItem(
        8,
        "import_time",
        "No import-time side effects",
        (
            "contract.import_io",
            "contract.import_opaque",
            "contract.import_unreadable",
            "contract.import_no_package",
        ),
    ),
    ContractItem(9, "no_caps", "No upper-bound pins", ("contract.dependency_cap",)),
    ContractItem(
        10,
        "oidc",
        "OIDC publishing",
        ("contract.oidc_publish", "contract.oidc_publish_unscoped"),
        requires_project_type="package",
    ),
    ContractItem(
        11,
        "branch_protection",
        "Branch protection",
        ("contract.branch_protection", "contract.branch_protection_skipped"),
        needs_network=True,
    ),
    ContractItem(
        12,
        "conda_forge",
        "conda-forge feedstock",
        ("contract.conda_forge", "contract.conda_forge_skipped"),
        requires_project_type="package",
        needs_network=True,
    ),
)

FLOOR = (3, 12)
FLOOR_EXEMPT: frozenset[str] = frozenset({"dcp-tools", "dcp_tools"})


@cache
def na_item_keys(project: Project) -> frozenset[str]:
    """`ContractItem.key`s that are not applicable to `project`.

    An item's checks return no findings when the project satisfies it, when
    it doesn't need it, and — for items 6 and 7 — when the source scan
    couldn't determine which of those two it is. All three must not render
    the same `✓`: only the middle one is n/a. Covers:

    - item 6 (`readerkit`) when the package definitely does not fetch;
    - item 7 (`cache`) when the package definitely does not cache;
    - any item whose `requires_project_type` disagrees with
      `project.detect_type()` (items 10 and 12, today).

    Items 6 and 7 use `_scan_evidence_status` for the same three-way split
    `_check_readerkit`/`_check_cache_contract` use, so this set and those
    checks' `*_skipped` advisories can never disagree about which n/a is
    real: a "could not determine" result is excluded from `na` here and
    left for the check functions to surface as an advisory instead — see
    `_scan_evidence_status`.

    The `readerkit` package itself is excluded from the first two: its
    checks pass it outright (the provider exemption in `_check_readerkit`
    and `_check_cache_contract`), which is a real `✓`, not an n/a.

    Memoized per-`Project` — `_source_scan.scan_package` is already
    memoized, but `package_fetches`/`package_caches` re-walk its result on
    every call, and both the CLI's `run_checks` and its renderer call this
    for the same project in one `doctor` invocation.
    """
    detected = project.detect_type()
    na = {
        item.key
        for item in FAMILY_CONTRACT
        if item.requires_project_type is not None
        and item.requires_project_type != detected
    }
    is_readerkit_itself = (
        _source_scan.normalize_name(project.get_project_name() or "") == "readerkit"
    )
    if not is_readerkit_itself:
        modules = _source_scan.scan_package(project)
        fetches = modules is not None and _source_scan.package_fetches(project, modules)
        caches = modules is not None and _source_scan.package_caches(project, modules)
        if _scan_evidence_status(modules, fetches) == "absent":
            na.add("readerkit")
        if _scan_evidence_status(modules, caches) == "absent":
            na.add("cache")
    return frozenset(na)


_ScanEvidenceStatus = Literal["present", "absent", "unknown"]


def _scan_evidence_status(
    modules: tuple[_source_scan.ModuleScan, ...] | None, found: bool
) -> _ScanEvidenceStatus:
    """Three-way outcome for an item-6/7 evidence detector (`package_fetches`,
    `package_caches`): the evidence is there, it is genuinely absent, or the
    scan can't back up either claim.

    `modules is None` means `scan_package` never got a package root to walk
    — no evidence was ever gathered, so this is "unknown", not "absent".
    `found` being True stands on its own regardless of parse failures
    elsewhere: whatever tripped the detector was actually read, so the
    scan's other gaps don't undermine it. `found` being False is only
    trustworthy as "absent" when every module parsed cleanly — a False
    result reached while some module has `.error` set is indistinguishable
    from "the evidence was sitting in the module that couldn't be read",
    which is exactly the case a syntax error hides a bare `import requests`
    behind. That case is "unknown" too, not "absent".
    """
    if modules is None:
        return "unknown"
    if found:
        return "present"
    if any(module.error is not None for module in modules):
        return "unknown"
    return "absent"


def _scan_gap_reason(
    project: Project, modules: tuple[_source_scan.ModuleScan, ...] | None
) -> str:
    """Why an item-6/7 scan landed on `"unknown"`, for a `*_skipped` message."""
    if modules is None:
        return "no package found under src/"
    errored = [m for m in modules if m.error is not None]
    names = ", ".join(_relpath(project, m.path) for m in errored)
    noun = "module" if len(errored) == 1 else "modules"
    return f"{len(errored)} {noun} could not be parsed ({names})"


_UV_BUILD_REMEDIATION = (
    'Set build-backend = "uv_build" and requires = ["uv_build>=0.11.29,<0.12"] '
    "in [build-system]"
)


def run_contract_checks(project: Project, *, check_remote: bool) -> list[Finding]:
    """Run every family-contract check, in item-number order."""
    findings: list[Finding] = []
    findings += _check_build_backend(project)
    findings += _check_ruff(project)
    findings += _check_ty(project)
    findings += _check_pre_commit(project)
    findings += _check_python_floor(project)
    findings += _check_readerkit(project)
    findings += _check_cache_contract(project)
    findings += _check_import_time(project)
    findings += _check_dependency_cap(project)
    findings += _check_oidc_publish(project)
    findings += _check_branch_protection(project, check_remote=check_remote)
    findings += _check_conda_forge(project, check_remote=check_remote)
    return findings


# --- item 1: uv build backend --------------------------------------------


def _check_build_backend(project: Project) -> list[Finding]:
    backend = project.get_build_backend()
    if backend == "uv_build":
        return []
    actual = (
        f"build-backend is {backend!r}, not uv_build"
        if backend
        else ("no [build-system] table")
    )
    return [Finding("contract.build_backend", "finding", actual, _UV_BUILD_REMEDIATION)]


# --- item 2: ruff -----------------------------------------------------------


def _check_ruff(project: Project) -> list[Finding]:
    if _component_installed(COMPONENTS_REGISTRY["ruff"], project):
        return []
    return [
        Finding(
            "contract.ruff",
            "finding",
            "ruff is not installed",
            "bblocks-projects add ruff",
        )
    ]


# --- item 3: ty -------------------------------------------------------------


def _check_ty(project: Project) -> list[Finding]:
    has_dep = project.has_dev_dependency("ty")
    has_config = project.has_config_section(
        "tool.ty.src"
    ) or project.has_config_section("tool.ty.environment")
    if has_dep and has_config:
        return []
    if not has_dep:
        message = "ty is not a dev dependency"
    else:
        message = "no [tool.ty.src] or [tool.ty.environment] section is configured"
    return [
        Finding(
            "contract.ty",
            "finding",
            message,
            "Add ty>=0.0.59 to the dev group and a [tool.ty.src] include = "
            '["src/<slug>"] section',
        )
    ]


# --- item 4: pre-commit ------------------------------------------------------


def _check_pre_commit(project: Project) -> list[Finding]:
    if _component_installed(COMPONENTS_REGISTRY["pre-commit"], project):
        return []
    return [
        Finding(
            "contract.pre_commit",
            "finding",
            "pre-commit is not installed",
            "bblocks-projects add pre-commit",
        )
    ]


# --- item 5: Python floor 3.12 -----------------------------------------------

_REQUIRES_PYTHON_RE = re.compile(r">=\s*(\d+)\.(\d+)")


def _check_python_floor(project: Project) -> list[Finding]:
    name = project.get_project_name()
    requires = project.get_requires_python()
    match = _REQUIRES_PYTHON_RE.search(requires) if requires else None
    if match is not None and (int(match.group(1)), int(match.group(2))) >= FLOOR:
        return []
    # The exemption is a fallback, not a precondition: a project on
    # FLOOR_EXEMPT that already meets the floor gets the real pass above,
    # not this advisory. The carve-out only ever softens a failure.
    if name in FLOOR_EXEMPT:
        return [
            Finding(
                "contract.python_floor_exempt",
                "advisory",
                f"python floor not enforced: {name} is on its own cadence",
                None,
            )
        ]
    quoted = f'"{requires}"' if requires else "unset"
    return [
        Finding(
            "contract.python_floor",
            "finding",
            f"requires-python is {quoted}; the family floor is 3.12",
            'Set requires-python = ">=3.12", target-version = "py312", and '
            '[tool.ty.environment] python-version = "3.12"',
        )
    ]


# --- item 6: readerkit --------------------------------------------------------

_READERKIT_REMEDIATION = (
    "Migrate HTTP and caching to readerkit (github.com/ONEcampaign/readerkit)"
)


def _readerkit_skipped(reason: str) -> Finding:
    return Finding(
        "contract.readerkit_skipped",
        "advisory",
        f"could not determine readerkit adoption: {reason}",
        None,
    )


def _check_readerkit(project: Project) -> list[Finding]:
    # Provider exemption: readerkit declares requests, requests-cache,
    # urllib3 to implement the contract, and cannot depend on itself to
    # satisfy it.
    if _source_scan.normalize_name(project.get_project_name() or "") == "readerkit":
        return []
    modules = _source_scan.scan_package(project)
    fetches = modules is not None and _source_scan.package_fetches(project, modules)
    status = _scan_evidence_status(modules, fetches)
    if status == "unknown":
        # "Could not scan" is not "doesn't fetch" — see _scan_evidence_status.
        # Surfacing this keeps the item from rendering the n/a dash it
        # hasn't earned, or worse, a green check over a hidden violation.
        return [_readerkit_skipped(_scan_gap_reason(project, modules))]
    if status == "absent":
        return []  # doesn't fetch: item is n/a
    assert modules is not None  # "present" only reachable with real modules
    if _source_scan.package_uses_readerkit(project, modules):
        return []
    evidence = _source_scan.fetch_evidence(project, modules)
    return [
        Finding(
            "contract.readerkit",
            "finding",
            f"{evidence} but does not depend on readerkit",
            _READERKIT_REMEDIATION,
        )
    ]


# --- item 7: the cache contract -----------------------------------------------

_SET_CACHE_DIR_RE = re.compile(r"^set_.*cache.*dir$")
_DISABLE_CACHE_RE = re.compile(r"^disable_.*cache.*$|^.*cache.*_disable$")


def _cache_skipped(reason: str) -> Finding:
    return Finding(
        "contract.cache_skipped",
        "advisory",
        f"could not determine cache-contract compliance: {reason}",
        None,
    )


def _check_cache_contract(project: Project) -> list[Finding]:
    # Same provider exemption as item 6, for the same reason: readerkit is
    # the delegate item 7c's second leg points at, and cannot delegate to
    # itself. See _source_scan's module docstring for the full reasoning —
    # readerkit's real disable path is a `cache_dir=None` kwarg, not a
    # `disable_*`-shaped name.
    if _source_scan.normalize_name(project.get_project_name() or "") == "readerkit":
        return []
    modules = _source_scan.scan_package(project)
    caches = modules is not None and _source_scan.package_caches(project, modules)
    status = _scan_evidence_status(modules, caches)
    if status == "unknown":
        # Same distinction item 6 draws: a scan that couldn't run, or
        # couldn't parse the one module that might have cached, is not
        # evidence the package doesn't cache.
        return [_cache_skipped(_scan_gap_reason(project, modules))]
    if status == "absent":
        return []  # doesn't cache: item is n/a
    assert modules is not None  # "present" only reachable with real modules
    surface = _source_scan.public_surface(project)
    findings: list[Finding] = []
    if not (
        _source_scan.public_surface_matches(surface, _SET_CACHE_DIR_RE)
        or _source_scan.has_cache_dir_kwarg(modules)
    ):
        findings.append(
            Finding(
                "contract.cache_redirect",
                "finding",
                "no set_cache_dir-shaped name or cache_dir kwarg found",
                "Expose set_cache_dir(path) (and reset_cache_dir()), or accept a "
                "cache_dir kwarg — see readerkit.resolve_cache_dir",
            )
        )
    if not (
        _source_scan.has_cache_env_var_literal(modules)
        or _source_scan.calls_resolve_cache_dir(modules)
    ):
        findings.append(
            Finding(
                "contract.cache_env_var",
                "finding",
                "no <SLUG>_CACHE_DIR-shaped literal or resolve_cache_dir(...) call found",
                "Read <SLUG_UPPER>_CACHE_DIR, or delegate to "
                "readerkit.resolve_cache_dir(app=..., app_version=...)",
            )
        )
    if not (
        _source_scan.public_surface_matches(surface, _DISABLE_CACHE_RE)
        # Delegating to readerkit means its disable path is this
        # package's disable path.
        or _source_scan.imports_readerkit(modules)
    ):
        findings.append(
            Finding(
                "contract.cache_disable",
                "finding",
                "no disable_*cache*-shaped name found, and readerkit is not imported",
                "Expose disable_cache() / enable_cache() so callers can turn "
                "caching off entirely",
            )
        )
    return findings


# --- item 8: no import-time side effects ---------------------------------------


def _relpath(project: Project, path: Path) -> str:
    try:
        return str(path.relative_to(project.path))
    except ValueError:
        return str(path)


def _check_import_time(project: Project) -> list[Finding]:
    modules = _source_scan.scan_package(project)
    if modules is None:
        # No package found under src/ — "could not scan" is not "no side
        # effects found". Surface it so this item can never render a bare
        # green checkmark it hasn't actually earned.
        return [
            Finding(
                "contract.import_no_package",
                "advisory",
                "no package found under src/; could not scan for import-time "
                "side effects",
                None,
            )
        ]
    findings: list[Finding] = []
    for module in modules:
        if module.error is not None:
            findings.append(
                Finding(
                    "contract.import_unreadable",
                    "advisory",
                    f"{_relpath(project, module.path)}: "
                    f"{type(module.error).__name__}: could not be parsed for "
                    "the import-time scan",
                    "Fix the syntax error, or exclude the module from the import graph",
                )
            )
            continue
        for call in module.calls:
            target = (
                _source_scan.resolve_call_target(call, module.aliases)
                or "<dynamic call>"
            )
            classification = _source_scan.classify_call(call, target)
            if classification == "deny":
                findings.append(
                    Finding(
                        "contract.import_io",
                        "finding",
                        f"{_relpath(project, module.path)}:{call.lineno} calls "
                        f"{target} at import time",
                        f"Move {target} inside a function or behind a lazy __getattr__",
                    )
                )
            elif classification == "opaque":
                findings.append(
                    Finding(
                        "contract.import_opaque",
                        "advisory",
                        f"{_relpath(project, module.path)}:{call.lineno} "
                        f"constructs {target}() at import time; doctor cannot "
                        "tell whether it touches the network, disk, or "
                        "global state",
                        f"Make {target}() lazy (a module __getattr__ or a "
                        "cached accessor), or confirm it is pure",
                    )
                )
    return findings


# --- item 9: no upper-bound pins ----------------------------------------------

# Detects a capped upper bound (`<`, `<=`, `~=`, or `==`). `!=` shares no
# characters with any of these alternatives, so it is never matched —
# `numpy>=1.26,!=2.0.0` produces no finding. The `(?!=)` on `==` only
# excludes matching `=` mid-run of a longer `===` (PEP 440 arbitrary
# equality); the search still finds `==` one character over, so
# `foo===1.0` is still flagged as a cap — arbitrary-equality pins are
# exactly as much a cap as `==`, and that is intended.
_CAP_RE = re.compile(r"(?:<=?|~=|==(?!=))\s*\d")
_LOWER_BOUND_RE = re.compile(r">=\s*([\w.*+!-]+)")
_CAP_VERSION_RE = re.compile(r"(?:~=|==(?!=))\s*([\w.*+!-]+)")


def _check_dependency_cap(project: Project) -> list[Finding]:
    findings: list[Finding] = []
    for spec in project.iter_runtime_dependencies():
        stripped = spec.strip()
        name = _parse_dep_name(stripped)
        remainder = stripped[len(name) :]
        if not _CAP_RE.search(remainder):
            continue
        lower_match = _LOWER_BOUND_RE.search(remainder) or _CAP_VERSION_RE.search(
            remainder
        )
        if lower_match:
            remediation = f"Relax {stripped} to {name}>={lower_match.group(1)}"
        else:
            remediation = f"Remove the upper bound from {stripped}"
        findings.append(
            Finding(
                "contract.dependency_cap",
                "finding",
                f"{stripped} pins an upper bound on an external library",
                remediation,
            )
        )
    return findings


# --- item 10: OIDC publishing -------------------------------------------------

_PUBLISH_RE = re.compile(
    r"uv publish|twine upload|pypa/gh-action-pypi-publish|poetry publish", re.IGNORECASE
)
# `\b` instead of an end-of-line anchor: the shipped template, `oda_reader`,
# and `readerkit` all write this as `id-token: write  # <comment>`, so an
# anchored `\s*$` would false-positive every compliant workflow in the
# family. Used only by the text-fallback path below — the YAML path reads
# `permissions.id-token` as a structured value instead.
_OIDC_RE = re.compile(r"^\s*id-token:\s*write\b", re.MULTILINE)
_TOKEN_RE = re.compile(
    r"PYPI_API_TOKEN|PYPI_TOKEN|TWINE_PASSWORD|UV_PUBLISH_TOKEN|password:\s*\$\{\{\s*secrets\.",
    re.IGNORECASE,
)
# A secret bound to *some* variable, and a flag shape that passes a
# credential on the command line. Neither is suspicious alone — plenty of
# compliant jobs reference other secrets, and plenty of CLIs take a
# `-p`-shaped flag for something that isn't a password. Together, in a job
# that already matched `_PUBLISH_RE`, they are exactly the shape of the
# indirection `_TOKEN_RE`'s literal names miss: `env: CRED: ${{ secrets.X
# }}` feeding `run: uv publish --password "$CRED"`.
_SECRET_INTERPOLATION_RE = re.compile(r"secrets\.")
_CRED_FLAG_RE = re.compile(r"(?<!\S)(?:--password|--token|-p)(?!\S)")
_OIDC_REMEDIATION = (
    'Use PyPI trusted publishing: add "permissions: id-token: write", an '
    "environment: pypi block, and drop the token secret"
)


def _yaml_text_blob(*values: object) -> str:
    """Flatten parsed YAML back into `key: value` lines for regex scanning.

    `_TOKEN_RE`'s `password:\\s*\\$\\{\\{\\s*secrets\\.` half, and the
    secret/credential-flag pairing below, both depend on a mapping key
    sitting next to its value the way it does in the source file — a plain
    `str(dict)` repr or a depth-first walk that emits keys and values on
    separate lines would break that adjacency. This rebuilds it well enough
    for regex purposes without needing the original text span.
    """
    lines: list[str] = []

    def walk(value: object) -> None:
        if isinstance(value, dict):
            for key, val in value.items():
                if isinstance(val, dict | list):
                    lines.append(f"{key}:")
                    walk(val)
                else:
                    lines.append(f"{key}: {val}")
        elif isinstance(value, list):
            for item in value:
                walk(item)
        elif value is not None:
            lines.append(str(value))

    for value in values:
        walk(value)
    return "\n".join(lines)


def _job_has_oidc(job: dict, workflow_permissions: object) -> bool:
    """`id-token: write` in effect for `job`.

    A job's own `permissions:` block, when present, *replaces* the
    workflow-level default rather than merging with it — GitHub Actions
    semantics, not a bblocks convention — so a job with its own
    `permissions:` that omits `id-token: write` gets no credit for a
    workflow-level grant, and a different job's `permissions:` never counts
    here at all. Only a job with no `permissions:` of its own inherits the
    workflow-level block.
    """
    job_permissions = job.get("permissions")
    if job_permissions is not None:
        if job_permissions == "write-all":
            return True
        return (
            isinstance(job_permissions, dict)
            and job_permissions.get("id-token") == "write"
        )
    if workflow_permissions == "write-all":
        return True
    return (
        isinstance(workflow_permissions, dict)
        and workflow_permissions.get("id-token") == "write"
    )


def _check_publish_job(
    filename: str,
    job_id: str,
    job: dict,
    workflow_permissions: object,
    workflow_env: object,
) -> list[Finding]:
    """OIDC findings for one job, already known to run a publish step.

    Scoped to what this job can actually reach: its own `env`/`with`/`run`
    text, plus the workflow-level `env` it inherits. A secret bound in some
    unrelated job's `env`, or permissions granted to some unrelated job,
    are not reachable here and must not launder this job's credential use.
    """
    label = f"{filename} ({job_id})"
    blob = _yaml_text_blob(workflow_env, job)
    uses_token_credential = bool(_TOKEN_RE.search(blob)) or (
        _SECRET_INTERPOLATION_RE.search(blob) is not None
        and _CRED_FLAG_RE.search(blob) is not None
    )
    if uses_token_credential:
        message = f"{label} publishes with a PyPI token"
    elif not _job_has_oidc(job, workflow_permissions):
        message = f"{label} does not request id-token: write"
    else:
        return []
    return [Finding("contract.oidc_publish", "finding", message, _OIDC_REMEDIATION)]


def _check_oidc_publish_fallback(name: str, text: str, reason: str) -> list[Finding]:
    """The pre-YAML, whole-file text heuristic — plus an advisory saying so.

    Used when a workflow can't be parsed as YAML at all, or doesn't parse
    into the `jobs:`-mapping shape this check expects, or matches
    `_PUBLISH_RE` without any individual job owning the publish step — a
    syntax error, a reusable-workflow-call file, an anchor pyyaml can't
    resolve. This path is exactly the weak, whole-file heuristic the
    per-job rewrite exists to replace: it can't scope `id-token: write` or
    a secret to the actual publishing job the way `_check_publish_job`
    does, so a pass here is a weaker result than a pass from the
    structural path. The `contract.oidc_publish_unscoped` advisory makes
    that visible in the report — `reason` says which of the three
    situations above applied — rather than letting this item render an
    identical green check for a verification it didn't actually do. A
    missed distinction is still preferable to a crash or a silently
    skipped file, hence keeping the fallback rather than refusing to check
    at all.
    """
    findings: list[Finding] = [
        Finding(
            "contract.oidc_publish_unscoped",
            "advisory",
            f"{name}: {reason}, so the OIDC check fell back to a whole-file "
            "heuristic that cannot scope id-token: write or secret "
            "credentials to the publishing job specifically",
            None,
        )
    ]
    if _TOKEN_RE.search(text):
        message = f"{name} publishes with a PyPI token"
    elif not _OIDC_RE.search(text):
        message = f"{name} does not request id-token: write"
    else:
        return findings
    findings.append(
        Finding("contract.oidc_publish", "finding", message, _OIDC_REMEDIATION)
    )
    return findings


def _check_oidc_publish_workflow(name: str, text: str) -> list[Finding]:
    """Every OIDC finding for one publishing-shaped workflow file."""
    try:
        parsed = yaml.safe_load(text)
    except yaml.YAMLError as e:
        return _check_oidc_publish_fallback(
            name, text, f"could not be parsed as YAML ({type(e).__name__})"
        )
    jobs = parsed.get("jobs") if isinstance(parsed, dict) else None
    if not isinstance(jobs, dict):
        return _check_oidc_publish_fallback(
            name, text, "does not parse into a jobs: mapping"
        )
    workflow_permissions = parsed.get("permissions")
    workflow_env = parsed.get("env")
    findings: list[Finding] = []
    matched_job = False
    for job_id, job in jobs.items():
        if not isinstance(job, dict) or not _PUBLISH_RE.search(_yaml_text_blob(job)):
            continue
        matched_job = True
        findings += _check_publish_job(
            name, job_id, job, workflow_permissions, workflow_env
        )
    # `_PUBLISH_RE` matched the raw file (that's how this workflow ended up
    # in `publishing` below) but not any individual job — e.g. the publish
    # step lives in a `uses:`-called reusable workflow this file only
    # references by name. Fall back rather than silently clearing findings
    # for a file that is, by the raw-text signal, still a publishing
    # workflow.
    if not matched_job:
        return _check_oidc_publish_fallback(
            name, text, "the publish step could not be attributed to a specific job"
        )
    return findings


def _check_oidc_publish(project: Project) -> list[Finding]:
    if project.detect_type() != "package":
        return []
    workflows = project.read_workflows()
    publishing = {
        name: text for name, text in workflows.items() if _PUBLISH_RE.search(text)
    }
    if not publishing:
        return [
            Finding(
                "contract.oidc_publish",
                "finding",
                "no PyPI publishing workflow found",
                _OIDC_REMEDIATION,
            )
        ]
    findings: list[Finding] = []
    for name, text in sorted(publishing.items()):
        findings += _check_oidc_publish_workflow(name, text)
    return findings


# --- items 11-12: network -------------------------------------------------------

_BRANCH_PROTECTION_REMEDIATION = (
    "Enable a branch ruleset on main requiring a pull request and passing CI"
)
_CONDA_FORGE_REMEDIATION = (
    "Submit a recipe to conda-forge/staged-recipes (see the family contract docs)"
)


def _branch_protection_skipped(reason: str) -> Finding:
    return Finding(
        "contract.branch_protection_skipped",
        "advisory",
        f"branch-protection check skipped: {reason}",
        None,
    )


def _conda_forge_skipped(reason: str) -> Finding:
    return Finding(
        "contract.conda_forge_skipped",
        "advisory",
        f"feedstock check skipped: {reason}",
        None,
    )


def _run_gh_api(path: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["gh", "api", path],
        capture_output=True,
        text=True,
        timeout=_NETWORK_TIMEOUT,
        check=False,
    )


def _gh_output(result: subprocess.CompletedProcess[str]) -> str:
    return f"{result.stdout}\n{result.stderr}"


# Rule types that actually gate a merge into the branch. A ruleset can
# target `main` and carry only e.g. a `deletion` or `non_fast_forward`
# rule — real, but not what the remediation string promises ("requiring a
# pull request and passing CI"). Matches the classic-protection path's
# leniency (any protection at all counts): either half of that promise is
# enough, not both.
_MERGE_GATING_RULE_TYPES = frozenset({"pull_request", "required_status_checks"})
# Every ref-name shape GitHub rulesets use for "main": the default-branch
# alias, and the two forms a repo owner might type literally.
_MAIN_REF_ALIASES = ("~DEFAULT_BRANCH", "refs/heads/main", "main")


def _ruleset_covers_main(entry: object) -> bool:
    """A branch ruleset entry that actively protects `main` (or the default
    branch alias) by gating merges into it.

    Four things must all hold:

    - `target == "branch"`
    - `enforcement == "active"` — GitHub rulesets also carry `"evaluate"`
      (dry-run: findings are recorded but nothing is blocked) and
      `"disabled"`. Both enforce nothing, so a ruleset in either state is
      not protection.
    - `conditions.ref_name.include` names `main` (or its alias) — and
      `conditions.ref_name.exclude` does not. A ruleset can `include`
      `~DEFAULT_BRANCH` for a broad "protect every default-ish branch"
      intent and then carve `main` back out with `exclude`; GitHub applies
      `exclude` after `include`, so a ref listed in both is not covered.
      Reading `include` alone would count that ruleset as protecting a
      branch it explicitly protects nothing on.
    - `rules` contains something that actually gates a merge (a
      `pull_request` requirement or required status checks) — a ruleset
      that only restricts e.g. tag deletion still matches `target` and
      `conditions` but guarantees none of what this item's remediation
      promises.
    """
    if not isinstance(entry, dict) or entry.get("target") != "branch":
        return False
    if entry.get("enforcement") != "active":
        return False
    conditions = entry.get("conditions")
    ref_name = conditions.get("ref_name") if isinstance(conditions, dict) else None
    included = ref_name.get("include") if isinstance(ref_name, dict) else None
    excluded = ref_name.get("exclude") if isinstance(ref_name, dict) else None
    included_main = isinstance(included, list) and any(
        ref in _MAIN_REF_ALIASES for ref in included
    )
    excluded_main = isinstance(excluded, list) and any(
        ref in _MAIN_REF_ALIASES for ref in excluded
    )
    if not included_main or excluded_main:
        return False
    rules = entry.get("rules")
    if not isinstance(rules, list):
        return False
    return any(
        isinstance(rule, dict) and rule.get("type") in _MERGE_GATING_RULE_TYPES
        for rule in rules
    )


def _classic_protection_gates_main(body: object) -> bool:
    """A classic branch-protection body that actually gates a merge into main.

    A 200 from the classic protection endpoint only means *some* protection
    is configured on the branch — it says nothing about what. Settings like
    `allow_force_pushes: false`, `allow_deletions: false`,
    `required_linear_history`, `required_conversation_resolution`, and
    `enforce_admins` are all real protections, but none of them stops a
    direct push straight to main without a pull request or passing CI,
    which is what this item's remediation promises. Only two settings do
    that, and either is sufficient:

    - `required_pull_request_reviews` is present — merging requires a pull
      request. `required_approving_review_count: 0` still counts: the count
      controls how many approvals are needed, not whether a PR is required
      at all, and it is `0` on every repo this check currently protects.
    - `required_status_checks` is present and names at least one check —
      an empty `{}` (no `contexts`/`checks` listed) requires nothing and is
      not evidence of anything.
    """
    if not isinstance(body, dict):
        return False
    if isinstance(body.get("required_pull_request_reviews"), dict):
        return True
    status_checks = body.get("required_status_checks")
    if not isinstance(status_checks, dict):
        return False
    checks = status_checks.get("checks")
    contexts = status_checks.get("contexts")
    return (isinstance(checks, list) and len(checks) > 0) or (
        isinstance(contexts, list) and len(contexts) > 0
    )


def _run_gh_api_or_skip(path: str) -> subprocess.CompletedProcess[str] | Finding:
    """Run `gh api <path>`; a skip Finding when `gh` itself couldn't run."""
    try:
        return _run_gh_api(path)
    except FileNotFoundError:
        return _branch_protection_skipped("gh is not installed")
    except subprocess.TimeoutExpired:
        return _branch_protection_skipped("gh api timed out")
    except OSError as e:
        # Broader than FileNotFoundError alone: a PermissionError on the gh
        # binary (or any other OSError running it) is exactly as much
        # "could not tell" as a missing binary, not a doctor crash.
        return _branch_protection_skipped(f"gh api could not run: {e}")


def _gh_error_reason(result: subprocess.CompletedProcess[str]) -> str:
    """A skip-reason for a non-zero `gh api` exit whose shape wasn't expected."""
    output = _gh_output(result)
    # A 403 means the token can't tell — not that the branch is unprotected.
    if "HTTP 403" in output:
        return "gh lacks permission to check (HTTP 403)"
    detail = output.strip()[:200] or "unknown error"
    return f"gh api failed: {detail}"


def _branch_protected_directly(slug: str) -> list[Finding] | None:
    """The classic branch-protection API. `None` means: fall through to rulesets."""
    result = _run_gh_api_or_skip(f"repos/{slug}/branches/main/protection")
    if isinstance(result, Finding):
        return [result]
    if result.returncode == 0:
        try:
            body = json.loads(result.stdout)
        except json.JSONDecodeError:
            return [
                _branch_protection_skipped(
                    "gh api branch protection output was not valid JSON"
                )
            ]
        if _classic_protection_gates_main(body):
            return []
        # Classic protection is configured but doesn't gate a merge (e.g.
        # force-push/deletion restrictions only) — a ruleset might still
        # cover main, so fall through instead of failing outright.
        return None
    output = _gh_output(result)
    if "Branch not protected" in output and "HTTP 403" not in output:
        return None
    return [_branch_protection_skipped(_gh_error_reason(result))]


def _branch_protected_by_ruleset(slug: str) -> list[Finding]:
    result = _run_gh_api_or_skip(f"repos/{slug}/rulesets")
    if isinstance(result, Finding):
        return [result]
    if result.returncode != 0:
        return [_branch_protection_skipped(_gh_error_reason(result))]
    try:
        parsed = json.loads(result.stdout)
    except json.JSONDecodeError:
        return [_branch_protection_skipped("gh api rulesets output was not valid JSON")]
    if not isinstance(parsed, list):
        # An error object or a paginated envelope, not a rulesets array —
        # "not the shape we expected" is "could not tell", same as every
        # other unexpected shape in these two network checks. It is not
        # evidence the branch is unprotected.
        return [_branch_protection_skipped("gh api rulesets output was not a list")]
    if any(_ruleset_covers_main(entry) for entry in parsed):
        return []
    return [
        Finding(
            "contract.branch_protection",
            "finding",
            f"main is not protected on {slug}",
            _BRANCH_PROTECTION_REMEDIATION,
        )
    ]


def _check_branch_protection(project: Project, *, check_remote: bool) -> list[Finding]:
    if not check_remote:
        return [_branch_protection_skipped("not checked (pass --check-remote)")]
    slug = project.get_git_remote_slug()
    if slug is None:
        return [_branch_protection_skipped("no GitHub origin remote found")]
    direct = _branch_protected_directly(slug)
    if direct is not None:
        return direct
    return _branch_protected_by_ruleset(slug)


def _conda_forge_guard(project: Project, *, check_remote: bool) -> list[Finding] | None:
    """Pre-network gates for item 12. `None` means: proceed to the network call."""
    if project.detect_type() != "package":
        return []
    if not check_remote:
        return [_conda_forge_skipped("not checked (pass --check-remote)")]
    if not project.get_project_name():
        return [_conda_forge_skipped("project name could not be determined")]
    return None


def _conda_forge_status(url: str) -> int | Finding:
    """The HTTP status for `url`, or a skip Finding when the host is unreachable."""
    try:
        with urlopen(url, timeout=_NETWORK_TIMEOUT) as response:
            return response.status
    except HTTPError as e:
        return e.code
    except (URLError, TimeoutError) as e:
        return _conda_forge_skipped(
            f"{type(e).__name__}: could not reach api.anaconda.org"
        )


def _check_conda_forge(project: Project, *, check_remote: bool) -> list[Finding]:
    guard = _conda_forge_guard(project, check_remote=check_remote)
    if guard is not None:
        return guard
    # PEP-503 normalisation is load-bearing: the same package 404s under its
    # underscored form and 200s under its hyphenated one.
    normalized = _source_scan.normalize_name(project.get_project_name() or "")
    result = _conda_forge_status(
        f"https://api.anaconda.org/package/conda-forge/{normalized}"
    )
    if isinstance(result, Finding):
        return [result]
    if result == 200:
        return []
    if result == 404:
        return [
            Finding(
                "contract.conda_forge",
                "finding",
                f"no conda-forge feedstock for {normalized}",
                _CONDA_FORGE_REMEDIATION,
            )
        ]
    return [
        _conda_forge_skipped(f"unexpected HTTP status {result} from api.anaconda.org")
    ]
