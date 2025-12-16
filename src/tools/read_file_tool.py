from agents import function_tool
import asyncio
import os
from pathlib import Path


def _read_from_file(file_path: str, start_line: int, limit: int | None) -> str:
    """Synchronous helper that actually reads the file contents."""
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


ROOT = Path.cwd().resolve()


@function_tool
async def read_file(file_path: str, start_line: int, limit: int | None = None) -> str:
    """Read part of a file using an absolute path, starting line, and optional line limit.

    Output format: line number right-aligned in 6 columns, then `|`, then content (e.g., `     1|line`).
    """
    if not os.path.isabs(file_path):
        return "Error: file_path must be an absolute path"

    path = Path(file_path).resolve()
    if ROOT not in path.parents and path != ROOT:
        return (
            "Error: file_path must be inside the workspace root directory. "
            f"ROOT={ROOT}, got={path}"
        )

    # Offload blocking disk I/O to a thread to avoid blocking the event loop.
    return await asyncio.to_thread(_read_from_file, file_path, start_line, limit)
