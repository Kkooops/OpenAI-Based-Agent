from agents import function_tool
import asyncio
import os
from pathlib import Path


def _edit_file(file_path: str, old_content: str, new_content: str) -> str:
    """
    :param file_path: 文件绝对路径
    :param old_content: 旧字符串（待替换内容）
    :param new_content: 新字符串
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
    """
    编辑文件，用于Update文件内容时调用，注意和write_file进行区分，edit_file是在已有文件中进行内容替换完成更新
    old_content是待替换的字符串，这里必须保证old_content是文件中唯一的内容。
    new_content是替换后的字符串
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
