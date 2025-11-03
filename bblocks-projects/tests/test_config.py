"""Tests for configuration."""

from bblocks.projects.config import DEFAULT_REF, TEMPLATE_URL


def test_template_url() -> None:
    """Test template URL is correct."""
    assert TEMPLATE_URL == "gh:ONEcampaign/bblocks-projects"


def test_default_ref() -> None:
    """Test default ref is main."""
    assert DEFAULT_REF == "main"
