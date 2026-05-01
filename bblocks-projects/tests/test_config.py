"""Tests for configuration."""

from pathlib import Path

import pytest

from bblocks.projects.config import DEFAULT_REF, TEMPLATE_URL, resolve_template_url


def test_template_url() -> None:
    """Test template URL is correct."""
    assert TEMPLATE_URL == "gh:ONEcampaign/bblocks-projects"


def test_default_ref() -> None:
    """Test default ref is main."""
    assert DEFAULT_REF == "main"


def test_resolver_default_when_nothing_set(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("BBLOCKS_PROJECTS_TEMPLATE", raising=False)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    assert resolve_template_url() == TEMPLATE_URL


def test_resolver_env_var_wins_over_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BBLOCKS_PROJECTS_TEMPLATE", "gh:foo/bar")
    assert resolve_template_url() == "gh:foo/bar"


def test_resolver_cli_override_wins_over_env_var(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BBLOCKS_PROJECTS_TEMPLATE", "gh:foo/bar")
    assert resolve_template_url(cli_override="gh:baz/qux") == "gh:baz/qux"


def test_resolver_config_file_used_when_env_absent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("BBLOCKS_PROJECTS_TEMPLATE", raising=False)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    config_dir = tmp_path / "bblocks-projects"
    config_dir.mkdir()
    (config_dir / "config.toml").write_text('template_url = "gh:from/config"\n', encoding="utf-8")
    assert resolve_template_url() == "gh:from/config"


def test_resolver_env_var_wins_over_config_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BBLOCKS_PROJECTS_TEMPLATE", "gh:from/env")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    config_dir = tmp_path / "bblocks-projects"
    config_dir.mkdir()
    (config_dir / "config.toml").write_text('template_url = "gh:from/config"\n', encoding="utf-8")
    assert resolve_template_url() == "gh:from/env"


def test_resolver_config_file_with_unknown_keys_ignored(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("BBLOCKS_PROJECTS_TEMPLATE", raising=False)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    config_dir = tmp_path / "bblocks-projects"
    config_dir.mkdir()
    (config_dir / "config.toml").write_text(
        'template_url = "gh:from/config"\nextra_key = "ignored"\n',
        encoding="utf-8",
    )
    assert resolve_template_url() == "gh:from/config"


def test_resolver_malformed_config_falls_through_to_default(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("BBLOCKS_PROJECTS_TEMPLATE", raising=False)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    config_dir = tmp_path / "bblocks-projects"
    config_dir.mkdir()
    (config_dir / "config.toml").write_bytes(b"this is { not toml ===")
    assert resolve_template_url() == TEMPLATE_URL


def test_resolver_xdg_config_home_honoured(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("BBLOCKS_PROJECTS_TEMPLATE", raising=False)
    custom_xdg = tmp_path / "custom_xdg"
    custom_xdg.mkdir()
    monkeypatch.setenv("XDG_CONFIG_HOME", str(custom_xdg))
    config_dir = custom_xdg / "bblocks-projects"
    config_dir.mkdir()
    (config_dir / "config.toml").write_text('template_url = "gh:from/custom"\n', encoding="utf-8")
    assert resolve_template_url() == "gh:from/custom"
