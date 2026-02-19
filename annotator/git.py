"""Git helpers for annotator: staged files, diffs, and staging."""

from __future__ import annotations

import subprocess
from pathlib import Path


def is_git_repo(path: Path) -> bool:
    """Return True if path is inside a git repository."""
    result = subprocess.run(
        ["git", "-C", str(path), "rev-parse", "--git-dir"],
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def get_staged_files(repo_root: Path) -> list[Path]:
    """Return list of staged (cached) file paths with supported extensions."""
    result = subprocess.run(
        ["git", "-C", str(repo_root), "diff", "--cached", "--name-only", "--diff-filter=ACM"],
        capture_output=True,
        text=True,
        check=True,
    )
    supported = {".py", ".ts", ".js"}
    files = []
    for line in result.stdout.splitlines():
        p = repo_root / line.strip()
        if p.suffix in supported and p.exists():
            files.append(p)
    return files


def get_diff(file_path: Path, cached: bool = False) -> str:
    """Return the git diff for a file relative to HEAD (or cached diff).

    Args:
        file_path: Absolute path to the file.
        cached: If True, show the cached (staged) diff.

    Returns:
        Unified diff string, or empty string if not in a repo or no diff.
    """
    repo_root = file_path.parent
    if not is_git_repo(repo_root):
        return ""

    cmd = ["git", "-C", str(repo_root), "diff"]
    if cached:
        cmd.append("--cached")
    cmd += ["HEAD", "--", str(file_path)]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        # HEAD may not exist yet (new repo), try without HEAD
        cmd_no_head = ["git", "-C", str(repo_root), "diff"]
        if cached:
            cmd_no_head.append("--cached")
        cmd_no_head += ["--", str(file_path)]
        result = subprocess.run(cmd_no_head, capture_output=True, text=True)

    return result.stdout


def stage_files(files: list[Path], repo_root: Path) -> None:
    """Stage the given files with git add.

    Args:
        files: List of file paths to stage.
        repo_root: Root of the git repository.
    """
    if not files:
        return
    str_paths = [str(f) for f in files]
    subprocess.run(
        ["git", "-C", str(repo_root), "add", "--"] + str_paths,
        check=True,
    )


def get_repo_root(path: Path) -> Path | None:
    """Return the root of the git repository containing path, or None."""
    result = subprocess.run(
        ["git", "-C", str(path), "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None
    return Path(result.stdout.strip())
