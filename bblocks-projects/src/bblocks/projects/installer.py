"""Component installation logic."""

from typing import Any

import toml
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm
from rich.syntax import Syntax

from bblocks.projects.components import Component
from bblocks.projects.project import Project

console = Console()


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
            else:
                # Different types or values - keep existing by default
                # This case should be handled by confirmation logic
                result[key] = value
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
                f"\n[yellow]Will merge into existing:[/yellow] "
                f"[tool.{section}]"
            )
        else:
            console.print(
                f"\n[green]Will add new section:[/green] [tool.{section}]"
            )

        # Show the content
        toml_str = toml.dumps({section: content})
        syntax = Syntax(toml_str, "toml", theme="monokai", line_numbers=False)
        console.print(Panel(syntax, border_style="dim"))


def install_component(
    component: Component,
    project: Project,
    force: bool = False,
    interactive: bool = True,
) -> bool:
    """Install a component into a project.

    Args:
        component: Component to install
        project: Target project
        force: Force overwrite existing files
        interactive: Ask for confirmation before changes

    Returns:
        True if installation succeeded
    """
    console.print(f"\n[bold]Installing component:[/bold] {component.name}")
    console.print(f"[dim]{component.description}[/dim]\n")

    # Check if can install
    can_install, reason = component.can_install(project)
    if not can_install:
        console.print(f"[bold red]Cannot install:[/bold red] {reason}")
        return False

    # Check conflicts
    conflicts = component.get_conflicts(project)
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

    # Show what will be changed
    config_updates = component.get_config_updates(project)
    if config_updates:
        existing_tool = project.pyproject_data.get("tool", {})
        show_config_diff(component.name, existing_tool, config_updates)

        if interactive:
            if not Confirm.ask("\nApply these config changes?"):
                console.print("[yellow]Installation cancelled[/yellow]")
                return False

    # Install files
    files_created = []
    for file_spec in component.get_files(project):
        dest_path = project.path / file_spec.destination

        if dest_path.exists() and not force:
            console.print(
                f"[yellow]Skipping existing file:[/yellow] "
                f"{file_spec.destination}"
            )
            continue

        if file_spec.create_dirs:
            dest_path.parent.mkdir(parents=True, exist_ok=True)

        dest_path.write_text(file_spec.source_template, encoding="utf-8")
        files_created.append(file_spec.destination)
        console.print(f"[green]✓[/green] Created: {file_spec.destination}")

    # Update pyproject.toml
    if config_updates:
        pyproject_data = project.pyproject_data.copy()

        # Ensure tool section exists
        if "tool" not in pyproject_data:
            pyproject_data["tool"] = {}

        # Merge config updates
        for section_path, content in config_updates.items():
            parts = section_path.split(".")
            target = pyproject_data

            # Navigate to the target section
            for part in parts[:-1]:
                if part not in target:
                    target[part] = {}
                target = target[part]

            # Merge the content
            last_part = parts[-1]
            if last_part in target:
                target[last_part] = merge_config_sections(target[last_part], content)
            else:
                target[last_part] = content

        # Write updated pyproject.toml
        with open(project.pyproject_path, "w", encoding="utf-8") as f:
            toml.dump(pyproject_data, f)
        console.print("[green]✓[/green] Updated: pyproject.toml")

        # Reload project data
        project._pyproject_data = None

    # Add dependencies
    dev_deps = component.get_dev_dependencies(project)
    if dev_deps:
        console.print("\n[bold]Dev dependencies to add:[/bold]")
        for dep in dev_deps:
            # Check if already present
            if project.has_dev_dependency(dep.split(">=")[0].split("==")[0]):
                console.print(f"  • {dep} [dim](already present)[/dim]")
            else:
                console.print(f"  • {dep}")

        if interactive and dev_deps:
            if Confirm.ask("\nAdd these dependencies now?"):
                _add_dependencies(project, dev_deps, dev=True)
            else:
                console.print(
                    "[yellow]Skipped dependency installation. "
                    "Add manually with:[/yellow]"
                )
                console.print(f"  uv add --dev {' '.join(dev_deps)}")

    # Show post-install steps
    steps = component.get_post_install_steps(project)
    if steps:
        console.print("\n[bold green]✓ Component installed successfully![/bold green]")
        console.print("\n[bold]Next steps:[/bold]")
        for i, step in enumerate(steps, 1):
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
    import subprocess

    for dep in dependencies:
        # Check if already present
        dep_name = dep.split(">=")[0].split("==")[0]
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
        except subprocess.CalledProcessError as e:
            console.print(f"[red]✗[/red] Failed to add {dep}: {e}")
