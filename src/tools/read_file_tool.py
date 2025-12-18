from agents import function_tool
import asyncio
import os
from pathlib import Path


def _read_from_file(file_path: str, start_line: int, limit: int | None) -> str:
    """Read file contents synchronously and format with line numbers.

    Args:
        file_path: Absolute file path.
        start_line: 1-based start line number.
        limit: Optional max number of lines to read; `None` means read to EOF.

    Returns:
        Formatted text where each line is prefixed with a right-aligned line number
        in 6 columns, followed by `|` (e.g., `     1|line`), or an error string.
    """
    path = Path(file_path)
    if not path.exists():
        return f"Error: file does not exist: {file_path}"
    if not path.is_file():
        return f"Error: path is not a file: {file_path}"
    if start_line < 1:
        return "Error: start_line must be greater than or equal to 1"
    if limit is not None and limit < 0:
        return "Error: limit must be None or a non-negative integer"

    try:
        with path.open("r", encoding="utf-8", errors="replace") as fh:
            # Skip lines before the requested starting line
            for _ in range(start_line - 1):
                skipped = fh.readline()
                if skipped == "":
                    return ""  # Requested start is beyond EOF

            formatted_lines: list[str] = []
            current_line = start_line

            if limit is None:
                for line in fh:
                    formatted_lines.append(f"{current_line:>6}|{line.rstrip(chr(13)+chr(10))}")
                    current_line += 1
            else:
                for _ in range(limit):
                    line = fh.readline()
                    if line == "":
                        break
                    formatted_lines.append(f"{current_line:>6}|{line.rstrip(chr(13)+chr(10))}")
                    current_line += 1

            return "\n".join(formatted_lines)
    except OSError as exc:
        return f"Error reading file {file_path}: {exc}"




@function_tool
async def read_file(file_path: str, start_line: int, limit: int | None = None) -> str:
    """Read a slice of a text file (for code/context lookup).
    **Important**: Must Not invoke parallelly like `{"file_path":"xx","start_line":1}{"file_path":"xxxx","start_line":1}{"file_path":"xxxx","start_line":1}`

    Notes:
        - `file_path` must be an absolute path inside the workspace root.
        - `start_line` is 1-based.
        - Output lines are prefixed as `     1|content` to make patching easier.

    Args:
        file_path: Absolute path to a file inside the workspace.
        start_line: 1-based start line number.
        limit: Optional max number of lines; `None` means read to EOF.

    Returns:
        The formatted file slice, or an error string.
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
    return await asyncio.to_thread(_read_from_file, file_path, start_line, limit)
