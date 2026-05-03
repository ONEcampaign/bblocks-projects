"""Component installation logic."""

import re
import subprocess
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import copier
import tomlkit
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm
from rich.syntax import Syntax

from bblocks.projects.components import ComponentDef
from bblocks.projects.config import DEFAULT_REF, resolve_template_url
from bblocks.projects.project import Project

console = Console()

# PEP-440 specifiers (`==`, `!=`, `<=`, `>=`, `<`, `>`, `~=`, `===`),
# extras (`[extra]`), markers (`;`), or whitespace all delimit the package name.
_DEP_NAME_DELIM_RE = re.compile(r"[\[<>=!~ ;]")


class ConfigMergeError(ValueError):
    """Raised when merge_config_sections encounters a type mismatch at a leaf key."""


def _parse_dep_name(spec: str) -> str:
    """Extract the bare package name from a PEP 508 dep spec.

    Handles `pkg`, `pkg>=1`, `pkg==1.0`, `pkg~=1.0`, `pkg<2`, `pkg!=1.5`,
    `pkg[extra]`, `pkg[extra]>=1`, and `pkg ; python_version>='3.10'`.
    """
    return _DEP_NAME_DELIM_RE.split(spec.strip(), maxsplit=1)[0]


def merge_config_sections(
    existing: dict[str, Any], updates: dict[str, Any], path: str = ""
) -> dict[str, Any]:
    """Recursively merge config updates into existing config.

    Args:
        existing: Existing configuration dictionary
        updates: Updates to merge in
        path: Current path (for nested dicts, used in display)

    Returns:
        Merged configuration dictionary
    """
    result = existing.copy()

    for key, value in updates.items():
        current_path = f"{path}.{key}" if path else key

        if key in result:
            # Key exists - need to merge
            if isinstance(value, dict) and isinstance(result[key], dict):
                # Both are dicts - recurse
                result[key] = merge_config_sections(result[key], value, current_path)
            elif isinstance(value, list) and isinstance(result[key], list):
                # Both are lists - append unique items
                for item in value:
                    if item not in result[key]:
                        result[key].append(item)
            elif isinstance(result[key], type(value)) or isinstance(
                value, type(result[key])
            ):
                # Same logical type (handles tomlkit.String/Integer/etc.
                # vs native str/int — both are subclass-related). Component wins.
                result[key] = value
            else:
                raise ConfigMergeError(
                    f"Type mismatch at {current_path}: existing is "
                    f"{type(result[key]).__name__}, component requires "
                    f"{type(value).__name__}"
                )
        else:
            # New key - add it
            result[key] = value

    return result


def show_config_diff(
    component_name: str, existing: dict[str, Any], updates: dict[str, Any]
) -> None:
    """Show what config changes will be made.

    Args:
        component_name: Name of the component
        existing: Existing config
        updates: Proposed updates
    """
    console.print(
        f"\n[bold cyan]{component_name}[/bold cyan] will add/modify these "
        "config sections:"
    )

    for section, content in updates.items():
        if section in existing:
            console.print(
                f"\n[yellow]Will merge into existing:[/yellow] [tool.{section}]"
            )
        else:
            console.print(f"\n[green]Will add new section:[/green] [tool.{section}]")

        # Show the content
        toml_str = tomlkit.dumps({section: content})
        syntax = Syntax(toml_str, "toml", theme="monokai", line_numbers=False)
        console.print(Panel(syntax, border_style="dim"))


def can_install_component(comp: ComponentDef, project: Project) -> tuple[bool, str]:
    """Check if a component can be installed into a project.

    Args:
        comp: Component definition
        project: Target project

    Returns:
        Tuple of (can_install, reason)
    """
    requires = comp.requires_project_type
    if requires is not None and project.detect_type() != requires:
        return False, f"{comp.name} component is only for {requires} projects"
    return True, ""


def get_conflicts(comp: ComponentDef, project: Project) -> list[str]:
    """Get list of conflicting files/configs for a component.

    Args:
        comp: Component definition
        project: Target project

    Returns:
        List of conflict descriptions
    """
    conflicts = [
        f"File exists: {relpath.removesuffix('.jinja')}"
        for relpath in comp.template_files
        if project.has_file(relpath.removesuffix(".jinja"))
    ]
    conflicts.extend(
        f"Config section exists: {section}"
        for section in comp.pyproject_sections
        if project.has_config_section(section) and section != "build-system"
    )
    return conflicts


def _copier_run_copy(**kwargs: Any) -> None:
    """Indirection over copier.run_copy so tests can stub without hitting the network."""
    copier.run_copy(**kwargs)


def _render_template_to_tempdir(
    project: Project, tempdir: Path, *, template_url: str
) -> None:
    """Render the template into the caller-provided tempdir."""
    project_type = project.detect_type()
    if project_type == "unknown":
        project_type = "package"  # copier.yml only accepts package|project
    _copier_run_copy(
        src_path=template_url,
        dst_path=str(tempdir),
        vcs_ref=DEFAULT_REF,
        data={
            "project_name": project.get_project_name() or "project",
            "project_slug": project.get_project_slug(),
            "project_description": "",
            "project_type": project_type,
            "include_notebooks": False,
            "python_version": project.get_python_version(),
            "author_name": "",
            "author_email": "",
            "license": "mit",
            "github_username": "",
        },
        defaults=True,
        quiet=True,
        skip_tasks=True,
        unsafe=False,
        overwrite=False,
    )


def _extract_pyproject_sections(
    rendered_pyproject: Path, section_paths: list[str]
) -> dict[str, Any]:
    """Read a rendered pyproject.toml and return the named sections as a single merged nested dict.

    Returns a nested dict (e.g. {"tool": {"ruff": {...}}, "build-system": {...}}).
    Sections absent from the rendered file are silently skipped.
    """
    paths_by_depth = sorted(section_paths, key=lambda p: p.count("."))

    with open(rendered_pyproject, encoding="utf-8") as f:
        data: Any = tomlkit.load(f)

    result: dict[str, Any] = {}
    for path in paths_by_depth:
        parts = path.split(".")
        source = data
        try:
            for part in parts:
                source = source[part]
        except (KeyError, TypeError):
            continue

        target = result
        for part in parts[:-1]:
            if part not in target:
                target[part] = {}
            target = target[part]
        last = parts[-1]
        if last not in target:
            # shallower path may have already populated this; preserve it
            target[last] = source.unwrap() if hasattr(source, "unwrap") else source

    return result


def _render_post_install_steps(
    component: ComponentDef, project: Project, steps: list[str]
) -> list[str]:
    """Substitute project-derived placeholders into post-install step strings."""
    if component.name != "pypi-publish":
        return steps
    username = project.get_github_username() or "<YOUR-GITHUB-USERNAME>"
    return [step.replace("{github_username}", username) for step in steps]


@contextmanager
def rendered_template_for(project: Project) -> Iterator[Path]:
    """Render the template for `project` into a tempdir and yield the path.

    Hoist this once around a batch of `install_component` calls so the template
    is rendered a single time per `add` invocation rather than once per component.
    """
    with tempfile.TemporaryDirectory(prefix="bblocks-add-") as tempdir_str:
        tempdir = Path(tempdir_str)
        _render_template_to_tempdir(
            project, tempdir, template_url=resolve_template_url()
        )
        yield tempdir


def install_component(
    component: ComponentDef,
    project: Project,
    *,
    force: bool = False,
    interactive: bool = True,
    rendered_template_dir: Path | None = None,
) -> bool:
    """Install a component into a project.

    Args:
        component: Component to install
        project: Target project
        force: Force overwrite existing files
        interactive: Ask for confirmation before changes
        rendered_template_dir: Pre-rendered template tempdir from
            `rendered_template_for(project)`. When None, the template is
            rendered for this single call.

    Returns:
        True if installation succeeded
    """
    console.print(f"\n[bold]Installing component:[/bold] {component.name}")
    console.print(f"[dim]{component.description}[/dim]\n")

    # Check if can install
    can_install, reason = can_install_component(component, project)
    if not can_install:
        console.print(f"[bold red]Cannot install:[/bold red] {reason}")
        return False

    # Check conflicts
    conflicts = get_conflicts(component, project)
    if conflicts and not force:
        console.print("[yellow]Conflicts detected:[/yellow]")
        for conflict in conflicts:
            console.print(f"  • {conflict}")

        if interactive:
            prompt = "\nContinue anyway? (will merge configs, skip existing files)"
            if not Confirm.ask(prompt):
                console.print("[yellow]Installation cancelled[/yellow]")
                return False
        else:
            console.print("[yellow]Use --force to overwrite existing files[/yellow]")
            return False

    if rendered_template_dir is not None:
        return _install_from_rendered(
            component,
            project,
            rendered_template_dir,
            force=force,
            interactive=interactive,
        )
    with rendered_template_for(project) as tempdir:
        return _install_from_rendered(
            component,
            project,
            tempdir,
            force=force,
            interactive=interactive,
        )


def _install_from_rendered(
    component: ComponentDef,
    project: Project,
    tempdir: Path,
    *,
    force: bool,
    interactive: bool,
) -> bool:
    config_updates: dict[str, Any] = {}
    if component.pyproject_sections:
        rendered_pyproject = tempdir / "pyproject.toml"
        if rendered_pyproject.exists():
            config_updates = _extract_pyproject_sections(
                rendered_pyproject, component.pyproject_sections
            )
        else:
            console.print(
                "[yellow]Warning: rendered pyproject.toml not found — "
                "skipping config injection[/yellow]"
            )

    if config_updates:
        existing_tool = project.pyproject_data.get("tool", {})
        if "tool" in config_updates:
            show_config_diff(component.name, existing_tool, config_updates["tool"])
        if "build-system" in config_updates:
            console.print(
                f"[bold cyan]{component.name}[/bold cyan] will inject a "
                r"\[build-system] section into pyproject.toml"
            )

        if interactive and not Confirm.ask("\nApply these config changes?"):
            console.print("[yellow]Installation cancelled[/yellow]")
            return False

    for relpath in component.template_files:
        dest_relpath = relpath.removesuffix(".jinja")
        src_path = tempdir / dest_relpath
        dest_path = project.path / dest_relpath

        if not src_path.exists():
            console.print(
                f"[yellow]Warning: rendered file not found in template:[/yellow] "
                f"{dest_relpath}"
            )
            continue

        if dest_path.exists() and not force:
            console.print(f"[yellow]Skipping existing file:[/yellow] {dest_relpath}")
            continue

        dest_path.parent.mkdir(parents=True, exist_ok=True)
        dest_path.write_text(src_path.read_text(encoding="utf-8"), encoding="utf-8")
        console.print(f"[green]✓[/green] Created: {dest_relpath}")

    if config_updates:
        with open(project.pyproject_path, encoding="utf-8") as f:
            pyproject_data: Any = tomlkit.load(f)

        for top_key, top_value in config_updates.items():
            if top_key == "build-system" and project.has_config_section("build-system"):
                continue
            if top_key in pyproject_data and isinstance(top_value, dict):
                pyproject_data[top_key] = merge_config_sections(
                    pyproject_data[top_key], top_value
                )
            else:
                pyproject_data[top_key] = top_value

        with open(project.pyproject_path, "w", encoding="utf-8") as f:
            tomlkit.dump(pyproject_data, f)
        console.print("[green]✓[/green] Updated: pyproject.toml")

        project.reload_pyproject()

    dev_deps = component.dev_deps
    if dev_deps:
        console.print("\n[bold]Dev dependencies to add:[/bold]")
        for dep in dev_deps:
            if project.has_dev_dependency(_parse_dep_name(dep)):
                console.print(f"  • {dep} [dim](already present)[/dim]")
            else:
                console.print(f"  • {dep}")

        if interactive:
            if Confirm.ask("\nAdd these dependencies now?"):
                _add_dependencies(project, dev_deps, dev=True)
            else:
                console.print(
                    "[yellow]Skipped dependency installation. "
                    "Add manually with:[/yellow]"
                )
                console.print(f"  uv add --dev {' '.join(dev_deps)}")
        else:
            _add_dependencies(project, dev_deps, dev=True)

    steps = component.post_install_steps
    if steps:
        console.print("\n[bold green]✓ Component installed successfully![/bold green]")
        console.print("\n[bold]Next steps:[/bold]")
        rendered_steps = _render_post_install_steps(component, project, steps)
        for i, step in enumerate(rendered_steps, 1):
            console.print(f"  {i}. {step}")

    return True


def _add_dependencies(
    project: Project, dependencies: list[str], dev: bool = False
) -> None:
    """Add dependencies to project using uv.

    Args:
        project: Target project
        dependencies: List of package specs
        dev: Whether these are dev dependencies
    """
    for dep in dependencies:
        dep_name = _parse_dep_name(dep)
        if dev:
            has_it = project.has_dev_dependency(dep_name)
        else:
            has_it = project.has_dependency(dep_name)

        if has_it:
            continue

        try:
            cmd = ["uv", "add"]
            if dev:
                cmd.append("--dev")
            cmd.append(dep)

            subprocess.run(
                cmd,
                cwd=project.path,
                check=True,
                capture_output=True,
            )
            console.print(f"[green]✓[/green] Added: {dep}")
        except (subprocess.CalledProcessError, OSError) as e:
            console.print(f"[red]✗[/red] Failed to add {dep}: {e}")
