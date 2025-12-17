from agents import function_tool
import asyncio
import os
from pathlib import Path


def _write_file(file_path: str, content: str) -> str:
    """Write content to a file, creating parent directories if needed.

    Args:
        file_path: Absolute path to the file to write.
        content: File content to write (overwrites existing file).

    Returns:
        Success message or an error string.
    """
    path = Path(file_path)
    parent = path.parent

    if parent.exists() and not parent.is_dir():
        return f"Error: parent path is not a directory: {parent}"
    if not parent.exists():
        try:
            parent.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            return f"Error creating parent directory {parent}: {exc}"
    if path.exists() and path.is_dir():
        return f"Error: path is a directory: {file_path}"

    try:
        with path.open("w", encoding="utf-8") as fh:
            fh.write(content)
    except OSError as exc:
        return f"Error writing file {file_path}: {exc}"

    return f"write to `{file_path}` successfully."




@function_tool
async def write_file(file_path: str, content: str) -> str:
    """Write a file by overwriting its entire contents.

    Use this tool when you want to create a new file or fully replace an existing file.
    For incremental edits, prefer `edit_file` to avoid accidentally losing content.

    Notes:
        - `file_path` must be an absolute path inside the workspace root.
        - Parent directories are created automatically if they do not exist.

    Args:
        file_path: Absolute path to the file inside the workspace.
        content: Full file content to write (overwrites existing file).

    Returns:
        A success message, or an error string.
    """
    if not os.path.isabs(file_path):
        return "Error: file_path must be an absolute path"

    path = Path(file_path).resolve()
    ROOT = Path.cwd().resolve()

    if ROOT not in path.parents and path != ROOT:
        return (
            "Error: file_path must be inside the workspace root directory. "
            f"ROOT={ROOT}, got={path}"
        )

    # Offload blocking disk I/O to a thread to avoid blocking the event loop.
    return await asyncio.to_thread(_write_file, file_path, content)
