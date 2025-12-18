import asyncio
import json
import re
from agents import (
    Agent,
    Runner,
    set_default_openai_client,
    set_default_openai_key,
    set_default_openai_api,
    RawResponsesStreamEvent,
    RunItemStreamEvent,
)
from openai import AsyncOpenAI
from agents import set_tracing_disabled, ModelSettings
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
TOOL_PREFIX = f"{Fore.YELLOW}🛠 Tool{Style.RESET_ALL}"

# 输入提示符（放在同一行，方便用户输入）
INPUT_PROMPT = f"{USER_PREFIX}{Fore.CYAN} ➤ {Style.RESET_ALL}"

import os

openaiClient = AsyncOpenAI(
    base_url="https://api.gptbest.vip/v1",
    api_key="sk-LWN1lU2Qg4spKQPmQWg1kKHTX9tgNSY2qhgAfsZM9wH1Re9u",
)
set_default_openai_client(openaiClient)
set_default_openai_api("chat_completions")
# set_tracing_disabled(True)
set_default_openai_key(os.environ["KK_OPENAI_TRACE_KEY"])

def visible_len(s):
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return len(ansi_escape.sub('', s))

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
        name="OAI-Based CodeAgent",
        model="gemini-3-flash-preview",
        instructions=system_prompt,
        model_settings=ModelSettings(
            reasoning={"effort": "low"},
            parallel_tool_calls=False
        ),
        tools=[
            bash,
            read_file,
            write_file,
            edit_file,
            grep, glob,
            think
        ]
    )
    import sys

    messages = []
    BOX_WIDTH = 80

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

            # ③ 美化后的模型输出
            print(f"{ASSISTANT_PREFIX}:\n{Fore.GREEN}{'-' * 60}{Style.RESET_ALL}")

            result = Runner.run_streamed(agent, messages, max_turns=80)

            async for event in result.stream_events():
                if isinstance(event, RawResponsesStreamEvent):
                    if event.data.type == "response.output_text.delta":
                        print(event.data.delta, end="", flush=True)
                    elif event.data.type == "response.refusal.delta":
                        print(event.data.delta, end="", flush=True)
                elif isinstance(event, RunItemStreamEvent):
                    if event.item.type == "tool_call_item":
                         tool_name = event.item.raw_item.name
                         tool_args = getattr(event.item.raw_item, "arguments", "")
                         
                         # 打印工具调用边框
                         print(f"\n{Fore.YELLOW}╭{'─' * (BOX_WIDTH - 2)}╮{Style.RESET_ALL}")
                         
                         # Tool Name Line
                         header_content = f" {TOOL_PREFIX}: {Fore.GREEN}{tool_name}{Style.RESET_ALL}"
                         padding = BOX_WIDTH - 2 - visible_len(header_content)
                         if padding < 0: padding = 0
                         print(f"{Fore.YELLOW}│{Style.RESET_ALL}{header_content}{' ' * padding}{Fore.YELLOW}│{Style.RESET_ALL}")
                         
                         try:
                             args_dict = json.loads(tool_args)
                             if isinstance(args_dict, dict):
                                 for k, v in args_dict.items():
                                     # Truncate value to fit in box
                                     # Available width: BOX_WIDTH - 2 (borders) - 3 (indent) - len(k) - 2 (": ")
                                     max_val_len = BOX_WIDTH - 7 - len(k)
                                     val_str = str(v).replace('\n', '\\n')
                                     if len(val_str) > max_val_len:
                                         val_str = val_str[:max_val_len-3] + "..."
                                     
                                     line_content = f"   {Fore.CYAN}{k}{Style.RESET_ALL}: {Fore.WHITE}{val_str}{Style.RESET_ALL}"
                                     padding = BOX_WIDTH - 2 - visible_len(line_content)
                                     if padding < 0: padding = 0
                                     print(f"{Fore.YELLOW}│{Style.RESET_ALL}{line_content}{' ' * padding}{Fore.YELLOW}│{Style.RESET_ALL}")
                             else:
                                 # Fallback for non-dict JSON
                                 val_str = str(tool_args).replace('\n', '\\n')
                                 max_len = BOX_WIDTH - 5
                                 if len(val_str) > max_len: val_str = val_str[:max_len-3] + "..."
                                 line_content = f"   {Fore.WHITE}{val_str}{Style.RESET_ALL}"
                                 padding = BOX_WIDTH - 2 - visible_len(line_content)
                                 if padding < 0: padding = 0
                                 print(f"{Fore.YELLOW}│{Style.RESET_ALL}{line_content}{' ' * padding}{Fore.YELLOW}│{Style.RESET_ALL}")

                         except:
                             if tool_args:
                                 val_str = str(tool_args).replace('\n', '\\n')
                                 max_len = BOX_WIDTH - 5
                                 if len(val_str) > max_len: val_str = val_str[:max_len-3] + "..."
                                 line_content = f"   {Fore.WHITE}{val_str}{Style.RESET_ALL}"
                                 padding = BOX_WIDTH - 2 - visible_len(line_content)
                                 if padding < 0: padding = 0
                                 print(f"{Fore.YELLOW}│{Style.RESET_ALL}{line_content}{' ' * padding}{Fore.YELLOW}│{Style.RESET_ALL}")
                         
                         print(f"{Fore.YELLOW}╰{'─' * (BOX_WIDTH - 2)}╯{Style.RESET_ALL}")

            print(f"\n{Fore.GREEN}{'-' * 60}{Style.RESET_ALL}\n")

            last_messages = result.to_input_list()
            messages = last_messages

        except KeyboardInterrupt:
            print(f"\n{SYSTEM_PREFIX} 已退出对话，再见！")
            break
        except Exception as e:
            print(f"\n{ERROR_PREFIX} {e}\n")


if __name__ == "__main__":
    asyncio.run(cli())
