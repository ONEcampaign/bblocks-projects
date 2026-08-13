"""Tests for the CLI interface."""

import contextlib
import re
import subprocess
from collections.abc import Iterator
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from copier.errors import CopierError
from typer.testing import CliRunner

from bblocks.projects import __version__
from bblocks.projects.cli import (
    _render_contract_panel,
    _render_doctor_report,
    app,
    console,
)
from bblocks.projects.contract import FAMILY_CONTRACT
from bblocks.projects.doctor import Finding
from bblocks.projects.project import Project
from tests._helpers import make_bblocks_project as _make_bblocks_project
from tests._helpers import make_family_project as _make_family_project

runner = CliRunner()

_ANSI_ESCAPE = re.compile(r"\x1b\[[0-9;]*m")


def _plain(text: str) -> str:
    """Strip ANSI styling so substring checks survive Rich's per-character coloring."""
    return _ANSI_ESCAPE.sub("", text)


def test_version() -> None:
    """Test version command."""
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert __version__ in result.stdout


def test_help() -> None:
    """Test help command."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "bblocks-projects" in result.stdout.lower()


def test_create_help() -> None:
    """Test create command help."""
    result = runner.invoke(app, ["create", "--help"])
    assert result.exit_code == 0
    assert "Create a new Python project from a template" in result.stdout


def test_update_help() -> None:
    """Test update command help."""
    result = runner.invoke(app, ["update", "--help"])
    assert result.exit_code == 0
    assert "Update an existing" in result.stdout


def test_update_without_copier_answers(tmp_path: Path) -> None:
    """Test update fails gracefully without .copier-answers.yml."""
    result = runner.invoke(app, ["update", "--path", str(tmp_path)])
    assert result.exit_code == 1
    assert ".copier-answers.yml" in result.stdout


def test_create_help_shows_template_flag() -> None:
    """Test that create --help shows --template / -T flag."""
    result = runner.invoke(app, ["create", "--help"])
    assert result.exit_code == 0
    assert "--template" in _plain(result.stdout)


def test_update_help_shows_template_flag() -> None:
    """Test that update --help shows --template / -T flag."""
    result = runner.invoke(app, ["update", "--help"])
    assert result.exit_code == 0
    assert "--template" in _plain(result.stdout)


def test_doctor_help() -> None:
    result = runner.invoke(app, ["doctor", "--help"])
    assert result.exit_code == 0
    assert "Run health checks" in result.stdout


def test_doctor_refuses_no_pyproject(tmp_path: Path) -> None:
    result = runner.invoke(app, ["doctor", "--path", str(tmp_path)])
    assert result.exit_code == 1
    assert "Python project" in result.stdout or "pyproject.toml" in result.stdout


def test_doctor_refuses_no_answers(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "demo"\n', encoding="utf-8"
    )
    result = runner.invoke(app, ["doctor", "--path", str(tmp_path)])
    assert result.exit_code == 1
    assert "bblocks-managed" in result.stdout or "appear to be" in result.stdout


def test_doctor_healthy_project(tmp_path: Path) -> None:
    _make_bblocks_project(tmp_path)
    result = runner.invoke(app, ["doctor", "--path", str(tmp_path)])
    assert result.exit_code == 0
    assert "Healthy" in result.stdout


def test_doctor_drift_detected(tmp_path: Path) -> None:
    p = _make_bblocks_project(tmp_path, python_version="3.11")
    answers = (p / ".copier-answers.yml").read_text()
    answers = answers.replace("python_version: '3.11'", "python_version: '3.12'")
    (p / ".copier-answers.yml").write_text(answers, encoding="utf-8")
    result = runner.invoke(app, ["doctor", "--path", str(tmp_path)])
    assert result.exit_code == 0
    assert (
        "3.12" in result.stdout
        or "drift" in result.stdout.lower()
        or "findings" in result.stdout
    )


def test_doctor_strict_flips_exit_code(tmp_path: Path) -> None:
    p = _make_bblocks_project(tmp_path, python_version="3.11")
    answers = (p / ".copier-answers.yml").read_text()
    answers = answers.replace("python_version: '3.11'", "python_version: '3.12'")
    (p / ".copier-answers.yml").write_text(answers, encoding="utf-8")
    result = runner.invoke(app, ["doctor", "--path", str(tmp_path), "--strict"])
    assert result.exit_code == 1


def test_doctor_strict_passes_with_only_advisories(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`--strict` gates on severity "finding" only (`cli.doctor`); an
    advisory-only run must exit 0. The only existing `--strict` test
    (`test_doctor_strict_flips_exit_code`) covers the failing direction —
    this covers the passing one, so a regression that makes `--strict`
    fail on advisories too would be caught.
    """

    def fake_run(*args: object, **kwargs: object) -> None:
        raise FileNotFoundError("git not found")

    monkeypatch.setattr("bblocks.projects.doctor.subprocess.run", fake_run)

    _make_bblocks_project(tmp_path)
    result = runner.invoke(
        app, ["doctor", "--path", str(tmp_path), "--check-updates", "--strict"]
    )
    plain = _plain(result.stdout)
    assert "advisory" in plain.lower()
    assert "finding" not in plain.lower()
    assert result.exit_code == 0


def test_doctor_missing_component_advisory(tmp_path: Path) -> None:
    _make_bblocks_project(
        tmp_path,
        with_components=("pre-commit", "ci", "pypi-publish"),
    )
    result = runner.invoke(app, ["doctor", "--path", str(tmp_path)])
    assert "pytest" in result.stdout
    assert "bblocks-projects add pytest" in result.stdout


def test_doctor_check_updates_graceful_when_subprocess_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fake_run(*args: object, **kwargs: object) -> None:
        raise FileNotFoundError("git not found")

    monkeypatch.setattr("bblocks.projects.doctor.subprocess.run", fake_run)

    _make_bblocks_project(tmp_path)
    result = runner.invoke(app, ["doctor", "--path", str(tmp_path), "--check-updates"])
    assert result.exit_code == 0
    assert "skipped" in result.stdout.lower()


# --- doctor summary line: findings and advisories counted separately --------------


def test_doctor_summary_findings_only(tmp_path: Path) -> None:
    """Findings-only: singular/plural noun, no advisory mentioned."""
    _make_bblocks_project(
        tmp_path,
        with_components=("ci",),  # missing pre-commit, ruff, pytest, pypi-publish
    )
    result = runner.invoke(app, ["doctor", "--path", str(tmp_path)])
    plain = _plain(result.stdout)
    assert "4 findings (use --strict to fail)" in plain
    assert "advisor" not in plain.lower()


def test_doctor_summary_advisories_only(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Advisories-only: the pre-existing 'N advisories (informational)' branch."""

    def fake_run(*args: object, **kwargs: object) -> None:
        raise FileNotFoundError("git not found")

    monkeypatch.setattr("bblocks.projects.doctor.subprocess.run", fake_run)

    _make_bblocks_project(tmp_path)
    result = runner.invoke(app, ["doctor", "--path", str(tmp_path), "--check-updates"])
    plain = _plain(result.stdout)
    assert "1 advisory (informational)" in plain
    assert "finding" not in plain.lower()


def test_doctor_summary_findings_and_advisories(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Both present: named and counted separately, not folded into one number.

    Conflating them would read "2 findings" for one missing component (a
    finding) plus one failed --check-updates call (an advisory), when it
    must read "1 finding, 1 advisory".
    """

    def fake_run(*args: object, **kwargs: object) -> None:
        raise FileNotFoundError("git not found")

    monkeypatch.setattr("bblocks.projects.doctor.subprocess.run", fake_run)

    _make_bblocks_project(
        tmp_path,
        with_components=("pre-commit", "ruff", "ci", "pypi-publish"),  # missing pytest
    )
    result = runner.invoke(app, ["doctor", "--path", str(tmp_path), "--check-updates"])
    plain = _plain(result.stdout)
    assert "1 finding, 1 advisory (use --strict to fail)" in plain


# --- doctor --family / --check-remote (the family contract panel) -----------------


def test_doctor_help_shows_family_and_check_remote_flags() -> None:
    result = runner.invoke(app, ["doctor", "--help"])
    assert result.exit_code == 0
    plain = _plain(result.stdout)
    assert "--family" in plain
    assert "--check-remote" in plain


def test_doctor_without_family_prints_no_contract_panel(tmp_path: Path) -> None:
    """A preset: standalone project (the default) prints no contract panel."""
    _make_bblocks_project(tmp_path)
    result = runner.invoke(app, ["doctor", "--path", str(tmp_path)])
    assert result.exit_code == 0
    assert "Healthy" in result.stdout
    assert "Family contract" not in result.stdout


def test_doctor_family_prints_contract_panel(tmp_path: Path) -> None:
    _make_family_project(tmp_path)
    result = runner.invoke(app, ["doctor", "--path", str(tmp_path), "--family"])
    assert result.exit_code == 0
    plain = _plain(result.stdout)
    assert "Doctor report for" in plain
    assert "Family contract" in plain
    assert "uv build backend" in plain
    assert "readerkit for HTTP and caching" in plain
    # Items 11/12 default to the skip advisory without --check-remote.
    assert "not checked (pass --check-remote)" in plain


def test_doctor_preset_family_runs_without_the_flag(tmp_path: Path) -> None:
    """`preset: family` in .copier-answers.yml is enough; --family is only the
    escape hatch for repos that predate the preset question."""
    _make_family_project(tmp_path)
    result = runner.invoke(app, ["doctor", "--path", str(tmp_path)])
    assert result.exit_code == 0
    assert "Family contract" in _plain(result.stdout)


def test_doctor_family_missing_answers_still_runs(tmp_path: Path) -> None:
    """--family relaxes the .copier-answers.yml refusal to exit 1."""
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "demo"\nrequires-python = ">=3.12"\n\n'
        '[build-system]\nrequires = ["uv_build"]\nbuild-backend = "uv_build"\n',
        encoding="utf-8",
    )
    result = runner.invoke(app, ["doctor", "--path", str(tmp_path), "--family"])
    assert result.exit_code == 0
    plain = _plain(result.stdout)
    assert "Not generated from the bblocks template" in plain
    # contract.not_adopted claims no ContractItem; the unclaimed-codes bucket
    # must render it rather than drop it.
    assert "Family contract" in plain
    # Scaffolding/Drift/Components checks that compare against the (absent)
    # answers file never ran — "not checked" must not read as "healthy".
    assert "not checked: no .copier-answers.yml" in plain
    assert "Scaffolding healthy" not in plain
    assert "Drift healthy" not in plain
    assert "Components healthy" not in plain


def test_doctor_family_na_glyph_for_non_fetching_package(tmp_path: Path) -> None:
    """A package with no HTTP and no cache renders the n/a glyph for items 6
    and 7, not a false pass."""
    _make_bblocks_project(
        tmp_path,
        preset="family",
        python_version="3.12",
        package_modules={"__init__.py": "x = 1\n"},
    )
    result = runner.invoke(app, ["doctor", "--path", str(tmp_path), "--family"])
    assert result.exit_code == 0
    plain = _plain(result.stdout)
    assert "–  6. readerkit for HTTP and caching" in plain  # noqa: RUF001
    assert "–  7. Cache redirectable and disableable" in plain  # noqa: RUF001


def test_doctor_family_skipped_glyph_when_package_cannot_be_scanned(
    tmp_path: Path,
) -> None:
    """A package doctor can't scan at all (no __init__.py anywhere under
    src/) must not render the same n/a dash as a package that genuinely
    doesn't fetch or cache — that reads as "nothing to do here" when the
    truth is "doctor couldn't tell." --strict must still exit 0: an advisory
    is honest uncertainty, not a proven violation."""
    # package_modules=None (explicit, overriding make_family_project's
    # default) keeps every other item clean — OIDC's publish workflow, the
    # 3.12 floor — so --strict exiting 0 is attributable to items 6/7 alone.
    _make_family_project(tmp_path, package_modules=None)
    result = runner.invoke(
        app, ["doctor", "--path", str(tmp_path), "--family", "--strict"]
    )
    assert result.exit_code == 0
    plain = _plain(result.stdout)
    assert "–  6. readerkit for HTTP and caching" not in plain  # noqa: RUF001
    assert "–  7. Cache redirectable and disableable" not in plain  # noqa: RUF001
    assert "could not determine readerkit adoption" in plain
    assert "could not determine cache-contract compliance" in plain


def test_doctor_family_check_remote_flags_unprotected_branch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _make_family_project(tmp_path)
    monkeypatch.setattr(Project, "get_git_remote_slug", lambda self: "ONEcampaign/demo")

    class _FakeCompleted:
        def __init__(self, returncode: int, stdout: str) -> None:
            self.returncode = returncode
            self.stdout = stdout
            self.stderr = ""

    def fake_run(args: list[str], **kwargs: object) -> _FakeCompleted:
        if args[-1].endswith("/protection"):
            return _FakeCompleted(1, '{"message":"Branch not protected"}')
        return _FakeCompleted(0, "[]")

    monkeypatch.setattr("bblocks.projects.contract.subprocess.run", fake_run)
    monkeypatch.setattr(
        "bblocks.projects.contract.urlopen",
        lambda url, timeout=8: _FakeConnResponse(200),
    )
    result = runner.invoke(
        app,
        ["doctor", "--path", str(tmp_path), "--family", "--check-remote", "--strict"],
    )
    plain = _plain(result.stdout)
    assert "main is not protected on ONEcampaign/demo" in plain
    assert result.exit_code == 1


class _FakeConnResponse:
    def __init__(self, status: int) -> None:
        self.status = status

    def __enter__(self) -> "_FakeConnResponse":
        return self

    def __exit__(self, *exc_info: object) -> bool:
        return False


def test_render_contract_panel_buckets_unclaimed_codes() -> None:
    """Any `contract.*` finding whose code claims no `ContractItem` prints in
    the trailing bucket instead of vanishing — proven generically, not just
    for the one code (`contract.not_adopted`) that exists today."""
    finding = Finding("contract.totally_new_code", "advisory", "surprise finding", None)
    with console.capture() as capture:
        _render_contract_panel([finding], na_keys=frozenset(), title="Family contract")
    assert "surprise finding" in capture.get()


def test_render_contract_panel_escapes_bracketed_text(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Finding text goes straight into `Panel(...)`, and Rich's markup parser
    treats bracketed text as a style tag on sight —
    `Console().print("no [build-system] table")` silently deletes
    `[build-system]` with no error. Real contract findings and remediations
    carry literal TOML section names in brackets (`[build-system]`,
    `[tool.ty.src]`), so they must survive rendering escaped rather than
    stripped.
    """
    monkeypatch.setattr(console, "width", 200)
    finding = Finding(
        "contract.build_backend",
        "finding",
        "no [build-system] table",
        'Set build-backend = "uv_build" and requires = ["uv_build"] in [build-system]',
    )
    with console.capture() as capture:
        _render_contract_panel([finding], na_keys=frozenset(), title="Family contract")
    plain = _plain(capture.get())
    assert "no [build-system] table" in plain
    assert 'requires = ["uv_build"] in [build-system]' in plain


def test_render_contract_panel_unclaimed_bucket_escapes_brackets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The unclaimed-codes bucket is a separate render path from the
    per-item loop above; it needs its own escaping, not just the main one.
    """
    monkeypatch.setattr(console, "width", 200)
    finding = Finding(
        "contract.totally_new_code",
        "advisory",
        "no [tool.ty.src] section is configured",
        'Add a [tool.ty.src] include = ["src/<slug>"] section',
    )
    with console.capture() as capture:
        _render_contract_panel([finding], na_keys=frozenset(), title="Family contract")
    plain = _plain(capture.get())
    assert "no [tool.ty.src] section is configured" in plain
    assert 'Add a [tool.ty.src] include = ["src/<slug>"] section' in plain


def test_render_doctor_report_escapes_bracketed_finding_and_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The generic per-section loop (scaffolding/drift/components/template)
    is a third render path from the two contract-panel ones above, and the
    project path in the report header is interpolated outside any Finding
    at all — both need to survive a bracket in the text.
    """
    monkeypatch.setattr(console, "width", 200)
    project_dir = tmp_path / "proj[legacy]"
    project_dir.mkdir()
    project = Project(project_dir)
    finding = Finding(
        "scaffolding.demo",
        "finding",
        "missing [tool.pytest.ini_options] section",
        "Add a [tool.pytest.ini_options] section",
    )
    with console.capture() as capture:
        _render_doctor_report(project, [finding])
    plain = _plain(capture.get())
    assert "proj[legacy]" in plain
    assert "missing [tool.pytest.ini_options] section" in plain
    assert "Add a [tool.pytest.ini_options] section" in plain


def test_no_contract_item_claims_not_adopted() -> None:
    claimed = {code for item in FAMILY_CONTRACT for code in item.codes}
    assert "contract.not_adopted" not in claimed


def test_update_passes_overwrite_and_default_ref(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    mock_run_update = MagicMock()
    monkeypatch.setattr("bblocks.projects.cli.run_update", mock_run_update)
    _make_bblocks_project(tmp_path)
    result = runner.invoke(app, ["update", "--path", str(tmp_path)])
    assert result.exit_code == 0
    mock_run_update.assert_called_once()
    _, kwargs = mock_run_update.call_args
    assert kwargs["overwrite"] is True
    assert kwargs["defaults"] is True
    assert kwargs["vcs_ref"] == "main"


def test_update_uses_explicit_ref_when_provided(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    mock_run_update = MagicMock()
    monkeypatch.setattr("bblocks.projects.cli.run_update", mock_run_update)
    _make_bblocks_project(tmp_path)
    result = runner.invoke(app, ["update", "--path", str(tmp_path), "--ref", "v0.2.0"])
    assert result.exit_code == 0
    mock_run_update.assert_called_once()
    _, kwargs = mock_run_update.call_args
    assert kwargs["vcs_ref"] == "v0.2.0"


def test_create_passes_cleanup_on_error_false(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    mock_run_copy = MagicMock()
    monkeypatch.setattr("bblocks.projects.cli.run_copy", mock_run_copy)
    monkeypatch.setattr(
        "bblocks.projects.cli.subprocess.run",
        lambda *a, **kw: subprocess.CompletedProcess(a, 0),
    )
    result = runner.invoke(
        app,
        ["create", str(tmp_path / "newproj"), "--defaults", "--no-github"],
    )
    assert result.exit_code == 0
    mock_run_copy.assert_called_once()
    _, kwargs = mock_run_copy.call_args
    assert kwargs["cleanup_on_error"] is False


def test_create_refuses_existing_file_escapes_bracketed_path(tmp_path: Path) -> None:
    """Same class of bug as the doctor render paths (see
    `test_render_doctor_report_escapes_bracketed_finding_and_path`): a
    user-typed destination reaches `console.print` directly, and Rich reads
    a bracket in a path as a style tag unless it's escaped.
    """
    bad_destination = tmp_path / "proj[legacy]"
    bad_destination.write_text("not a directory", encoding="utf-8")
    result = runner.invoke(
        app, ["create", str(bad_destination), "--defaults", "--no-github"]
    )
    assert result.exit_code == 1
    assert "proj[legacy]" in _plain(result.stdout)


def test_create_copier_error_escapes_brackets(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`CopierError` text is copier's own rendering of template output, and
    this template has directory names shaped like Jinja conditionals — a
    `[...]`-looking fragment in the error is plausible, not hypothetical.
    """

    def fake_run_copy(*args: object, **kwargs: object) -> None:
        raise CopierError("cannot render [tool.ty.src] block")

    monkeypatch.setattr("bblocks.projects.cli.run_copy", fake_run_copy)
    monkeypatch.setattr(
        "bblocks.projects.cli.subprocess.run",
        lambda *a, **kw: subprocess.CompletedProcess(a, 0),
    )
    result = runner.invoke(
        app, ["create", str(tmp_path / "newproj"), "--defaults", "--no-github"]
    )
    assert result.exit_code == 1
    assert "[tool.ty.src]" in _plain(result.stdout)


@pytest.mark.parametrize(
    ("failing_tool", "failure_mode"),
    [("git", "returncode_nonzero"), ("uv", "filenotfound")],
)
def test_create_preflights_missing_tool_exits_one(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failing_tool: str,
    failure_mode: str,
) -> None:
    mock_run_copy = MagicMock()
    monkeypatch.setattr("bblocks.projects.cli.run_copy", mock_run_copy)

    def fake_subprocess_run(
        cmd: list[str], **kwargs: object
    ) -> subprocess.CompletedProcess:  # type: ignore[type-arg]
        if cmd[0] == failing_tool:
            if failure_mode == "filenotfound":
                raise FileNotFoundError(f"{failing_tool} not found")
            return subprocess.CompletedProcess(cmd, returncode=1)
        return subprocess.CompletedProcess(cmd, returncode=0)

    monkeypatch.setattr("bblocks.projects.cli.subprocess.run", fake_subprocess_run)
    result = runner.invoke(
        app, ["create", str(tmp_path / "newproj"), "--defaults", "--no-github"]
    )
    assert result.exit_code == 1
    assert failing_tool in result.stdout
    mock_run_copy.assert_not_called()
    mock_run_copy.assert_not_called()


def test_help_text_does_not_leak_cwd() -> None:
    cwd_str = str(Path.cwd())
    for subcmd in ("update", "add", "doctor"):
        result = runner.invoke(app, [subcmd, "--help"])
        assert result.exit_code == 0
        assert cwd_str not in result.stdout, (
            f"{subcmd} --help leaks CWD: {cwd_str!r} found in output"
        )


def test_add_bogus_component_yes_exits_one(tmp_path: Path) -> None:
    _make_bblocks_project(tmp_path)
    result = runner.invoke(app, ["add", "bogus-name", "--yes", "--path", str(tmp_path)])
    assert result.exit_code == 1


def test_add_unknown_component_escapes_bracketed_name(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`component_name` is a raw CLI argument; a bracket in it must survive
    the "Unknown component" message rather than being read as a style tag.

    `add` enters `rendered_template_for` (which clones the template via
    copier) before it ever looks up the component name, so reaching the
    "Unknown component" branch at all — with or without a bracket — requires
    a `uv.lock` (to clear `validate_for_component`) *and* a stub for
    `rendered_template_for` (to avoid a real network clone). Without the
    stub this is network-dependent: it happens to pass on a machine with a
    warm copier cache and git credentials, and fails in CI with a git clone
    error, never printing the message this test is meant to check.
    """
    _make_bblocks_project(tmp_path)
    (tmp_path / "uv.lock").touch()

    @contextlib.contextmanager
    def fake_rendered_template_for(project: object) -> Iterator[Path]:
        yield tmp_path

    monkeypatch.setattr(
        "bblocks.projects.installer.rendered_template_for", fake_rendered_template_for
    )
    result = runner.invoke(
        app, ["add", "bogus[name]", "--yes", "--path", str(tmp_path)]
    )
    plain = _plain(result.stdout)
    assert "Unknown component: bogus[name]" in plain
    assert result.exit_code == 1


def test_add_partial_success_exits_one(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _make_bblocks_project(tmp_path)

    import bblocks.projects.installer as _installer  # noqa: PLC0415

    def fake_install_component(
        component: object,
        project: object,
        *,
        force: bool = False,
        interactive: bool = True,
        rendered_template_dir: object = None,
    ) -> bool:
        from bblocks.projects.components import ComponentDef  # noqa: PLC0415

        assert isinstance(component, ComponentDef)
        return component.name == "pre-commit"  # type: ignore[union-attr]

    monkeypatch.setattr(_installer, "install_component", fake_install_component)

    result = runner.invoke(
        app,
        ["add", "pre-commit", "bogus-name", "--yes", "--path", str(tmp_path)],
    )
    assert result.exit_code == 1


def test_add_install_component_returns_false_exits_one(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A real component whose install_component returns False must exit 1."""
    _make_bblocks_project(tmp_path)

    import bblocks.projects.installer as _installer  # noqa: PLC0415

    monkeypatch.setattr(_installer, "install_component", lambda *a, **kw: False)

    result = runner.invoke(app, ["add", "pre-commit", "--yes", "--path", str(tmp_path)])
    assert result.exit_code == 1
