from agents import function_tool
import asyncio
import json
import os
from pathlib import Path

_DEFAULT_STORE_NAME = ".agent_todo.json"
_ALLOWED_STATUS = {"pending", "in_progress", "done"}


def _resolve_store_path(file_path: str | None) -> tuple[Path | None, str | None]:
    root = Path.cwd().resolve()
    if file_path is None:
        return root / _DEFAULT_STORE_NAME, None
    if not os.path.isabs(file_path):
        return None, "Error: file_path must be an absolute path"
    path = Path(file_path).resolve()
    if root not in path.parents and path != root:
        return None, (
            "Error: file_path must be inside the workspace root directory. "
            f"ROOT={root}, got={path}"
        )
    return path, None


def _load_items(path: Path) -> tuple[list[dict], str | None]:
    if not path.exists():
        return [], None
    if not path.is_file():
        return [], f"Error: path is not a file: {path}"
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        return [], f"Error reading file {path}: {exc}"
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        return [], f"Error: invalid JSON in {path}: {exc}"
    if not isinstance(data, list):
        return [], f"Error: todo store must be a list, got {type(data).__name__}"
    cleaned: list[dict] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        item_id = item.get("id")
        content = item.get("content")
        status = item.get("status", "pending")
        if not isinstance(item_id, int):
            continue
        if not isinstance(content, str) or not content.strip():
            continue
        if status not in _ALLOWED_STATUS:
            status = "pending"
        cleaned.append({"id": item_id, "content": content, "status": status})
    cleaned.sort(key=lambda x: x["id"])
    return cleaned, None


def _save_items(path: Path, items: list[dict]) -> str | None:
    try:
        path.write_text(json.dumps(items, ensure_ascii=True, indent=2), encoding="utf-8")
    except OSError as exc:
        return f"Error writing file {path}: {exc}"
    return None


def _next_id(items: list[dict]) -> int:
    if not items:
        return 1
    return max(item["id"] for item in items) + 1


def _format_response(ok: bool, message: str, items: list[dict]) -> str:
    return json.dumps(
        {"ok": ok, "message": message, "items": items},
        ensure_ascii=True,
    )


def _todo_list_sync(
    action: str,
    items_json: str | None,
    ids: list[int] | None,
    file_path: str | None,
) -> str:
    path, error = _resolve_store_path(file_path)
    if error:
        return _format_response(False, error, [])
    assert path is not None

    current_items, error = _load_items(path)
    if error:
        return _format_response(False, error, [])

    action = action.strip().lower() if isinstance(action, str) else ""
    if action not in {"list", "add", "update", "remove", "clear"}:
        return _format_response(False, "Error: invalid action", current_items)

    if action == "list":
        return _format_response(True, "OK", current_items)

    if action == "clear":
        error = _save_items(path, [])
        if error:
            return _format_response(False, error, current_items)
        return _format_response(True, "Cleared", [])

    items: list[dict] | None = None
    if items_json is not None:
        try:
            parsed = json.loads(items_json)
        except json.JSONDecodeError as exc:
            return _format_response(False, f"Error: items_json is invalid JSON: {exc}", current_items)
        if not isinstance(parsed, list):
            return _format_response(False, "Error: items_json must be a JSON array", current_items)
        items = parsed

    if action == "add":
        if not items:
            return _format_response(False, "Error: items must be a non-empty list", current_items)
        next_id = _next_id(current_items)
        added = 0
        for item in items:
            if not isinstance(item, dict):
                continue
            content = item.get("content")
            status = item.get("status", "pending")
            if not isinstance(content, str) or not content.strip():
                continue
            if status not in _ALLOWED_STATUS:
                status = "pending"
            current_items.append(
                {"id": next_id, "content": content.strip(), "status": status}
            )
            next_id += 1
            added += 1
        if added == 0:
            return _format_response(False, "Error: no valid items to add", current_items)
        current_items.sort(key=lambda x: x["id"])
        error = _save_items(path, current_items)
        if error:
            return _format_response(False, error, current_items)
        return _format_response(True, f"Added {added} item(s)", current_items)

    if action == "update":
        if not items:
            return _format_response(False, "Error: items must be a non-empty list", current_items)
        by_id = {item["id"]: item for item in current_items}
        updated = 0
        for patch in items:
            if not isinstance(patch, dict):
                continue
            item_id = patch.get("id")
            if not isinstance(item_id, int) or item_id not in by_id:
                continue
            content = patch.get("content")
            status = patch.get("status")
            if isinstance(content, str) and content.strip():
                by_id[item_id]["content"] = content.strip()
            if isinstance(status, str) and status in _ALLOWED_STATUS:
                by_id[item_id]["status"] = status
            updated += 1
        if updated == 0:
            return _format_response(False, "Error: no valid items to update", current_items)
        current_items = sorted(by_id.values(), key=lambda x: x["id"])
        error = _save_items(path, current_items)
        if error:
            return _format_response(False, error, current_items)
        return _format_response(True, f"Updated {updated} item(s)", current_items)

    if action == "remove":
        if not ids:
            return _format_response(False, "Error: ids must be a non-empty list", current_items)
        remove_ids = {i for i in ids if isinstance(i, int)}
        if not remove_ids:
            return _format_response(False, "Error: ids must contain integers", current_items)
        remaining = [item for item in current_items if item["id"] not in remove_ids]
        removed = len(current_items) - len(remaining)
        if removed == 0:
            return _format_response(False, "Error: no matching ids to remove", current_items)
        error = _save_items(path, remaining)
        if error:
            return _format_response(False, error, current_items)
        return _format_response(True, f"Removed {removed} item(s)", remaining)

    return _format_response(False, "Error: unsupported action", current_items)


@function_tool
async def todo_list(
    action: str,
    items_json: str | None = None,
    ids: list[int] | None = None,
    file_path: str | None = None,
) -> str:
    """Manage a persistent todo list stored in a workspace file.

    Args:
        action: One of `list`, `add`, `update`, `remove`, `clear`.
        items_json: For `add`/`update`, a JSON array string:
            - add: [{"content": str, "status": "pending|in_progress|done" (optional)}]
            - update: [{"id": int, "content": str (optional), "status": str (optional)}]
        ids: For `remove`, a list of integer ids.
        file_path: Optional absolute path to the JSON store file.

    Returns:
        JSON string: {"ok": bool, "message": str, "items": [..]}.
    """
    return await asyncio.to_thread(_todo_list_sync, action, items_json, ids, file_path)
