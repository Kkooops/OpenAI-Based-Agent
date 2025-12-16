import asyncio
from agents import Agent, Runner, set_default_openai_client, set_default_openai_key, set_default_openai_api
from openai import AsyncOpenAI
from agents import set_tracing_disabled
from tools import *
from pathlib import Path

# === CLI 样式相关 ===
from colorama import init as colorama_init, Fore, Style

# 初始化 colorama（在 Windows 上也能正常显示颜色）
colorama_init(autoreset=True)

# 统一的前缀图标 & 颜色
USER_PREFIX = f"{Fore.CYAN}👤 You{Style.RESET_ALL}"
ASSISTANT_PREFIX = f"{Fore.GREEN}🤖 Assistant{Style.RESET_ALL}"
SYSTEM_PREFIX = f"{Fore.MAGENTA}⚙ System{Style.RESET_ALL}"
ERROR_PREFIX = f"{Fore.RED}❌ Error{Style.RESET_ALL}"

# 输入提示符（放在同一行，方便用户输入）
INPUT_PROMPT = f"{USER_PREFIX}{Fore.CYAN} › {Style.RESET_ALL}"

import os

openaiClient = AsyncOpenAI(
    base_url=os.environ["KK_OPENAI_BASE_URL"],
    api_key=os.environ["KK_OPENAI_API_KEY"],
)
set_default_openai_client(openaiClient)
set_default_openai_api("chat_completions")
set_tracing_disabled(True)


async def cli(work_dir=None):
    if work_dir is None:
        work_dir = Path.cwd()

    # 入口欢迎信息
    print(
        f"{SYSTEM_PREFIX}  已进入交互模式\n"
        f"   工作目录: {Fore.YELLOW}{work_dir}{Style.RESET_ALL}\n"
        f"   提示：输入问题后回车，与 {ASSISTANT_PREFIX} 对话；按 Ctrl+C 退出。\n"
    )

    system_prompt = ""
    # 使用当前文件的绝对路径来定位 system_prompt.md，避免受执行目录影响
    base_dir = Path(__file__).resolve().parent.parent  # 项目根目录
    system_prompt_path = base_dir / "src" / "system_prompt.md"
    with system_prompt_path.open('r', encoding='utf-8') as f:
        system_prompt = f.read()

    system_prompt = system_prompt.replace('{work_dir}', str(work_dir))

    agent = Agent(
        name="Assistant",
        model="gpt-5.1",
        instructions=system_prompt,
        tools=[
            bash,
            read_file,
            write_file,
            edit_file
        ]
    )
    import sys

    messages = []

    while True:
        try:
            # ① 手动打印提示符，并用 readline 读取
            sys.stdout.write(INPUT_PROMPT)
            sys.stdout.flush()
            user_input = sys.stdin.readline()

            if user_input.rstrip("\n") == "":
                continue

            user_input = user_input.rstrip("\n")

            messages.append({
                "role": "user",
                "content": user_input
            })

            # ② 调用模型
            print(f"\n{ASSISTANT_PREFIX} 正在思考，请稍候...\n")

            result = await Runner.run(agent, messages)
            last_result_content = result.final_output

            # ③ 美化后的模型输出
            print(f"{ASSISTANT_PREFIX}:\n{Fore.GREEN}{'-' * 60}{Style.RESET_ALL}")
            print(last_result_content)
            print(f"{Fore.GREEN}{'-' * 60}{Style.RESET_ALL}\n")

            last_messages = result.to_input_list()
            messages = last_messages

        except KeyboardInterrupt:
            print(f"\n{SYSTEM_PREFIX} 已退出对话，再见！")
            break
        except Exception as e:
            print(f"\n{ERROR_PREFIX} {e}\n")


if __name__ == "__main__":
    asyncio.run(cli())
