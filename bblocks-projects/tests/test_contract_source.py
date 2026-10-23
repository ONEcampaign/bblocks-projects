"""Tests for the family contract's source-inspection heuristics (items 6, 7, 8)."""

from pathlib import Path

import pytest

from bblocks.projects.contract import (
    _check_cache_contract,
    _check_import_time,
    _check_readerkit,
    na_item_keys,
)
from bblocks.projects.project import Project
from tests._helpers import make_bblocks_project, make_family_project


def _codes(findings: list) -> list[str]:
    return [f.code for f in findings]


# --- item 6: readerkit ----------------------------------------------------------


def test_readerkit_flags_requests_without_readerkit(tmp_path: Path) -> None:
    p = make_bblocks_project(
        tmp_path,
        preset="family",
        python_version="3.12",
        dependencies=("requests>=2.32", "requests-cache>=1.0"),
        package_modules={"__init__.py": "import requests\n"},
    )
    findings = _check_readerkit(Project(p))
    assert _codes(findings) == ["contract.readerkit"]
    assert findings[0].severity == "finding"
    assert "requests" in findings[0].message
    assert "does not depend on readerkit" in findings[0].message


def test_readerkit_passes_when_readerkit_declared_and_imported(tmp_path: Path) -> None:
    p = make_family_project(tmp_path)
    assert _check_readerkit(Project(p)) == []


def test_readerkit_na_when_no_http_deps(tmp_path: Path) -> None:
    p = make_bblocks_project(
        tmp_path,
        preset="family",
        python_version="3.12",
        package_modules={"__init__.py": "x = 1\n"},
    )
    assert _check_readerkit(Project(p)) == []


def test_readerkit_skipped_when_no_package_found(tmp_path: Path) -> None:
    """package_roots() finding nothing under src/ must not read as "doesn't
    fetch" — na_item_keys and _check_readerkit agreeing on a bare `[]` here
    is exactly what let a genuine requests-without-readerkit violation hide
    behind item 6's n/a dash (see contract._scan_evidence_status)."""
    p = make_bblocks_project(tmp_path, preset="family", python_version="3.12")
    # No package_modules: src/demo/ exists but has no __init__.py anywhere.
    project = Project(p)
    findings = _check_readerkit(project)
    assert _codes(findings) == ["contract.readerkit_skipped"]
    assert findings[0].severity == "advisory"
    assert "readerkit" not in na_item_keys(project)


def test_readerkit_skipped_when_the_only_module_is_unparseable(
    tmp_path: Path,
) -> None:
    """A syntax error in the one module that imports requests must not read
    as "package doesn't fetch": package_fetches sees zero imports from an
    unparseable module and would otherwise hide the violation behind item
    6's n/a dash instead of surfacing it, even as an advisory."""
    p = make_bblocks_project(
        tmp_path,
        preset="family",
        python_version="3.12",
        package_modules={"__init__.py": "import requests\ndef fetch(:\n    pass\n"},
    )
    project = Project(p)
    findings = _check_readerkit(project)
    assert _codes(findings) == ["contract.readerkit_skipped"]
    assert findings[0].severity == "advisory"
    assert "readerkit" not in na_item_keys(project)


def test_readerkit_flags_when_declared_but_never_imported(tmp_path: Path) -> None:
    p = make_bblocks_project(
        tmp_path,
        preset="family",
        python_version="3.12",
        dependencies=("httpx>=0.27", "readerkit>=0.1.0"),
        package_modules={"__init__.py": "x = 1\n"},
    )
    findings = _check_readerkit(Project(p))
    assert _codes(findings) == ["contract.readerkit"]


def test_readerkit_provider_exemption(tmp_path: Path) -> None:
    p = make_bblocks_project(
        tmp_path,
        slug="readerkit",
        preset="family",
        python_version="3.12",
        dependencies=("requests>=2.32", "requests-cache>=1.0", "urllib3>=2.0"),
        package_modules={"__init__.py": "import requests\n"},
    )
    assert _check_readerkit(Project(p)) == []


@pytest.mark.parametrize("module", ["httpx", "httpx2"])
def test_readerkit_fetch_indicator_via_import_only(tmp_path: Path, module: str) -> None:
    """No fetch library declared as a dependency, but imported directly."""
    p = make_bblocks_project(
        tmp_path,
        preset="family",
        python_version="3.12",
        package_modules={"__init__.py": f"import {module}\n"},
    )
    findings = _check_readerkit(Project(p))
    assert _codes(findings) == ["contract.readerkit"]
    assert f"Imports {module}" in findings[0].message


def test_readerkit_fetch_indicator_via_httpx2_dependency(tmp_path: Path) -> None:
    p = make_bblocks_project(
        tmp_path,
        preset="family",
        python_version="3.12",
        dependencies=("httpx2>=2.15",),
        package_modules={"__init__.py": "x = 1\n"},
    )
    findings = _check_readerkit(Project(p))
    assert _codes(findings) == ["contract.readerkit"]
    assert "Declares httpx2" in findings[0].message


def _make_dfo_client(tmp_path: Path) -> Project:
    """A `development-finance` package on httpx2 that caches with no cache surface."""
    p = make_bblocks_project(
        tmp_path,
        slug="development_finance",
        preset="family",
        python_version="3.12",
        dependencies=("httpx2>=2.15", "platformdirs>=4.0"),
        package_modules={"__init__.py": "import httpx2\n"},
    )
    return Project(p)


def test_readerkit_exemption_is_advisory(tmp_path: Path) -> None:
    findings = _check_readerkit(_make_dfo_client(tmp_path))
    assert _codes(findings) == ["contract.readerkit_exempt"]
    assert findings[0].severity == "advisory"


def test_readerkit_exemption_leaves_the_cache_contract_in_force(
    tmp_path: Path,
) -> None:
    findings = _check_cache_contract(_make_dfo_client(tmp_path))
    assert _codes(findings) == [
        "contract.cache_redirect",
        "contract.cache_env_var",
        "contract.cache_disable",
    ]


# --- item 7: the cache contract --------------------------------------------------


def test_cache_redirect_passes_on_set_cache_dir(tmp_path: Path) -> None:
    p = make_bblocks_project(
        tmp_path,
        preset="family",
        python_version="3.12",
        dependencies=("requests-cache>=1.0",),
        package_modules={
            "__init__.py": (
                "__all__ = ['set_cache_dir']\n\ndef set_cache_dir(path):\n    pass\n"
            )
        },
    )
    findings = _check_cache_contract(Project(p))
    assert "contract.cache_redirect" not in _codes(findings)


def test_cache_redirect_passes_on_cache_dir_kwarg(tmp_path: Path) -> None:
    p = make_bblocks_project(
        tmp_path,
        preset="family",
        python_version="3.12",
        dependencies=("requests-cache>=1.0",),
        package_modules={
            "__init__.py": "def configure(*, cache_dir=None):\n    pass\n"
        },
    )
    findings = _check_cache_contract(Project(p))
    assert "contract.cache_redirect" not in _codes(findings)


def test_cache_redirect_flags_when_neither(tmp_path: Path) -> None:
    p = make_bblocks_project(
        tmp_path,
        preset="family",
        python_version="3.12",
        dependencies=("requests-cache>=1.0",),
        package_modules={"__init__.py": "def configure():\n    pass\n"},
    )
    findings = _check_cache_contract(Project(p))
    assert "contract.cache_redirect" in _codes(findings)


def test_cache_env_var_passes_on_literal(tmp_path: Path) -> None:
    p = make_bblocks_project(
        tmp_path,
        preset="family",
        python_version="3.12",
        dependencies=("requests-cache>=1.0",),
        package_modules={
            "cache_config.py": 'ENV_VAR = "DEMO_CACHE_DIR"\n',
            "__init__.py": "from demo.cache_config import ENV_VAR\n",
        },
        slug="demo",
    )
    findings = _check_cache_contract(Project(p))
    assert "contract.cache_env_var" not in _codes(findings)


def test_cache_env_var_passes_on_resolve_cache_dir(tmp_path: Path) -> None:
    p = make_bblocks_project(
        tmp_path,
        preset="family",
        python_version="3.12",
        dependencies=("readerkit>=0.1.0",),
        package_modules={
            "__init__.py": (
                "from readerkit import resolve_cache_dir\n\n"
                'CACHE_DIR = resolve_cache_dir(app="demo")\n'
            )
        },
    )
    findings = _check_cache_contract(Project(p))
    assert "contract.cache_env_var" not in _codes(findings)


def test_cache_env_var_flags_when_absent(tmp_path: Path) -> None:
    p = make_bblocks_project(
        tmp_path,
        preset="family",
        python_version="3.12",
        dependencies=("requests-cache>=1.0",),
        package_modules={"__init__.py": "x = 1\n"},
    )
    findings = _check_cache_contract(Project(p))
    assert "contract.cache_env_var" in _codes(findings)


def test_cache_disable_passes_on_disable_http_cache(tmp_path: Path) -> None:
    p = make_bblocks_project(
        tmp_path,
        preset="family",
        python_version="3.12",
        dependencies=("requests-cache>=1.0",),
        package_modules={
            "__init__.py": (
                "__all__ = ['disable_http_cache']\n\n"
                "def disable_http_cache():\n    pass\n"
            )
        },
    )
    findings = _check_cache_contract(Project(p))
    assert "contract.cache_disable" not in _codes(findings)


def test_cache_disable_passes_when_readerkit_imported(tmp_path: Path) -> None:
    """Delegating to readerkit satisfies 7c's disable-path leg."""
    p = make_bblocks_project(
        tmp_path,
        preset="family",
        python_version="3.12",
        dependencies=("readerkit>=0.1.0",),
        package_modules={"__init__.py": "from readerkit import build_session\n"},
    )
    findings = _check_cache_contract(Project(p))
    assert "contract.cache_disable" not in _codes(findings)


def test_cache_disable_flags_when_absent(tmp_path: Path) -> None:
    p = make_bblocks_project(
        tmp_path,
        preset="family",
        python_version="3.12",
        dependencies=("requests-cache>=1.0",),
        package_modules={"__init__.py": "x = 1\n"},
    )
    findings = _check_cache_contract(Project(p))
    assert "contract.cache_disable" in _codes(findings)


def test_cache_contract_na_when_package_does_not_cache(tmp_path: Path) -> None:
    p = make_bblocks_project(
        tmp_path,
        preset="family",
        python_version="3.12",
        package_modules={"__init__.py": "x = 1\n"},
    )
    assert _check_cache_contract(Project(p)) == []


@pytest.mark.parametrize("module", ["cache.py", "_cache.py"])
def test_cache_contract_applies_to_a_cache_module_without_a_cache_dependency(
    tmp_path: Path, module: str
) -> None:
    p = make_bblocks_project(
        tmp_path,
        preset="family",
        python_version="3.12",
        package_modules={"__init__.py": "x = 1\n", module: "x = 1\n"},
    )
    assert "contract.cache_redirect" in _codes(_check_cache_contract(Project(p)))


def test_cache_skipped_when_no_package_found(tmp_path: Path) -> None:
    """Same defect as item 6's n/a dash, one item over: no package root
    under src/ must not read as "doesn't cache" (see
    contract._scan_evidence_status)."""
    p = make_bblocks_project(tmp_path, preset="family", python_version="3.12")
    # No package_modules: src/demo/ exists but has no __init__.py anywhere.
    project = Project(p)
    findings = _check_cache_contract(project)
    assert _codes(findings) == ["contract.cache_skipped"]
    assert findings[0].severity == "advisory"
    assert "cache" not in na_item_keys(project)


def test_cache_skipped_when_a_sibling_module_is_unparseable(tmp_path: Path) -> None:
    """package_caches never reads a module's parsed content — it only
    checks declared dependencies and cache.py/_cache.py/cache/_cache modules — so
    a parse failure elsewhere can't literally hide cache evidence the way
    it can for item 6. But a scan with any parse failure is still not a
    clean scan, and item 7 must not claim a verified n/a on the strength
    of a package it couldn't fully read."""
    p = make_bblocks_project(
        tmp_path,
        preset="family",
        python_version="3.12",
        package_modules={
            "__init__.py": "from demo.broken import x\n",
            "broken.py": "def f(:\n    pass\n",
        },
    )
    project = Project(p)
    findings = _check_cache_contract(project)
    assert _codes(findings) == ["contract.cache_skipped"]
    assert findings[0].severity == "advisory"
    assert "cache" not in na_item_keys(project)


def test_cache_contract_provider_exemption(tmp_path: Path) -> None:
    """readerkit is exempt from item 7 entirely — it cannot delegate to itself
    (see contract.py's comment on _check_cache_contract)."""
    p = make_bblocks_project(
        tmp_path,
        slug="readerkit",
        preset="family",
        python_version="3.12",
        dependencies=("requests-cache>=1.0", "platformdirs>=4.0", "filelock>=3.0"),
        package_modules={"__init__.py": "x = 1\n"},
    )
    assert _check_cache_contract(Project(p)) == []


# --- item 8: no import-time side effects -----------------------------------------


def test_import_io_flags_module_level_read_csv(tmp_path: Path) -> None:
    p = make_bblocks_project(
        tmp_path,
        preset="family",
        python_version="3.12",
        package_modules={
            "__init__.py": "import pandas as pd\n\ndf = pd.read_csv('x.csv')\n"
        },
    )
    findings = _check_import_time(Project(p))
    assert "contract.import_io" in _codes(findings)
    io_finding = next(f for f in findings if f.code == "contract.import_io")
    # `pd` is alias-resolved to its canonical `pandas` before matching.
    assert "pandas.read_csv" in io_finding.message
    assert "__init__.py:3" in io_finding.message


def test_import_io_flags_module_level_open(tmp_path: Path) -> None:
    p = make_bblocks_project(
        tmp_path,
        preset="family",
        python_version="3.12",
        package_modules={"__init__.py": "f = open('x.txt')\n"},
    )
    findings = _check_import_time(Project(p))
    assert "contract.import_io" in _codes(findings)


def test_import_io_ignores_call_inside_function(tmp_path: Path) -> None:
    p = make_bblocks_project(
        tmp_path,
        preset="family",
        python_version="3.12",
        package_modules={"__init__.py": "def load():\n    return open('x.txt')\n"},
    )
    assert _check_import_time(Project(p)) == []


def test_import_io_ignores_call_inside_unimported_module(tmp_path: Path) -> None:
    p = make_bblocks_project(
        tmp_path,
        preset="family",
        python_version="3.12",
        package_modules={
            "__init__.py": "x = 1\n",
            "unused.py": "f = open('x.txt')\n",
        },
    )
    assert _check_import_time(Project(p)) == []


def test_import_opaque_flags_module_level_construction(tmp_path: Path) -> None:
    """The literal bblocks-places shape: a first-party class constructed at
    module level, which item 8 cannot classify."""
    p = make_bblocks_project(
        tmp_path,
        preset="family",
        python_version="3.12",
        package_modules={
            "resolver.py": "class PlaceResolver:\n    def __init__(self, **kw):\n        pass\n",
            "__init__.py": (
                "from demo.resolver import PlaceResolver\n\n"
                "_resolver = PlaceResolver(concordance_table='default')\n"
            ),
        },
        slug="demo",
    )
    findings = _check_import_time(Project(p))
    assert "contract.import_opaque" in _codes(findings)
    opaque = next(f for f in findings if f.code == "contract.import_opaque")
    assert opaque.severity == "advisory"
    assert "PlaceResolver" in opaque.message


def test_import_opaque_allows_getlogger_and_version(tmp_path: Path) -> None:
    p = make_bblocks_project(
        tmp_path,
        preset="family",
        python_version="3.12",
        package_modules={
            "__init__.py": (
                "import logging\n"
                "from importlib.metadata import version as _pkg_version\n\n"
                "logger = logging.getLogger(__name__)\n"
                "__version__ = _pkg_version('demo')\n"
            )
        },
    )
    assert _check_import_time(Project(p)) == []


def test_import_opaque_allows_re_compile(tmp_path: Path) -> None:
    p = make_bblocks_project(
        tmp_path,
        preset="family",
        python_version="3.12",
        package_modules={"__init__.py": "import re\n\n_PAT = re.compile('x')\n"},
    )
    assert _check_import_time(Project(p)) == []


def test_import_time_allows_file_resolve_idiom(tmp_path: Path) -> None:
    p = make_bblocks_project(
        tmp_path,
        preset="family",
        python_version="3.12",
        package_modules={
            "__init__.py": (
                "from pathlib import Path\n\n"
                "BASE_DIR = Path(__file__).resolve().parent\n"
            )
        },
    )
    assert _check_import_time(Project(p)) == []


def test_import_time_allows_file_resolve_idiom_parent_before_resolve(
    tmp_path: Path,
) -> None:
    """`.resolve()` need not be the first call in the chain — `Path(__file__)
    .parent.resolve()` is exactly as inert as `.resolve().parent`, but the
    call site (`.resolve()`) sits at a different point in the chain."""
    p = make_bblocks_project(
        tmp_path,
        preset="family",
        python_version="3.12",
        package_modules={
            "__init__.py": (
                "from pathlib import Path\n\n"
                "BASE_DIR = Path(__file__).parent.resolve()\n"
            )
        },
    )
    assert _check_import_time(Project(p)) == []


def test_import_time_allows_file_resolve_idiom_double_parent_before_resolve(
    tmp_path: Path,
) -> None:
    p = make_bblocks_project(
        tmp_path,
        preset="family",
        python_version="3.12",
        package_modules={
            "__init__.py": (
                "from pathlib import Path\n\n"
                "BASE_DIR = Path(__file__).parent.parent.resolve()\n"
            )
        },
    )
    assert _check_import_time(Project(p)) == []


def test_import_time_allows_file_resolve_idiom_parents_subscript_before_resolve(
    tmp_path: Path,
) -> None:
    p = make_bblocks_project(
        tmp_path,
        preset="family",
        python_version="3.12",
        package_modules={
            "__init__.py": (
                "from pathlib import Path\n\n"
                "BASE_DIR = Path(__file__).parents[1].resolve()\n"
            )
        },
    )
    assert _check_import_time(Project(p)) == []


def test_import_time_allows_file_resolve_idiom_resolve_then_parents_subscript(
    tmp_path: Path,
) -> None:
    """`.resolve()` first, `.parents[...]` after — the nested `.resolve()`
    call is the one this scan classifies; the trailing subscript is
    attribute access and never reaches the scan at all."""
    p = make_bblocks_project(
        tmp_path,
        preset="family",
        python_version="3.12",
        package_modules={
            "__init__.py": (
                "from pathlib import Path\n\n"
                "BASE_DIR = Path(__file__).resolve().parents[1]\n"
            )
        },
    )
    assert _check_import_time(Project(p)) == []


def test_import_time_still_flags_read_text_off_file_parent(tmp_path: Path) -> None:
    """The self-locating idiom must not be widened to allow arbitrary calls
    chained off `Path(__file__)` — a real disk read stays denied."""
    p = make_bblocks_project(
        tmp_path,
        preset="family",
        python_version="3.12",
        package_modules={
            "__init__.py": (
                "from pathlib import Path\n\nTEXT = Path(__file__).parent.read_text()\n"
            )
        },
    )
    findings = _check_import_time(Project(p))
    assert _codes(findings) == ["contract.import_io"]
    assert findings[0].severity == "finding"


def test_import_time_still_flags_mkdir_off_file_parent(tmp_path: Path) -> None:
    p = make_bblocks_project(
        tmp_path,
        preset="family",
        python_version="3.12",
        package_modules={
            "__init__.py": (
                "from pathlib import Path\n\nPath(__file__).parent.mkdir()\n"
            )
        },
    )
    findings = _check_import_time(Project(p))
    assert _codes(findings) == ["contract.import_io"]
    assert findings[0].severity == "finding"


def test_import_time_resolves_import_alias(tmp_path: Path) -> None:
    """`from importlib.metadata import version as _pkg_version` then a bare
    `_pkg_version(...)` call must resolve to the allowlisted canonical name
    — this is what makes readerkit's http.py clean."""
    p = make_bblocks_project(
        tmp_path,
        preset="family",
        python_version="3.12",
        package_modules={
            "__init__.py": (
                "from importlib.metadata import version as _pkg_version\n\n"
                "_V = _pkg_version('demo')\n"
            )
        },
    )
    assert _check_import_time(Project(p)) == []


def test_import_time_narrow_socket_denylist(tmp_path: Path) -> None:
    """socket.gethostname is a syscall, not network I/O — it must be
    allowlisted, while socket.socket stays denied."""
    p = make_bblocks_project(
        tmp_path,
        preset="family",
        python_version="3.12",
        package_modules={
            "__init__.py": "import socket\n\nHOST = socket.gethostname()\n"
        },
    )
    assert _check_import_time(Project(p)) == []


def test_import_time_flags_socket_socket(tmp_path: Path) -> None:
    p = make_bblocks_project(
        tmp_path,
        preset="family",
        python_version="3.12",
        package_modules={"__init__.py": "import socket\n\ns = socket.socket()\n"},
    )
    findings = _check_import_time(Project(p))
    assert "contract.import_io" in _codes(findings)


def test_import_unreadable_is_advisory(tmp_path: Path) -> None:
    p = make_bblocks_project(
        tmp_path,
        preset="family",
        python_version="3.12",
        package_modules={"__init__.py": "def broken(:\n"},
    )
    findings = _check_import_time(Project(p))
    assert _codes(findings) == ["contract.import_unreadable"]
    assert findings[0].severity == "advisory"
    assert "__init__.py" in findings[0].message


def test_import_time_clean_on_family_fixture(tmp_path: Path) -> None:
    p = make_family_project(tmp_path)
    assert _check_import_time(Project(p)) == []


def test_import_time_advisory_when_no_package_found(tmp_path: Path) -> None:
    """package_root() finding nothing under src/ must surface as an
    advisory, never a silent [] — the renderer reads [] as a pass, and
    "could not scan" is not the same claim as "found nothing wrong"."""
    p = make_bblocks_project(tmp_path, preset="family", python_version="3.12")
    # No package_modules: src/demo/ exists but has no __init__.py anywhere.
    findings = _check_import_time(Project(p))
    assert _codes(findings) == ["contract.import_no_package"]
    assert findings[0].severity == "advisory"


def test_family_checks_survive_empty_sibling_before_package(tmp_path: Path) -> None:
    """A violating package plus an empty sibling directory that sorts before
    it alphabetically must still surface items 6, 7, and 8 as failures —
    not the n/a dash and not a silent pass."""
    p = make_bblocks_project(
        tmp_path,
        preset="family",
        python_version="3.12",
        dependencies=("requests>=2.32", "requests-cache>=1.0"),
        package_modules={
            "__init__.py": (
                "import json\n"
                "import requests\n\n"
                "f = open('x.txt')\n"
                "data = json.load(f)\n"
                "session = requests.Session()\n"
            )
        },
    )
    (p / "src" / "_vendor").mkdir(parents=True)  # sorts before "demo"; empty

    project = Project(p)
    assert _codes(_check_readerkit(project)) == ["contract.readerkit"]
    cache_codes = set(_codes(_check_cache_contract(project)))
    assert {
        "contract.cache_redirect",
        "contract.cache_env_var",
        "contract.cache_disable",
    } <= cache_codes
    import_codes = _codes(_check_import_time(project))
    assert "contract.import_io" in import_codes


def test_multi_package_src_scans_every_root(tmp_path: Path) -> None:
    """Regression guard: a flat multi-package src/ (alpha_pkg sorts before
    zeta_pkg) must be scanned root-by-root, not just the first one found.
    A single-root scan would report a clean project while HTTP use, a
    cache directory, and import-time I/O all live entirely in zeta_pkg —
    every assertion below would then read as n/a or clean instead of
    catching the violation.
    """
    p = make_bblocks_project(
        tmp_path,
        slug="alpha_pkg",
        preset="family",
        python_version="3.12",
        package_modules={"__init__.py": "x = 1\n"},
    )
    zeta_dir = p / "src" / "zeta_pkg"
    zeta_dir.mkdir(parents=True)
    (zeta_dir / "__init__.py").write_text(
        "import requests\n\nsession = requests.Session()\nf = open('x.txt')\n",
        encoding="utf-8",
    )
    (zeta_dir / "cache.py").touch()

    project = Project(p)

    # item 8: the import-time I/O findings must name zeta_pkg's own file.
    io_findings = [
        f for f in _check_import_time(project) if f.code == "contract.import_io"
    ]
    assert len(io_findings) == 2
    assert all(
        "zeta_pkg" in f.message and "__init__.py" in f.message for f in io_findings
    )

    # item 6: alpha_pkg alone doesn't fetch; zeta_pkg's bare `requests`
    # use, invisible to a single-root scan, must surface as a finding.
    assert _codes(_check_readerkit(project)) == ["contract.readerkit"]

    # item 7: alpha_pkg alone doesn't cache; zeta_pkg's cache.py opens the
    # gate, and neither root exposes any redirect/env-var/disable surface.
    assert set(_codes(_check_cache_contract(project))) == {
        "contract.cache_redirect",
        "contract.cache_env_var",
        "contract.cache_disable",
    }


# --- item 8: definition-time expressions (decorators, defaults, bases) ----------


def test_import_io_flags_decorator_expression(tmp_path: Path) -> None:
    """A decorator expression runs when the `def` statement executes, i.e.
    at import time — it must be scanned, not pruned along with the body."""
    p = make_bblocks_project(
        tmp_path,
        preset="family",
        python_version="3.12",
        package_modules={
            "__init__.py": (
                "import requests\n\n@requests.get('http://x')\ndef f():\n    pass\n"
            )
        },
    )
    findings = _check_import_time(Project(p))
    assert "contract.import_io" in _codes(findings)


def test_import_io_flags_parameter_default(tmp_path: Path) -> None:
    """A parameter default is evaluated once, when the `def` statement
    runs — at import time for a module-level function."""
    p = make_bblocks_project(
        tmp_path,
        preset="family",
        python_version="3.12",
        package_modules={"__init__.py": "def f(x=open('data.csv')):\n    pass\n"},
    )
    findings = _check_import_time(Project(p))
    assert "contract.import_io" in _codes(findings)


def test_import_io_flags_class_base(tmp_path: Path) -> None:
    """A class base expression is evaluated when the `class` statement
    runs, not deferred to instantiation."""
    p = make_bblocks_project(
        tmp_path,
        preset="family",
        python_version="3.12",
        package_modules={
            "__init__.py": "import requests\n\nclass C(requests.Session()):\n    pass\n"
        },
    )
    findings = _check_import_time(Project(p))
    assert "contract.import_io" in _codes(findings)


def test_import_io_flags_metaclass_keyword(tmp_path: Path) -> None:
    """`metaclass=...` is a class-creation keyword, evaluated alongside
    `bases` when the `class` statement runs."""
    p = make_bblocks_project(
        tmp_path,
        preset="family",
        python_version="3.12",
        package_modules={
            "__init__.py": (
                "import requests\n\nclass C(metaclass=requests.Session()):\n    pass\n"
            )
        },
    )
    findings = _check_import_time(Project(p))
    assert "contract.import_io" in _codes(findings)


def test_import_io_flags_annotation_without_future_import(tmp_path: Path) -> None:
    """Without `from __future__ import annotations`, a return annotation
    is a live expression evaluated when the `def` statement runs."""
    p = make_bblocks_project(
        tmp_path,
        preset="family",
        python_version="3.12",
        package_modules={
            "__init__.py": (
                "import requests\n\ndef h() -> requests.Session():\n    pass\n"
            )
        },
    )
    findings = _check_import_time(Project(p))
    assert "contract.import_io" in _codes(findings)


def test_import_time_future_annotations_suppresses_annotation_scan(
    tmp_path: Path,
) -> None:
    """`from __future__ import annotations` defers annotation evaluation
    entirely — the same return annotation that's a finding without the
    future import must not be scanned with it."""
    p = make_bblocks_project(
        tmp_path,
        preset="family",
        python_version="3.12",
        package_modules={
            "__init__.py": (
                "from __future__ import annotations\n\n"
                "import requests\n\n"
                "def h() -> requests.Session():\n"
                "    pass\n"
            )
        },
    )
    assert _check_import_time(Project(p)) == []


# --- item 8: the allowlist (inert builtins, pydantic, logging/threading) --------


def test_import_opaque_allows_inert_builtins(tmp_path: Path) -> None:
    p = make_bblocks_project(
        tmp_path,
        preset="family",
        python_version="3.12",
        package_modules={
            "__init__.py": (
                "_HAS = hasattr(int, 'x')\n"
                "_IS = isinstance(1, object)\n"
                "_ISSUB = issubclass(int, object)\n"
                "_OBJ = object()\n"
                "_TYPE = type('Dyn', (), {})\n"
                "_ENUM = enumerate([1, 2])\n"
                "_ZIP = zip([1], [2])\n"
                "_MIN = min(1, 2)\n"
                "_MAX = max(1, 2)\n"
                "_SUM = sum([1, 2])\n"
                "_ANY = any([True])\n"
                "_ALL = all([True])\n"
            )
        },
    )
    assert _check_import_time(Project(p)) == []


def test_import_opaque_allows_pydantic_field_and_configdict(tmp_path: Path) -> None:
    p = make_bblocks_project(
        tmp_path,
        preset="family",
        python_version="3.12",
        package_modules={
            "__init__.py": (
                "import pydantic\n\n"
                "_F = pydantic.Field(default=None)\n"
                "_C = pydantic.ConfigDict(frozen=True)\n"
            )
        },
    )
    assert _check_import_time(Project(p)) == []


def test_import_opaque_allows_pydantic_validators(tmp_path: Path) -> None:
    """field_validator/model_validator are decorator factories on class
    methods and must be recognised as allowlisted decorator-factory calls,
    not flagged as opaque import-time I/O."""
    p = make_bblocks_project(
        tmp_path,
        preset="family",
        python_version="3.12",
        package_modules={
            "__init__.py": (
                "import pydantic\n\n"
                "class Model(pydantic.BaseModel):\n"
                "    name: str\n\n"
                "    @pydantic.field_validator('name')\n"
                "    @classmethod\n"
                "    def _check(cls, v):\n"
                "        return v\n\n"
                "    @pydantic.model_validator(mode='after')\n"
                "    def _post(self):\n"
                "        return self\n"
            )
        },
    )
    assert _check_import_time(Project(p)) == []


def test_import_opaque_allows_dataclass_decorator(tmp_path: Path) -> None:
    """@dataclass(...) is a decorator factory in a class's decorator list,
    traversed alongside the body, and must be recognised as an allowlisted
    call rather than flagged as opaque import-time I/O."""
    p = make_bblocks_project(
        tmp_path,
        preset="family",
        python_version="3.12",
        package_modules={
            "__init__.py": (
                "from dataclasses import dataclass\n\n"
                "@dataclass(frozen=True)\n"
                "class Config:\n"
                "    name: str\n"
            )
        },
    )
    assert _check_import_time(Project(p)) == []


def test_import_opaque_allows_functools_decorator_factories(tmp_path: Path) -> None:
    """lru_cache/cache build a wrapper closure; wraps only copies metadata
    onto the wrapper it's applied to — none touches the network, disk, or
    state outside the function/class being defined."""
    p = make_bblocks_project(
        tmp_path,
        preset="family",
        python_version="3.12",
        package_modules={
            "__init__.py": (
                "import functools\n\n"
                "class Cached:\n"
                "    @functools.lru_cache(maxsize=32)\n"
                "    def get(self, key): ...\n\n"
                "    @functools.cache\n"
                "    def get2(self, key): ...\n\n"
                "def deco(f):\n"
                "    @functools.wraps(f)\n"
                "    def inner(*a, **kw):\n"
                "        return f(*a, **kw)\n\n"
                "    return inner\n"
            )
        },
    )
    assert _check_import_time(Project(p)) == []


def test_import_opaque_allows_descriptor_constructors_and_pure_markers(
    tmp_path: Path,
) -> None:
    """classmethod/staticmethod/property in their rarer *called* form
    (`f = classmethod(f)`, not `@classmethod`) just construct a descriptor;
    abc.abstractmethod and enum.unique either mutate only the object passed
    in or raise — none is I/O or global state."""
    p = make_bblocks_project(
        tmp_path,
        preset="family",
        python_version="3.12",
        package_modules={
            "__init__.py": (
                "import abc\n"
                "import enum\n\n"
                "def _f(cls):\n"
                "    return cls\n\n"
                "f = classmethod(_f)\n"
                "g = staticmethod(_f)\n"
                "h = property(_f)\n"
                "j = abc.abstractmethod(_f)\n\n"
                "class Color(enum.Enum):\n"
                "    RED = 1\n\n"
                "Color = enum.unique(Color)\n"
            )
        },
    )
    assert _check_import_time(Project(p)) == []


def test_import_opaque_still_flags_typing_overload(tmp_path: Path) -> None:
    """typing.overload(...) (the called form) appends to a module-level
    `_overload_registry` dict — genuine global-state mutation, so it must
    stay advisory rather than join the decorator-factory allowlist."""
    p = make_bblocks_project(
        tmp_path,
        preset="family",
        python_version="3.12",
        package_modules={
            "__init__.py": (
                "import typing\n\ndef f(x): ...\n\nf = typing.overload(f)\n"
            )
        },
    )
    findings = _check_import_time(Project(p))
    assert "contract.import_opaque" in _codes(findings)


def test_import_opaque_allows_threading_configuration(tmp_path: Path) -> None:
    p = make_bblocks_project(
        tmp_path,
        preset="family",
        python_version="3.12",
        package_modules={
            "__init__.py": (
                "import threading\n\n"
                "_LOCK = threading.Lock()\n"
                "_LOCAL = threading.local()\n"
            )
        },
    )
    assert _check_import_time(Project(p)) == []


def test_import_opaque_allows_logger_configuration_on_any_receiver(
    tmp_path: Path,
) -> None:
    """logger.setLevel/addHandler and shell_handler.setFormatter — configuration
    calls made on a receiver other than the `logging` module itself."""
    p = make_bblocks_project(
        tmp_path,
        preset="family",
        python_version="3.12",
        package_modules={
            "__init__.py": (
                "import logging\n\n"
                "logger = logging.getLogger(__name__)\n"
                "logger.setLevel(logging.INFO)\n"
                "shell_handler = logging.StreamHandler()\n"
                "shell_handler.setFormatter(logging.Formatter('%(message)s'))\n"
                "logger.addHandler(shell_handler)\n"
            )
        },
    )
    assert _check_import_time(Project(p)) == []


def test_import_opaque_still_flags_register_at_fork(tmp_path: Path) -> None:
    """The allowlist must not swallow the genuinely interesting opaque
    calls — os.register_at_fork can touch global state."""
    p = make_bblocks_project(
        tmp_path,
        preset="family",
        python_version="3.12",
        package_modules={
            "__init__.py": (
                "import os\n\nos.register_at_fork(after_in_child=lambda: None)\n"
            )
        },
    )
    findings = _check_import_time(Project(p))
    assert "contract.import_opaque" in _codes(findings)


def test_import_opaque_still_flags_atexit_register(tmp_path: Path) -> None:
    p = make_bblocks_project(
        tmp_path,
        preset="family",
        python_version="3.12",
        package_modules={
            "__init__.py": ("import atexit\n\natexit.register(lambda: None)\n")
        },
    )
    findings = _check_import_time(Project(p))
    assert "contract.import_opaque" in _codes(findings)


# --- import graph: relative from-imports queue the imported submodule ----------


def test_import_io_flags_relative_from_import_submodule(tmp_path: Path) -> None:
    """`from .sub import dangerous` must queue `demo.sub.dangerous` itself,
    not just `demo.sub` — Python imports `dangerous` as a submodule (running
    it in full) whenever one exists on disk at that name, rather than
    looking it up as an attribute of `sub`. Queuing only `demo.sub` would
    read as clean, leaving the import-time HTTP session and file open
    inside `dangerous.py` outside the scanned graph entirely."""
    p = make_bblocks_project(
        tmp_path,
        preset="family",
        python_version="3.12",
        dependencies=("requests>=2.32",),
        package_modules={
            "__init__.py": "from .sub import dangerous\n",
            "sub/__init__.py": "",
            "sub/dangerous.py": (
                "import requests\n\nsession = requests.Session()\nf = open('x.txt')\n"
            ),
        },
    )
    findings = _check_import_time(Project(p))
    io_findings = [f for f in findings if f.code == "contract.import_io"]
    assert len(io_findings) == 2
    assert all("dangerous.py" in f.message for f in io_findings)


def test_import_io_flags_multi_level_relative_from_import_submodule(
    tmp_path: Path,
) -> None:
    """`from ..other import thing` (level 2, from inside a non-package
    module) must resolve to the sibling package `other` and still queue
    `other.thing` as a submodule candidate."""
    p = make_bblocks_project(
        tmp_path,
        preset="family",
        python_version="3.12",
        package_modules={
            "__init__.py": "from .sub import mod\n",
            "sub/__init__.py": "",
            "sub/mod.py": "from ..other import thing\n",
            "other/__init__.py": "",
            "other/thing.py": "f = open('x.txt')\n",
        },
    )
    findings = _check_import_time(Project(p))
    io_findings = [f for f in findings if f.code == "contract.import_io"]
    assert len(io_findings) == 1
    assert "thing.py" in io_findings[0].message


def test_import_io_flags_bare_relative_from_import(tmp_path: Path) -> None:
    """`from . import mod` (no `imp.module`) queues `mod` as a submodule
    candidate — pinned here alongside the `from .sub import name` cases
    above so the whole family-import shape is covered."""
    p = make_bblocks_project(
        tmp_path,
        preset="family",
        python_version="3.12",
        package_modules={
            "__init__.py": "from . import mod\n",
            "mod.py": "f = open('x.txt')\n",
        },
    )
    findings = _check_import_time(Project(p))
    assert "contract.import_io" in _codes(findings)


def test_relative_from_import_attribute_not_submodule_is_silent(
    tmp_path: Path,
) -> None:
    """`from .sub import CONST` where `CONST` is an attribute defined inside
    `sub/__init__.py`, not a `sub/CONST.py` file, must not resolve to a file
    — and a candidate that doesn't resolve to a file is silently dropped by
    the BFS, not surfaced as `contract.import_unreadable`. Getting this
    wrong would spray false advisories across every family repo that does
    ordinary `from .sub import some_attribute`."""
    p = make_bblocks_project(
        tmp_path,
        preset="family",
        python_version="3.12",
        package_modules={
            "__init__.py": "from .sub import CONST\n",
            "sub/__init__.py": "CONST = 1\n",
        },
    )
    assert _check_import_time(Project(p)) == []


def test_relative_from_import_multiple_names_mixed_module_and_attribute(
    tmp_path: Path,
) -> None:
    """`from .sub import mod_a, ATTR, mod_c` — two of the three imported
    names are submodules and must both be queued and scanned; `ATTR` isn't
    a file and must resolve to nothing, silently."""
    p = make_bblocks_project(
        tmp_path,
        preset="family",
        python_version="3.12",
        package_modules={
            "__init__.py": "from .sub import mod_a, ATTR, mod_c\n",
            "sub/__init__.py": "ATTR = 1\n",
            "sub/mod_a.py": "f = open('a.txt')\n",
            "sub/mod_c.py": "f = open('c.txt')\n",
        },
    )
    findings = _check_import_time(Project(p))
    assert _codes(findings) == ["contract.import_io", "contract.import_io"]
    messages = " ".join(f.message for f in findings)
    assert "mod_a.py" in messages
    assert "mod_c.py" in messages


# --- item 7: env-var shape vs. slug correspondence (known false positive) --------


def test_cache_env_var_passes_on_shape_match_regardless_of_slug(
    tmp_path: Path,
) -> None:
    """has_cache_env_var_literal checks the <SLUG>_CACHE_DIR *shape*, not
    that <SLUG> is this project's own slug — pinned here as a known false
    positive (see docs/the-family-contract.md and _source_scan.py's module
    docstring) rather than left as an accident of the test fixtures, which
    always happened to build the literal from the project's own slug."""
    p = make_bblocks_project(
        tmp_path,
        slug="demo",
        preset="family",
        python_version="3.12",
        dependencies=("requests-cache>=1.0",),
        package_modules={
            "__init__.py": 'SOME_OTHER_PROJECT_CACHE_DIR = "SOME_OTHER_PROJECT_CACHE_DIR"\n'
        },
    )
    findings = _check_cache_contract(Project(p))
    assert "contract.cache_env_var" not in _codes(findings)
