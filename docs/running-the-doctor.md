# How to run the doctor

`uvx bblocks-projects doctor` runs a set of health checks against a managed project and prints a report grouped by section. Use it to see what's drifted from the standards (manual edits, missed updates, deleted files) without re-running the full template.

## Before you start

`doctor` only works on bblocks-managed projects. The project must have:

- A `pyproject.toml` at the root.
- A `.copier-answers.yml` recording which template version generated it.

If either is missing, `doctor` exits with an error and points you at the [adoption guide](adopting-an-existing-project.md).

## Diagnose the current project

```bash
cd my-project
uvx bblocks-projects doctor
```

A healthy project prints four green panels and a `Healthy` summary:

```
Doctor report for /Users/you/my-project

╭─ Scaffolding ────────────────╮
│ ✓ Scaffolding healthy        │
╰──────────────────────────────╯
╭─ Drift ──────────────────────╮
│ ✓ Drift healthy              │
╰──────────────────────────────╯
╭─ Components ─────────────────╮
│ ✓ Components healthy         │
╰──────────────────────────────╯
╭─ Template version ───────────╮
│ ✓ Template version healthy   │
╰──────────────────────────────╯
Healthy
```

A project with issues shows the specific findings and suggested remediations.

## Diagnose a project somewhere else

```bash
uvx bblocks-projects doctor --path /path/to/project
```

Useful when scripting checks across several projects.

## Check whether the template has moved

By default, `doctor` doesn't touch the network. The `--check-updates` flag adds one extra check that compares your local template commit against the upstream repo's `HEAD`:

```bash
uvx bblocks-projects doctor --check-updates
```

If the upstream has newer commits, the Template panel will show:

```
✗ Local template at abc1234e but remote main is at def56789
   → bblocks-projects update
```

The check uses `git ls-remote` and times out after 5 seconds. On a network failure it downgrades to an advisory rather than a hard finding.

## What it checks

Three severities, grouped into four sections:

- **Catastrophic** — the project is unreadable (`pyproject.toml` missing or malformed, `.copier-answers.yml` missing, malformed, or not a YAML mapping). Always exits non-zero. Other checks are skipped because they can't run.
- **Finding** — a drift the maintainer should know about: project type doesn't match the on-disk layout, `project_slug` in `.copier-answers.yml` doesn't match the actual package name, `python_version` in `.copier-answers.yml` disagrees (in either direction) with the lower bound parsed from `requires-python`, a standard component is missing, or the local template is behind upstream.
- **Advisory** — informational only. Currently used when `--check-updates` couldn't reach the network.

The four sections in the report:

| Section | What it covers |
|---|---|
| Scaffolding | `pyproject.toml` and `.copier-answers.yml` parseability |
| Drift | `project_type`, `project_slug`, `python_version` agreement between answers and actual files |
| Components | Whether each standard component (pre-commit, ruff, ci, pytest, and — for packages — pypi-publish) is installed |
| Template version | Local `_commit` vs upstream `HEAD` (only when `--check-updates` is passed) |

## Use it in CI

Exit codes:

- Default: exit `0` unless something is catastrophic.
- `--strict`: exit `1` on any *finding* (advisories never affect the exit code).

A typical CI job:

```yaml
- name: Project doctor
  run: uvx bblocks-projects doctor --strict --check-updates
```

This will fail the build if the project has drifted from the standards or is behind upstream. Drop `--check-updates` if you don't want CI making network calls outside the workflow's pinned actions.

## Verify it worked

If `doctor` exits cleanly with the four green panels, you're done. If it surfaced findings, each one prints a one-line remediation under the message:

```
✗ Component not installed: pytest (Pytest with coverage reporting)
   → bblocks-projects add pytest
```

Run the suggested command and re-run `doctor` to confirm.

## Troubleshooting

**`This project doesn't appear to be bblocks-managed (no .copier-answers.yml)`**
Either run `bblocks-projects create` to generate the project from scratch, or follow [Adopting an existing project](adopting-an-existing-project.md) to write a `.copier-answers.yml` by hand.

**`pyproject.toml is malformed: ...`**
Catastrophic. Fix the TOML syntax error first; until then, the rest of the checks can't run.

**`project_slug='donor_analysis' but pyproject name slugifies to 'donor-analysis'`**
Either rename `[project].name` in `pyproject.toml` to match `.copier-answers.yml`, or update the `project_slug` line in `.copier-answers.yml` to match the package. The two need to agree for `update` to know which slug-derived paths to manage.

**`template-version check skipped: TimeoutExpired`**
Your network couldn't reach the template repo within 5 seconds. This is an advisory, not a finding — `doctor` will still exit cleanly. Re-run on a better connection if you need the check to run.

## See also

- [Reference: `doctor` flags](reference.md#doctor)
- [Updating projects](updating-projects.md) — most "Template version" findings are fixed by `update`
- [Adding components](adding-components.md) — most "Components" findings are fixed by `add`
