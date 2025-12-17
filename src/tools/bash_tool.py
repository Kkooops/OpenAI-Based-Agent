from agents import function_tool
import asyncio

@function_tool
async def bash(shell_command: str, timeout: int) -> str:
    """Run a shell command and return stdout/stderr.

    Use this tool for command-line operations (e.g. `git`, `python`, `pytest`).
    For reading/writing/editing files, prefer dedicated file tools.
    For searching content or finding files, prefer dedicated `grep` or `glob` tools.

    Args:
        shell_command: Command string to execute in a shell.
        timeout: Timeout in seconds for the command execution.

    Returns:
        A success message including stdout/stderr, or an error string.

    Examples:
        - `git status`
        - `python -m py_compile src/main.py`
    """
    process = await asyncio.create_subprocess_shell(
            shell_command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
    
    try:
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        process.kill()
        error_msg = f"The Command `{shell_command}` timed out after {timeout} seconds"
        return error_msg

    # Decode output
    stdout_text = stdout.decode("utf-8", errors="replace")
    stderr_text = stderr.decode("utf-8", errors="replace")

    # Create result (content auto-formatted by model_validator)
    is_success = process.returncode == 0
    error_msg = None
    if not is_success:
        error_msg = f"The Command `{shell_command}` failed with exit code {process.returncode}"
        if stderr_text:
            error_msg += f"\n{stderr_text.strip()}"
        return error_msg

    return f"The Command `{shell_command}` exectued successfully.\nThe StdOut:\n{stdout_text}\n\nThe StdErr:\n{stderr_text}\n"
