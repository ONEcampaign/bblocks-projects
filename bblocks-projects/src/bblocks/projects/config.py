"""Configuration constants for bblocks-projects."""

import os
import sys
import tomllib
from pathlib import Path

# Template repository URL
TEMPLATE_URL = "gh:ONEcampaign/bblocks-projects"

# Environment variable name for overriding the template URL
TEMPLATE_ENV_VAR = "BBLOCKS_PROJECTS_TEMPLATE"

# Default template reference (branch/tag)
DEFAULT_REF = "main"

# Template description
TEMPLATE_DESCRIPTION = """
Python Project Templates

Available project types:
  - Package: Full Python package with tests, CI/CD, and PyPI publishing
  - Research: Data analysis project with organized scripts structure
"""


def _config_file_path() -> Path:
    xdg = os.environ.get("XDG_CONFIG_HOME")
    base = Path(xdg) if xdg else Path.home() / ".config"
    return base / "bblocks-projects" / "config.toml"


def resolve_template_url(*, cli_override: str | None = None) -> str:
    """Resolve the template URL using precedence: CLI > env > config file > default."""
    if cli_override:
        return cli_override

    env_value = os.environ.get(TEMPLATE_ENV_VAR)
    if env_value:
        return env_value

    config_path = _config_file_path()
    if config_path.is_file():
        try:
            data = tomllib.loads(config_path.read_text(encoding="utf-8"))
        except OSError:
            data = {}
        except tomllib.TOMLDecodeError:
            print(
                f"Warning: malformed config file at {config_path} — "
                f"using default template URL.",
                file=sys.stderr,
            )
            data = {}
        value = data.get("template_url")
        if isinstance(value, str) and value:
            return value

    return TEMPLATE_URL
