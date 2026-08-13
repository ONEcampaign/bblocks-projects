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

## Check the family contract

`--family` runs the [bblocks family contract](the-family-contract.md) checks — the twelve conventions that keep `oda_reader`, `readerkit`, `imf-reader`, and the rest of the family consistent. It runs automatically when `.copier-answers.yml` records `preset: family`; pass the flag explicitly for a repo that answered `standalone`, or one that predates the `preset` question and has no answers file at all:

```bash
uvx bblocks-projects doctor --path /path/to/my-package --family
```

```
Doctor report for /path/to/my-package

╭───── Scaffolding ─────╮
│ ✓ Scaffolding healthy │
╰───────────────────────╯
╭───── Drift ─────╮
│ ✓ Drift healthy │
╰─────────────────╯
╭───── Components ─────╮
│ ✓ Components healthy │
╰──────────────────────╯
╭──────────────────────────── Family contract ────────────────────────────╮
│ ✓  1. uv build backend                                                  │
│ ✓  2. ruff                                                              │
│ ✓  3. ty                                                                │
│ ✓  4. pre-commit                                                        │
│ ✓  5. Python floor 3.12                                                 │
│ –  6. readerkit for HTTP and caching                                    │
│ –  7. Cache redirectable and disableable                                │
│ ✓  8. No import-time side effects                                       │
│ ✓  9. No upper-bound pins                                               │
│ ✓ 10. OIDC publishing                                                   │
│ ! 11. Branch protection                                                 │
│    ! branch-protection check skipped: not checked (pass --check-remote) │
│ ! 12. conda-forge feedstock                                             │
│    ! feedstock check skipped: not checked (pass --check-remote)         │
╰─────────────────────────────────────────────────────────────────────────╯
╭───── Template version ─────╮
│ ✓ Template version healthy │
╰────────────────────────────╯
2 advisories (informational)
```

Items 6 and 7 render `–` here because this package doesn't do HTTP or caching — not applicable, not a pass. Items 11 and 12 need the network; add `--check-remote` to actually run them instead of reporting the skip advisory:

```bash
uvx bblocks-projects doctor --path /path/to/my-package --family --check-remote --strict
```

`--check-remote` calls `gh api` (branch protection) and `api.anaconda.org` (the conda-forge feedstock), 8-second timeout each. Every failure mode — no `gh` on `PATH`, a timeout, a 403 that means "can't tell" rather than "unprotected" — degrades to the same `*_skipped` advisory rather than a false finding.

See [The bblocks family contract](the-family-contract.md) for what each item means, the two named exemptions, and the checks' known false negatives and false positives.

## What it checks

Four severities, grouped into five sections:

- **Catastrophic** — the project is unreadable (`pyproject.toml` missing, malformed, or unreadable; `.copier-answers.yml` missing, unreadable, malformed, or not a YAML mapping). Always exits non-zero. Other checks are skipped because they can't run.
- **Finding** — a drift the maintainer should know about: project type doesn't match the on-disk layout, `project_slug` in `.copier-answers.yml` doesn't match the actual package name, `python_version` in `.copier-answers.yml` disagrees (in either direction) with the lower bound parsed from `requires-python`, a standard component is missing, the local template is behind upstream, or (under `--family`) a family-contract item fails outright.
- **Advisory** — informational only: `--check-updates` or `--check-remote` couldn't reach the network, a family-contract source scan couldn't run or couldn't attribute what it found to a job or module, an import-time call `doctor` can't classify, or an item that's exempted rather than checked (the Python-floor exemption).
- **Not applicable** (`–`) — family-contract items 6 and 7 render this instead of a pass when the package doesn't fetch or doesn't cache at all. Only appears in the Family contract section, only under `--family`.

The five sections in the report:

| Section          | What it covers                                                                                                 |
| ---------------- | -------------------------------------------------------------------------------------------------------------- |
| Scaffolding      | `pyproject.toml` and `.copier-answers.yml` parseability                                                        |
| Drift            | `project_type`, `project_slug`, `python_version` agreement between answers and actual files                    |
| Components       | Whether each standard component (pre-commit, ruff, ci, pytest, and — for packages — pypi-publish) is installed |
| Family contract  | The twelve items in [the family contract](the-family-contract.md), only under `--family`                       |
| Template version | Local `_commit` vs upstream `HEAD` (only when `--check-updates` is passed)                                     |

## Use it in CI

Exit codes:

- Default: exit `0` unless something is catastrophic.
- `--strict`: exit `1` on any _finding_ (advisories never affect the exit code).

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

**`branch-protection check skipped: gh lacks permission to check (HTTP 403)`**
The `gh` token authenticated on this machine doesn't have admin rights on the repo, so `doctor` can't tell whether `main` is protected — a 403 means "can't tell", not "unprotected". This is an advisory; `--strict` won't fail on it. Use a token with admin access on the repo to get a real answer.

**`branch-protection check skipped: not checked (pass --check-remote)` / `feedstock check skipped: not checked (pass --check-remote)`**
Expected without `--check-remote` — items 11 and 12 are the only two family-contract checks that touch the network, and `doctor` doesn't make network calls unless you ask it to. Add `--check-remote` to actually run them; see [Check the family contract](#check-the-family-contract).

**`contract.readerkit` finding on a package that doesn't actually fetch**
The check is a static heuristic (see [the family contract](the-family-contract.md#known-false-negatives-and-false-positives)): `urllib.request` is on the fetch-indicator list because it's a fetch mechanism, but it's also the home of `pathname2url`. A package importing it only to build `file://` URLs gets flagged with nothing to migrate — `import urllib.request` and `from urllib.request import pathname2url` both match, since the check only looks at which module an import statement names, not which symbol it pulls from it. This is a `finding`, so `--strict` fails on it. There's no suppression flag; note the false positive where it comes up (a PR comment, or a line in the repo's own docs) rather than restructuring the import to dodge it.

## See also

- [Reference: `doctor` flags](reference.md#doctor)
- [Updating projects](updating-projects.md) — most "Template version" findings are fixed by `update`
- [Adding components](adding-components.md) — most "Components" findings are fixed by `add`
