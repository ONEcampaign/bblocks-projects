"""Static source-inspection heuristics backing family-contract items 6, 7, and 8.

Kept out of `contract.py` so that module stays a registry plus twelve thin
checks. This module owns the import-graph BFS, the denylist/allowlist
tables for import-time calls, and the public-surface reader those three
items share.

None of this executes the target package. Everything is read via
`ast.parse` over files reachable from each package root's `__init__.py`
by first-party imports only — a breadth-first walk capped at
`_MAX_MODULES` modules per root. A distribution with a flat multi-package
`src/` (`src/alpha_pkg/`, `src/zeta_pkg/`) gets one BFS per root, and
every module from every root is reported together. A module the package
never imports at module level (a lazy import inside a function) is
invisible here, correctly: it does not run at import time either.

Within each reachable module, call-site scanning (used by item 8, and by
item 7's "does it delegate to readerkit" leg) walks the AST but prunes only
the *body* of a `FunctionDef`, `AsyncFunctionDef`, or `Lambda` — code that
runs when the function is called, not when it is defined. Everything else
attached to a `def`/`lambda`/`class` statement executes as that statement
runs, so it is traversed: decorator expressions, parameter defaults,
parameter/return annotations (unless deferred — see below), and, for
classes, `bases` and `keywords` (the metaclass) alongside the body.
Top-level `if`/`try`/`with`/`for` bodies are also kept — they execute at
import time. `import ... as ...` and `from ... import ... as ...`
bindings are tracked per module and resolved before a call's target is
matched against any list, so `from importlib.metadata import version as
_pkg_version` followed by `_pkg_version(...)` is recognised as a call to
`importlib.metadata.version`, not treated as an unknown name.

Annotations are the one place where "attached to the statement" doesn't
imply "evaluated at import time": `from __future__ import annotations`
(PEP 563) defers every annotation in the module to a string, and a bare
forward-reference string annotation (`-> "SomeType"`) is never evaluated
either way. Both are detected and excluded from the scan rather than
walked.

Item 7's env-var/literal scan and its "calls `resolve_cache_dir`" leg walk
the *unpruned* tree instead — those checks ask "does this package own this
mechanism anywhere", not "does it run at import time".

## Known false negatives — item 6 (readerkit adoption)

1. A package that fetches only through a third-party client SDK
   (`datacommons`, `wbgapi`, a vendored gRPC stub) declares none of the
   fetch-indicator libraries and imports none of them directly — it reads
   as "does not fetch".
2. A package that fetches through a first-party sibling package (reaching
   the network via a dependency it owns) likewise reads as "does not
   fetch" at its own boundary. The sibling owns the contract, but that is
   a gap in this check, not a judgement it made.
3. `readerkit` declared and imported but used only for e.g. `cache_key`
   while HTTP still goes through a bare `requests.Session` reads as
   adopted — the check sees dependency edges and import statements, not
   call sites.
4. A package that downloads files through `pooch` and nothing else reads
   as "does not fetch". `pooch` is deliberately excluded from the fetch
   indicator list: it brings its own caching, and including it would gate
   a family repo (`resolvekit`) on an inference rather than on evidence.

## Known false negatives — item 7 (the cache contract)

- A package that names its redirect env var something other than the
  `<SLUG>_CACHE_DIR` / `resolve_cache_dir` shapes (e.g. `FOO_CACHE_PATH`)
  fails the env-var leg even when it genuinely honours a redirect.
- A `set_cache_dir` that is a no-op stub passes the redirect leg. The
  check reads names, not behaviour.

## Known false positives — a compliant repo can hit these

- `urllib.request` is on the item-6 fetch-indicator list because it is a
  fetch mechanism, but it is also the home of `pathname2url`. A repo
  importing it only to build `file://` URLs gets gated into "needs
  readerkit" with nothing to migrate.
- A package that caches derived data via `platformdirs` without ever
  fetching anything trips item 7's gate (`platformdirs` is a cache
  indicator) and then has to expose an HTTP-shaped `disable_*cache*`
  entry point it has no reason to own.
- `has_cache_env_var_literal` checks the `<SLUG>_CACHE_DIR` *shape*
  (`_ENV_VAR_RE`), not that `<SLUG>` is this project's own slug — any
  string of that shape anywhere in the package passes the env-var leg,
  even one lifted from an unrelated project.

## Known false negatives — item 8 (import-time side effects)

- Anything reached only through a first-party call is invisible to the
  denylist; `contract.import_opaque` names the call site but cannot
  classify what it does.
- A module imported lazily inside a function, that itself does
  import-time I/O, is outside the import graph — correctly, since it
  never runs at package import time.
- A parameter/return annotation is skipped once `from __future__ import
  annotations` is present, or when it's a bare forward-reference string —
  correctly, since neither is evaluated at import time. A module without
  the future import gets its annotations scanned like any other
  definition-time expression.

Decorator expressions, parameter defaults, class bases, and metaclass
keywords are all scanned, since Python evaluates all four at import time:
`@dataframe_cache(...)`, `def f(x=open("data.csv")): ...`, and
`class C(make_base_by_io()): ...` are classified like any other
import-time call site.

Decorator *factories* — `@dataclass(...)`, `@pydantic.field_validator(...)`,
`@functools.lru_cache(...)`, and similar — are calls too, and every one of
them is visible to this scan. Each addition to `_ALLOW_EXACT` below for
this class was verified against the real implementation (stdlib source or
the installed third-party package), not assumed from the name: it earns
allowlisting only if it touches nothing but the function/class object
it's decorating. `typing.overload` was checked the same way and
*rejected* — its called form appends to a module-level `_overload_registry`
dict, which is the genuine global-state mutation this item exists to
surface, so it stays an advisory like `os.register_at_fork` and
`atexit.register`.

## Deliberate deviation: `readerkit` is exempt from item 7 entirely

Item 6 exempts the `readerkit` package itself (it cannot depend on
itself). Item 7c gives every *other* package a second pass leg —
"imports readerkit" — on the theory that delegating to the provider
makes the provider's disable path the package's disable path. That leg
cannot apply to `readerkit` checking itself (it does not import itself),
and inspection of the real repo shows it has no
`disable_*cache*`-shaped name either: its disable path is
`build_session(cache_dir=None)` / `resolve_cache_dir(cache_dir=None)`, a
kwarg, not a named function. So `_check_cache_contract` carries the same
provider exemption as item 6, for the same reason — a package cannot be
its own delegate.
"""

import ast
import re
from dataclasses import dataclass, field
from functools import cache
from pathlib import Path
from typing import Literal

from bblocks.projects.installer import _parse_dep_name
from bblocks.projects.project import Project

_MAX_MODULES = 200

# --- name normalisation -------------------------------------------------------


def normalize_name(name: str) -> str:
    """PEP-503 normalise a distribution or project name for comparison."""
    return re.sub(r"[-_.]+", "-", name).lower()


# --- the import graph ----------------------------------------------------------


@dataclass(frozen=True)
class ModuleScan:
    """One module in the package's import-time-reachable graph."""

    path: Path
    dotted: str
    is_package: bool
    tree: ast.Module | None = None
    error: BaseException | None = None
    aliases: dict[str, str] = field(default_factory=dict)
    # Calls surviving the function/lambda body prune — item 8's scope.
    calls: tuple[ast.Call, ...] = ()
    # Import statements surviving the same prune — used both to walk the
    # import graph and, for item 6, to see what a module imports at
    # module level.
    imports: tuple[ast.Import | ast.ImportFrom, ...] = ()


def _has_future_annotations(tree: ast.Module) -> bool:
    """`from __future__ import annotations` (PEP 563) defers every
    annotation in the module to a string — none of them run at import
    time. It must be the first statement (after an optional docstring),
    so a shallow scan of the module body is enough; it never appears
    nested inside a class or function.
    """
    for node in tree.body:
        if (
            isinstance(node, ast.ImportFrom)
            and node.module == "__future__"
            and any(alias.name == "annotations" for alias in node.names)
        ):
            return True
    return False


class _ImportTimeCollector(ast.NodeVisitor):
    """Collects `Call` and import nodes reachable at import time.

    Prunes `FunctionDef`/`AsyncFunctionDef`/`Lambda` *bodies* — those run
    only when the function is called, never at import time. Everything
    else attached to a definition runs while the `def`/`lambda`/`class`
    statement itself executes, so it is traversed rather than pruned:
    decorator expressions, parameter defaults (`args.defaults` and
    `args.kw_defaults`), parameter and return annotations (unless PEP 563
    defers them — see below), and, for classes, `bases` and `keywords`
    (the metaclass and other class-creation kwargs) alongside the body.

    Annotations are a special case: with `from __future__ import
    annotations` in effect, Python never evaluates them — they are stored
    as strings — so this collector skips annotation traversal entirely
    for such a module. Without that future import, a *string* annotation
    (`-> "SomeType"`, PEP 484 forward-reference style) is likewise never
    evaluated, so it is skipped regardless of the future import; anything
    else in annotation position is a live expression and is traversed.
    """

    def __init__(self, *, annotations_deferred: bool) -> None:
        self.calls: list[ast.Call] = []
        self.imports: list[ast.Import | ast.ImportFrom] = []
        self._annotations_deferred = annotations_deferred

    def _visit_definition_time(
        self, node: ast.FunctionDef | ast.AsyncFunctionDef
    ) -> None:
        for decorator in node.decorator_list:
            self.visit(decorator)
        args = node.args
        for default in (*args.defaults, *args.kw_defaults):
            if default is not None:
                self.visit(default)
        if not self._annotations_deferred:
            all_args = (
                *args.posonlyargs,
                *args.args,
                *([args.vararg] if args.vararg else []),
                *args.kwonlyargs,
                *([args.kwarg] if args.kwarg else []),
            )
            for arg in all_args:
                if arg.annotation is not None:
                    self._visit_annotation(arg.annotation)
            if node.returns is not None:
                self._visit_annotation(node.returns)
        # `node.body` is deliberately never visited — it runs on call, not
        # on import.

    def _visit_annotation(self, node: ast.expr) -> None:
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return  # forward-reference string; never evaluated
        self.visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._visit_definition_time(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._visit_definition_time(node)

    def visit_Lambda(self, node: ast.Lambda) -> None:
        args = node.args
        for default in (*args.defaults, *args.kw_defaults):
            if default is not None:
                self.visit(default)
        # `node.body` is a single expression, but it's a *call* expression
        # only when invoked — pruned just like a function body.

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        for decorator in node.decorator_list:
            self.visit(decorator)
        for base in node.bases:
            self.visit(base)
        for keyword in node.keywords:
            self.visit(keyword.value)
        for stmt in node.body:
            self.visit(stmt)

    def visit_Call(self, node: ast.Call) -> None:
        self.calls.append(node)
        self.generic_visit(node)

    def visit_Import(self, node: ast.Import) -> None:
        self.imports.append(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        self.imports.append(node)


def _collect_aliases(imports: list[ast.Import | ast.ImportFrom]) -> dict[str, str]:
    """Map each local name bound by `import x as y` / `from x import y [as z]`
    to the fully-resolved dotted name it refers to, so call-site matching
    can see through re-binding — e.g. `from importlib.metadata import
    version as _pkg_version` then `_pkg_version(...)`.
    """
    aliases: dict[str, str] = {}
    for imp in imports:
        if isinstance(imp, ast.Import):
            for alias in imp.names:
                if alias.asname:
                    aliases[alias.asname] = alias.name
        elif isinstance(imp, ast.ImportFrom) and imp.level == 0 and imp.module:
            for alias in imp.names:
                local = alias.asname or alias.name
                target = f"{imp.module}.{alias.name}"
                if local != target:
                    aliases[local] = target
    return aliases


def _dotted_of(src_dir: Path, path: Path) -> str:
    rel = path.relative_to(src_dir)
    parts = list(rel.parts)
    if parts[-1] == "__init__.py":
        parts = parts[:-1]
    else:
        parts[-1] = parts[-1].removesuffix(".py")
    return ".".join(parts)


def _resolve_module_file(src_dir: Path, dotted: str) -> tuple[Path | None, bool]:
    base = src_dir.joinpath(*dotted.split("."))
    init = base / "__init__.py"
    if init.is_file():
        return init, True
    py = base.with_suffix(".py")
    if py.is_file():
        return py, False
    return None, False


def _relative_base(current_dotted: str, is_package: bool, level: int) -> str:
    base = current_dotted if is_package else current_dotted.rpartition(".")[0]
    parts = base.split(".") if base else []
    strip = level - 1
    if strip:
        parts = parts[:-strip] if strip < len(parts) else []
    return ".".join(parts)


def _first_party_candidates(
    imp: ast.Import | ast.ImportFrom,
    *,
    current_dotted: str,
    is_package: bool,
    root_prefix: str,
) -> list[str]:
    """Dotted module names this import statement might reference internally.

    Candidates that don't resolve to an actual file (because the imported
    name is an attribute, not a submodule) are simply dropped by the BFS.
    """
    if isinstance(imp, ast.Import):
        return [
            alias.name
            for alias in imp.names
            if alias.name == root_prefix or alias.name.startswith(root_prefix + ".")
        ]
    if imp.level > 0:
        base = _relative_base(current_dotted, is_package, imp.level)
        if imp.module:
            resolved = f"{base}.{imp.module}" if base else imp.module
            # Mirror the absolute branch below: `from .sub import dangerous`
            # queues both `base.sub` (the module itself) and
            # `base.sub.dangerous` (in case `dangerous` is itself a
            # submodule, not an attribute defined inside `sub`). Python
            # resolves `from package import name` by importing
            # `package.name` as a submodule whenever one exists on disk,
            # executing it in full — so a bare "queue the module" misses
            # exactly the case (`from .sub import dangerous_submodule`)
            # this item exists to catch.
            return [resolved] + [f"{resolved}.{a.name}" for a in imp.names]
        return [f"{base}.{a.name}" if base else a.name for a in imp.names]
    if imp.module and (
        imp.module == root_prefix or imp.module.startswith(root_prefix + ".")
    ):
        return [imp.module] + [f"{imp.module}.{a.name}" for a in imp.names]
    return []


def _scan_module(path: Path, dotted: str, is_package: bool) -> ModuleScan:
    try:
        text = path.read_text(encoding="utf-8")
        tree = ast.parse(text, filename=str(path))
    except (OSError, SyntaxError, UnicodeDecodeError, ValueError) as e:
        return ModuleScan(path=path, dotted=dotted, is_package=is_package, error=e)
    collector = _ImportTimeCollector(annotations_deferred=_has_future_annotations(tree))
    collector.visit(tree)
    aliases = _collect_aliases(collector.imports)
    return ModuleScan(
        path=path,
        dotted=dotted,
        is_package=is_package,
        tree=tree,
        aliases=aliases,
        calls=tuple(collector.calls),
        imports=tuple(collector.imports),
    )


def _scan_one_root(src_dir: Path, root: Path) -> tuple[ModuleScan, ...]:
    """Import-graph BFS from a single package root's `__init__.py`.

    Each root gets its own `_MAX_MODULES` budget and its own `visited` set,
    keyed by the dotted name rooted at that package — two roots never
    collide because `root_dotted` (the root's own name, e.g. `alpha_pkg`
    or `zeta_pkg`) is always the first component.
    """
    root_dotted = ".".join(root.relative_to(src_dir).parts)
    visited: dict[str, ModuleScan] = {}
    queue: list[tuple[Path, str, bool]] = [(root / "__init__.py", root_dotted, True)]
    while queue and len(visited) < _MAX_MODULES:
        path, dotted, is_package = queue.pop(0)
        if dotted in visited or not path.is_file():
            continue
        module = _scan_module(path, dotted, is_package)
        visited[dotted] = module
        if module.tree is None:
            continue
        for imp in module.imports:
            for candidate in _first_party_candidates(
                imp,
                current_dotted=dotted,
                is_package=is_package,
                root_prefix=root_dotted,
            ):
                if candidate in visited:
                    continue
                file, is_pkg = _resolve_module_file(src_dir, candidate)
                if file is not None:
                    queue.append((file, candidate, is_pkg))
    return tuple(visited.values())


def _scan_all_modules(project: "Project") -> tuple[ModuleScan, ...] | None:
    roots = project.package_roots()
    if not roots:
        return None
    src_dir = project.path / "src"
    modules: list[ModuleScan] = []
    for root in roots:
        modules.extend(_scan_one_root(src_dir, root))
    return tuple(modules)


@cache
def scan_package(project: "Project") -> tuple[ModuleScan, ...] | None:
    """Scan every module reachable from every package root, memoized
    per-project.

    A flat multi-package `src/` (`src/alpha_pkg/`, `src/zeta_pkg/`) runs
    one import-graph BFS per root, and every module from every root is
    reported together — a clean root must not hide a violation in a
    sibling root. Items 6, 7, and 8 all call this for the same `Project`
    instance during one `doctor` run, so caching avoids re-walking the
    tree three times.
    """
    return _scan_all_modules(project)


# --- call-site classification (item 8, and item 7's readerkit-delegation leg) --


def _call_target(node: ast.expr) -> str | None:
    """Build a dotted string describing a call's target.

    `socket.gethostname` for a plain attribute chain; `Path().resolve` for
    a chained method call on a constructor. Returns None when the shape is
    too dynamic to name (a subscript, a computed expression, ...).
    """
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base = _call_target(node.value)
        return f"{base}.{node.attr}" if base is not None else None
    if isinstance(node, ast.Call):
        base = _call_target(node.func)
        return f"{base}()" if base is not None else None
    return None


_ALIAS_HEAD_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*")


def _resolve_aliases(target: str, aliases: dict[str, str]) -> str:
    match = _ALIAS_HEAD_RE.match(target)
    if not match:
        return target
    head = match.group(0)
    rest = target[len(head) :]
    if rest.startswith("("):
        # `head` is itself being invoked (e.g. the `Path` in `Path().resolve`)
        # rather than referenced by name; alias resolution doesn't apply.
        return target
    return aliases.get(head, head) + rest


def resolve_call_target(call: ast.Call, aliases: dict[str, str]) -> str | None:
    """The alias-resolved dotted name of what `call` invokes, or None."""
    target = _call_target(call.func)
    return _resolve_aliases(target, aliases) if target is not None else None


def _is_path_file_arithmetic(node: ast.expr) -> bool:
    """True for `Path(__file__)` itself, or that call with any number of
    `.parent` / `.parents[...]` hops stacked on top — the pure
    path-arithmetic expressions `_is_file_resolve_idiom` treats as the
    inert root of the self-locating idiom, regardless of how many hops
    separate `Path(__file__)` from the `.resolve()` call wrapping it.
    """
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "Path"
        and len(node.args) == 1
        and isinstance(node.args[0], ast.Name)
        and node.args[0].id == "__file__"
    ):
        return True
    if isinstance(node, ast.Attribute) and node.attr == "parent":
        return _is_path_file_arithmetic(node.value)
    if (
        isinstance(node, ast.Subscript)
        and isinstance(node.value, ast.Attribute)
        and node.value.attr == "parents"
    ):
        return _is_path_file_arithmetic(node.value.value)
    return False


def _is_file_resolve_idiom(call: ast.Call) -> bool:
    """`Path(__file__).resolve()` — how a module locates its own directory —
    recognised regardless of where `.resolve()` sits relative to any
    `.parent` / `.parents[...]` hops: `Path(__file__).parent.resolve()`,
    `Path(__file__).resolve().parents[1]`'s inner `.resolve()` call, and
    `Path(__file__).parents[1].resolve()` are all the same inert path
    arithmetic as the bare form.

    Pure path arithmetic; it touches no disk in any way this contract
    cares about. Named explicitly rather than folded into the general
    `Path` allowlist entry, because the general entry only covers a bare,
    unchained `Path(...)` construction — this is the chained-off-it form
    that's just as inert. Only the outermost `.resolve()` call in a chain
    is itself a `Call` node reachable by this scan — `Path(__file__)
    .resolve().parent` ends in attribute access, not a call, so it is
    never classified at all; the `.resolve()` call nested inside it is
    still visited and still matches here. A non-path-arithmetic call
    anywhere between the root and `.resolve()` — `Path(__file__)
    .parent.read_text().resolve()` — fails this match and falls through to
    the denylist, same as it always has.
    """
    func = call.func
    return (
        isinstance(func, ast.Attribute)
        and func.attr == "resolve"
        and _is_path_file_arithmetic(func.value)
    )


# I/O denylist (item 8a). `socket.*` covers only the three network-touching
# members, not `socket.gethostname` (a syscall, not network I/O —
# allowlisted below).
_DENY_EXACT = tuple(
    re.compile(p)
    for p in (
        r"^open$",
        r"^requests\..+$",
        r"^httpx\..+$",
        r"^aiohttp\..+$",
        r"^urllib3\..+$",
        r"^urllib\.request\.urlopen$",
        r"^socket\.(socket|create_connection|getaddrinfo)$",
        r"^http\.client\..+$",
        r"^(pandas|pd)\.read_\w+$",
        r"^subprocess\.(run|call|Popen|check_output)$",
        r"^shutil\.(copy\w*|rmtree|move)$",
        r"^os\.(makedirs|remove|rmdir|listdir|walk|scandir)$",
        r"^json\.load$",
        r"^yaml\.(safe_load|load)$",
        r"^tomllib\.load$",
        r"^pickle\.load$",
        r"^sqlite3\.connect$",
        # Default `ensure_exists=True` creates a directory.
        r"^(readerkit\.)?resolve_cache_dir$",
    )
)
# A method call on any receiver, e.g. `Path(x).mkdir()`, `self._dir.glob(...)`.
_DENY_METHOD_SUFFIX = re.compile(
    r"\.(read_text|read_bytes|write_text|write_bytes|mkdir|touch|unlink|glob|rglob|iterdir)$"
)

# Safe-construction allowlist (item 8b). Alias resolution normalises local
# names to their canonical dotted form first, so `from typing import TypeVar;
# TypeVar(...)` matches `typing.TypeVar` here without a separate bare-name
# entry, and builtins (never imported) are matched bare.
_ALLOW_EXACT = tuple(
    re.compile(p)
    for p in (
        r"^logging\.(getLogger|Formatter|StreamHandler|NullHandler|basicConfig)$",
        r"^importlib\.metadata\.version$",
        r"^re\.compile$",
        r"^typing\.(TypeVar|NewType|NamedTuple|TypedDict|ParamSpec)$",
        r"^collections\.namedtuple$",
        r"^(frozenset|set|dict|list|tuple|str|int|float|bool|range|sorted|len|getattr)$",
        r"^(pathlib\.)?Path$",
        r"^collections\.(defaultdict|Counter|deque)$",
        r"^enum\.auto$",
        # `unique(...)` (the called form) either raises or returns the
        # enum class unchanged — no I/O, no state outside the raise.
        r"^enum\.unique$",
        r"^datetime\.timedelta$",
        r"^datetime\.timezone\.utc$",
        # `@dataclass(...)` (the called form; the bare `@dataclass` form
        # isn't even a `Call` node, so it never reaches this scan) mutates
        # only the class being defined — same bar as the pydantic
        # constructors below.
        r"^dataclasses\.(dataclass|field)$",
        r"^os\.environ\.get$",
        r"^platformdirs\.user_cache_dir$",
        # A hostname lookup is a syscall, not network I/O.
        r"^socket\.gethostname$",
        r"^contextvars\.ContextVar$",
        # Inert builtins: introspection and construction, never I/O or
        # global state. Real item-8 output on family repos was dominated
        # by these — noise that buried the two genuinely interesting
        # advisories (os.register_at_fork, atexit.register).
        r"^(hasattr|isinstance|issubclass|object|type|super|enumerate|zip|"
        r"min|max|sum|any|all)$",
        # `classmethod(f)`/`staticmethod(f)`/`property(...)` construct a
        # descriptor object; the constructor itself does nothing beyond
        # that regardless of how it's later attached. Ordinarily reached
        # bare (`@property`, not a `Call` at all), but the called form is
        # just as inert.
        r"^(classmethod|staticmethod|property)$",
        # Pure-declaration constructors: they describe a field/model shape,
        # they don't touch the network, disk, or global state.
        r"^pydantic\.(Field|ConfigDict)$",
        # Validator/model-validator decorator *factories*: they validate
        # their own arguments and return a closure that pydantic's
        # metaclass later inspects — verified against the installed
        # pydantic source, neither does I/O or touches anything outside
        # the closure it builds.
        r"^pydantic\.(field_validator|model_validator)$",
        # Decorator factories that only touch the function/class object
        # being defined, verified against the stdlib source:
        # `lru_cache`/`cache` build a wrapper closure; `wraps` copies
        # `__name__`/`__doc__`/etc. onto the wrapper; `abstractmethod` sets
        # one attribute and returns the function unchanged. None allocates,
        # opens a handle, or writes outside the object it decorates.
        # (`typing.overload` was considered and rejected — it appends to a
        # module-level `_overload_registry` dict, which is exactly the
        # global-state mutation this item exists to surface.)
        r"^functools\.(lru_cache|cache|wraps)$",
        r"^abc\.abstractmethod$",
        # Logging/threading configuration — see _ALLOW_METHOD_SUFFIX for
        # the same calls made on a non-canonically-named receiver
        # (`shell_handler.setFormatter(...)`, not `logging.setFormatter`).
        r"^threading\.(Lock|local)$",
    )
)
# The same allowlisted logging/threading configuration calls as
# `_ALLOW_EXACT`, but matched by method-name suffix on any receiver — mirrors
# `_DENY_METHOD_SUFFIX`, because `logger.setLevel()` and
# `shell_handler.setFormatter()` don't share a fixed left-hand side the way
# `logging.getLogger` does.
_ALLOW_METHOD_SUFFIX = re.compile(
    r"\.(setLevel|addHandler|removeHandler|setFormatter)$"
)


def classify_call(call: ast.Call, target: str) -> Literal["deny", "allow", "opaque"]:
    """Classify one import-time call site for item 8."""
    if _is_file_resolve_idiom(call):
        return "allow"
    if any(p.fullmatch(target) for p in _DENY_EXACT) or _DENY_METHOD_SUFFIX.search(
        target
    ):
        return "deny"
    if any(p.fullmatch(target) for p in _ALLOW_EXACT) or _ALLOW_METHOD_SUFFIX.search(
        target
    ):
        return "allow"
    return "opaque"


# --- item 6: does the package fetch, and does it use readerkit? ---------------

_FETCH_DEP_NAMES = frozenset(
    {
        "requests",
        "httpx",
        "httpx2",
        "aiohttp",
        "urllib3",
        "requests-cache",
        "requests-ratelimiter",
    }
)
_FETCH_IMPORT_MODULES = (
    "requests",
    "httpx",
    "httpx2",
    "aiohttp",
    "urllib.request",
    "http.client",
)


def _imports_module(
    imp: ast.Import | ast.ImportFrom, target_modules: tuple[str, ...]
) -> bool:
    if isinstance(imp, ast.Import):
        return any(alias.name in target_modules for alias in imp.names)
    if isinstance(imp, ast.ImportFrom) and imp.level == 0 and imp.module:
        return imp.module in target_modules
    return False


def _matched_fetch_module(imp: ast.Import | ast.ImportFrom) -> str | None:
    for module_name in _FETCH_IMPORT_MODULES:
        if _imports_module(imp, (module_name,)):
            return module_name
    return None


def package_fetches(project: "Project", modules: tuple[ModuleScan, ...]) -> bool:
    for spec in project.iter_runtime_dependencies():
        if normalize_name(_parse_dep_name(spec.strip())) in _FETCH_DEP_NAMES:
            return True
    return any(
        _matched_fetch_module(imp) is not None
        for module in modules
        for imp in module.imports
    )


def fetch_evidence(project: "Project", modules: tuple[ModuleScan, ...]) -> str:
    """A short phrase naming what made `package_fetches` true, for the finding message."""
    dep_hits = [
        _parse_dep_name(spec.strip())
        for spec in project.iter_runtime_dependencies()
        if normalize_name(_parse_dep_name(spec.strip())) in _FETCH_DEP_NAMES
    ]
    if dep_hits:
        return "Declares " + ", ".join(dep_hits)
    import_hits = sorted(
        {
            hit
            for module in modules
            for imp in module.imports
            if (hit := _matched_fetch_module(imp)) is not None
        }
    )
    return "Imports " + ", ".join(import_hits) if import_hits else "Fetches"


def imports_readerkit(modules: tuple[ModuleScan, ...]) -> bool:
    return any(
        _imports_module(imp, ("readerkit",))
        for module in modules
        for imp in module.imports
    )


def package_uses_readerkit(project: "Project", modules: tuple[ModuleScan, ...]) -> bool:
    declared = any(
        normalize_name(_parse_dep_name(spec.strip())) == "readerkit"
        for spec in project.iter_runtime_dependencies()
    )
    return declared and imports_readerkit(modules)


# --- item 7: the cache contract -------------------------------------------------

_CACHE_DEP_NAMES = frozenset(
    {"requests-cache", "diskcache", "platformdirs", "filelock", "readerkit"}
)
_SET_CACHE_DIR_RE = re.compile(r"^set_.*cache.*dir$")
_DISABLE_CACHE_RE = re.compile(r"^disable_.*cache.*$|^.*cache.*_disable$")
_ENV_VAR_RE = re.compile(r"^[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)*_CACHE_DIR$")


def package_caches(project: "Project", modules: tuple[ModuleScan, ...]) -> bool:
    for spec in project.iter_runtime_dependencies():
        if normalize_name(_parse_dep_name(spec.strip())) in _CACHE_DEP_NAMES:
            return True
    for root in project.package_roots():
        for name in ("cache.py", "cache", "_cache"):
            if (root / name).exists():
                return True
    return False


def _public_names(tree: ast.Module) -> set[str]:
    names: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
            names.add(node.name)
        elif isinstance(node, ast.Assign):
            for tgt in node.targets:
                if not isinstance(tgt, ast.Name):
                    continue
                if tgt.id == "__all__" and isinstance(node.value, ast.List | ast.Tuple):
                    names.update(
                        elt.value
                        for elt in node.value.elts
                        if isinstance(elt, ast.Constant) and isinstance(elt.value, str)
                    )
                else:
                    names.add(tgt.id)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            names.add(node.target.id)
        elif isinstance(node, ast.ImportFrom):
            names.update(alias.asname or alias.name for alias in node.names)
    return names


def public_surface(project: "Project") -> frozenset[str]:
    """`__all__` plus top-level def/class/assignment/re-export names,
    unioned across every package root.

    Reads `<root>/__init__.py`, `<root>/cache/__init__.py`, and
    `<root>/_cache/__init__.py` when present for each root — the
    canonical shapes a cache-owning package's public surface takes. On a
    flat multi-package `src/`, the union is what item 7 checks against:
    a `set_cache_dir` exposed by one root satisfies the redirect leg for
    the distribution as a whole.
    """
    names: set[str] = set()
    for root in project.package_roots():
        for relpath in ("__init__.py", "cache/__init__.py", "_cache/__init__.py"):
            candidate = root / relpath
            if not candidate.is_file():
                continue
            try:
                tree = ast.parse(
                    candidate.read_text(encoding="utf-8"), filename=str(candidate)
                )
            except (OSError, SyntaxError, UnicodeDecodeError):
                continue
            names |= _public_names(tree)
    return frozenset(names)


def has_cache_dir_kwarg(modules: tuple[ModuleScan, ...]) -> bool:
    """Any public (non-underscore) function anywhere in the package taking `cache_dir`."""
    for module in modules:
        if module.tree is None:
            continue
        for node in ast.walk(module.tree):
            if isinstance(
                node, ast.FunctionDef | ast.AsyncFunctionDef
            ) and not node.name.startswith("_"):
                params = node.args.args + node.args.kwonlyargs
                if any(a.arg == "cache_dir" for a in params):
                    return True
    return False


def has_cache_env_var_literal(modules: tuple[ModuleScan, ...]) -> bool:
    for module in modules:
        if module.tree is None:
            continue
        for node in ast.walk(module.tree):
            if (
                isinstance(node, ast.Constant)
                and isinstance(node.value, str)
                and _ENV_VAR_RE.match(node.value)
            ):
                return True
    return False


def calls_resolve_cache_dir(modules: tuple[ModuleScan, ...]) -> bool:
    """Anywhere in the file, not just at import time — this asks "does the
    package own this mechanism", not "does it run eagerly"."""
    for module in modules:
        if module.tree is None:
            continue
        for node in ast.walk(module.tree):
            if not isinstance(node, ast.Call):
                continue
            target = resolve_call_target(node, module.aliases)
            if target in ("resolve_cache_dir", "readerkit.resolve_cache_dir"):
                return True
    return False


def public_surface_matches(surface: frozenset[str], pattern: re.Pattern[str]) -> bool:
    return any(pattern.match(name) for name in surface)
