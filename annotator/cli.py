"""Typer CLI for annotator: run and check commands."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Annotated, Optional

import typer
from rich.console import Console

from . import analyzer as analyze_mod
from . import git
from .api_docs import openapi as openapi_mod
from .api_docs import postman as postman_mod
from .client import DocProposal
from .ui.diff_viewer import Decision, print_summary, show_file_proposals

app = typer.Typer(
    name="annotator",
    help="AI-powered code documentation agent. Analyzes source code and generates docs.",
    add_completion=True,
    no_args_is_help=True,
)

console = Console()

_TargetArg = Annotated[
    Optional[Path],
    typer.Argument(
        help="File or directory to analyze. Defaults to current directory.",
        show_default=False,
    ),
]


def _resolve_target(target: Path | None) -> Path:
    t = target or Path(".")
    if not t.exists():
        console.print(f"[red]Error:[/red] path does not exist: {t}")
        raise typer.Exit(1)
    return t.resolve()


def _check_api_key() -> str:
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not key:
        console.print(
            "[red]Error:[/red] ANTHROPIC_API_KEY environment variable is not set.\n"
            "Set it with: export ANTHROPIC_API_KEY=your_key"
        )
        raise typer.Exit(1)
    return key


def _process_files(
    files: list[Path],
    staged_only: bool,
    accept_all: bool,
    dry_run: bool,
    api_key: str,
    search_root: Path,
) -> None:
    """Core processing loop shared by run and check commands."""
    if not files:
        console.print("[yellow]No supported files found.[/yellow]")
        return

    console.print(f"Found [cyan]{len(files)}[/cyan] file(s) to analyze.")

    openapi_path = openapi_mod.find_openapi_file(search_root)
    postman_path = postman_mod.find_postman_file(search_root)

    if openapi_path:
        console.print(f"OpenAPI spec: [dim]{openapi_path}[/dim]")
    if postman_path:
        console.print(f"Postman collection: [dim]{postman_path}[/dim]")

    all_decisions: list[Decision] = []
    openapi_updated: list[str] = []
    postman_updated: list[str] = []

    for file_path in files:
        console.print(f"\nAnalyzing [dim]{file_path}[/dim]...")
        try:
            proposals = analyze_mod.analyze_file(
                file_path=file_path,
                staged_only=staged_only,
                api_key=api_key,
            )
        except Exception as exc:
            console.print(f"  [red]Error analyzing {file_path}: {exc}[/red]")
            continue

        if not proposals:
            console.print(f"  [dim]No missing documentation found.[/dim]")
            continue

        language = analyze_mod.get_language(file_path)

        if dry_run:
            console.print(f"  [bold]{len(proposals)} proposal(s)[/bold] (dry-run, no changes):")
            for p in proposals:
                console.print(f"    - [green]{p.symbol_name}[/green] (line {p.line})")
            continue

        source = file_path.read_text(encoding="utf-8", errors="replace")
        decision = show_file_proposals(
            file_path=file_path,
            proposals=proposals,
            source=source,
            language=language,
            accept_all=accept_all,
        )
        all_decisions.append(decision)

        if decision.accepted:
            analyze_mod.apply_proposals(file_path, decision.accepted, language)

            # Handle API doc updates for endpoint proposals
            endpoint_proposals = [p for p in decision.accepted if p.openapi_snippet]
            for prop in endpoint_proposals:
                if openapi_path and prop.openapi_snippet:
                    # Find matching symbol to get method/path
                    _prompt_openapi_update(prop, openapi_path, openapi_updated)
                if postman_path and prop.postman_item:
                    _prompt_postman_update(prop, postman_path, postman_updated)

    if not dry_run:
        # Stage modified files if in staged mode
        if staged_only:
            modified = [d.file_path for d in all_decisions if d.accepted]
            repo_root = git.get_repo_root(search_root)
            if modified and repo_root:
                git.stage_files(modified, repo_root)

        print_summary(all_decisions, openapi_updated, postman_updated)


def _prompt_openapi_update(
    prop: DocProposal,
    openapi_path: Path,
    updated_list: list[str],
) -> None:
    """Prompt user to update OpenAPI spec for an endpoint proposal."""
    from rich.prompt import Confirm

    if not prop.openapi_snippet:
        return

    # Try to extract method/path from the snippet structure
    # snippet may be: {"summary": ..., "description": ...} or full path item
    method = None
    path = None

    # The snippet might embed method/path info or we may need to infer from symbol
    for http_method in ["get", "post", "put", "delete", "patch", "head", "options"]:
        if http_method in prop.openapi_snippet:
            method = http_method.upper()
            path = list(prop.openapi_snippet[http_method].keys())[0] if isinstance(prop.openapi_snippet[http_method], dict) else None

    # Fallback: treat the whole snippet as the operation object
    if not method:
        return

    console.print(
        f"\n  OpenAPI: update [cyan]{method} {path}[/cyan] in [dim]{openapi_path}[/dim]?"
    )
    if Confirm.ask("  Apply OpenAPI update?", default=True):
        openapi_mod.update_operation(openapi_path, method, path or "/", prop.openapi_snippet)
        if str(openapi_path) not in updated_list:
            updated_list.append(str(openapi_path))


def _prompt_postman_update(
    prop: DocProposal,
    postman_path: Path,
    updated_list: list[str],
) -> None:
    """Prompt user to update Postman collection for an endpoint proposal."""
    from rich.prompt import Confirm

    if not prop.postman_item:
        return

    console.print(
        f"\n  Postman: update collection [dim]{postman_path}[/dim]?"
    )
    if Confirm.ask("  Apply Postman update?", default=True):
        postman_mod.update_request(
            collection_path=postman_path,
            name=prop.symbol_name,
            http_method=prop.postman_item.get("method", "GET"),
            endpoint_path=prop.postman_item.get("path", "/"),
            postman_item=prop.postman_item,
        )
        if str(postman_path) not in updated_list:
            updated_list.append(str(postman_path))


@app.command()
def run(
    target: _TargetArg = None,
    staged: Annotated[
        bool,
        typer.Option("--staged", help="Only analyze git-staged files."),
    ] = False,
    all_: Annotated[
        bool,
        typer.Option("--all", "-a", help="Accept all proposals without prompting."),
    ] = False,
    api_key: Annotated[
        Optional[str],
        typer.Option("--api-key", envvar="ANTHROPIC_API_KEY", help="Anthropic API key.", show_default=False),
    ] = None,
) -> None:
    """Analyze source files and apply documentation interactively."""
    resolved = _resolve_target(target)
    key = api_key or _check_api_key()
    search_root = resolved if resolved.is_dir() else resolved.parent

    files = analyze_mod.collect_files(resolved, staged_only=staged)
    _process_files(
        files=files,
        staged_only=staged,
        accept_all=all_,
        dry_run=False,
        api_key=key,
        search_root=search_root,
    )


@app.command()
def check(
    target: _TargetArg = None,
    staged: Annotated[
        bool,
        typer.Option("--staged", help="Only analyze git-staged files."),
    ] = False,
    api_key: Annotated[
        Optional[str],
        typer.Option("--api-key", envvar="ANTHROPIC_API_KEY", help="Anthropic API key.", show_default=False),
    ] = None,
) -> None:
    """Dry-run: show what documentation would be generated without modifying files."""
    resolved = _resolve_target(target)
    key = api_key or _check_api_key()
    search_root = resolved if resolved.is_dir() else resolved.parent

    files = analyze_mod.collect_files(resolved, staged_only=staged)
    console.print("[bold]Dry-run mode[/bold] - no files will be modified.")
    _process_files(
        files=files,
        staged_only=staged,
        accept_all=False,
        dry_run=True,
        api_key=key,
        search_root=search_root,
    )


if __name__ == "__main__":
    app()
