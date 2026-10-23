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
from rich.markup import escape
from rich.panel import Panel
from rich.prompt import Confirm
from rich.syntax import Syntax

from bblocks.projects.components import ComponentDef
from bblocks.projects.config import DEFAULT_REF, resolve_template_url
from bblocks.projects.project import Project, is_repo_level

console = Console()

# PEP-440 specifiers (`==`, `!=`, `<=`, `>=`, `<`, `>`, `~=`, `===`),
# extras (`[extra]`), markers (`;`), or whitespace all delimit the package name.
_DEP_NAME_DELIM_RE = re.compile(r"[\[<>=!~ ;]")


_MULTI_LANGUAGE_DOCS = (
    "https://github.com/ONEcampaign/bblocks-projects/blob/main/docs/"
    "the-family-contract.md#a-package-in-a-multi-language-repo"
)


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


def _template_paths(comp: ComponentDef) -> list[str]:
    """List the paths `comp` writes, relative to the package or the git root."""
    return [relpath.removesuffix(".jinja") for relpath in comp.template_files]


def repo_level_files(comp: ComponentDef) -> list[str]:
    """List the files of `comp` that git tooling reads from the git root."""
    return [relpath for relpath in _template_paths(comp) if is_repo_level(relpath)]


def package_files(comp: ComponentDef, project: Project) -> list[str]:
    """List the files `add` writes into the package directory for `comp`.

    A package below its git root shares the repo-level files with every
    language in the repo, so `add` leaves them out. At the git root or
    outside git, every file of the component lands in the package.
    """
    if not project.below_repo_root:
        return _template_paths(comp)
    return [relpath for relpath in _template_paths(comp) if not is_repo_level(relpath)]


def root_file_advice(files: list[str], project: Project) -> str:
    """Tell the user to add shared root `files` by hand, with the docs section."""
    return (
        f"Add {', '.join(files)} at the git root ({project.repo_root}) by hand. "
        'See "A package in a multi-language repo": '
        f"{_MULTI_LANGUAGE_DOCS}"
    )


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
        f"File exists: {relpath}"
        for relpath in package_files(comp, project)
        if (project.path / relpath).exists()
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
            "module_name": project.get_module_name() or project.get_project_slug(),
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


def _report_skipped_root_files(component: ComponentDef, project: Project) -> None:
    """Name each repo-level file `add` leaves alone, and say whether it exists."""
    for relpath in repo_level_files(component):
        root_path = project.tooling_path(relpath)
        if root_path.exists():
            console.print(
                f"[yellow]Skipped {relpath}:[/yellow] shared at the git root, "
                f"where it exists ({escape(str(root_path))})"
            )
        else:
            console.print(
                f"[yellow]Skipped {relpath}:[/yellow] shared at the git root, "
                f"where it is missing. {escape(root_file_advice([relpath], project))}"
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

    if project.below_repo_root:
        _report_skipped_root_files(component, project)

    written: list[str] = []
    for dest_relpath in package_files(component, project):
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
        written.append(f"Created: {dest_relpath}")

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
        written.append("Updated: pyproject.toml")

        project.reload_pyproject()

    dev_deps = component.dev_deps
    if dev_deps:
        console.print("\n[bold]Dev dependencies to add:[/bold]")
        for dep in dev_deps:
            if project.has_dev_dependency(_parse_dep_name(dep)):
                console.print(f"  • {dep} [dim](already present)[/dim]")
            else:
                console.print(f"  • {dep}")

        if interactive and not Confirm.ask("\nAdd these dependencies now?"):
            console.print(
                "[yellow]Skipped dependency installation. Add manually with:[/yellow]"
            )
            console.print(f"  uv add --dev {' '.join(dev_deps)}")
        elif not _add_dependencies(project, dev_deps, dev=True):
            console.print(
                f"\n[bold red]✗ {component.name} not installed:[/bold red] "
                "`uv add` failed."
            )
            if written:
                console.print("Left in place, not rolled back:")
                for item in written:
                    console.print(f"  • {item}")
            return False

    steps = component.post_install_steps
    installed_in_package = (
        package_files(component, project)
        or component.pyproject_sections
        or component.dev_deps
    )
    if steps and not installed_in_package:
        console.print(
            f"\n[yellow]{component.name} has nothing to install in the "
            "package.[/yellow]"
        )
    elif steps:
        console.print("\n[bold green]✓ Component installed successfully![/bold green]")
        console.print("\n[bold]Next steps:[/bold]")
        rendered_steps = _render_post_install_steps(component, project, steps)
        for i, step in enumerate(rendered_steps, 1):
            console.print(f"  {i}. {step}")

    return True


def _add_dependencies(
    project: Project, dependencies: list[str], dev: bool = False
) -> bool:
    """Add dependencies to project using uv.

    Stops at the first failure and prints uv's stderr.

    Args:
        project: Target project
        dependencies: List of package specs
        dev: Whether these are dev dependencies

    Returns:
        True when every dependency is present afterwards
    """
    for dep in dependencies:
        dep_name = _parse_dep_name(dep)
        if dev:
            has_it = project.has_dev_dependency(dep_name)
        else:
            has_it = project.has_dependency(dep_name)

        if has_it:
            continue

        cmd = ["uv", "add"]
        if dev:
            cmd.append("--dev")
        cmd.append(dep)

        try:
            subprocess.run(
                cmd,
                cwd=project.path,
                check=True,
                capture_output=True,
                text=True,
            )
        except subprocess.CalledProcessError as e:
            console.print(f"[red]✗[/red] Failed to add {dep}: {escape(str(e))}")
            if e.stderr:
                console.print(escape(e.stderr.strip()))
            return False
        except OSError as e:
            console.print(f"[red]✗[/red] Failed to add {dep}: {escape(str(e))}")
            return False
        console.print(f"[green]✓[/green] Added: {dep}")
    return True
