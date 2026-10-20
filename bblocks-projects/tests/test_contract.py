"""Tests for the bblocks family contract checks (items 1-5, 9, 10)."""

import json
from pathlib import Path

import pytest

from bblocks.projects.contract import (
    FAMILY_CONTRACT,
    FLOOR,
    FLOOR_EXEMPT,
    ContractItem,
    _check_build_backend,
    _check_dependency_cap,
    _check_oidc_publish,
    _check_pre_commit,
    _check_python_floor,
    _check_ruff,
    _check_ty,
    run_contract_checks,
)
from bblocks.projects.doctor import Finding, is_family_project, run_checks
from bblocks.projects.project import Project
from tests._helpers import make_bblocks_project, make_family_project

# Absolute path to the template's real release workflow, so item 10's
# "passes on the template" test exercises the actual shipped text rather
# than a hand-copied approximation. Jinja placeholders elsewhere in the
# file don't affect the plain-text regexes this check runs.
_TEMPLATE_RELEASE_WORKFLOW = (
    Path(__file__).resolve().parents[2]
    / "template"
    / "{% if project_type == 'package' %}.github{% endif %}"
    / "workflows"
    / "release.yml.jinja"
)


def _codes(findings: list[Finding]) -> list[str]:
    return [f.code for f in findings]


# --- registry sanity ----------------------------------------------------------


def test_family_contract_has_twelve_items() -> None:
    assert len(FAMILY_CONTRACT) == 12
    assert [item.number for item in FAMILY_CONTRACT] == list(range(1, 13))


def test_oidc_item_claims_the_unscoped_advisory_code() -> None:
    """`contract.oidc_publish_unscoped` must render nested under item 10,
    not fall into the CLI's unclaimed-codes bucket (see
    `test_render_contract_panel_buckets_unclaimed_codes` in test_cli.py) —
    unlike `contract.not_adopted`, which claims no item on purpose.
    """
    oidc_item = next(item for item in FAMILY_CONTRACT if item.key == "oidc")
    assert "contract.oidc_publish_unscoped" in oidc_item.codes


@pytest.mark.parametrize(
    "code", ["contract.readerkit_skipped", "contract.readerkit_exempt"]
)
def test_readerkit_item_claims_its_advisory_codes(code: str) -> None:
    """Item 6's advisories must render nested under item 6, not fall into
    the CLI's unclaimed-codes bucket."""
    item = next(i for i in FAMILY_CONTRACT if i.key == "readerkit")
    assert code in item.codes


def test_cache_item_claims_the_skipped_advisory_code() -> None:
    """`contract.cache_skipped` must render nested under item 7, not fall
    into the CLI's unclaimed-codes bucket."""
    item = next(i for i in FAMILY_CONTRACT if i.key == "cache")
    assert "contract.cache_skipped" in item.codes


def test_floor_is_3_12() -> None:
    assert FLOOR == (3, 12)


def test_floor_exempt_covers_both_slug_forms() -> None:
    assert {"dcp-tools", "dcp_tools"} <= FLOOR_EXEMPT


def test_contract_item_is_frozen() -> None:
    item = ContractItem(1, "x", "X", ("contract.x",))
    with pytest.raises((AttributeError, TypeError)):
        item.number = 2  # type: ignore[misc]


# --- item 1: uv build backend --------------------------------------------------


def test_build_backend_passes_uv_build(tmp_path: Path) -> None:
    p = make_bblocks_project(tmp_path)
    assert _check_build_backend(Project(p)) == []


def test_build_backend_flags_poetry_core(tmp_path: Path) -> None:
    p = make_bblocks_project(tmp_path, build_backend="poetry.core.masonry.api")
    findings = _check_build_backend(Project(p))
    assert _codes(findings) == ["contract.build_backend"]
    assert findings[0].severity == "finding"
    assert "poetry.core.masonry.api" in findings[0].message


# --- item 2: ruff ---------------------------------------------------------------


def test_ruff_missing_flags(tmp_path: Path) -> None:
    p = make_bblocks_project(
        tmp_path, with_components=("pre-commit", "ci", "pytest", "pypi-publish")
    )
    findings = _check_ruff(Project(p))
    assert _codes(findings) == ["contract.ruff"]
    assert findings[0].remediation == "bblocks-projects add ruff"


def test_ruff_present_passes(tmp_path: Path) -> None:
    p = make_bblocks_project(tmp_path)
    assert _check_ruff(Project(p)) == []


# --- item 3: ty -------------------------------------------------------------------


def test_ty_missing_dep_flags(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "demo"\nrequires-python = ">=3.12"\n\n'
        '[tool.ty.src]\ninclude = ["src/demo"]\n',
        encoding="utf-8",
    )
    findings = _check_ty(Project(tmp_path))
    assert _codes(findings) == ["contract.ty"]
    assert "dev dependency" in findings[0].message


def test_ty_missing_config_flags(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "demo"\nrequires-python = ">=3.12"\n\n'
        '[dependency-groups]\ndev = ["ty>=0.0.59"]\n',
        encoding="utf-8",
    )
    findings = _check_ty(Project(tmp_path))
    assert _codes(findings) == ["contract.ty"]
    assert "tool.ty" in findings[0].message


def test_ty_present_passes(tmp_path: Path) -> None:
    p = make_bblocks_project(tmp_path)
    assert _check_ty(Project(p)) == []


# --- item 4: pre-commit -----------------------------------------------------------


def test_pre_commit_missing_flags(tmp_path: Path) -> None:
    p = make_bblocks_project(
        tmp_path, with_components=("ruff", "ci", "pytest", "pypi-publish")
    )
    findings = _check_pre_commit(Project(p))
    assert _codes(findings) == ["contract.pre_commit"]


def test_pre_commit_present_passes(tmp_path: Path) -> None:
    p = make_bblocks_project(tmp_path)
    assert _check_pre_commit(Project(p)) == []


# --- item 5: Python floor 3.12 ------------------------------------------------------


def test_python_floor_below_fails(tmp_path: Path) -> None:
    p = make_bblocks_project(tmp_path, python_version="3.11")
    findings = _check_python_floor(Project(p))
    assert _codes(findings) == ["contract.python_floor"]
    assert findings[0].severity == "finding"
    assert '">=3.11"' in findings[0].message


@pytest.mark.parametrize("version", ["3.12", "3.13"])
def test_python_floor_at_or_above_passes(tmp_path: Path, version: str) -> None:
    p = make_bblocks_project(tmp_path, python_version=version)
    assert _check_python_floor(Project(p)) == []


def test_python_floor_exempt_is_advisory(tmp_path: Path) -> None:
    p = make_bblocks_project(tmp_path, slug="dcp_tools", python_version="3.11")
    findings = _check_python_floor(Project(p))
    assert _codes(findings) == ["contract.python_floor_exempt"]
    assert findings[0].severity == "advisory"


def test_python_floor_exempt_project_that_meets_floor_passes_cleanly(
    tmp_path: Path,
) -> None:
    """The exemption is a fallback for a project that fails the floor, not a
    precondition checked before the floor itself. dcp-tools is exempt but
    already requires-python >=3.13 — it must get the real pass ([]), not
    the "not enforced" advisory (reproduces the bblocks-datacommons-tools
    false report)."""
    p = make_bblocks_project(tmp_path, slug="dcp_tools", python_version="3.13")
    assert _check_python_floor(Project(p)) == []


def test_python_floor_missing_requires_python_fails(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "demo"\n', encoding="utf-8"
    )
    findings = _check_python_floor(Project(tmp_path))
    assert _codes(findings) == ["contract.python_floor"]
    assert "unset" in findings[0].message


# --- item 9: no upper-bound pins ------------------------------------------------------


def test_dependency_cap_flags_tilde_equals(tmp_path: Path) -> None:
    p = make_bblocks_project(tmp_path, dependencies=("pandas-stubs~=2.3.3",))
    findings = _check_dependency_cap(Project(p))
    assert _codes(findings) == ["contract.dependency_cap"]
    assert "pandas-stubs~=2.3.3 pins an upper bound" in findings[0].message
    assert findings[0].remediation == "Relax pandas-stubs~=2.3.3 to pandas-stubs>=2.3.3"


def test_dependency_cap_flags_less_than(tmp_path: Path) -> None:
    p = make_bblocks_project(tmp_path, dependencies=("pydantic>=2.9,<3.0",))
    findings = _check_dependency_cap(Project(p))
    assert _codes(findings) == ["contract.dependency_cap"]
    assert findings[0].remediation == "Relax pydantic>=2.9,<3.0 to pydantic>=2.9"


def test_dependency_cap_ignores_not_equals(tmp_path: Path) -> None:
    p = make_bblocks_project(tmp_path, dependencies=("numpy>=1.26,!=2.0.0",))
    assert _check_dependency_cap(Project(p)) == []


def test_dependency_cap_ignores_build_system(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "demo"\ndependencies = []\n\n'
        '[build-system]\nrequires = ["uv_build>=0.12.3,<0.13"]\nbuild-backend = "uv_build"\n',
        encoding="utf-8",
    )
    assert _check_dependency_cap(Project(tmp_path)) == []


def test_dependency_cap_one_finding_per_dep(tmp_path: Path) -> None:
    """Four caps picked for this fixture, not mirrored from a live repo's
    dependency list (which would drift out from under this assertion)."""
    p = make_bblocks_project(
        tmp_path,
        dependencies=(
            "pandas-stubs~=2.3.3",
            "pydantic>=2.9,<3.0",
            "numpy<2.0",
            "requests==2.31.0",
        ),
    )
    findings = _check_dependency_cap(Project(p))
    assert len(findings) == 4
    assert all(f.code == "contract.dependency_cap" for f in findings)


def test_dependency_cap_ignores_dev_named_optional_group(tmp_path: Path) -> None:
    """The dev-named optional-dependencies group is dev tooling, not a
    runtime extra a consumer resolves against — consistent with
    Project.has_dev_dependency's own reading of that table. Reproduces the
    imf-reader false positive: `dev = ["ruff~=0.15.0"]` must not flag."""
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "demo"\ndependencies = []\n\n'
        "[project.optional-dependencies]\n"
        'dev = ["ruff~=0.15.0", "pytest~=8.0"]\n',
        encoding="utf-8",
    )
    assert _check_dependency_cap(Project(tmp_path)) == []


def test_dependency_cap_still_flags_other_optional_groups(tmp_path: Path) -> None:
    """Only the dev-named group is excluded — every other optional-dependencies
    list is still scanned for caps."""
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "demo"\ndependencies = []\n\n'
        "[project.optional-dependencies]\n"
        'dev = ["ruff~=0.15.0"]\n'
        'plots = ["matplotlib<4.0"]\n',
        encoding="utf-8",
    )
    findings = _check_dependency_cap(Project(tmp_path))
    assert _codes(findings) == ["contract.dependency_cap"]
    assert "matplotlib<4.0" in findings[0].message


def test_dependency_cap_flags_0x_family_sibling(tmp_path: Path) -> None:
    """Item 9 is absolute: no exemption for a family sibling or for a
    dependency still on a 0.x version. `imf-reader`'s
    `readerkit>=0.1.0,<0.2` must be flagged like any other capped dep."""
    p = make_bblocks_project(tmp_path, dependencies=("readerkit>=0.1.0,<0.2",))
    findings = _check_dependency_cap(Project(p))
    assert _codes(findings) == ["contract.dependency_cap"]


# --- item 10: OIDC publishing ------------------------------------------------------


def test_oidc_passes_on_template_release_workflow(tmp_path: Path) -> None:
    """The template writes a `{% raw %}...{% endraw %}` Jinja block inside a
    YAML value (`key: {% raw %}...`), which is not valid YAML — this file
    exercises the "could not be parsed as YAML" fallback for real, not as a
    contrived fixture. The underlying text is still OIDC-compliant, so the
    fallback's own verdict is a pass; only the accompanying advisory (not a
    `finding`, so `--strict` still exits 0) marks the check as unscoped.
    """
    text = _TEMPLATE_RELEASE_WORKFLOW.read_text(encoding="utf-8")
    p = make_bblocks_project(
        tmp_path, with_components=(), workflows={"release.yml": text}
    )
    findings = _check_oidc_publish(Project(p))
    assert _codes(findings) == ["contract.oidc_publish_unscoped"]
    assert findings[0].severity == "advisory"
    assert "could not be parsed as YAML" in findings[0].message


def test_oidc_flags_uv_publish_token(tmp_path: Path) -> None:
    workflow = (
        "name: Release\non:\n  push:\n    tags: ['v*']\n"
        "jobs:\n  publish:\n    runs-on: ubuntu-latest\n"
        "    env:\n"
        "      UV_PUBLISH_TOKEN: ${{ secrets.PYPI_API_TOKEN }}\n"
        "    steps:\n      - run: uv publish\n"
    )
    p = make_bblocks_project(
        tmp_path, with_components=(), workflows={"release.yml": workflow}
    )
    findings = _check_oidc_publish(Project(p))
    assert _codes(findings) == ["contract.oidc_publish"]
    assert "publishes with a PyPI token" in findings[0].message


def test_oidc_flags_gh_action_password(tmp_path: Path) -> None:
    workflow = (
        "name: Release\non:\n  push:\n    tags: ['v*']\n"
        "jobs:\n  publish:\n    runs-on: ubuntu-latest\n"
        "    steps:\n      - uses: pypa/gh-action-pypi-publish@release/v1\n"
        "        with:\n          password: ${{ secrets.PYPI_API_TOKEN }}\n"
    )
    p = make_bblocks_project(
        tmp_path, with_components=(), workflows={"release.yml": workflow}
    )
    findings = _check_oidc_publish(Project(p))
    assert _codes(findings) == ["contract.oidc_publish"]
    assert "publishes with a PyPI token" in findings[0].message


def test_oidc_ignores_id_token_in_unrelated_job(tmp_path: Path) -> None:
    """`id-token: write` on a job that never publishes must not certify a
    sibling job that does. Only the publishing job's own permissions (or
    the workflow-level block it inherits) count."""
    workflow = (
        "name: Release\non:\n  push:\n    tags: ['v*']\n"
        "jobs:\n"
        "  lint:\n"
        "    runs-on: ubuntu-latest\n"
        "    permissions:\n"
        "      id-token: write\n"
        "    steps:\n"
        "      - run: ruff check .\n"
        "  publish:\n"
        "    runs-on: ubuntu-latest\n"
        "    steps:\n"
        "      - run: uv publish\n"
    )
    p = make_bblocks_project(
        tmp_path, with_components=(), workflows={"release.yml": workflow}
    )
    findings = _check_oidc_publish(Project(p))
    assert _codes(findings) == ["contract.oidc_publish"]
    assert "does not request id-token: write" in findings[0].message


def test_oidc_flags_indirect_secret_credential(tmp_path: Path) -> None:
    """A secret bound to an arbitrarily-named env var, then fed to a
    `--password`-shaped flag, is still token-based publishing even though
    no name in `_TOKEN_RE` appears anywhere in the file.
    """
    workflow = (
        "name: Release\non:\n  push:\n    tags: ['v*']\n"
        "jobs:\n"
        "  publish:\n"
        "    runs-on: ubuntu-latest\n"
        "    env:\n"
        "      CRED: ${{ secrets.SOME_ARBITRARY_NAME }}\n"
        "    steps:\n"
        '      - run: uv publish --password "$CRED"\n'
    )
    p = make_bblocks_project(
        tmp_path, with_components=(), workflows={"release.yml": workflow}
    )
    findings = _check_oidc_publish(Project(p))
    assert _codes(findings) == ["contract.oidc_publish"]
    assert "publishes with a PyPI token" in findings[0].message


def test_oidc_passes_with_job_level_permissions(tmp_path: Path) -> None:
    """`id-token: write` set directly on the publishing job, with no
    workflow-level `permissions:` block at all, is just as valid as the
    workflow-level form the other passing tests exercise."""
    workflow = (
        "name: Release\non:\n  push:\n    tags: ['v*']\n"
        "jobs:\n"
        "  publish:\n"
        "    runs-on: ubuntu-latest\n"
        "    permissions:\n"
        "      id-token: write\n"
        "    steps:\n"
        "      - run: uv publish\n"
    )
    p = make_bblocks_project(
        tmp_path, with_components=(), workflows={"release.yml": workflow}
    )
    assert _check_oidc_publish(Project(p)) == []


def test_oidc_malformed_yaml_falls_back_with_advisory(tmp_path: Path) -> None:
    """Cause A: a workflow that fails to parse at all degrades to the text
    heuristic instead of letting `yaml.YAMLError` escape `doctor` — and
    says so via `contract.oidc_publish_unscoped`, alongside the fallback's
    own verdict.
    """
    workflow = "name: Release\ton: push\njobs:\n  publish:\n    steps:\n      - run: uv publish\n"
    p = make_bblocks_project(
        tmp_path, with_components=(), workflows={"release.yml": workflow}
    )
    findings = _check_oidc_publish(Project(p))
    assert _codes(findings) == [
        "contract.oidc_publish_unscoped",
        "contract.oidc_publish",
    ]
    advisory, verdict = findings
    assert advisory.severity == "advisory"
    assert "could not be parsed as YAML" in advisory.message
    assert verdict.severity == "finding"
    assert "does not request id-token: write" in verdict.message


def test_oidc_unscoped_advisory_when_no_jobs_mapping(tmp_path: Path) -> None:
    """Cause B: the file is valid YAML and matches `_PUBLISH_RE` on raw
    text (a comment mentioning `uv publish`), but doesn't parse into the
    `jobs:`-mapping shape this check expects at all.
    """
    workflow = "name: release\n# migrate this job to `uv publish` eventually\n"
    p = make_bblocks_project(
        tmp_path, with_components=(), workflows={"release.yml": workflow}
    )
    findings = _check_oidc_publish(Project(p))
    assert _codes(findings) == [
        "contract.oidc_publish_unscoped",
        "contract.oidc_publish",
    ]
    advisory, verdict = findings
    assert advisory.severity == "advisory"
    assert "does not parse into a jobs: mapping" in advisory.message
    assert verdict.severity == "finding"
    assert "does not request id-token: write" in verdict.message


def test_oidc_unscoped_advisory_when_publish_step_unattributed(tmp_path: Path) -> None:
    """Cause C: valid YAML, a real `jobs:` mapping, and `_PUBLISH_RE`
    matches the raw file (in the workflow `name:`, not any job's steps) —
    but no individual job's steps actually publish, so the publish step
    can't be attributed to a specific job.
    """
    workflow = (
        "name: uv publish helper\n"
        "on: push\n"
        "jobs:\n"
        "  noop:\n"
        "    runs-on: ubuntu-latest\n"
        "    steps:\n"
        "      - run: echo hi\n"
    )
    p = make_bblocks_project(
        tmp_path, with_components=(), workflows={"release.yml": workflow}
    )
    findings = _check_oidc_publish(Project(p))
    assert _codes(findings) == [
        "contract.oidc_publish_unscoped",
        "contract.oidc_publish",
    ]
    advisory, verdict = findings
    assert advisory.severity == "advisory"
    assert (
        "the publish step could not be attributed to a specific job" in advisory.message
    )
    assert verdict.severity == "finding"
    assert "does not request id-token: write" in verdict.message


def test_oidc_flags_no_publish_workflow(tmp_path: Path) -> None:
    p = make_bblocks_project(
        tmp_path,
        with_components=(),
        workflows={
            "ci.yml": "name: CI\non: push\njobs:\n  test:\n    runs-on: ubuntu-latest\n"
        },
    )
    findings = _check_oidc_publish(Project(p))
    assert _codes(findings) == ["contract.oidc_publish"]
    assert findings[0].message == "no PyPI publishing workflow found"


def test_oidc_skipped_for_project_type(tmp_path: Path) -> None:
    p = make_bblocks_project(tmp_path, project_type="project", with_components=())
    assert _check_oidc_publish(Project(p)) == []


# --- a package in a subdirectory of a multi-language repo ---------------------------

_SUBDIRECTORY_RELEASE_WORKFLOW = (
    "name: Python release\n"
    "on:\n"
    "  push:\n"
    "    tags: ['python-v*']\n"
    "jobs:\n"
    "  publish:\n"
    "    runs-on: ubuntu-latest\n"
    "    environment: pypi\n"
    "    permissions:\n"
    "      id-token: write\n"
    "    defaults:\n"
    "      run:\n"
    "        working-directory: python\n"
    "    steps:\n"
    "      - run: uv build\n"
    "      - run: uv publish\n"
)


def _make_subdirectory_repo(tmp_path: Path, *, git: bool) -> Project:
    """A family package in `python/`, with pre-commit and workflows at the root."""
    (tmp_path / "python").mkdir()
    package = make_family_project(
        tmp_path / "python",
        with_components=("pre-commit", "ruff", "pytest"),
        dependencies=("readerkit>=0.1.0",),
        workflows=None,
    )
    # The pre-commit component adds the dev dependency; the config lives at the root.
    (package / ".pre-commit-config.yaml").unlink()
    if git:
        (tmp_path / ".git").mkdir()
    (tmp_path / ".pre-commit-config.yaml").write_text("repos: []\n", encoding="utf-8")
    workflows = tmp_path / ".github" / "workflows"
    workflows.mkdir(parents=True)
    (workflows / "python-release.yml").write_text(
        _SUBDIRECTORY_RELEASE_WORKFLOW, encoding="utf-8"
    )
    return Project(package)


def test_subdirectory_package_reads_repo_level_files_from_git_root(
    tmp_path: Path,
) -> None:
    project = _make_subdirectory_repo(tmp_path, git=True)
    findings = run_contract_checks(project, check_remote=False)
    assert [f for f in findings if f.severity == "finding"] == []
    assert _check_pre_commit(project) == []
    assert _check_oidc_publish(project) == []


def test_subdirectory_package_outside_git_reads_its_own_directory(
    tmp_path: Path,
) -> None:
    """Without a `.git` above it the package directory is the root, so the
    parent's files are invisible: the walk stops at the work tree."""
    project = _make_subdirectory_repo(tmp_path, git=False)
    assert _codes(_check_pre_commit(project)) == ["contract.pre_commit"]
    assert _codes(_check_oidc_publish(project)) == ["contract.oidc_publish"]


@pytest.mark.parametrize(
    ("package_part", "root_file"),
    [(False, True), (True, False), (False, False)],
    ids=["package-part-missing", "root-file-missing", "both-missing"],
)
def test_pre_commit_advice_names_the_missing_part_below_the_git_root(
    tmp_path: Path, package_part: bool, root_file: bool
) -> None:
    project = _make_subdirectory_repo(tmp_path, git=True)
    if not root_file:
        (tmp_path / ".pre-commit-config.yaml").unlink()
    if not package_part:
        pyproject = project.path / "pyproject.toml"
        pyproject.write_text(pyproject.read_text().replace('"pre-commit>=4.6.0", ', ""))
        project.reload_pyproject()

    [finding] = _check_pre_commit(project)

    advice = finding.remediation or ""
    assert ("bblocks-projects add pre-commit" in advice) is not package_part
    assert (".pre-commit-config.yaml" in advice) is not root_file
    assert ("a-package-in-a-multi-language-repo" in advice) is not root_file


@pytest.mark.parametrize("git_at_package", [True, False])
def test_pre_commit_advice_is_the_add_command_at_the_git_root(
    tmp_path: Path, git_at_package: bool
) -> None:
    """A package at its git root, or outside git, can run `add` safely."""
    project = _make_subdirectory_repo(tmp_path, git=False)
    if git_at_package:
        (project.path / ".git").mkdir()

    [finding] = _check_pre_commit(project)

    assert finding.remediation == "bblocks-projects add pre-commit"


# --- gating: is_family_project, run_checks(family=...), stubs ----------------------


def test_is_family_project_reads_preset(tmp_path: Path) -> None:
    p = make_bblocks_project(tmp_path, preset="family")
    assert is_family_project(Project(p)) is True


def test_is_family_project_defaults_false(tmp_path: Path) -> None:
    p = make_bblocks_project(tmp_path)
    assert is_family_project(Project(p)) is False


def test_is_family_project_force_overrides(tmp_path: Path) -> None:
    p = make_bblocks_project(tmp_path)
    assert is_family_project(Project(p), force=True) is True


def test_run_checks_without_family_never_runs_contract_checks(tmp_path: Path) -> None:
    p = make_bblocks_project(
        tmp_path, preset="family", build_backend="poetry.core.masonry.api"
    )
    findings = run_checks(Project(p), check_updates=False)
    assert "contract.build_backend" not in _codes(findings)


def test_run_checks_family_runs_contract_checks(tmp_path: Path) -> None:
    p = make_bblocks_project(
        tmp_path, preset="family", build_backend="poetry.core.masonry.api"
    )
    findings = run_checks(Project(p), check_updates=False, family=True)
    assert "contract.build_backend" in _codes(findings)


def test_run_checks_missing_answers_with_family_emits_not_adopted(
    tmp_path: Path,
) -> None:
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "demo"\nrequires-python = ">=3.12"\n\n'
        '[build-system]\nrequires = ["uv_build"]\nbuild-backend = "uv_build"\n',
        encoding="utf-8",
    )
    findings = run_checks(Project(tmp_path), check_updates=False, family=True)
    assert "contract.not_adopted" in _codes(findings)
    not_adopted = next(f for f in findings if f.code == "contract.not_adopted")
    assert not_adopted.severity == "advisory"
    # Drift/component checks compare against the (absent) answers file, so
    # they must not run.
    assert not any(f.code.startswith("drift.") for f in findings)
    assert not any(f.code.startswith("components.") for f in findings)


def test_run_checks_missing_answers_without_family_emits_nothing_extra(
    tmp_path: Path,
) -> None:
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "demo"\n', encoding="utf-8"
    )
    findings = run_checks(Project(tmp_path), check_updates=False)
    assert findings == []


class _FakeCompleted:
    """Stand-in for `subprocess.CompletedProcess`, for monkeypatching `gh api`."""

    def __init__(self, returncode: int = 0, stdout: str = "", stderr: str = "") -> None:
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


class _FakeHTTPResponse:
    """Stand-in for the context manager `urlopen(...)` returns."""

    def __init__(self, status: int) -> None:
        self.status = status

    def __enter__(self) -> "_FakeHTTPResponse":
        return self

    def __exit__(self, *exc_info: object) -> bool:
        return False


def test_family_project_fixture_passes_every_contract_item(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The `make_family_project` baseline is the contract-clean baseline.

    All twelve items pass, network checks included once the network is
    mocked clean. This is the regression test that keeps
    `make_family_project` honest: if a check tightens and the fixture
    stops satisfying it, this is what breaks.

    The `gh api` mock is argv-aware and shaped like real `gh` output for
    each endpoint it answers — a mock that returned `{}` for any argv
    would make item 11 pass on the classic-protection branch without
    either response resembling reality, leaving the ruleset branch
    unexercised. Here the classic-protection call reports "not
    protected" (a real 404 shape) so the check falls through to the
    ruleset endpoint, which is what actually gets exercised.
    """
    p = make_family_project(tmp_path)
    monkeypatch.setattr(Project, "get_git_remote_slug", lambda self: "ONEcampaign/demo")

    def fake_run(args: list[str], **kwargs: object) -> _FakeCompleted:
        path = args[-1]
        if path.endswith("/branches/main/protection"):
            return _FakeCompleted(
                returncode=1,
                stdout='{"message":"Branch not protected","status":"404"}',
            )
        if path.endswith("/rulesets"):
            rulesets = [
                {
                    "id": 1,
                    "name": "Protect main",
                    "target": "branch",
                    "enforcement": "active",
                    "conditions": {"ref_name": {"include": ["~DEFAULT_BRANCH"]}},
                    "rules": [{"type": "pull_request"}],
                }
            ]
            return _FakeCompleted(returncode=0, stdout=json.dumps(rulesets))
        if path == "repos/ONEcampaign/demo":
            # Resolves the ruleset's `~DEFAULT_BRANCH` to `refs/heads/main`.
            return _FakeCompleted(
                returncode=0, stdout=json.dumps({"default_branch": "main"})
            )
        raise AssertionError(f"unexpected gh api call: {path}")

    monkeypatch.setattr("bblocks.projects.contract.subprocess.run", fake_run)
    monkeypatch.setattr(
        "bblocks.projects.contract.urlopen",
        lambda url, timeout=8: _FakeHTTPResponse(200),
    )
    findings = run_contract_checks(Project(p), check_remote=True)
    assert findings == []


def test_family_project_fixture_is_clean_without_check_remote(tmp_path: Path) -> None:
    """Without `--check-remote`, items 11-12 degrade to skip advisories, not findings."""
    p = make_family_project(tmp_path)
    findings = run_contract_checks(Project(p), check_remote=False)
    implemented_codes = {
        "contract.build_backend",
        "contract.ruff",
        "contract.ty",
        "contract.pre_commit",
        "contract.python_floor",
        "contract.python_floor_exempt",
        "contract.dependency_cap",
        "contract.oidc_publish",
        "contract.readerkit",
        "contract.cache_redirect",
        "contract.cache_env_var",
        "contract.cache_disable",
        "contract.import_io",
        "contract.import_opaque",
        "contract.import_unreadable",
        "contract.branch_protection",
        "contract.conda_forge",
    }
    assert implemented_codes.isdisjoint(_codes(findings))
    assert _codes(findings) == [
        "contract.branch_protection_skipped",
        "contract.conda_forge_skipped",
    ]
