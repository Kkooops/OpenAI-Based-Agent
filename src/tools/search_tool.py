from agents import function_tool
import asyncio
import os
import re
from fnmatch import fnmatch
from pathlib import Path
from pathlib import PurePath


_BINARY_SNIFF_BYTES = 2048

_DEFAULT_EXCLUDE_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".venv",
    "venv",
    "__pycache__",
    "node_modules",
    ".mypy_cache",
    ".pytest_cache",
}

_DEFAULT_EXCLUDE_FILE_GLOBS = {
    "*.pyc",
    "*.pyo",
    "*.png",
    "*.jpg",
    "*.jpeg",
    "*.gif",
    "*.pdf",
    "*.zip",
    "*.gz",
    "*.tar",
    "*.tgz",
    "*.woff",
    "*.woff2",
    "*.ico",
    "*.mp4",
    "*.mp3",
    "*.mov",
    "*.sqlite",
    "*.db",
}


def _is_probably_binary(path: Path) -> bool:
    """二进制文件的简单启发式判断：如果包含 NUL 字节，则认为是二进制并跳过。

    目的：避免扫描图片/压缩包等内容，减少无意义输出并提升速度。
    """
    try:
        with path.open("rb") as fh:
            chunk = fh.read(_BINARY_SNIFF_BYTES)
    except OSError:
        return True
    return b"\x00" in chunk


def _clean_str_list(values: list[str] | None) -> list[str]:
    """清洗可选字符串列表：strip、跳过空值和非字符串。"""
    if not values:
        return []
    cleaned: list[str] = []
    for value in values:
        if not isinstance(value, str):
            continue
        stripped = value.strip()
        if stripped:
            cleaned.append(stripped)
    return cleaned


def _clean_split_str(value: str | None, *, split_commas: bool) -> list[str]:
    """清洗并拆分单个字符串输入，返回字符串列表。

    - 默认按换行拆分；
    - 当 split_commas=True 时，也会按逗号拆分（适用于 glob/目录列表）。
    """
    if value is None or not isinstance(value, str):
        return []
    raw = value.strip()
    if not raw:
        return []

    parts: list[str] = []
    for line in raw.splitlines():
        if split_commas:
            candidates = line.split(",")
        else:
            candidates = [line]
        for item in candidates:
            stripped = item.strip()
            if stripped:
                parts.append(stripped)
    return parts


def _compile_patterns(
    patterns: list[str], *, case_sensitive: bool
) -> tuple[list[tuple[str, re.Pattern[str]]], str | None]:
    """预编译正则；返回 (compiled, error_message)。"""
    flags = re.MULTILINE | (0 if case_sensitive else re.IGNORECASE)
    compiled: list[tuple[str, re.Pattern[str]]] = []
    for pattern in patterns:
        try:
            compiled.append((pattern, re.compile(pattern, flags=flags)))
        except re.error as exc:
            return [], f"Error: invalid regex pattern `{pattern}`: {exc}"
    return compiled, None


def _should_match_any_glob(rel_path: str, name: str, globs: list[str] | tuple[str, ...]) -> bool:
    """任意 glob 命中相对路径或文件名则返回 True。"""
    return any(fnmatch(rel_path, g) or fnmatch(name, g) for g in globs)


def _iter_candidate_files(
    root_path: Path,
    *,
    include_globs: list[str],
    exclude_dir_names: set[str],
    exclude_file_globs: tuple[str, ...],
    max_file_size_kb: int,
):
    """遍历并产出通过过滤条件的候选文件（include/exclude/大小/二进制判断）。"""
    for dirpath, dirnames, filenames in os.walk(root_path):
        # 原地剪枝：让 os.walk 不进入这些目录递归
        dirnames[:] = [d for d in dirnames if d not in exclude_dir_names]

        for filename in filenames:
            file_path = Path(dirpath) / filename

            try:
                rel_path = str(file_path.relative_to(root_path))
            except ValueError:
                rel_path = str(file_path)

            if include_globs and not _should_match_any_glob(rel_path, filename, include_globs):
                continue
            if _should_match_any_glob(rel_path, filename, exclude_file_globs):
                continue

            try:
                if not file_path.is_file():
                    continue
            except OSError:
                continue

            try:
                size = file_path.stat().st_size
            except OSError:
                continue
            if size > max_file_size_kb * 1024:
                continue
            if _is_probably_binary(file_path):
                continue

            yield file_path


def _search_sync(
    patterns: list[str],
    root_dir: str,
    include_globs: list[str] | None,
    exclude_dirs: list[str] | None,
    exclude_globs: list[str] | None,
    case_sensitive: bool,
    max_results: int,
    max_file_size_kb: int,
) -> str:
    """同步搜索实现（通过 asyncio.to_thread 在线程里跑，避免阻塞事件循环）。"""
    root_path = Path(root_dir)
    if not root_path.exists():
        return f"Error: root_dir does not exist: {root_dir}"
    if not root_path.is_dir():
        return f"Error: root_dir is not a directory: {root_dir}"

    include_globs_list = _clean_str_list(include_globs)
    exclude_globs_list = _clean_str_list(exclude_globs)
    exclude_dir_set = set(_DEFAULT_EXCLUDE_DIRS)
    exclude_dir_set |= set(_clean_str_list(exclude_dirs))

    exclude_file_globs = set(_DEFAULT_EXCLUDE_FILE_GLOBS)
    exclude_file_globs |= set(exclude_globs_list)

    compiled_patterns, error = _compile_patterns(patterns, case_sensitive=case_sensitive)
    if error:
        return error
    exclude_file_globs_tuple = tuple(exclude_file_globs)

    results: list[str] = []
    matched_files: set[str] = set()

    for file_path in _iter_candidate_files(
        root_path,
        include_globs=include_globs_list,
        exclude_dir_names=exclude_dir_set,
        exclude_file_globs=exclude_file_globs_tuple,
        max_file_size_kb=max_file_size_kb,
    ):
        try:
            with file_path.open("r", encoding="utf-8", errors="replace") as fh:
                for line_no, line in enumerate(fh, start=1):
                    # 一行可能同时匹配多个 pattern：按 (line, pattern) 维度输出多条结果
                    for raw_pattern, compiled in compiled_patterns:
                        if not compiled.search(line):
                            continue
                        results.append(
                            f"{file_path}:{line_no}: [{raw_pattern}] {line.rstrip('\r\n')}"
                        )
                        matched_files.add(str(file_path))
                        if len(results) >= max_results:
                            summary = (
                                f"Found {len(results)} matches (limit reached) in "
                                f"{len(matched_files)} files under {root_path}."
                            )
                            return summary + "\n" + "\n".join(results)
        except OSError:
            continue

    if not results:
        return f"No matches found under {root_path}."

    summary = f"Found {len(results)} matches in {len(matched_files)} files under {root_path}."
    return summary + "\n" + "\n".join(results)


@function_tool
async def grep(
    patterns: str,
    root_dir: str | None = None,
    include_globs: str | None = None,
    exclude_dirs: str | None = None,
    exclude_globs: str | None = None,
    case_sensitive: bool = True,
    max_results: int = 200,
    max_file_size_kb: int = 2048,
) -> str:
    """Search file contents under a directory using regular expressions (grep-like).

    Notes:
        - `patterns` is a single string; provide multiple regex patterns separated by newlines.
          Avoid comma-separated patterns to prevent breaking valid regex syntax.
        - `root_dir` defaults to the current working directory and must be an absolute path
          inside the workspace root.
        - `include_globs` / `exclude_dirs` / `exclude_globs` are optional filters; provide
          multiple values separated by commas or newlines.
        - The scan skips common generated/vendor directories and common binary file types.

    Args:
        patterns: One or more regex patterns (newline-separated).
        root_dir: Absolute directory to search under (defaults to workspace root).
        include_globs: Optional file include glob(s), e.g. `*.py,src/*`.
        exclude_dirs: Optional directory name(s) to skip, e.g. `node_modules,.git`.
        exclude_globs: Optional file exclude glob(s), e.g. `*.lock,dist/*`.
        case_sensitive: Whether regex matching is case-sensitive.
        max_results: Max number of matching lines to return.
        max_file_size_kb: Max file size to scan (in KB).

    Returns:
        A summary line followed by matches in the format:
        `/abs/path/to/file:line: [pattern] content`, or an error string.
    """
    patterns_list = _clean_split_str(patterns, split_commas=False)
    if not patterns_list:
        return "Error: patterns must be a non-empty string (optionally newline-separated)"
    if max_results <= 0:
        return "Error: max_results must be greater than 0"
    if max_file_size_kb <= 0:
        return "Error: max_file_size_kb must be greater than 0"

    if root_dir is None:
        root_dir = str(Path.cwd().resolve())
    if not os.path.isabs(root_dir):
        return "Error: root_dir must be an absolute path"

    root_path = Path(root_dir).resolve()
    ROOT = Path.cwd().resolve()
    # 安全限制：禁止扫描 workspace 之外的目录
    if ROOT not in root_path.parents and root_path != ROOT:
        return (
            "Error: root_dir must be inside the workspace root directory. "
            f"ROOT={ROOT}, got={root_path}"
        )

    include_globs_list = _clean_split_str(include_globs, split_commas=True)
    exclude_dirs_list = _clean_split_str(exclude_dirs, split_commas=True)
    exclude_globs_list = _clean_split_str(exclude_globs, split_commas=True)

    return await asyncio.to_thread(
        _search_sync,
        patterns_list,
        str(root_path),
        include_globs_list,
        exclude_dirs_list,
        exclude_globs_list,
        case_sensitive,
        max_results,
        max_file_size_kb,
    )


def _is_workspace_root_or_child(path: Path) -> bool:
    root = Path.cwd().resolve()
    return path == root or root in path.parents


def _rel_posix(path: Path, root_path: Path) -> str:
    try:
        rel = path.relative_to(root_path)
    except ValueError:
        rel = path
    return rel.as_posix()


@function_tool
async def glob(
    pattern: str,
    path: str | None = None,
    max_results: int = 500,
) -> str:
    """Find files under a directory using a glob pattern (file paths only).

    Notes:
        - `pattern` supports `*` / `?` / `**`.
        - If `pattern` contains a path separator (`/`), it is treated as a path pattern
          relative to `path` (e.g. `src/**/*.jsx`).
        - If `pattern` does not contain a path separator, it is applied recursively as a
          filename/pattern match (e.g. `*.py`).
        - Default exclude dirs (e.g. `.git`, `node_modules`) are skipped.

    Args:
        pattern: Glob pattern, e.g. `**/*.ts` or `src/**/*.jsx`.
        path: Absolute directory to search under (defaults to current working directory).
        max_results: Max number of file paths to return.

    Returns:
        A summary line followed by one absolute file path per line, or an error string.
    """
    if not isinstance(pattern, str) or not pattern.strip():
        return "Error: pattern must be a non-empty string"
    if max_results <= 0:
        return "Error: max_results must be greater than 0"

    if path is None:
        path = str(Path.cwd().resolve())
    if not os.path.isabs(path):
        return "Error: path must be an absolute path"

    root_path = Path(path).resolve()
    if not _is_workspace_root_or_child(root_path):
        return (
            "Error: path must be inside the workspace root directory. "
            f"ROOT={Path.cwd().resolve()}, got={root_path}"
        )
    if not root_path.exists():
        return f"Error: path does not exist: {path}"
    if not root_path.is_dir():
        return f"Error: path is not a directory: {path}"

    exclude_dir_set = set(_DEFAULT_EXCLUDE_DIRS)
    results: list[str] = []

    pattern_norm = pattern.strip().replace("\\", "/")
    # 如果 pattern 不包含路径分隔符，使用递归匹配（更符合“按文件名查找”的直觉）。
    # 如果包含路径分隔符，则按相对 root_path 的路径模式匹配（例如 src/**/*.jsx）。
    if "/" in pattern_norm:
        iterator = root_path.glob(pattern_norm)
    else:
        iterator = root_path.rglob(pattern_norm)

    for file_path in iterator:
        try:
            is_dir = file_path.is_dir()
            is_file = file_path.is_file()
            if not is_dir and not is_file:
                continue
        except OSError:
            continue

        try:
            rel_parts = file_path.relative_to(root_path).parts
        except ValueError:
            rel_parts = PurePath(file_path).parts

        # 过滤默认排除目录（如 .git、node_modules）
        if any(part in exclude_dir_set for part in rel_parts[:-1]):
            continue

        results.append(str(file_path))
        if len(results) >= max_results:
            summary = f"Found {len(results)} files (limit reached) under {root_path}."
            return summary + "\n" + "\n".join(results)

    if not results:
        return f"No files matched under {root_path}."
    summary = f"Found {len(results)} files under {root_path}."
    return summary + "\n" + "\n".join(results)
