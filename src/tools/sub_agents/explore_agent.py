from agents import Agent, Runner, ModelSettings, function_tool
import os
from pathlib import Path

from ..read_file_tool import read_file
from ..search_tool import grep, glob


def _validate_root_dir(root_dir: str | None) -> tuple[str | None, str | None]:
    if root_dir is None:
        return str(Path.cwd().resolve()), None
    if not isinstance(root_dir, str) or not root_dir.strip():
        return None, "Error: root_dir must be a non-empty string"
    if not os.path.isabs(root_dir):
        return None, "Error: root_dir must be an absolute path"
    root_path = Path(root_dir).resolve()
    workspace_root = Path.cwd().resolve()
    if workspace_root not in root_path.parents and root_path != workspace_root:
        return (
            None,
            "Error: root_dir must be inside the workspace root directory. "
            f"ROOT={workspace_root}, got={root_path}",
        )
    return str(root_path), None


@function_tool
async def explore_agent(
    query: str,
    root_dir: str | None = None
) -> str:
    """Sub-agent for exploration and search tasks (read-only).

    Args:
        query: Task or question for exploration.
        root_dir: Optional absolute directory to explore under (defaults to workspace root).
        max_turns: Max turns for the sub-agent.

    Returns:
        Natural language summary from the sub-agent.
    """
    max_turns = 66
    if not isinstance(query, str) or not query.strip():
        return "Error: query must be a non-empty string"

    resolved_root, error = _validate_root_dir(root_dir)
    if error:
        return error

    instructions = (
        "You are an explore/search sub-agent"
        "**Important**: You only have tools: read_file, grep, glob. And you only use `read_file` / `grep` / `glob` for read-only analysis.\n"
        "Your goal is to quickly locate relevant files and key code, then provide a clear, concise conclusion."
        "If you need more context, use `grep` or `glob` to narrow the scope first, then `read_file` for deep reading."
        "**Important** You Must Not use `bash`, Beacause you **Only** have tools: read_file, grep, glob. Must Not use other tools !!!"
        "Your final output should include: key file paths, relevant functions/locations, and a brief conclusion/next-step suggestion."
    )

    agent = Agent(
        name="Explore SubAgent",
        model="mimo-v2-flash",
        instructions=instructions,
        tools=[read_file, grep, glob],
    )

    prompt = (
        f"<explore_goal>\n{query}\n</explore_goal>\n"
        f"<base_dir>\n{resolved_root}\n</base_dir>\n"
        "Please search within the base directory and summarize your findings."
    )

    result = await Runner.run(agent, prompt, max_turns=max_turns)
    return str(getattr(result, "final_output", result))
