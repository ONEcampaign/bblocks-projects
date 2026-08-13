# How to update an existing project

`uvx bblocks-projects update` re-runs the template against a project that was created from it, merging the latest template changes into your working tree. Your code, dependencies, and data stay where they are; only template-managed files move.

This guide assumes the project was originally generated with `bblocks-projects create` (or has a hand-rolled `.copier-answers.yml`). If it wasn't, see [Adopting an existing project](adopting-an-existing-project.md).

## Before you start

- Run from inside the project directory, or pass `--path` to point at it.
- Commit or stash uncommitted changes first. The update writes directly to the working tree — it's much easier to review the diff against a clean baseline.

## Update to the latest template

```bash
cd my-project
uvx bblocks-projects update
```

What happens:

1. Copier reads `.copier-answers.yml` to find the template URL and the commit you originally rendered from.
2. It re-runs the template at the new version (default: `main`), feeding it your previous answers so it doesn't re-prompt.
3. It applies the diff between old-template and new-template to your working tree, merging where it can.
4. It stops there — no `git init`, no automatic commit, no `uv sync`, no reinstalling the pre-commit hook. Copier runs none of the template's post-generation tasks on update, on purpose (see "What the update will and won't touch" below). You run `uv sync`, `uv run pre-commit install` if the hook config changed, and `git commit` yourself, same as any other working-tree change.

Then review and commit:

```bash
git diff
uv sync                      # refresh the lockfile if pyproject changed
uv run pytest                # for packages
git commit -am "Update from template"
```

## Update to a specific template version

```bash
uvx bblocks-projects update --ref v1.2.0       # pin to a tag
uvx bblocks-projects update --ref develop      # try a branch
uvx bblocks-projects update --ref abc1234      # roll back to a commit
```

Useful when your team standardises on a known-good version, or when you want to test an unreleased branch before adopting it.

## Re-answer questions

By default, `update` reuses your previous answers silently. To re-prompt for any of them:

```bash
uvx bblocks-projects update --no-skip-answered
```

Use this when something fundamental has changed — Python version, license, author name. To change one or two specific answers without re-prompting for all of them, pass `--data`:

```bash
uvx bblocks-projects update \
  --data author_email=jane@one.org \
  --data python_version=3.12
```

## Resolve conflicts

When the template changed a file _and_ you've changed the same file, Copier writes Git-style conflict markers into the file:

```
<<<<<<< before updating
your version
=======
template version
>>>>>>> after updating
```

Open the file, pick what you want to keep (often a mix), delete the markers, save, and stage the file. `git status` will list any file with unresolved markers.

You can also abandon the merge and start over:

```bash
git checkout -- path/to/conflicted/file
uvx bblocks-projects update
```

…or accept the template's version wholesale:

```bash
git checkout --theirs path/to/file   # only works mid-rebase, not after copier
# or, simpler:
rm path/to/file && uvx bblocks-projects update
```

## What the update will and won't touch

Touched: anything the template owns. That includes `.github/workflows/`, `.pre-commit-config.yaml`, `.gitignore`, the tool sections of `pyproject.toml` (`[tool.ruff]`, `[tool.ty]`, etc.), and the generated `README.md` if you haven't customised it.

Not touched: your source code, your dependency list (`[project.dependencies]`), your data, your git history, your custom CI jobs. Copier's three-way merge is conservative — if you've edited a file, the updater tries to preserve your edits and only flags a conflict when it genuinely can't.

Before 1.1.1, this guarantee had a hole: Copier applies template changes to your real working tree _before_ it replays that merge, and the template's post-generation tasks (`git init`, `uv venv`, `uv sync`, `git add`, `git commit`, installing the pre-commit hook) used to re-run at that point too. If one of them failed — a pre-commit hook reformatting a file during the commit was enough, but a `uv sync` network hiccup or dependency conflict would have done it just as well — the update aborted right there, leaving your source and tests overwritten with template scaffold and no merge ever applied. 1.1.1 stopped every one of those tasks from running on `update`, closing that hole for good: rather than judging each task as "safe enough" to leave running, none of them run, so there's no task left that can abort the update partway through.

## Verify it worked

```bash
git status                     # any conflicts will show as "both modified"
git diff                       # review what changed
uv sync
uv run ruff check .
uv run pytest                  # packages
uvx bblocks-projects doctor    # quick sanity check against the standards
```

If `doctor` flags drift after an update, the [doctor how-to](running-the-doctor.md) explains each finding.

## Troubleshooting

**`No .copier-answers.yml found`**
The project wasn't created from this template, or someone deleted the file. See [Adopting an existing project](adopting-an-existing-project.md).

**`Template version not found`**
The ref you passed doesn't exist in the template repo. Check available refs with:

```bash
git ls-remote --tags https://github.com/ONEcampaign/bblocks-projects
git ls-remote --heads https://github.com/ONEcampaign/bblocks-projects
```

**Update completes but `uv sync` fails**
The template may have bumped a dependency lower bound. Delete `uv.lock` and re-sync:

```bash
rm uv.lock && uv sync
```

**`uv.lock` disappeared after updating to 1.1.1 (or later)**
Expected, one-time, and harmless: run `uv sync` and it's back. `uv.lock` isn't a template file — it only exists because `uv sync` used to run automatically. Updating a project that was still on an older template version, onto 1.1.1 or later, is the one update where Copier's internal bookkeeping sees `uv.lock` "disappear" from what the template produces and removes it from your project to match. It won't happen again on your next update.

**Pre-commit fails on files you didn't touch**
The template updated the `ruff` or `ty` config to a stricter rule set. Either fix the issues (`uv run ruff check --fix .`), or revert the relevant section of `pyproject.toml` and open an issue on the template repo if you think the rule shouldn't have shipped.

## See also

- [Reference: `update` flags](reference.md#update) — for the full flag list and exit codes
- [Running the doctor](running-the-doctor.md) — to sanity-check the project after an update
- [Copier's documentation on updating](https://copier.readthedocs.io/en/stable/updating/) — for the underlying merge mechanics
