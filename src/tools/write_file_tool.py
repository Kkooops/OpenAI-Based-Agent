from agents import function_tool
import asyncio
import os
from pathlib import Path


def _write_file(file_path: str, content: str) -> str:
    """
    :param file_path: 文件绝对路径
    :param content: 写入内容
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
    """写入文件，这个工具会把写入文件进行覆盖，当使用编辑文件时不要调用这个工具
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
