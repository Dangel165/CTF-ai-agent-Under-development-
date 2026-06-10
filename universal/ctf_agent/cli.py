from __future__ import annotations

import asyncio
from pathlib import Path

import click
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

from ctf_agent.challenge import Category, ChallengeSpec
from ctf_agent.solver import solve_workspace_async
from ctf_agent.workspace import create_workspace, load_workspace, build_prompt_markdown

load_dotenv()
console = Console()

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_WORKSPACES = ROOT / "workspaces"


def _fail(message: str) -> None:
    console.print(f"[red]오류:[/red] {message}")
    raise SystemExit(1)


def _handle_errors(fn):
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except (ValueError, FileNotFoundError, RuntimeError) as exc:
            _fail(str(exc))

    return wrapper


def _read_multiline(prompt_text: str) -> str:
    console.print(f"[bold]{prompt_text}[/bold] (finish with empty line + Ctrl-D on Unix, or Ctrl-Z+Enter on Windows)")
    lines: list[str] = []
    try:
        while True:
            line = input()
            lines.append(line)
    except EOFError:
        pass
    return "\n".join(lines).strip()


@click.group()
@click.option("--workspaces", type=click.Path(path_type=Path), default=DEFAULT_WORKSPACES, show_default=True)
@click.pass_context
def main(ctx: click.Context, workspaces: Path) -> None:
    """Universal CTF AI agent — any platform, you provide the challenge details."""
    workspaces.mkdir(parents=True, exist_ok=True)
    ctx.ensure_object(dict)
    ctx.obj["workspaces"] = workspaces


@main.command("new")
@click.option("--from-yaml", type=click.Path(exists=True, path_type=Path), help="Load fields from challenge.yaml")
@click.option("--name", required=False, help="Challenge name")
@click.option(
    "--category", "-c",
    type=click.Choice(Category.choices(), case_sensitive=False),
    required=False,
    help="Challenge field (web, pwn, crypto, ...)",
)
@click.option("--flag-format", "-f", required=False, help="Flag format, e.g. flag{{...}} or HTB{{...}}")
@click.option("--description", "-d", required=False, help="Problem statement (use --interactive for multiline)")
@click.option("--connection", required=False, help="nc host port / URL")
@click.option("--platform", "-p", default="", help="Optional: HackTheBox, picoCTF, local, etc.")
@click.option("--hint", multiple=True, help="Hint (repeatable)")
@click.option("--file", "files", type=click.Path(exists=True, path_type=Path), multiple=True, help="Attachment file or folder")
@click.option("--interactive", "-i", is_flag=True, help="Prompt for all fields interactively")
@click.pass_context
@_handle_errors
def cmd_new(
    ctx: click.Context,
    from_yaml: Path | None,
    name: str | None,
    category: str | None,
    flag_format: str | None,
    description: str | None,
    connection: str | None,
    platform: str,
    hint: tuple[str, ...],
    files: tuple[Path, ...],
    interactive: bool,
) -> None:
    """Create a challenge workspace from your inputs."""
    if from_yaml:
        spec = ChallengeSpec.load_yaml(from_yaml)
        ws = create_workspace(spec, root=ctx.obj["workspaces"], files=list(files) if files else None)
        console.print(f"[green]Created[/green] `{ws}` from `{from_yaml}`")
        return

    if interactive or not all([name, category, flag_format, description]):
        console.print(Panel("Enter challenge details (any CTF platform)", title="CTF Agent"))
        name = name or Prompt.ask("Problem name")
        if not category:
            cat_table = Table(show_header=False, box=None)
            cat_table.add_row("Categories:", ", ".join(Category.choices()))
            console.print(cat_table)
            category = Prompt.ask("Field / category", default="misc")
        flag_format = flag_format or Prompt.ask("Flag format", default="flag{...}")
        if not description:
            description = _read_multiline("Problem content / description")
        connection = connection or Prompt.ask("Connection info (optional)", default="")
        platform = platform or Prompt.ask("Platform name (optional)", default="")

    assert name and category and flag_format and description

    spec = ChallengeSpec(
        name=name,
        category=category,
        flag_format=flag_format,
        description=description,
        connection_info=connection or "",
        hints=list(hint),
        platform=platform,
    )
    ws = create_workspace(spec, root=ctx.obj["workspaces"], files=list(files) if files else None)
    console.print(f"[green]Created[/green] `{ws}`")
    console.print("Next: [bold]ctf-agent solve[/bold] that path, or open the folder in Cursor and use the ctf-solve skill.")


@main.command("edit")
@click.argument("workspace", type=click.Path(exists=True, path_type=Path))
@click.option("--name", default=None)
@click.option("--category", "-c", type=click.Choice(Category.choices(), case_sensitive=False), default=None)
@click.option("--flag-format", "-f", default=None)
@click.option("--description", "-d", default=None)
@click.option("--connection", default=None)
@click.option("--platform", "-p", default=None)
@_handle_errors
def cmd_edit(
    workspace: Path,
    name: str | None,
    category: str | None,
    flag_format: str | None,
    description: str | None,
    connection: str | None,
    platform: str | None,
) -> None:
    """Update challenge.yaml in an existing workspace."""
    ws, spec = load_workspace(workspace)
    if name:
        spec.name = name
    if category:
        spec.category = Category.normalize(category)
    if flag_format:
        spec.flag_format = flag_format
    if description:
        spec.description = description
    if connection is not None:
        spec.connection_info = connection
    if platform is not None:
        spec.platform = platform
    spec.save_yaml(ws / "challenge.yaml")
    (ws / "PROMPT.md").write_text(build_prompt_markdown(spec, ws), encoding="utf-8")
    console.print(f"[green]Updated[/green] `{ws / 'challenge.yaml'}`")


@main.command("show")
@click.argument("workspace", type=click.Path(exists=True, path_type=Path))
@_handle_errors
def cmd_show(workspace: Path) -> None:
    """Print challenge metadata."""
    _, spec = load_workspace(workspace)
    table = Table(title=spec.name)
    table.add_column("Field", style="cyan")
    table.add_column("Value")
    table.add_row("Category", spec.category.value)
    table.add_row("Flag format", spec.flag_format)
    table.add_row("Platform", spec.platform or "-")
    table.add_row("Connection", spec.connection_info or "-")
    table.add_row("Description", spec.description[:500] + ("..." if len(spec.description) > 500 else ""))
    console.print(table)


@main.command("solve")
@click.argument("workspace", type=click.Path(exists=True, path_type=Path), required=False)
@click.option("--interactive", "-i", is_flag=True, help="Create challenge interactively, then solve")
@click.option("--name", default=None)
@click.option("--category", "-c", type=click.Choice(Category.choices(), case_sensitive=False), default=None)
@click.option("--flag-format", "-f", default=None)
@click.option("--description", "-d", default=None)
@click.option("--connection", default=None)
@click.option("--platform", "-p", default="")
@click.option("--file", "files", type=click.Path(exists=True, path_type=Path), multiple=True)
@click.pass_context
@_handle_errors
def cmd_solve(
    ctx: click.Context,
    workspace: Path | None,
    interactive: bool,
    name: str | None,
    category: str | None,
    flag_format: str | None,
    description: str | None,
    connection: str | None,
    platform: str,
    files: tuple[Path, ...],
) -> None:
    """Run the AI solver on a workspace (or create one with -i)."""
    if interactive or workspace is None:
        ctx.invoke(
            cmd_new,
            name=name,
            category=category,
            flag_format=flag_format,
            description=description,
            connection=connection,
            platform=platform,
            hint=(),
            files=files,
            interactive=True,
        )
        # pick latest workspace
        root: Path = ctx.obj["workspaces"]
        workspace = sorted(root.iterdir(), key=lambda p: p.stat().st_mtime)[-1]

    ws, spec = load_workspace(workspace)
    console.print(f"Solving [bold]{spec.name}[/bold] ({spec.category.value}) in `{ws}` ...")

    result = asyncio.run(solve_workspace_async(ws, spec))

    if result.error:
        console.print(f"[red]오류:[/red] {result.error}")
    if result.flag:
        console.print(Panel(f"[bold green]{result.flag}[/bold green]", title="Flag"))
    else:
        console.print("[yellow]플래그를 찾지 못했습니다.[/yellow]")
        if result.raw_text:
            console.print(result.raw_text[-2000:])


@main.command("init-template")
@click.argument("path", type=click.Path(path_type=Path), default="challenge.yaml")
def cmd_init_template(path: Path) -> None:
    """Write a blank challenge.yaml template you can fill in."""
    template = """# Universal CTF challenge — edit and run: ctf-agent new --file challenge.yaml
# Or copy fields into: ctf-agent new -i

name: "Example challenge"
category: web          # web | pwn | crypto | rev | forensics | stego | osint | misc | mobile
flag_format: "flag{...}"   # or regex:flag\\{[^}]+\\}
platform: ""           # optional: HackTheBox, picoCTF, local CTF, etc.
connection_info: ""     # nc host 1337 / https://...

description: |
  Paste the full problem statement here.

hints: []
notes: ""
"""
    path.write_text(template, encoding="utf-8")
    console.print(f"Wrote template to [bold]{path}[/bold]")


@main.command("web")
@click.option("--host", default="127.0.0.1", show_default=True)
@click.option("--port", default=8765, show_default=True)
@click.pass_context
def cmd_web(ctx: click.Context, host: str, port: int) -> None:
    """Open browser form to enter challenge details (Korean UI)."""
    from ctf_agent.web_server import run_web_server

    workspaces: Path = ctx.obj["workspaces"]
    console.print(f"[bold]Web UI[/bold] http://{host}:{port}")
    console.print(f"Template: [cyan]templates/CURSOR-CHAT-KO.md[/cyan]")
    run_web_server(host, port, workspaces)


if __name__ == "__main__":
    main()
