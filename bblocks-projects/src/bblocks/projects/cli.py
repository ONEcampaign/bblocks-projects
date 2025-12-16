"""Command-line interface for bblocks-projects."""

import json
import subprocess
from pathlib import Path

import typer
from copier import run_copy, run_update
from copier.errors import CopierError
from rich.console import Console

from bblocks.projects import __version__
from bblocks.projects.config import DEFAULT_REF, TEMPLATE_DESCRIPTION, TEMPLATE_URL

app = typer.Typer(
    name="bblocks-projects",
    help="ONE Campaign Python project utilities",
    add_completion=False,
)
console = Console()


def version_callback(value: bool) -> None:
    """Print version and exit."""
    if value:
        console.print(f"bblocks-projects version {__version__}")
        raise typer.Exit()


def get_github_user_info() -> dict[str, str]:
    """Get user info from GitHub CLI if available and authenticated.

    Returns:
        Dictionary with author_name, author_email, and github_username if available.
    """
    info: dict[str, str] = {}

    try:
        # Check if gh is installed and user is authenticated
        result = subprocess.run(
            ["gh", "auth", "status"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode != 0:
            return info

        # Get user info from GitHub API
        result = subprocess.run(
            ["gh", "api", "user"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            return info

        user_data = json.loads(result.stdout)

        # Extract relevant fields
        if user_data.get("name"):
            info["author_name"] = user_data["name"]
        if user_data.get("email"):
            info["author_email"] = user_data["email"]
        if user_data.get("login"):
            info["github_username"] = user_data["login"]

    except (subprocess.TimeoutExpired, FileNotFoundError, json.JSONDecodeError):
        # gh not installed, timed out, or returned invalid JSON
        pass

    return info


@app.command()
def create(
    destination: Path | None = typer.Argument(
        None,
        help="Directory for the project (use '.' or --here for current dir)",
    ),
    here: bool = typer.Option(
        False,
        "--here",
        "-H",
        help="Create project in current directory instead of a subdirectory",
    ),
    template_ref: str | None = typer.Option(
        None,
        "--ref",
        "-r",
        help="Template version (branch, tag, or commit). Defaults to 'main'",
    ),
    project_type: str | None = typer.Option(
        None,
        "--type",
        "-t",
        help="Project type: 'package' or 'research'",
    ),
    data: list[str] | None = typer.Option(
        None,
        "--data",
        "-d",
        help="Override template variables in KEY=VALUE format",
    ),
    defaults: bool = typer.Option(
        False,
        "--defaults",
        help="Use default answers for all questions",
    ),
    no_github: bool = typer.Option(
        False,
        "--no-github",
        help="Don't prefill author info from GitHub CLI",
    ),
) -> None:
    """Create a new ONE Campaign Python project.

    If you're logged into GitHub CLI (gh), author info will be prefilled.

    Examples:

        # Interactive mode (asks where to create)
        bblocks-projects create

        # Create in a new subdirectory
        bblocks-projects create my-awesome-project

        # Create in current directory
        bblocks-projects create --here
        bblocks-projects create .

        # Create a package project with defaults
        bblocks-projects create my-package --type package --defaults

        # Create using a specific template version
        bblocks-projects create my-project --ref v1.0.0

        # Override template variables
        bblocks-projects create my-project --data author_name="Jane Doe"

        # Skip GitHub detection
        bblocks-projects create my-project --no-github
    """
    # Handle --here flag or '.' as destination
    if here:
        destination = Path.cwd()
    elif destination is None:
        # Ask user interactively
        console.print("\n[bold]Where would you like to create the project?[/bold]\n")
        console.print(f"  [cyan]1.[/cyan] Current directory ({Path.cwd().name}/)")
        console.print("  [cyan]2.[/cyan] New subdirectory")
        choice = typer.prompt("\nChoice", default="1")

        if choice == "1":
            destination = Path.cwd()
        else:
            dir_name = typer.prompt("Directory name")
            destination = Path.cwd() / dir_name
    elif str(destination) == ".":
        destination = Path.cwd()

    # Check if destination exists as a file (not a directory)
    if destination.exists() and destination.is_file():
        console.print(
            f"[bold red]Error:[/bold red] '{destination}' is a file, not a directory."
        )
        raise typer.Exit(code=1)

    # Check if destination exists and has files
    if destination.exists() and destination.is_dir() and any(destination.iterdir()):
        # Check for non-hidden files (allow .git, etc.)
        non_hidden = [f for f in destination.iterdir() if not f.name.startswith(".")]
        if non_hidden:
            console.print(
                f"[bold yellow]Warning:[/bold yellow] Directory '{destination}' "
                "is not empty."
            )
            if not typer.confirm("Continue anyway? Files may be overwritten."):
                raise typer.Exit(code=0)

    console.print(TEMPLATE_DESCRIPTION)
    console.print(f"\n[bold green]Creating project at:[/bold green] {destination}")

    # Try to get defaults from GitHub CLI
    github_info: dict[str, str] = {}
    if not no_github:
        github_info = get_github_user_info()
        if github_info:
            gh_user = github_info.get("github_username", "unknown")
            console.print(f"\n[dim]Detected GitHub user: {gh_user}[/dim]")

    # Prepare data overrides (GitHub info as base, then explicit overrides)
    data_dict: dict[str, str] = {}

    # Start with GitHub-detected values as defaults
    data_dict.update(github_info)

    # Add project_type if specified
    if project_type:
        data_dict["project_type"] = project_type

    # Explicit --data overrides take precedence
    if data:
        for item in data:
            if "=" not in item:
                console.print(
                    f"[bold red]Error:[/bold red] Invalid data format: {item}. "
                    "Use KEY=VALUE format."
                )
                raise typer.Exit(code=1)
            key, value = item.split("=", 1)
            data_dict[key] = value

    try:
        run_copy(
            src_path=TEMPLATE_URL,
            dst_path=destination,
            vcs_ref=template_ref or DEFAULT_REF,
            data=data_dict if data_dict else None,
            defaults=defaults,
            unsafe=True,  # Allow template tasks like git init
        )
        console.print(
            f"\n[bold green]✓[/bold green] Project created successfully at "
            f"{destination}"
        )
        console.print("\n[bold]Next steps:[/bold]")
        console.print(f"  cd {destination}")
        console.print("  # Review and edit README.md")
        console.print("  # Start coding!")
    except CopierError as e:
        console.print(f"[bold red]Error creating project:[/bold red] {e}")
        raise typer.Exit(code=1) from e
    except Exception as e:
        console.print(f"[bold red]Unexpected error:[/bold red] {e}")
        raise typer.Exit(code=1) from e


@app.command()
def update(
    destination: Path = typer.Option(
        Path.cwd(),
        "--path",
        "-p",
        help="Path to the project to update (defaults to current directory)",
    ),
    template_ref: str | None = typer.Option(
        None,
        "--ref",
        "-r",
        help="Update to specific template version (branch, tag, or commit)",
    ),
    data: list[str] | None = typer.Option(
        None,
        "--data",
        "-d",
        help="Override template variables in KEY=VALUE format",
    ),
    skip_answered: bool = typer.Option(
        True,
        "--skip-answered/--no-skip-answered",
        help="Skip questions that were already answered",
    ),
) -> None:
    """Update an existing ONE Campaign project to the latest template version.

    This command should be run from within the project directory or use --path.

    Examples:

        # Update current project to latest template
        bblocks-projects update

        # Update to specific template version
        bblocks-projects update --ref v1.2.0

        # Update a specific project
        bblocks-projects update --path /path/to/my-project

        # Re-answer all questions
        bblocks-projects update --no-skip-answered
    """
    console.print(
        f"[bold cyan]Updating project at:[/bold cyan] {destination.absolute()}"
    )

    # Check if .copier-answers.yml exists
    copier_answers = destination / ".copier-answers.yml"
    if not copier_answers.exists():
        console.print(
            "[bold red]Error:[/bold red] No .copier-answers.yml found. "
            "This doesn't appear to be a project created with bblocks-projects."
        )
        console.print(
            "\nIf this is an existing project, see the adoption guide:\n"
            "https://github.com/ONEcampaign/bblocks-projects/blob/main/docs/usage/adopting-existing.md"
        )
        raise typer.Exit(code=1)

    # Prepare data overrides
    data_dict = None
    if data:
        data_dict = {}
        for item in data:
            if "=" not in item:
                console.print(
                    f"[bold red]Error:[/bold red] Invalid data format: {item}. "
                    "Use KEY=VALUE format."
                )
                raise typer.Exit(code=1)
            key, value = item.split("=", 1)
            data_dict[key] = value

    try:
        run_update(
            dst_path=destination,
            vcs_ref=template_ref,
            data=data_dict,
            skip_answered=skip_answered,
            unsafe=True,  # Allow template tasks
        )
        console.print("\n[bold green]✓[/bold green] Project updated successfully!")
        console.print("\n[bold]Next steps:[/bold]")
        console.print("  git diff  # Review changes")
        console.print("  uv sync   # Update dependencies if needed")
        console.print("  uv run pytest  # Run tests")
        console.print("  git commit -m 'Update from template'")
    except CopierError as e:
        console.print(f"[bold red]Error updating project:[/bold red] {e}")
        raise typer.Exit(code=1) from e
    except Exception as e:
        console.print(f"[bold red]Unexpected error:[/bold red] {e}")
        raise typer.Exit(code=1) from e


@app.command()
def add(
    components: list[str] | None = typer.Argument(
        None,
        help="Component(s) to add: pre-commit, ruff, ci, pytest, pypi-publish",
    ),
    path: Path = typer.Option(
        Path.cwd(),
        "--path",
        "-p",
        help="Path to the project (defaults to current directory)",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Force overwrite existing files",
    ),
    yes: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help="Skip confirmation prompts",
    ),
    list_available: bool = typer.Option(
        False,
        "--list",
        "-l",
        help="List available components and exit",
    ),
) -> None:
    """Add template components to an existing project.

    Add specific template features (pre-commit hooks, CI workflows, etc.) to your
    existing Python project without adopting the full template.

    Examples:

        # Add pre-commit hooks
        bblocks-projects add pre-commit

        # Add multiple components
        bblocks-projects add ruff ci pytest

        # Add to a specific project
        bblocks-projects add pre-commit --path /path/to/project

        # Skip confirmations
        bblocks-projects add ruff --yes

        # List available components
        bblocks-projects add --list
    """
    from bblocks.projects.components import get_component, list_components
    from bblocks.projects.installer import install_component
    from bblocks.projects.project import Project

    # List components if requested
    if list_available:
        console.print("\n[bold]Available components:[/bold]\n")
        for comp in list_components():
            console.print(f"  • [cyan]{comp.name}[/cyan] - {comp.description}")
        console.print()
        return

    # Check components were provided
    if not components:
        console.print("[bold red]Error:[/bold red] No components specified")
        console.print("\nUse --list to see available components")
        raise typer.Exit(code=1)

    # Validate project
    project = Project(path)
    is_valid, errors = project.validate_for_component()

    if not is_valid:
        console.print("[bold red]Project validation failed:[/bold red]")
        for error in errors:
            console.print(f"  • {error}")
        raise typer.Exit(code=1)

    # Show project info
    console.print("\n[bold]Project Analysis:[/bold]")
    console.print(f"  Path: {project.path}")
    console.print(f"  Name: {project.get_project_name() or 'Unknown'}")
    console.print(f"  Type: {project.detect_type()}")
    console.print("  Uses uv: Yes")

    # Install each component
    success_count = 0
    for component_name in components:
        component = get_component(component_name)

        if component is None:
            console.print(f"\n[bold red]Unknown component:[/bold red] {component_name}")
            console.print(
                "\nAvailable components: pre-commit, ruff, ci, pytest, pypi-publish"
            )
            console.print("Use --list to see descriptions")
            continue

        try:
            if install_component(
                component,
                project,
                force=force,
                interactive=not yes,
            ):
                success_count += 1
        except Exception as e:
            console.print(
                f"\n[bold red]Error installing {component_name}:[/bold red] {e}"
            )
            continue

    # Summary
    console.print(
        f"\n[bold]Summary:[/bold] Installed {success_count}/{len(components)} "
        "components"
    )


@app.callback()
def main(
    version: bool | None = typer.Option(
        None,
        "--version",
        "-v",
        callback=version_callback,
        is_eager=True,
        help="Show version and exit",
    ),
) -> None:
    """Create and update ONE Campaign Python projects from templates."""
    pass


if __name__ == "__main__":
    app()
