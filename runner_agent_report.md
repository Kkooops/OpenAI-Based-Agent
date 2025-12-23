# Runner Agent 包分析报告

**生成时间**: 2025年1月
**包路径**: `/Users/admin/OpenAI-Based-Agent/.venv/lib/python3.12/site-packages/agents/`
**主文件**: `run.py` (85KB)

---

## 目录

1. [概述](#概述)
2. [核心类](#核心类)
3. [配置系统](#配置系统)
4. [结果类型](#结果类型)
5. [生命周期钩子](#生命周期钩子)
6. [护栏系统](#护栏系统)
7. [执行流程](#执行流程)
8. [类关系图](#类关系图)
9. [使用示例](#使用示例)

---

## 概述

`agents` 包是 OpenAI Agent SDK 的核心实现，提供了完整的 Agent 运行框架。主要组件包括：

- **Runner**: 公共 API 入口
- **AgentRunner**: 内部实现类
- **RunConfig**: 配置管理
- **Guardrails**: 安全护栏系统
- **Lifecycle Hooks**: 生命周期钩子系统

---

## 核心类

### 1. Runner 类

**位置**: `run.py:302-524`

**描述**: 公共 API 类，是用户调用的主要入口点。是一个包装器，内部委托给 `DEFAULT_AGENT_RUNNER` 执行实际逻辑。

**核心方法**:

| 方法 | 功能 | 返回类型 |
|------|------|----------|
| `run()` | 异步运行代理工作流 | `RunResult` |
| `run_sync()` | 同步运行代理工作流 | `RunResult` |
| `run_streamed()` | 流式运行代理工作流 | `RunResultStreaming` |

**参数说明**:

```python
Runner.run(
    starting_agent: Agent[Any],
    input: str | list[TResponseInputItem],
    context: RunContextWrapper[Any] | None = None,
    max_turns: int = 10,
    hooks: RunHooksBase | None = None,
    run_config: RunConfig | None = None,
    session: ServerSession | None = None,
) -> RunResult
```

**使用示例**:

```python
from agents import Agent, Runner

agent = Agent(name="MyAgent", instructions="You are a helpful assistant.")
result = Runner.run(agent, "Hello, world!")
print(result.final_output)
```

---

### 2. AgentRunner 类

**位置**: `run.py:527-2020`

**描述**: 内部实现类，包含完整的代理运行逻辑。**注意：此为实验性 API，不建议直接使用。**

**核心方法**:

| 方法 | 功能 |
|------|------|
| `run()` | 异步执行单次代理运行 |
| `run_sync()` | 同步执行代理运行 |
| `run_streamed()` | 流式执行代理运行 |
| `_run_single_turn()` | 执行单轮代理 |
| `_run_single_turn_streamed()` | 流式模式下执行单轮 |
| `_run_input_guardrails()` | 运行输入护栏 |
| `_run_output_guardrails()` | 运行输出护栏 |
| `_get_new_response()` | 获取模型响应 |
| `_get_all_tools()` | 获取所有可用工具 |
| `_get_handoffs()` | 获取可用的 handoff |
| `_get_model()` | 解析并获取模型 |
| `_maybe_filter_model_input()` | 可选地过滤模型输入 |
| `_prepare_input_with_session()` | 准备输入（与会话整合） |
| `_save_result_to_session()` | 保存结果到会话 |

**关键属性**:

```python
class AgentRunner:
    _model: Model | None
    _model_provider: ModelProvider
    _session: ServerSession | None
    _last_agent: Agent[Any]
    _result: RunResult
```

---

## 配置系统

### RunConfig 类

**位置**: `run.py:183-271`

**描述**: 定义整个代理运行的全局配置。

**完整参数**:

```python
@dataclass
class RunConfig:
    # 模型配置
    model: str | Model | None = None
    model_provider: ModelProvider | None = None
    model_settings: ModelSettings | None = None

    # 行为配置
    handoff_input_filter: Callable[[str, Agent[Any], list[RunItem]], dict[str, str]] | None = None
    nest_handoff_history: bool = False

    # 安全护栏
    input_guardrails: list[InputGuardrail] | None = None
    output_guardrails: list[OutputGuardrail] | None = None

    # 追踪配置
    tracing_disabled: bool = False
    trace_include_sensitive_data: bool = False
    workflow_name: str | None = None
    trace_id: str | None = None
    group_id: str | None = None
    trace_metadata: dict[str, str] | None = None

    # 会话配置
    session_input_callback: Callable[[str], Awaitable[str]] | None = None
    call_model_input_filter: Callable[..., Awaitable[ModelInputData]] | None = None
```

### RunOptions TypedDict

**位置**: `run.py:274-299`

**描述**: 定义 `AgentRunner` 方法的参数类型。

```python
class RunOptions(TypedDict, total=False):
    model: str | Model | None
    model_provider: ModelProvider | None
    model_settings: ModelSettings | None
    handoff_input_filter: Callable[[str, Agent[Any], list[RunItem]], dict[str, str]]
    input_guardrails: list[InputGuardrail]
    output_guardrails: list[OutputGuardrail]
    tracing_disabled: bool
    trace_include_sensitive_data: bool
    workflow_name: str
    trace_id: str
    group_id: str
    trace_metadata: dict[str, str]
```

---

## 结果类型

### RunResult 类

**位置**: `result.py:141-174`

**描述**: 同步运行的结果类型。

```python
@dataclass
class RunResult(RunResultBase):
    _last_agent: Agent[Any]
```

**继承自 RunResultBase**:

| 属性 | 类型 | 说明 |
|------|------|------|
| `input` | str \| list[TResponseInputItem] | 原始输入 |
| `new_items` | list[RunItem] | 生成的新项 |
| `raw_responses` | list[ModelResponse] | 原始模型响应 |
| `final_output` | str \| None | 最终输出 |
| `input_guardrail_results` | list[GuardrailResult] | 输入护栏结果 |
| `output_guardrail_results` | list[GuardrailResult] | 输出护栏结果 |
| `tool_input_guardrail_results` | list[ToolInputGuardrailResult] | 工具输入护栏结果 |
| `tool_output_guardrail_results` | list[ToolOutputGuardrailResult] | 工具输出护栏结果 |
| `context_wrapper` | RunContextWrapper \| None | 上下文包装器 |

**新增属性**:

| 属性 | 类型 | 说明 |
|------|------|------|
| `last_agent` | Agent | 最后一个运行的代理 |

---

### RunResultStreaming 类

**位置**: `result.py:177-299`

**描述**: 流式运行的结果类型。

```python
class RunResultStreaming:
    def __init__(
        self,
        current_agent: Agent[Any],
        current_turn: int,
        max_turns: int,
        input: str | list[TResponseInputItem],
        result: RunResult | None = None,
        result茶水
    ```

**完整属性**:

| 属性 | 类型 | 说明 |
|------|------|------|
| `current_agent` | Agent | 当前运行的代理 |
| `current_turn` | int | 当前轮数 |
| `max_turns` | int | 最大轮数 |
| `input` | str \| list[TResponseInputItem] | 输入 |
| `result` | RunResult \| None | 完整结果 |
| `is_complete` | bool | 是否完成 |

**核心方法**:

| 方法 | 功能 |
|------|------|
| `stream_events()` | 异步迭代运行事件 |
| `cancel()` | 取消运行 |

**使用示例**:

```python
result = Runner.run_streamed(agent, "Hello!")

async for event in result.stream_events():
    if event.type == "raw_response_event":
        print(event.data)
    elif event.type == "tool_call_events":
        for tool_event in event.data:
            print(f"Tool: {tool_event.tool_name}")

print(result.result.final_output)
```

---

### SingleStepResult 类

**位置**: `_run_impl.py:233-260`

**描述**: 单步执行的结果。

```python
@dataclass
class SingleStepResult:
    original_input: str | list[TResponseInputItem]
    model_response: ModelResponse
    pre_step_items: list[RunItem]
    new_step_items: list[RunItem]
    next_step: NextStepHandoff | NextStepFinalOutput | NextStepRunAgain
    tool_input_guardrail_results: list[ToolInputGuardrailResult]
    tool_output_guardrail_results: list[ToolOutputGuardrailResult]
```

---

### NextStep* 类

**位置**: `_run_impl.py:217-229`

**描述**: 表示下一步操作的类型。

| 类 | 说明 |
|-----|------|
| `NextStepHandoff(new_agent: Agent)` | 需要 handoff 到新代理 |
| `NextStepFinalOutput(output: str)` | 产生最终输出 |
| `NextStepRunAgain()` | 需要再次运行 |

---

## 生命周期钩子

### RunHooksBase 类

**位置**: `lifecycle.py:13-77`

**描述**: 运行级别钩子，可监听整个代理运行过程。

**完整方法**:

```python
class RunHooksBase:
    async def on_llm_start(
        self,
        agent: Agent[Any],
        messages: list[CoreMessage],
    ) -> None:
        """LLM 调用开始时触发"""

    async def on_llm_end(
        self,
        agent: Agent[Any],
        response: str | None,
        response_token_cnt: int,
    ) -> None:
        """LLM 调用结束时触发"""

    async def on_agent_start(
        self,
        agent: Agent[Any],
    ) -> None:
        """代理开始运行时触发"""

    async def on_agent_end(
        self,
        agent: Agent[Any],
        output: str,
    ) -> None:
        """代理结束时触发"""

    async def on_handoff(
        self,
        source: Agent[Any],
        target: Agent[Any],
    ) -> None:
        """Handoff 发生时触发"""

    async def on_tool_start(
        self,
        agent: Agent[Any],
        tool: Tool,
        input: str,
    ) -> None:
        """工具开始执行时触发"""

    async def on_tool_end(
        self,
        agent: Agent[Any],
        tool: Tool,
        result: str,
    ) -> None:
        """工具执行完成时触发"""
```

**使用示例**:

```python
from agents import RunHooksBase

class MyHooks(RunHooksBase):
    async def on_agent_start(self, agent):
        print(f"Starting agent: {agent.name}")

    async def on_tool_start(self, agent, tool, input):
        print(f"Tool called: {tool.name}")

result = Runner.run(agent, "Calculate 2+2", hooks=MyHooks())
```

---

### AgentHooksBase 类

**位置**: `lifecycle.py:79-147`

**描述**: 特定于代理的钩子，绑定到 `Agent` 对象。

```python
class AgentHooksBase:
    async def on_agent_start(self, agent, context) -> None:
        """代理开始运行时触发"""

    async def on_agent_end(self, agent, context, output) -> None:
        """代理结束时触发"""
```

---

## 护栏系统

### 输入护栏 (InputGuardrail)

**位置**: `guardrail.py`

**描述**: 在代理处理输入之前验证输入。

```python
@dataclass
class InputGuardrail:
    guardrail_function: Callable[..., Awaitable[GuardrailResult]]
    """
    函数签名: async def(input: str, context: RunContextWrapper) -> GuardrailResult
    """
    on_ignore_result: IgnoreResult = "ignore"
```

**使用示例**:

```python
from agents import InputGuardrail, RunContextWrapper

async def validate_input(input: str, context: RunContextWrapper) -> GuardrailResult:
    if "badword" in input.lower():
        return GuardrailResult(triggered=True, output="Input contains inappropriate content")
    return GuardrailResult(triggered=False)

input_guardrails = [
    InputGuardrail(guardrail_function=validate_input)
]

result = Runner.run(agent, "Hello!", input_guardrails=input_guardrails)
```

---

### 输出护栏 (OutputGuardrail)

**位置**: `guardrail.py`

**描述**: 在返回最终输出之前验证输出。

```python
@dataclass
class OutputGuardrail:
    guardrail_function: Callable[..., Awaitable[GuardrailResultOutput]]
    on_ignore_result: IgnoreResult = "ignore"
```

---

## 执行流程

### 同步执行流程

```
Runner.run_sync(starting_agent, input)
    │
    ▼
AgentRunner.run_sync()
    │
    ├── 初始化追踪上下文
    ├── 创建 ServerSession（如果需要）
    │
    ├── 循环执行（最多 max_turns 次）
    │   │
    │   ├── 第一次迭代：运行输入护栏
    │   │
    │   ├── _run_single_turn()
    │   │   │
    │   │   ├── 获取所有工具和 handoffs
    │   │   ├── 调用模型获取响应
    │   │   ├── 处理工具调用和 handoffs
    │   │   │
    │   │   └── 返回 NextStep*
    │   │
    │   ├── 处理 NextStep
    │   │   ├── NextStepFinalOutput → 跳出循环
    │   │   ├── NextStepHandoff → 更新当前代理，继续循环
    │   │   └── NextStepRunAgain → 继续循环
    │   │
    │   └── 执行工具和副作用
    │
    ├── 运行输出护栏
    │
    └── 保存结果到会话
```

### 同步执行流程

```
Runner.run(starting_agent, input)
    │
    ▼
AgentRunner.run()
    │
    └── 异步执行上述流程
```

### 流式执行流程

```
Runner.run_streamed(starting_agent, input)
    │
    ▼
AgentRunner.run_streamed()
    │
    ├── 创建 RunResultStreaming
    │
    ├── 异步迭代事件
    │   │
    │   └── 触发各种事件：
    │       ├── raw_response_event
    │       ├── tool_call_events
    │       ├── tool_call_stream_event
    │       ├── handoff_event
    │       └── agent_updated_event
    │
    └── 返回完整的 RunResult
```

---

## 类关系图

```
┌─────────────────────────────────────────────────────────────┐
│                        用户代码                              │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                        Runner (公共 API)                     │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ run() │ run_sync() │ run_streamed()                 │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
                              │
                    委托 DEFAULT_AGENT_RUNNER
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   AgentRunner (内部实现)                     │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ _run_single_turn() │ _get_new_response()            │    │
│  │ _get_all_tools() │ _run_input_guardrails()          │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
                              │
            ┌─────────────────┼─────────────────┐
            │                 │                 │
            ▼                 ▼                 ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│   RunConfig     │ │   RunHooks      │ │   Guardrails    │
│  (配置)         │ │  (生命周期钩子) │ │  (安全护栏)     │
├─────────────────┤ ├─────────────────┤ ├─────────────────┤
│ model           │ │ on_llm_start   │ │ input_guardrails│
│ model_settings  │ │ on_agent_start │ │ output_guardrails│
│ input_guardrails│ │ on_tool_start  │ │                 │
│ output_guardrails│ │ ...           │ │                 │
└─────────────────┘ └─────────────────┘ └─────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                     RunResult / RunResultStreaming          │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ final_output │ new_items │ raw_responses            │    │
│  │ last_agent │ context_wrapper                          │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

---

## 使用示例

### 基础使用

```python
from agents import Agent, Runner

agent = Agent(name="Assistant", instructions="You are a helpful assistant.")

result = Runner.run(agent, "What is 2+2?")
print(result.final_output)  # "2+2 equals 4."
```

### 带配置的使用

```python
from agents import Agent, Runner, RunConfig
from openai import OpenAI

config = RunConfig(
    model="gpt-4",
    model_provider=OpenAIProvider(),
    model_settings=ModelSettings(temperature=0.5),
    max_turns=5,
)

agent = Agent(name="MathHelper", instructions="You are a math expert.")
result = Runner.run(agent, "Solve x^2 - 4 = 0", run_config=config)
```

### 带钩子的使用

```python
from agents import Agent, Runner, RunHooksBase

class DebugHooks(RunHooksBase):
    async def on_tool_start(self, agent, tool, input):
        print(f"[DEBUG] {agent.name} called {tool.name} with {input}")

result = Runner.run(agent, "Hello!", hooks=DebugHooks())
```

### 流式输出

```python
result = Runner.run_streamed(agent, "Tell me a story")

async for event in result.stream_events():
    if event.type == "raw_response_event":
        print(event.data.delta, end="", flush=True)

print("\n" + result.result.final_output)
```

### 带护栏的使用

```python
from agents import Agent, Runner, InputGuardrail, RunContextWrapper

async def check_safety(input: str, context: RunContextWrapper):
    if "dangerous" in input.lower():
        return GuardrailResult(triggered=True, output="Unsafe input blocked")
    return GuardrailResult(triggered=False)

agent = Agent(name="SafeAgent", instructions="You are safe.")
result = Runner.run(
    agent,
    "Hello!",
    input_guardrails=[InputGuardrail(check_safety)]
)
```

---

## 文件结构

```
agents/
├── __init__.py                    # 包初始化，导出公共 API
├── run.py                         # Runner 和 AgentRunner 核心实现
├── run_context.py                 # 运行上下文
├── result.py                      # RunResult 结果类型
├── _run_impl.py                   # 内部运行实现
├── agent.py                       # Agent 类定义
├── tool.py                        # Tool 基类
├── function_schema.py             # 函数模式定义
├── guardrail.py                   # 护栏系统
├── lifecycle.py                   # 生命周期钩子
├── items.py                       # 运行项类型
├── stream_events.py               # 流式事件类型
├── tool_guardrails.py             # 工具护栏
├── model_settings.py              # 模型设置
├── exceptions.py                  # 异常定义
├── handoffs/                      # Handoff 模块
├── models/                        # 模型相关
├── mcp/                           # MCP 协议支持
├── memory/                        # 内存管理
├── tracing/                       # 追踪系统
├── realtime/                      # 实时功能
└── voice/                         # 语音功能
```

---

## 总结

`agents` 包提供了一个完整的 Agent 运行框架，主要特点：

1. **简洁的 API**: 通过 `Runner` 类提供简单易用的公共接口
2. **灵活的扩展**: 支持自定义模型、护栏、钩子等
3. **完整的生命周期管理**: 提供丰富的生命周期钩子用于监控和调试
4. **强大的安全机制**: 输入/输出护栏系统确保运行安全
5. **流式支持**: 支持流式输出，提供实时反馈

---

*报告生成完毕*
