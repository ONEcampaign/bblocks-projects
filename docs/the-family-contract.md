# The bblocks family contract

> As of `bblocks-projects 1.1.0`.

## What this is

The bblocks family is the set of ONE Data Python packages meant to interoperate — `oda_reader`, `readerkit`, `imf-reader`, `pydeflate`, `resolvekit`, `bblocks`, `bblocks-places`, and others. Twelve conventions keep them consistent: one build backend, one lint/type toolchain, one Python floor, one HTTP/caching library, no import-time surprises, no upper-bound pins, trusted PyPI publishing, protected branches, conda-forge availability.

`bblocks-projects doctor --family` checks a repo against all twelve and reports pass, fail, or not-applicable for each. This page is what each item means, how a repo opts in, and where the checks are known to be wrong.

## The twelve items

| #   | Item                               | `doctor` checks                                                            | Severity                                                    |
| --- | ---------------------------------- | -------------------------------------------------------------------------- | ----------------------------------------------------------- |
| 1   | uv build backend                   | `[build-system].build-backend` is `"uv_build"`                             | finding                                                     |
| 2   | ruff                               | `tool.ruff*` configured and `ruff` in dev deps                             | finding                                                     |
| 3   | ty                                 | `ty` in dev deps and `[tool.ty.src]` or `[tool.ty.environment]` configured | finding                                                     |
| 4   | pre-commit                         | `.pre-commit-config.yaml` at the git root and `pre-commit` in dev deps     | finding                                                     |
| 5   | Python floor 3.12                  | `requires-python` lower bound is `>=3.12` or higher                        | finding (advisory if exempt)                                |
| 6   | readerkit for HTTP and caching     | a package that fetches depends on and imports `readerkit`                  | finding (advisory if exempt), n/a if it doesn't fetch       |
| 7   | Cache redirectable and disableable | a package that caches exposes a redirect, an env var, and a disable path   | finding, n/a if it doesn't cache                            |
| 8   | No import-time side effects        | nothing on the I/O denylist runs during `import <package>`                 | finding (denylisted calls), advisory (unclassifiable calls) |
| 9   | No upper-bound pins                | no `<`, `<=`, `~=`, or `==` cap on a runtime dependency                    | finding (advisory if exempt)                                |
| 10  | OIDC publishing                    | the PyPI publish workflow uses trusted publishing, not a token             | finding, packages only                                      |
| 11  | Branch protection                  | `main` is protected — classic protection or a ruleset                      | finding, only under `--check-remote`                        |
| 12  | conda-forge feedstock              | a conda-forge package exists for the project                               | finding, packages only, `--check-remote`                    |

Items 1–5 and 9 read straight off `pyproject.toml` — no interpretation involved. Item 10 parses the git root's `.github/workflows/*.yml` as structured YAML to resolve which job publishes and what permissions actually apply to it, falling back to a whole-file text scan when it can't. Items 6, 7, and 8 are static source-inspection heuristics: `doctor` walks the package's AST without executing it. Items 11 and 12 are the only two that touch the network.

### Item 5: the floor, and how it's enforced going forward

`requires-python` must have a lower bound of `3.12` or higher. This is a `finding`, so `doctor --strict --family` fails on it.

It's also enforced earlier than `doctor`: once a repo's `.copier-answers.yml` records `preset: family` (see below), the `python_version` question's validator runs on every subsequent `copier update` — a family repo still on `3.11` makes `copier update` fail outright, not just `doctor`.

### Item 6: readerkit for HTTP and caching

A package that fetches over HTTP must depend on and import [`readerkit`](https://github.com/ONEcampaign/readerkit) rather than rolling its own `requests`/`httpx`/caching stack. "Does it fetch" is decided first — a package with no HTTP surface renders `–` (not applicable), not a pass.

Detection: `doctor` checks the runtime dependency list for `requests`, `httpx`, `httpx2`, `aiohttp`, `urllib3`, `requests-cache`, or `requests-ratelimiter`, and separately scans the package's own first-party imports for `requests`, `httpx`, `httpx2`, `aiohttp`, `urllib.request`, or `http.client`. If either signal fires, the package must also declare and import `readerkit`.

"Doesn't fetch" and "couldn't tell" are different outcomes. When no package can be found under `src/`, or a module the scan needed to read fails to parse, `doctor` can't say either way — it reports `contract.readerkit_skipped` (an advisory) rather than rendering the `–` a genuine non-fetcher earns.

### Item 7: the cache contract

A package that caches must let callers redirect the cache directory, read it back from an env var, and disable caching entirely. "Does it cache" is decided first, the same way as item 6 — no cache surface renders `–`.

Three sub-checks, each independently satisfiable:

- **Redirect** — a public name matching `set_*cache*dir` (e.g. `set_cache_dir`), or any public function taking a `cache_dir` keyword argument.
- **Env var** — a string literal shaped like `<SLUG>_CACHE_DIR` anywhere in the package, or a call to `readerkit.resolve_cache_dir(...)` (which derives the env var name for free).
- **Disable** — a public name matching `disable_*cache*` or `*cache*_disable`, or the package importing `readerkit` (delegating to the provider means the provider's disable path is the package's disable path).

The same distinction item 6 draws applies here: when the scan can't run, or a module that might cache fails to parse, `doctor` can't tell "doesn't cache" from "couldn't check" — it reports `contract.cache_skipped` (an advisory) instead of guessing at the `–`.

### Item 8: no import-time side effects

`import <package>` must not touch the network, the filesystem, or a subprocess. `doctor` builds the package's import graph (starting at each package root's `__init__.py`, following only first-party imports) and walks each reachable module's AST.

Only the _body_ of a function, async function, or lambda is pruned — code that runs when the function is called, not when the module is imported. Everything else attached to a `def`, `lambda`, or `class` statement runs while that statement itself executes, so it's in scope: decorator expressions, parameter defaults, parameter and return annotations, and — for classes — base classes and metaclass keywords, alongside the class body. Annotations are the one exception: `from __future__ import annotations` defers every annotation in the module to a string, and a bare forward-reference string annotation (`-> "SomeType"`) is never evaluated either way, so both are skipped rather than walked.

Every surviving call is classified three ways:

- **Denylisted** (`contract.import_io`, a `finding`) — `open`, `requests.*`, `pandas.read_*`, `subprocess.run`, `Path(...).mkdir()`, and similar. Definite I/O.
- **Allowlisted** (no finding) — `logging.getLogger`, `re.compile`, `TypeVar(...)`, bare `Path(...)` construction, `Path(__file__)` chained through any mix of `.parent`, `.parents[...]`, and `.resolve()` (the idiom a module uses to locate its own directory), and decorator factories verified to touch only the object they decorate — `@dataclass(...)`, `@functools.lru_cache(...)`, `@pydantic.field_validator(...)`/`@pydantic.model_validator(...)`, `@abc.abstractmethod`, `@enum.unique`, and the called forms of `property`/`staticmethod`/`classmethod`. `typing.overload` is a deliberate exception: its called form appends to a module-level registry, which is exactly the kind of global-state mutation this item exists to catch, so it stays classified as opaque.
- **Opaque** (`contract.import_opaque`, an `advisory`) — a first-party call `doctor` can't classify either way, e.g. `_country_resolver = PlaceResolver(...)` at module level. Named with file and line, not silently passed.

A module that fails to parse is `contract.import_unreadable` (`advisory`), never silently skipped. Likewise, when no package can be found under `src/` at all, `doctor` can't run this scan — that renders `contract.import_no_package` (`advisory`), not a pass. "Could not tell" and "found nothing wrong" are different outcomes, and only one of them earns a green checkmark.

### Item 9: no upper-bound pins

No runtime dependency (`[project].dependencies` or any `[project.optional-dependencies]` list except `dev`) may cap an external library with `<`, `<=`, `~=`, or `==`. `!=` is not a cap. `[build-system].requires`, `[dependency-groups]`, and `[project.optional-dependencies.dev]` are not scanned — the template's own `uv_build<0.13` pin and dev-tool caps aren't dependencies a consumer resolves against, and `dev` is excluded here for the same reason `Project.has_dev_dependency` already treats it as the pre-PEP-735 home for dev tooling.

One finding per capped dependency, naming the exact spec and a relaxed replacement. A family sibling or a dependency still on a `0.x` version gets no exemption, and the one listed exemption under [Exemptions](#exemptions) names its dependencies. `readerkit>=0.1.0,<0.2` in a runtime dependency list is flagged the same as any other capped external dependency.

This has a consequence for `readerkit` itself: because every consumer declares it uncapped, `readerkit` must never bump `CACHE_SCHEMA_VERSION` without a coordinated family release. That constant is a path segment in every consumer's on-disk cache directory (see `readerkit.resolve_cache_dir`), so a schema bump silently relocates caches across the whole family the next time each consumer happens to pick up the new `readerkit` release — with no release of the consumer itself involved, and no version bound anywhere to stop it from arriving unannounced. The family accepts this as the trade-off for item 9 admitting no exemption for a family sibling.

### Item 10: OIDC publishing

The package's PyPI-publishing workflow must use [trusted publishing](https://docs.pypi.org/trusted-publishers/) (`permissions: id-token: write`, no token secret) rather than an API token. `doctor` looks for a publish command (`uv publish`, `twine upload`, `pypa/gh-action-pypi-publish`, `poetry publish`) across every workflow in the git root's `.github/workflows/*.yml` / `*.yaml`, the only workflows GitHub runs; no match at all is a finding on its own. A publishing job in a multi-language repo that runs `uv publish` with `working-directory: python` counts.

When a publish command does exist, `doctor` parses the workflow as YAML, finds the job that runs it, and checks _that job_ — not the file as a whole — for `id-token: write`. A job's own `permissions:` block replaces the workflow-level default rather than merging with it (GitHub Actions semantics, not a bblocks convention), so a job with `permissions:` of its own that omits `id-token: write` gets no credit for a workflow-level grant, and a grant on some other job never counts. Only a job with no `permissions:` of its own inherits the workflow-level block. Token use is checked the same way, scoped to the publishing job's own `env`/`with`/`run` text plus the workflow-level `env` it inherits: a named token secret (`PYPI_API_TOKEN`, `TWINE_PASSWORD`, and similar) fails it directly, and so does a secret bound to an arbitrarily-named variable that's then passed to a `--password`/`--token`/`-p`-shaped flag — the indirection a literal-name check alone would miss.

A workflow that can't be parsed as YAML, doesn't parse into a `jobs:` mapping, or matches a publish command without any individual job owning it (the step lives in a `uses:`-called reusable workflow, say) falls back to a whole-file text heuristic instead — the same `id-token: write` / token-secret scan, but unable to scope either to the publishing job specifically. `doctor` reports this with `contract.oidc_publish_unscoped`, an advisory, alongside whatever verdict the fallback reaches.

Packages only — `project`-type repos don't publish.

### Item 11: branch protection

`main` must carry protection that actually gates a merge — not just settings that stop a force push or a branch deletion. `doctor` checks classic branch protection first: it counts only when `required_pull_request_reviews` is configured, or `required_status_checks` names at least one check. Force-push restrictions, deletion restrictions, linear history, conversation resolution, and admin enforcement are all real protections, but none of them stops a direct push to `main` without a review or a passing check, so none of them counts on its own.

When classic protection isn't configured, or is configured but doesn't gate a merge, `doctor` falls back to the rulesets API. A ruleset counts only when it targets `main` (or the default-branch alias) without excluding it, is `enforcement: active` (not `evaluate` or `disabled`), and carries a `pull_request` or `required_status_checks` rule — a ruleset that only restricts, say, tag deletion doesn't count even though it matches everything else.

Only runs under `--check-remote`, since it calls `gh api`. A 403 (the token can't tell) degrades to `contract.branch_protection_skipped`, an advisory, not a false "unprotected" finding.

### Item 12: conda-forge feedstock

Packages must have a conda-forge feedstock. Only runs under `--check-remote`; it checks `https://api.anaconda.org/package/conda-forge/<name>` for the PEP-503-normalized project name. A 404 is a finding; anything else that isn't a clean 200 or 404 (a timeout, an unreachable host) degrades to `contract.conda_forge_skipped`.

## Exemptions

Three packages hold exemptions from parts of the contract, because the contract doesn't make sense applied to them. Each exemption is a named entry in `contract.py`, and no `pyproject.toml` or answers-file key opts a package out.

- **`dcp-tools`** is exempt from item 5 (the Python floor). It's on its own cadence. `doctor` reports this as an advisory (`contract.python_floor_exempt`), not a silent pass — the exemption stays visible in the report.
- **`readerkit`** is exempt from items 6 and 7 (readerkit adoption and the cache contract). It's the provider both items point at — it can't depend on itself or delegate to itself. `doctor` passes it outright rather than flagging a package for not using its own library.
- **`development-finance`**, the DFO client (import module `dfo`), is exempt from item 6. It needs an async `httpx2` transport and a store of immutable, digest-keyed dataset versions that a cache refresh never touches, and readerkit is synchronous with a TTL-bound cache. `doctor` reports `contract.readerkit_exempt`, an advisory, when the package fetches without readerkit (`READERKIT_EXEMPT` in `contract.py`, beside `FLOOR_EXEMPT`). Item 7 still applies in full: the client must expose a cache redirect, a `DFO_CACHE_DIR` env var, and a disable path.
- **`development-finance`** is also exempt from item 9 for `httpx2` and `httpcore2` alone. The client routes connections through their private pool layout to enforce its deadlines, so it bounds both below the next minor release, which could move that layout and break every client at construction. `doctor` reports each bound as `contract.dependency_cap_exempt`, an advisory (`CAP_EXEMPT` in `contract.py`), and any other capped dependency of the package is still a finding.

## A package in a multi-language repo

A repo that ships the same library in several languages keeps one package per language directory, with the Python package in `python/` holding its own `pyproject.toml`, `src/`, `tests/`, and `.copier-answers.yml`. Run `doctor --family --path python` against it. `doctor` reads `.pre-commit-config.yaml` and `.github/workflows/` from the root of the git work tree that contains `--path`, because pre-commit and GitHub Actions read them only there, so items 4 and 10 pass on the root's files. Every other item reads the package directory. Outside a git work tree, `--path` itself is the root. `bblocks-projects add` follows the same split below the git root: it installs a component's package-side part (dev dependencies and `pyproject.toml` sections) and skips `.pre-commit-config.yaml` and `.github/`, printing each skipped root path and whether it exists. `doctor` advises `bblocks-projects add <component>` when the package-side part is missing, names the root file when only that is missing, and names both when both are. A root workflow for a package in `python/` needs `working-directory: python` on its jobs, and a root pre-commit hook needs `uv run --directory python`; the template's own files assume the package sits at the root.

When `[tool.uv.build-backend] module-name` names the import package, as `module-name = "dfo"` does for `development-finance`, the answers file's `project_slug` should match `module-name`. The `drift.project_slug_mismatch` check compares against it.

## Known false negatives and false positives

The three source-inspection heuristics (items 6, 7, 8) read names and imports, not behavior. Their documented gaps live in `_source_scan.py`'s module docstring — the authoritative source — and are summarized here.

**Item 6 (readerkit adoption) false negatives:**

- A package that fetches only through a third-party client SDK (a vendored gRPC stub, `wbgapi`, `datacommons`) declares and imports none of the fetch-indicator libraries — it reads as "doesn't fetch".
- A package that fetches through a first-party sibling package reads as "doesn't fetch" at its own boundary. The sibling owns the contract; this is a gap in the check, not a judgment it made.
- `readerkit` declared and imported but used only for something like `cache_key`, while HTTP still goes through a bare `requests.Session`, reads as adopted. The check sees dependency edges and import statements, not call sites.
- A package that downloads files through `pooch` and nothing else reads as "doesn't fetch". `pooch` is deliberately excluded from the fetch-indicator list — it brings its own caching, and including it would gate a family repo (`resolvekit`) on an inference rather than on evidence.

**Item 7 (the cache contract) false negatives:**

- A redirect env var named outside the `<SLUG>_CACHE_DIR` / `resolve_cache_dir` shapes (e.g. `FOO_CACHE_PATH`) fails the env-var leg even when the package genuinely honors a redirect.
- A `set_cache_dir` that's a no-op stub passes the redirect leg. The check reads names, not behavior.

**Item 8 (import-time side effects) false negatives:**

- Anything reached only through a first-party call is invisible to the denylist; the resulting `contract.import_opaque` advisory names the call site but can't classify what it does.
- A module imported lazily inside a function, that itself does import-time I/O, is outside the import graph — correctly, since it never runs at package import time.
- A parameter or return annotation is skipped once the module has `from __future__ import annotations`, or when the annotation is a bare forward-reference string (`-> "SomeType"`) — correctly, since neither is evaluated at import time. A module without the future import gets its annotations scanned like any other definition-time expression.

**False positives a compliant repo can hit:**

- `urllib.request` is on the item-6 fetch-indicator list because it's a fetch mechanism, but it's also the home of `pathname2url`. A repo importing it only to build `file://` URLs gets gated into "needs readerkit" with nothing to migrate.
- A package that caches derived data via `platformdirs` without ever fetching anything trips item 7's gate (`platformdirs` is a cache indicator) and then has to expose an HTTP-shaped `disable_*cache*` entry point it has no reason to own.
- The env-var leg of item 7 checks the `<SLUG>_CACHE_DIR` shape, not that `<SLUG>` is this project's own slug — any string of that shape anywhere in the package passes, even one that doesn't belong to it.

## How a repo opts in

**Generated from the template:** answer `family` at the `preset` question during `create`, or set it later with `bblocks-projects update --data preset=family`. This writes `preset: family` into `.copier-answers.yml`, and `doctor` runs the contract checks automatically from then on — no flag needed.

**Never generated from the template** (`pydeflate`, `resolvekit`, `imf-reader`, `bblocks`, as of this writing): pass `--family` on the `doctor` command line. There's no answers file to record intent in, so the flag is the escape hatch:

```bash
uvx bblocks-projects doctor --path /path/to/oda_reader --family
```

Add `--check-remote` to also run items 11 and 12 (branch protection, conda-forge) — both are skipped with an advisory otherwise, since they're the only two checks that touch the network:

```bash
uvx bblocks-projects doctor --family --check-remote --strict
```

## See also

- [Reference: the contract table](reference.md#the-family-contract) — codes and exact detection rules
- [Running the doctor](running-the-doctor.md) — the full command surface, including `--family` and `--check-remote`
- [Adopting an existing project](adopting-an-existing-project.md) — writing a `.copier-answers.yml` by hand for a repo the template never generated
