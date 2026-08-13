"""Tests for the family contract's network checks (items 11, 12).

No test in this module touches the network — `contract.subprocess.run` and
`contract.urlopen` are monkeypatched throughout, and `Project.get_git_remote_slug`
is monkeypatched directly rather than exercising the real `git remote get-url`
subprocess call it wraps.
"""

import json
import subprocess
from pathlib import Path
from urllib.error import HTTPError, URLError

import pytest

from bblocks.projects.contract import _check_branch_protection, _check_conda_forge
from bblocks.projects.doctor import Finding
from bblocks.projects.project import Project
from tests._helpers import make_family_project


def _codes(findings: list[Finding]) -> list[str]:
    return [f.code for f in findings]


class _FakeCompleted:
    def __init__(self, returncode: int = 0, stdout: str = "", stderr: str = "") -> None:
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


class _FakeHTTPResponse:
    def __init__(self, status: int) -> None:
        self.status = status

    def __enter__(self) -> "_FakeHTTPResponse":
        return self

    def __exit__(self, *exc_info: object) -> bool:
        return False


# --- item 11: branch protection --------------------------------------------------


def test_branch_protection_skipped_without_flag(tmp_path: Path) -> None:
    p = make_family_project(tmp_path)
    findings = _check_branch_protection(Project(p), check_remote=False)
    assert _codes(findings) == ["contract.branch_protection_skipped"]
    assert findings[0].severity == "advisory"
    assert "not checked (pass --check-remote)" in findings[0].message


def test_branch_protection_skipped_without_remote(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    p = make_family_project(tmp_path)
    monkeypatch.setattr(Project, "get_git_remote_slug", lambda self: None)
    findings = _check_branch_protection(Project(p), check_remote=True)
    assert _codes(findings) == ["contract.branch_protection_skipped"]
    assert "no GitHub origin remote" in findings[0].message


def test_branch_protection_skipped_on_missing_gh(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    p = make_family_project(tmp_path)
    monkeypatch.setattr(Project, "get_git_remote_slug", lambda self: "ONEcampaign/demo")

    def fake_run(*args: object, **kwargs: object) -> None:
        raise FileNotFoundError("gh not found")

    monkeypatch.setattr("bblocks.projects.contract.subprocess.run", fake_run)
    findings = _check_branch_protection(Project(p), check_remote=True)
    assert _codes(findings) == ["contract.branch_protection_skipped"]
    assert "gh is not installed" in findings[0].message


def test_branch_protection_skipped_on_timeout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    p = make_family_project(tmp_path)
    monkeypatch.setattr(Project, "get_git_remote_slug", lambda self: "ONEcampaign/demo")

    def fake_run(*args: object, **kwargs: object) -> None:
        raise subprocess.TimeoutExpired(cmd="gh", timeout=8)

    monkeypatch.setattr("bblocks.projects.contract.subprocess.run", fake_run)
    findings = _check_branch_protection(Project(p), check_remote=True)
    assert _codes(findings) == ["contract.branch_protection_skipped"]
    assert "timed out" in findings[0].message


def test_branch_protection_skipped_on_403(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A 403 means the token can't tell, not that the branch is unprotected."""
    p = make_family_project(tmp_path)
    monkeypatch.setattr(Project, "get_git_remote_slug", lambda self: "ONEcampaign/demo")

    def fake_run(args: list[str], **kwargs: object) -> _FakeCompleted:
        return _FakeCompleted(
            returncode=1,
            stderr="gh: Must have admin rights to Repository. (HTTP 403)",
        )

    monkeypatch.setattr("bblocks.projects.contract.subprocess.run", fake_run)
    findings = _check_branch_protection(Project(p), check_remote=True)
    assert _codes(findings) == ["contract.branch_protection_skipped"]
    assert "403" in findings[0].message


def test_branch_protection_skipped_on_unparseable_gh_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    p = make_family_project(tmp_path)
    monkeypatch.setattr(Project, "get_git_remote_slug", lambda self: "ONEcampaign/demo")

    def fake_run(args: list[str], **kwargs: object) -> _FakeCompleted:
        return _FakeCompleted(returncode=1, stderr="gh: connection reset")

    monkeypatch.setattr("bblocks.projects.contract.subprocess.run", fake_run)
    findings = _check_branch_protection(Project(p), check_remote=True)
    assert _codes(findings) == ["contract.branch_protection_skipped"]
    assert "connection reset" in findings[0].message


def test_branch_protection_passes_on_classic_with_required_reviews(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The real shape ONEcampaign repos use: `required_approving_review_count`
    is `0` (a PR is required, approvals aren't), which still gates a merge.
    """
    p = make_family_project(tmp_path)
    monkeypatch.setattr(Project, "get_git_remote_slug", lambda self: "ONEcampaign/demo")

    def fake_run(args: list[str], **kwargs: object) -> _FakeCompleted:
        body = {
            "required_status_checks": {
                "strict": False,
                "contexts": ["Lint & type check", "Run tests (ubuntu-latest, 3.12)"],
            },
            "required_pull_request_reviews": {
                "dismiss_stale_reviews": False,
                "require_code_owner_reviews": False,
                "required_approving_review_count": 0,
            },
            "enforce_admins": {"enabled": False},
            "required_conversation_resolution": {"enabled": True},
        }
        return _FakeCompleted(returncode=0, stdout=json.dumps(body))

    monkeypatch.setattr("bblocks.projects.contract.subprocess.run", fake_run)
    assert _check_branch_protection(Project(p), check_remote=True) == []


def test_branch_protection_passes_on_classic_with_required_status_checks_only(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    p = make_family_project(tmp_path)
    monkeypatch.setattr(Project, "get_git_remote_slug", lambda self: "ONEcampaign/demo")

    def fake_run(args: list[str], **kwargs: object) -> _FakeCompleted:
        body = {"required_status_checks": {"strict": True, "contexts": ["test"]}}
        return _FakeCompleted(returncode=0, stdout=json.dumps(body))

    monkeypatch.setattr("bblocks.projects.contract.subprocess.run", fake_run)
    assert _check_branch_protection(Project(p), check_remote=True) == []


def test_branch_protection_falls_through_to_ruleset_when_classic_does_not_gate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Classic protection is configured but gates nothing this item cares
    about (an empty `required_status_checks`, plus settings — force-push and
    deletion restrictions, linear history — that protect the branch without
    requiring a pull request or passing CI). A ruleset that does gate should
    still be found, so the check must fall through rather than pass or fail
    on the classic body alone.
    """
    p = make_family_project(tmp_path)
    monkeypatch.setattr(Project, "get_git_remote_slug", lambda self: "ONEcampaign/demo")
    calls: list[str] = []

    def fake_run(args: list[str], **kwargs: object) -> _FakeCompleted:
        calls.append(args[-1])
        if args[-1].endswith("/protection"):
            body = {
                "required_status_checks": {},
                "allow_force_pushes": {"enabled": False},
                "allow_deletions": {"enabled": False},
                "required_linear_history": {"enabled": True},
            }
            return _FakeCompleted(returncode=0, stdout=json.dumps(body))
        if args[-1].endswith("/rulesets"):
            rulesets = [
                {
                    "id": 1,
                    "name": "Protect main",
                    "target": "branch",
                    "enforcement": "active",
                    "conditions": {
                        "ref_name": {"include": ["~DEFAULT_BRANCH"], "exclude": []}
                    },
                    "rules": [{"type": "pull_request"}],
                }
            ]
            return _FakeCompleted(returncode=0, stdout=json.dumps(rulesets))
        # `repos/<slug>` — resolves `~DEFAULT_BRANCH` to `refs/heads/main`.
        return _FakeCompleted(
            returncode=0, stdout=json.dumps({"default_branch": "main"})
        )

    monkeypatch.setattr("bblocks.projects.contract.subprocess.run", fake_run)
    assert _check_branch_protection(Project(p), check_remote=True) == []
    assert len(calls) == 3  # protection, rulesets, then the default-branch lookup


def test_branch_protection_flags_when_classic_and_rulesets_both_fail_to_gate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    p = make_family_project(tmp_path)
    monkeypatch.setattr(
        Project, "get_git_remote_slug", lambda self: "ONEcampaign/oda_reader"
    )

    def fake_run(args: list[str], **kwargs: object) -> _FakeCompleted:
        if args[-1].endswith("/protection"):
            body = {
                "required_status_checks": {},
                "allow_force_pushes": {"enabled": False},
            }
            return _FakeCompleted(returncode=0, stdout=json.dumps(body))
        return _FakeCompleted(returncode=0, stdout="[]")

    monkeypatch.setattr("bblocks.projects.contract.subprocess.run", fake_run)
    findings = _check_branch_protection(Project(p), check_remote=True)
    assert _codes(findings) == ["contract.branch_protection"]
    assert findings[0].severity == "finding"
    assert "main is not protected on ONEcampaign/oda_reader" in findings[0].message


def test_branch_protection_flags_when_unprotected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    p = make_family_project(tmp_path)
    monkeypatch.setattr(
        Project, "get_git_remote_slug", lambda self: "ONEcampaign/oda_reader"
    )
    calls: list[str] = []

    def fake_run(args: list[str], **kwargs: object) -> _FakeCompleted:
        calls.append(args[-1])
        if args[-1].endswith("/protection"):
            return _FakeCompleted(
                returncode=1,
                stdout='{"message":"Branch not protected","status":"404"}',
            )
        return _FakeCompleted(returncode=0, stdout="[]")

    monkeypatch.setattr("bblocks.projects.contract.subprocess.run", fake_run)
    findings = _check_branch_protection(Project(p), check_remote=True)
    assert _codes(findings) == ["contract.branch_protection"]
    assert findings[0].severity == "finding"
    assert "main is not protected on ONEcampaign/oda_reader" in findings[0].message
    assert len(calls) == 2  # protection, then rulesets


def _not_protected_completed() -> _FakeCompleted:
    return _FakeCompleted(
        returncode=1,
        stdout='{"message":"Branch not protected","status":"404"}',
    )


def test_branch_protection_passes_on_ruleset(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    p = make_family_project(tmp_path)
    monkeypatch.setattr(Project, "get_git_remote_slug", lambda self: "ONEcampaign/demo")

    def fake_run(args: list[str], **kwargs: object) -> _FakeCompleted:
        if args[-1].endswith("/protection"):
            return _not_protected_completed()
        if args[-1].endswith("/rulesets"):
            # Real `gh api repos/<slug>/rulesets` shape: `enforcement` and
            # `rules` sit alongside `target`/`conditions`, and both must be
            # inspected for this ruleset to count as protection.
            rulesets = [
                {
                    "id": 1,
                    "name": "Protect main",
                    "target": "branch",
                    "enforcement": "active",
                    "conditions": {
                        "ref_name": {"include": ["~DEFAULT_BRANCH"], "exclude": []}
                    },
                    "rules": [
                        {"type": "deletion"},
                        {
                            "type": "pull_request",
                            "parameters": {"required_approving_review_count": 1},
                        },
                    ],
                }
            ]
            return _FakeCompleted(returncode=0, stdout=json.dumps(rulesets))
        # `repos/<slug>` — resolves `~DEFAULT_BRANCH` to `refs/heads/main`.
        return _FakeCompleted(
            returncode=0, stdout=json.dumps({"default_branch": "main"})
        )

    monkeypatch.setattr("bblocks.projects.contract.subprocess.run", fake_run)
    assert _check_branch_protection(Project(p), check_remote=True) == []


def test_branch_protection_flags_when_rulesets_empty(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    p = make_family_project(tmp_path)
    monkeypatch.setattr(Project, "get_git_remote_slug", lambda self: "ONEcampaign/demo")

    def fake_run(args: list[str], **kwargs: object) -> _FakeCompleted:
        if args[-1].endswith("/protection"):
            return _not_protected_completed()
        return _FakeCompleted(returncode=0, stdout="[]")

    monkeypatch.setattr("bblocks.projects.contract.subprocess.run", fake_run)
    findings = _check_branch_protection(Project(p), check_remote=True)
    assert _codes(findings) == ["contract.branch_protection"]


def test_branch_protection_flags_when_ruleset_is_disabled(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A ruleset targeting main with `enforcement: disabled` protects nothing.

    Regression guard: matching on `target` + `conditions.ref_name.include`
    alone, without checking `enforcement`, would count a disabled (or
    evaluate-mode) ruleset as protection.
    """
    p = make_family_project(tmp_path)
    monkeypatch.setattr(Project, "get_git_remote_slug", lambda self: "ONEcampaign/demo")

    def fake_run(args: list[str], **kwargs: object) -> _FakeCompleted:
        if args[-1].endswith("/protection"):
            return _not_protected_completed()
        rulesets = [
            {
                "target": "branch",
                "enforcement": "disabled",
                "conditions": {"ref_name": {"include": ["~DEFAULT_BRANCH"]}},
                "rules": [{"type": "pull_request"}],
            }
        ]
        return _FakeCompleted(returncode=0, stdout=json.dumps(rulesets))

    monkeypatch.setattr("bblocks.projects.contract.subprocess.run", fake_run)
    findings = _check_branch_protection(Project(p), check_remote=True)
    assert _codes(findings) == ["contract.branch_protection"]


def test_branch_protection_flags_when_ruleset_is_evaluate_only(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`enforcement: evaluate` is dry-run mode: recorded, never blocked."""
    p = make_family_project(tmp_path)
    monkeypatch.setattr(Project, "get_git_remote_slug", lambda self: "ONEcampaign/demo")

    def fake_run(args: list[str], **kwargs: object) -> _FakeCompleted:
        if args[-1].endswith("/protection"):
            return _not_protected_completed()
        rulesets = [
            {
                "target": "branch",
                "enforcement": "evaluate",
                "conditions": {"ref_name": {"include": ["~DEFAULT_BRANCH"]}},
                "rules": [{"type": "pull_request"}],
            }
        ]
        return _FakeCompleted(returncode=0, stdout=json.dumps(rulesets))

    monkeypatch.setattr("bblocks.projects.contract.subprocess.run", fake_run)
    findings = _check_branch_protection(Project(p), check_remote=True)
    assert _codes(findings) == ["contract.branch_protection"]


def test_branch_protection_flags_when_ruleset_has_no_gating_rule(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Active, targets main, but the only rule restricts tag deletion.

    The remediation promises "requiring a pull request and passing CI";
    a ruleset with no `pull_request` or `required_status_checks` rule
    delivers neither, so it must not count as protection.
    """
    p = make_family_project(tmp_path)
    monkeypatch.setattr(Project, "get_git_remote_slug", lambda self: "ONEcampaign/demo")

    def fake_run(args: list[str], **kwargs: object) -> _FakeCompleted:
        if args[-1].endswith("/protection"):
            return _not_protected_completed()
        if args[-1].endswith("/rulesets"):
            rulesets = [
                {
                    "target": "branch",
                    "enforcement": "active",
                    "conditions": {"ref_name": {"include": ["~DEFAULT_BRANCH"]}},
                    "rules": [{"type": "deletion"}, {"type": "non_fast_forward"}],
                }
            ]
            return _FakeCompleted(returncode=0, stdout=json.dumps(rulesets))
        # `repos/<slug>` — resolves `~DEFAULT_BRANCH` to `refs/heads/main`, so
        # the finding below is actually reached for the "no gating rule"
        # reason this test is about, not because of an unresolved alias.
        return _FakeCompleted(
            returncode=0, stdout=json.dumps({"default_branch": "main"})
        )

    monkeypatch.setattr("bblocks.projects.contract.subprocess.run", fake_run)
    findings = _check_branch_protection(Project(p), check_remote=True)
    assert _codes(findings) == ["contract.branch_protection"]


def test_branch_protection_flags_when_ruleset_excludes_main(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`include: ["~DEFAULT_BRANCH"]` paired with `exclude: ["refs/heads/main"]`
    protects every default-ish branch except the one that matters.

    Regression guard: reading `conditions.ref_name.include` alone, without
    also checking `exclude`, would count this ruleset as covering `main`
    when GitHub applies the exclusion and blocks nothing on it.
    """
    p = make_family_project(tmp_path)
    monkeypatch.setattr(Project, "get_git_remote_slug", lambda self: "ONEcampaign/demo")

    def fake_run(args: list[str], **kwargs: object) -> _FakeCompleted:
        if args[-1].endswith("/protection"):
            return _not_protected_completed()
        # Real `gh api repos/<slug>/rulesets` shape for an
        # include/exclude pair: both lists sit under `conditions.ref_name`.
        rulesets = [
            {
                "target": "branch",
                "enforcement": "active",
                "conditions": {
                    "ref_name": {
                        "include": ["~DEFAULT_BRANCH"],
                        "exclude": ["refs/heads/main"],
                    }
                },
                "rules": [{"type": "pull_request"}],
            }
        ]
        return _FakeCompleted(returncode=0, stdout=json.dumps(rulesets))

    monkeypatch.setattr("bblocks.projects.contract.subprocess.run", fake_run)
    findings = _check_branch_protection(Project(p), check_remote=True)
    assert _codes(findings) == ["contract.branch_protection"]


def test_branch_protection_flags_when_ruleset_wildcard_excludes_main(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`exclude: ["refs/heads/ma*"]` is an fnmatch pattern, not a literal —
    it excludes `main` exactly like `exclude: ["refs/heads/main"]` would.

    Regression guard: a check that compares `exclude` entries against a
    fixed set of literal strings, instead of matching them as GitHub
    patterns, misses this and counts the ruleset as covering `main`.
    """
    p = make_family_project(tmp_path)
    monkeypatch.setattr(Project, "get_git_remote_slug", lambda self: "ONEcampaign/demo")

    def fake_run(args: list[str], **kwargs: object) -> _FakeCompleted:
        if args[-1].endswith("/protection"):
            return _not_protected_completed()
        if args[-1].endswith("/rulesets"):
            rulesets = [
                {
                    "target": "branch",
                    "enforcement": "active",
                    "conditions": {
                        "ref_name": {
                            "include": ["~DEFAULT_BRANCH"],
                            "exclude": ["refs/heads/ma*"],
                        }
                    },
                    "rules": [{"type": "pull_request"}],
                }
            ]
            return _FakeCompleted(returncode=0, stdout=json.dumps(rulesets))
        # `repos/<slug>` — resolves `~DEFAULT_BRANCH` to `refs/heads/main`.
        return _FakeCompleted(
            returncode=0, stdout=json.dumps({"default_branch": "main"})
        )

    monkeypatch.setattr("bblocks.projects.contract.subprocess.run", fake_run)
    findings = _check_branch_protection(Project(p), check_remote=True)
    assert _codes(findings) == ["contract.branch_protection"]


def test_branch_protection_passes_on_ruleset_with_all_meta_include(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`~ALL` ("includes all branches") covers `main` exactly like
    `~DEFAULT_BRANCH` or a literal ref does. It isn't in a fixed alias
    set of three literal strings, so a literal-comparison check misses it
    and calls `main` unprotected even though this ruleset gates it.
    """
    p = make_family_project(tmp_path)
    monkeypatch.setattr(Project, "get_git_remote_slug", lambda self: "ONEcampaign/demo")

    def fake_run(args: list[str], **kwargs: object) -> _FakeCompleted:
        if args[-1].endswith("/protection"):
            return _not_protected_completed()
        rulesets = [
            {
                "target": "branch",
                "enforcement": "active",
                "conditions": {"ref_name": {"include": ["~ALL"], "exclude": []}},
                "rules": [{"type": "pull_request"}],
            }
        ]
        return _FakeCompleted(returncode=0, stdout=json.dumps(rulesets))

    monkeypatch.setattr("bblocks.projects.contract.subprocess.run", fake_run)
    assert _check_branch_protection(Project(p), check_remote=True) == []


def test_branch_protection_flags_when_ruleset_all_meta_excludes_main(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`exclude: ["~ALL"]` excludes every branch, `main` included — the
    same blind spot as the wildcard-exclude case above, for the other
    meta-value GitHub supports.
    """
    p = make_family_project(tmp_path)
    monkeypatch.setattr(Project, "get_git_remote_slug", lambda self: "ONEcampaign/demo")

    def fake_run(args: list[str], **kwargs: object) -> _FakeCompleted:
        if args[-1].endswith("/protection"):
            return _not_protected_completed()
        rulesets = [
            {
                "target": "branch",
                "enforcement": "active",
                "conditions": {
                    "ref_name": {"include": ["refs/heads/main"], "exclude": ["~ALL"]}
                },
                "rules": [{"type": "pull_request"}],
            }
        ]
        return _FakeCompleted(returncode=0, stdout=json.dumps(rulesets))

    monkeypatch.setattr("bblocks.projects.contract.subprocess.run", fake_run)
    findings = _check_branch_protection(Project(p), check_remote=True)
    assert _codes(findings) == ["contract.branch_protection"]


def test_branch_protection_passes_on_ruleset_with_wildcard_include(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`include: ["refs/heads/*"]` is a pattern that matches every
    top-level branch, `main` included. It isn't a literal alias either, so
    a literal-comparison check misses it too, in the opposite direction
    from the exclude cases above: it calls a genuinely-covered `main`
    unprotected.
    """
    p = make_family_project(tmp_path)
    monkeypatch.setattr(Project, "get_git_remote_slug", lambda self: "ONEcampaign/demo")

    def fake_run(args: list[str], **kwargs: object) -> _FakeCompleted:
        if args[-1].endswith("/protection"):
            return _not_protected_completed()
        rulesets = [
            {
                "target": "branch",
                "enforcement": "active",
                "conditions": {
                    "ref_name": {"include": ["refs/heads/*"], "exclude": []}
                },
                "rules": [{"type": "pull_request"}],
            }
        ]
        return _FakeCompleted(returncode=0, stdout=json.dumps(rulesets))

    monkeypatch.setattr("bblocks.projects.contract.subprocess.run", fake_run)
    assert _check_branch_protection(Project(p), check_remote=True) == []


def test_branch_protection_flags_when_wildcard_include_does_not_cover_main(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`include: ["refs/heads/release/*"]` covers release branches, not
    `main` — sharing the `refs/heads/` prefix must not be enough for a
    match. This isn't a regression guard for pattern-vs-literal matching:
    a check comparing `include` against fixed literal strings would also
    fail to count this ruleset as covering `main`, just for the wrong
    reason (it never recognises patterns at all). It exists to guard the
    pattern matcher's own precision — that a shared prefix isn't mistaken
    for a full segment match — in the direction opposite the wildcard
    cases above.
    """
    p = make_family_project(tmp_path)
    monkeypatch.setattr(Project, "get_git_remote_slug", lambda self: "ONEcampaign/demo")

    def fake_run(args: list[str], **kwargs: object) -> _FakeCompleted:
        if args[-1].endswith("/protection"):
            return _not_protected_completed()
        rulesets = [
            {
                "target": "branch",
                "enforcement": "active",
                "conditions": {
                    "ref_name": {"include": ["refs/heads/release/*"], "exclude": []}
                },
                "rules": [{"type": "pull_request"}],
            }
        ]
        return _FakeCompleted(returncode=0, stdout=json.dumps(rulesets))

    monkeypatch.setattr("bblocks.projects.contract.subprocess.run", fake_run)
    findings = _check_branch_protection(Project(p), check_remote=True)
    assert _codes(findings) == ["contract.branch_protection"]


def test_branch_protection_flags_when_default_branch_is_not_main(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`~DEFAULT_BRANCH` only covers `main` when the repository's actual
    default branch *is* `main`. A repo whose default branch is `develop`
    can carry a ruleset that reads `~DEFAULT_BRANCH` and protects
    `develop` while leaving `main` completely open.

    Regression guard: treating `~DEFAULT_BRANCH` as an unconditional
    synonym for `main`, without checking what the repository's default
    branch actually is, would certify this repo as protected.
    """
    p = make_family_project(tmp_path)
    monkeypatch.setattr(Project, "get_git_remote_slug", lambda self: "ONEcampaign/demo")

    def fake_run(args: list[str], **kwargs: object) -> _FakeCompleted:
        if args[-1].endswith("/protection"):
            return _not_protected_completed()
        if args[-1].endswith("/rulesets"):
            rulesets = [
                {
                    "target": "branch",
                    "enforcement": "active",
                    "conditions": {
                        "ref_name": {"include": ["~DEFAULT_BRANCH"], "exclude": []}
                    },
                    "rules": [{"type": "pull_request"}],
                }
            ]
            return _FakeCompleted(returncode=0, stdout=json.dumps(rulesets))
        # `repos/<slug>` — this repo's actual default branch is `develop`.
        return _FakeCompleted(
            returncode=0, stdout=json.dumps({"default_branch": "develop"})
        )

    monkeypatch.setattr("bblocks.projects.contract.subprocess.run", fake_run)
    findings = _check_branch_protection(Project(p), check_remote=True)
    assert _codes(findings) == ["contract.branch_protection"]


def test_branch_protection_skipped_when_default_branch_lookup_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When `~DEFAULT_BRANCH` needs resolving but the `repos/<slug>` lookup
    fails, and no other ruleset already covers `main`, the check must not
    assert "main is not protected" — that would turn a lookup failure into
    a false accusation, exactly what `_branch_protection_skipped` exists to
    avoid for every other `gh api` failure mode this item handles (a 403,
    a timeout, a missing `gh`). It degrades to the same advisory instead,
    with a reason naming why. `--strict` must not fail on an advisory.
    """
    p = make_family_project(tmp_path)
    monkeypatch.setattr(Project, "get_git_remote_slug", lambda self: "ONEcampaign/demo")

    def fake_run(args: list[str], **kwargs: object) -> _FakeCompleted:
        if args[-1].endswith("/protection"):
            return _not_protected_completed()
        if args[-1].endswith("/rulesets"):
            rulesets = [
                {
                    "target": "branch",
                    "enforcement": "active",
                    "conditions": {
                        "ref_name": {"include": ["~DEFAULT_BRANCH"], "exclude": []}
                    },
                    "rules": [{"type": "pull_request"}],
                }
            ]
            return _FakeCompleted(returncode=0, stdout=json.dumps(rulesets))
        return _FakeCompleted(returncode=1, stderr="gh: connection reset")

    monkeypatch.setattr("bblocks.projects.contract.subprocess.run", fake_run)
    findings = _check_branch_protection(Project(p), check_remote=True)
    assert _codes(findings) == ["contract.branch_protection_skipped"]
    assert findings[0].severity == "advisory"
    assert "connection reset" in findings[0].message


def test_branch_protection_default_branch_lookup_is_called_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Three rulesets all read `~DEFAULT_BRANCH` — the `repos/<slug>` lookup
    must still run at most once, its result (success or failure) memoized
    for every pattern in every ruleset that asks for it, not repeated
    per-ruleset or per-pattern.
    """
    p = make_family_project(tmp_path)
    monkeypatch.setattr(Project, "get_git_remote_slug", lambda self: "ONEcampaign/demo")
    repo_lookup_calls: list[str] = []

    def fake_run(args: list[str], **kwargs: object) -> _FakeCompleted:
        path = args[-1]
        if path.endswith("/protection"):
            return _not_protected_completed()
        if path.endswith("/rulesets"):
            ruleset = {
                "target": "branch",
                "enforcement": "active",
                "conditions": {
                    "ref_name": {"include": ["~DEFAULT_BRANCH"], "exclude": []}
                },
                "rules": [{"type": "pull_request"}],
            }
            return _FakeCompleted(returncode=0, stdout=json.dumps([ruleset] * 3))
        repo_lookup_calls.append(path)
        return _FakeCompleted(returncode=1, stderr="gh: connection reset")

    monkeypatch.setattr("bblocks.projects.contract.subprocess.run", fake_run)
    findings = _check_branch_protection(Project(p), check_remote=True)
    assert _codes(findings) == ["contract.branch_protection_skipped"]
    assert len(repo_lookup_calls) == 1


def test_branch_protection_passes_on_required_status_checks_rule(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The other merge-gating rule type, on its own, is also sufficient."""
    p = make_family_project(tmp_path)
    monkeypatch.setattr(Project, "get_git_remote_slug", lambda self: "ONEcampaign/demo")

    def fake_run(args: list[str], **kwargs: object) -> _FakeCompleted:
        if args[-1].endswith("/protection"):
            return _not_protected_completed()
        rulesets = [
            {
                "target": "branch",
                "enforcement": "active",
                "conditions": {"ref_name": {"include": ["refs/heads/main"]}},
                "rules": [
                    {
                        "type": "required_status_checks",
                        "parameters": {"required_status_checks": [{"context": "ci"}]},
                    }
                ],
            }
        ]
        return _FakeCompleted(returncode=0, stdout=json.dumps(rulesets))

    monkeypatch.setattr("bblocks.projects.contract.subprocess.run", fake_run)
    assert _check_branch_protection(Project(p), check_remote=True) == []


def test_branch_protection_skipped_when_rulesets_response_is_not_a_list(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`gh` exits 0 with valid JSON that isn't a rulesets array — an error
    object or a paginated envelope. That's "could not tell", not evidence
    the branch is unprotected, so it must degrade to the skip advisory
    like every other unexpected shape in these two network checks, not
    fall through to the `contract.branch_protection` finding.
    """
    p = make_family_project(tmp_path)
    monkeypatch.setattr(Project, "get_git_remote_slug", lambda self: "ONEcampaign/demo")

    def fake_run(args: list[str], **kwargs: object) -> _FakeCompleted:
        if args[-1].endswith("/protection"):
            return _not_protected_completed()
        return _FakeCompleted(
            returncode=0, stdout='{"message": "not found", "documentation_url": "..."}'
        )

    monkeypatch.setattr("bblocks.projects.contract.subprocess.run", fake_run)
    findings = _check_branch_protection(Project(p), check_remote=True)
    assert _codes(findings) == ["contract.branch_protection_skipped"]
    assert "not a list" in findings[0].message


def test_branch_protection_skipped_on_permission_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A `PermissionError` running `gh` degrades like `FileNotFoundError`
    instead of tracebacking out of `doctor` — `_run_gh_api_or_skip` must
    catch `OSError` broadly, not just `FileNotFoundError` and
    `subprocess.TimeoutExpired`.
    """
    p = make_family_project(tmp_path)
    monkeypatch.setattr(Project, "get_git_remote_slug", lambda self: "ONEcampaign/demo")

    def fake_run(*args: object, **kwargs: object) -> None:
        raise PermissionError("gh is not executable")

    monkeypatch.setattr("bblocks.projects.contract.subprocess.run", fake_run)
    findings = _check_branch_protection(Project(p), check_remote=True)
    assert _codes(findings) == ["contract.branch_protection_skipped"]
    assert findings[0].severity == "advisory"


# --- item 12: conda-forge feedstock ------------------------------------------------


def test_conda_forge_skipped_without_flag(tmp_path: Path) -> None:
    p = make_family_project(tmp_path)
    findings = _check_conda_forge(Project(p), check_remote=False)
    assert _codes(findings) == ["contract.conda_forge_skipped"]
    assert "not checked (pass --check-remote)" in findings[0].message


def test_conda_forge_skipped_for_project_type(tmp_path: Path) -> None:
    p = make_family_project(tmp_path, project_type="project")
    assert _check_conda_forge(Project(p), check_remote=True) == []


def test_conda_forge_passes_on_200(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    p = make_family_project(tmp_path)
    monkeypatch.setattr(
        "bblocks.projects.contract.urlopen",
        lambda url, timeout=8: _FakeHTTPResponse(200),
    )
    assert _check_conda_forge(Project(p), check_remote=True) == []


def test_conda_forge_flags_on_404(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    p = make_family_project(tmp_path)

    def fake_urlopen(url: str, timeout: int = 8) -> None:
        raise HTTPError(url, 404, "Not Found", {}, None)

    monkeypatch.setattr("bblocks.projects.contract.urlopen", fake_urlopen)
    findings = _check_conda_forge(Project(p), check_remote=True)
    assert _codes(findings) == ["contract.conda_forge"]
    assert findings[0].severity == "finding"


def test_conda_forge_normalises_underscore_name(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`oda_reader` 404s on api.anaconda.org; `oda-reader` 200s for the same package."""
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "oda_reader"\nrequires-python = ">=3.12"\n\n'
        '[build-system]\nrequires = ["uv_build"]\nbuild-backend = "uv_build"\n',
        encoding="utf-8",
    )
    (tmp_path / ".copier-answers.yml").write_text(
        "project_type: package\npreset: family\n", encoding="utf-8"
    )
    captured: dict[str, str] = {}

    def fake_urlopen(url: str, timeout: int = 8) -> _FakeHTTPResponse:
        captured["url"] = url
        return _FakeHTTPResponse(200)

    monkeypatch.setattr("bblocks.projects.contract.urlopen", fake_urlopen)
    _check_conda_forge(Project(tmp_path), check_remote=True)
    assert captured["url"].endswith("/oda-reader")


def test_conda_forge_skipped_on_urlerror(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    p = make_family_project(tmp_path)

    def fake_urlopen(url: str, timeout: int = 8) -> None:
        raise URLError("no network")

    monkeypatch.setattr("bblocks.projects.contract.urlopen", fake_urlopen)
    findings = _check_conda_forge(Project(p), check_remote=True)
    assert _codes(findings) == ["contract.conda_forge_skipped"]


def test_conda_forge_skipped_on_500(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    p = make_family_project(tmp_path)
    monkeypatch.setattr(
        "bblocks.projects.contract.urlopen",
        lambda url, timeout=8: _FakeHTTPResponse(500),
    )
    findings = _check_conda_forge(Project(p), check_remote=True)
    assert _codes(findings) == ["contract.conda_forge_skipped"]
    assert "500" in findings[0].message
