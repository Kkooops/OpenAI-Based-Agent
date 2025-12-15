import asyncio
from agents import Agent, Runner, set_default_openai_client, set_default_openai_key, set_default_openai_api
from openai import AsyncOpenAI
from agents import function_tool, set_tracing_disabled


openaiClient = AsyncOpenAI()
set_default_openai_client(openaiClient)
set_default_openai_api("chat_completions")
set_tracing_disabled(True)


@function_tool
async def bash(shell_command: str, timeout: int) -> str:
    """Execute bash commands in foreground or background.
For terminal operations like git, npm, docker, etc. DO NOT use for file operations - use specialized tools.

Parameters:
  - command (required): Bash command to execute
  - timeout (optional): Timeout in seconds (default: 120, max: 600) for foreground commands
  - run_in_background (optional): Set true for long-running commands (servers, etc.)

Tips:
  - Quote file paths with spaces: cd "My Documents"
  - Chain dependent commands with &&: git add . && git commit -m "msg"
  - Use absolute paths instead of cd when possible
  - For background commands, monitor with bash_output and terminate with bash_kill

Examples:
  - git status
  - npm test
  - python3 -m http.server 8080 (with run_in_background=true)"""
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

async def main():
    agent = Agent(
        name="Assistant",
        model="gpt-5.1",
        instructions="你是人工智能助手，具有一系列工具可以与外界进行交互，来帮助用户执行任务。",
        tools=[bash]
    )
    messages = []
    while True:
        user_input = input("You:")
        messages.append({
            "role": "user",
            "content": user_input
        })
        result = await Runner.run(agent, messages)
        last_result_content = result.final_output
        print(last_result_content)
        last_messages = result.to_input_list()
        messages = last_messages



if __name__ == "__main__":
    asyncio.run(main())