from agents import function_tool
import asyncio
import os
from pathlib import Path


def _edit_file(file_path: str, old_content: str, new_content: str) -> str:
    """Replace a unique substring in a file (synchronous helper).

    This helper performs a single, exact string replacement. It requires `old_content`
    to appear exactly once to avoid unintended edits.

    Args:
        file_path: Absolute path to the target file.
        old_content: Exact substring to be replaced (must be unique within the file).
        new_content: Replacement substring.

    Returns:
        Success message or an error string.
    """
    path = Path(file_path)
    if not path.exists():
        return f"Error: file does not exist: {file_path}"
    if not path.is_file():
        return f"Error: path is not a file: {file_path}"

    try:
        content = path.read_text(encoding="utf-8")
    except OSError as exc:
        return f"Error reading file {file_path}: {exc}"

    count = content.count(old_content)
    if count == 0:
        return "Error: old_content not found in file"
    if count > 1:
        return "Error: old_content is not unique in file, please change `old_content` input argument to Guaranteed to be unique."

    updated_content = content.replace(old_content, new_content, 1)

    try:
        path.write_text(updated_content, encoding="utf-8")
    except OSError as exc:
        return f"Error writing file {file_path}: {exc}"

    return f"edit `{file_path}` successfully."



@function_tool
async def edit_file(file_path: str, old_content: str, new_content: str) -> str:
    """Update an existing file by replacing a unique substring.

    Use this tool to modify an existing file without overwriting the whole file.
    `old_content` must match exactly and must be unique in the file, otherwise the
    tool will refuse to apply the change.

    Notes:
        - `file_path` must be an absolute path inside the workspace root.
        - This tool performs a single replacement (first occurrence) after uniqueness check.

    Args:
        file_path: Absolute path to a file inside the workspace.
        old_content: Exact substring to replace (must be unique in the file).
        new_content: Replacement substring.

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
    return await asyncio.to_thread(_edit_file, file_path, old_content, new_content)
