from agents import function_tool

@function_tool
async def think(thought: str) -> str:
    """Record an internal thought for reasoning/debugging (no side effects).

    This tool does not read files, run commands, or fetch new information. It exists
    only to let the agent capture intermediate reasoning or a short working memory
    note during a multi-step task.

    Args:
        thought: The internal note to record.

    Returns:
        An empty string.
    """

    return ""
