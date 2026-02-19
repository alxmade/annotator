"""Rich-powered diff display and interactive user confirmation."""

from __future__ import annotations

import difflib
from pathlib import Path
from typing import NamedTuple

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.syntax import Syntax
from rich.text import Text

from ..client import DocProposal

console = Console()


class Decision(NamedTuple):
    """User decision for a file's proposals."""

    file_path: Path
    accepted: list[DocProposal]
    rejected: list[DocProposal]


def _make_diff(original: str, modified: str, filename: str) -> str:
    """Generate a unified diff string between original and modified content."""
    orig_lines = original.splitlines(keepends=True)
    mod_lines = modified.splitlines(keepends=True)
    diff = difflib.unified_diff(
        orig_lines,
        mod_lines,
        fromfile=f"a/{filename}",
        tofile=f"b/{filename}",
        lineterm="",
    )
    return "".join(diff)


def _apply_proposals_to_source(source: str, proposals: list[DocProposal], language: str) -> str:
    """Insert proposed documentation into source code.

    Inserts each doc comment immediately before the function definition line.
    Works by line number (1-indexed).

    Args:
        source: Original source file content.
        proposals: List of documentation proposals.
        language: "python" or "typescript".

    Returns:
        Modified source content with documentation inserted.
    """
    lines = source.splitlines(keepends=True)

    # Sort proposals by line descending so insertions don't shift line numbers
    sorted_props = sorted(proposals, key=lambda p: p.line, reverse=True)

    for prop in sorted_props:
        insert_at = prop.line - 1  # convert to 0-indexed
        if insert_at < 0 or insert_at > len(lines):
            continue

        doc = prop.proposed_doc
        if not doc.endswith("\n"):
            doc += "\n"

        # Determine indentation from the function line
        func_line = lines[insert_at] if insert_at < len(lines) else ""
        indent = len(func_line) - len(func_line.lstrip())
        indent_str = " " * indent

        if language == "python":
            # Insert docstring as the first line of the function body
            # Find the line after the def line (handle multi-line signatures)
            body_start = insert_at + 1
            while body_start < len(lines) and lines[body_start - 1].rstrip().endswith(","):
                body_start += 1
            # Indent docstring to function body level
            body_indent = indent_str + "    "
            doc_indented = "\n".join(
                body_indent + l if l.strip() else l
                for l in doc.rstrip("\n").splitlines()
            ) + "\n"
            lines.insert(body_start, doc_indented)
        else:
            # Insert JSDoc above the function line
            doc_indented = "\n".join(
                indent_str + l if l.strip() else l
                for l in doc.rstrip("\n").splitlines()
            ) + "\n"
            lines.insert(insert_at, doc_indented)

    return "".join(lines)


def show_file_proposals(
    file_path: Path,
    proposals: list[DocProposal],
    source: str,
    language: str,
    accept_all: bool = False,
) -> Decision:
    """Display proposals for a file and prompt the user for confirmation.

    Args:
        file_path: Path to the source file.
        proposals: Documentation proposals for this file.
        source: Original file content.
        language: "python" or "typescript".
        accept_all: If True, skip prompts and accept everything.

    Returns:
        Decision with accepted and rejected proposals.
    """
    if not proposals:
        return Decision(file_path=file_path, accepted=[], rejected=[])

    console.print()
    console.print(
        Panel(
            f"[bold cyan]{file_path}[/bold cyan]  "
            f"([yellow]{len(proposals)} proposal(s)[/yellow])",
            expand=False,
        )
    )

    accepted: list[DocProposal] = []
    rejected: list[DocProposal] = []

    for prop in proposals:
        console.print(
            f"\n  [bold]Symbol:[/bold] [green]{prop.symbol_name}[/green]"
            f"  [dim](line {prop.line})[/dim]"
        )

        # Show proposed doc
        doc_lang = "python" if language == "python" else "javascript"
        console.print(
            Syntax(prop.proposed_doc, doc_lang, theme="monokai", line_numbers=False)
        )

        if prop.openapi_snippet:
            import json
            console.print("  [bold]OpenAPI snippet:[/bold]")
            console.print(
                Syntax(
                    json.dumps(prop.openapi_snippet, indent=2),
                    "json",
                    theme="monokai",
                )
            )

        if accept_all:
            console.print("  [dim]Auto-accepted (--all)[/dim]")
            accepted.append(prop)
            continue

        while True:
            choice = Prompt.ask(
                "  Apply?",
                choices=["y", "n", "s", "a"],
                default="y",
                show_choices=True,
                show_default=True,
                console=console,
            )
            if choice == "s":
                # Show diff
                modified = _apply_proposals_to_source(source, [prop], language)
                diff_text = _make_diff(source, modified, file_path.name)
                if diff_text:
                    console.print(Syntax(diff_text, "diff", theme="monokai"))
                else:
                    console.print("  [dim]No diff to show.[/dim]")
                continue
            if choice == "a":
                # Accept all remaining
                accepted.append(prop)
                accept_all = True
                break
            if choice == "y":
                accepted.append(prop)
            else:
                rejected.append(prop)
            break

    return Decision(file_path=file_path, accepted=accepted, rejected=rejected)


def print_summary(
    decisions: list[Decision],
    openapi_updated: list[str],
    postman_updated: list[str],
) -> None:
    """Print a final summary of all changes made.

    Args:
        decisions: List of per-file decisions.
        openapi_updated: List of OpenAPI files that were updated.
        postman_updated: List of Postman collection files that were updated.
    """
    total_accepted = sum(len(d.accepted) for d in decisions)
    total_rejected = sum(len(d.rejected) for d in decisions)
    files_modified = sum(1 for d in decisions if d.accepted)

    console.print()
    console.rule("[bold]Summary[/bold]")
    console.print(
        f"  Annotated [green]{total_accepted}[/green] symbol(s) "
        f"across [cyan]{files_modified}[/cyan] file(s)"
        + (f", skipped [yellow]{total_rejected}[/yellow]" if total_rejected else "")
    )
    for path in openapi_updated:
        console.print(f"  Updated OpenAPI spec: [cyan]{path}[/cyan]")
    for path in postman_updated:
        console.print(f"  Updated Postman collection: [cyan]{path}[/cyan]")
    console.print()
