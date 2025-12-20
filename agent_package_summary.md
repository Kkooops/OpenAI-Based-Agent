# OpenAI Agents SDK - 功能总结与使用指南

## 概述

OpenAI Agents SDK (openai-agents) 是一个用于构建和运行 AI Agent 的 Python 框架。它提供了一套完整的工具链，用于创建智能代理、管理对话、处理工具调用、实现安全防护和多代理协作。

## 核心功能模块

### 1. Agent 核心 (Agent Core)

#### `Agent` 类
- **功能**: 定义一个 AI 代理，包含指令、工具、输出类型等配置
- **关键属性**:
  - `name`: 代理名称
  - `instructions`: 系统提示词（字符串或动态函数）
  - `tools`: 可用工具列表
  - `handoffs`: 可委托的子代理
  - `model`: 使用的模型
  - `model_settings`: 模型参数配置
  - `input_guardrails` / `output_guardrails`: 安全防护
  - `output_type`: 输出类型约束
  - `tool_use_behavior`: 工具调用行为配置

#### `AgentBase` 类
- **功能**: Agent 和 RealtimeAgent 的基类
- **共享属性**: `name`, `handoff_description`, `tools`, `mcp_servers`, `mcp_config`

#### `Runner` 类
- **功能**: 执行 Agent 工作流的核心类
- **主要方法**:
  - `run()`: 异步运行 Agent
  - `run_sync()`: 同步运行 Agent
  - `run_streamed()`: 流式运行 Agent，支持实时事件流

#### `RunConfig` 类
- **功能**: 配置整个 Agent 运行的全局设置
- **关键配置**:
  - `model`: 全局模型覆盖
  - `model_provider`: 模型提供者
  - `model_settings`: 全局模型设置
  - `handoff_input_filter`: 手动输入过滤器
  - `nest_handoff_history`: 历史记录嵌套配置
  - `input/output_guardrails`: 全局防护
  - `tracing_disabled`: 是否禁用追踪
  - `workflow_name`: 追踪工作流名称

### 2. 工具系统 (Tools)

#### `FunctionTool`
- **功能**: 将 Python 函数包装为 Agent 可用的工具
- **创建方式**: 使用 `@function_tool` 装饰器
- **特性**:
  - 自动从函数签名生成 JSON Schema
  - 支持同步/异步函数
  - 支持 `RunContextWrapper` 或 `ToolContext` 参数
  - 支持严格模式 JSON Schema
  - 支持动态启用/禁用

#### 内置工具类型
- **`FileSearchTool`**: 向量库搜索工具
- **`WebSearchTool`**: 网络搜索工具
- **`ComputerTool`**: 计算机控制工具
- **`CodeInterpreterTool`**: 代码解释器
- **`ImageGenerationTool`**: 图像生成工具
- **`LocalShellTool`**: 本地 Shell 命令执行
- **`ShellTool`**: 下一代 Shell 工具
- **`ApplyPatchTool`**: 文件补丁工具
- **`HostedMCPTool`**: 托管 MCP 工具

#### `ToolContext`
- **功能**: 工具执行上下文
- **包含**: 运行上下文、当前 Agent、工具调用信息

### 3. 手动委托 (Handoffs)

#### `Handoff` 类
- **功能**: 实现 Agent 之间的任务委托
- **关键特性**:
  - 将一个 Agent 包装为另一个 Agent 的工具
  - 支持输入过滤和历史记录处理
  - 支持启用/禁用条件

#### `handoff()` 函数
- **功能**: 创建 Handoff 对象的便捷函数
- **参数**:
  - `agent`: 目标 Agent
  - `tool_name_override`: 工具名覆盖
  - `tool_description_override`: 工具描述覆盖
  - `on_handoff`: 委托时的回调函数
  - `input_type`: 输入类型验证
  - `input_filter`: 输入过滤函数
  - `is_enabled`: 动态启用条件

#### 历史记录管理
- **`HandoffInputData`**: 包含委托前后的所有信息
- **历史记录处理函数**: `nest_handoff_history`, `set_conversation_history_wrappers` 等

### 4. 安全防护 (Guardrails)

#### `InputGuardrail`
- **功能**: 在 Agent 执行前或并行执行的输入检查
- **使用**: `@input_guardrail` 装饰器
- **触发**: `InputGuardrailTripwireTriggered` 异常

#### `OutputGuardrail`
- **功能**: 在 Agent 生成输出后进行检查
- **使用**: `@output_guardrail` 装饰器
- **触发**: `OutputGuardrailTripwireTriggered` 异常

#### `GuardrailFunctionOutput`
- **包含**: `output_info` (可选信息), `tripwire_triggered` (是否触发)

#### 工具级防护
- **`ToolInputGuardrail`**: 工具输入检查
- **`ToolOutputGuardrail`**: 工具输出检查
- **使用**: 在 `FunctionTool` 或 `@function_tool` 中配置

### 5. 模型上下文协议 (MCP)

#### `MCPServer` 系列
- **`MCPServerStdio`**: 通过标准输入输出连接的 MCP 服务器
- **`MCPServerSse`**: 通过 SSE (Server-Sent Events) 连接的 MCP 服务器
- **`MCPServerStreamableHttp`**: 通过可流式 HTTP 连接的 MCP 服务器

#### 使用方式
- 在 `Agent` 中配置 `mcp_servers`
- 在 `Agent` 中配置 `mcp_config` (如 `convert_schemas_to_strict`)
- Agent 会自动获取 MCP 服务器的工具

### 6. 会话管理 (Memory/Session)

#### `Session` 协议
- **功能**: 存储和管理对话历史
- **方法**:
  - `get_items()`: 获取历史记录
  - `add_items()`: 添加新条目
  - `pop_item()`: 移除最新条目
  - `clear_session()`: 清空会话

#### 内置实现
- **`SQLiteSession`**: SQLite 数据库存储
- **`OpenAIConversationsSession`**: 使用 OpenAI Conversations API
- **扩展实现**:
  - `RedisSession`: Redis 存储
  - `SQLAlchemySession`: SQLAlchemy ORM 支持
  - `AdvancedSQLiteSession`: 高级 SQLite 功能
  - `EncryptSession`: 加密存储
  - `DaprSession`: Dapr 状态存储

### 7. 追踪与监控 (Tracing)

#### `Trace` 和 `Span`
- **功能**: 记录 Agent 执行的详细过程
- **Span 类型**:
  - `AgentSpanData`: Agent 执行跨度
  - `FunctionSpanData`: 函数调用跨度
  - `GenerationSpanData`: 生成跨度
  - `GuardrailSpanData`: 防护跨度
  - `HandoffSpanData`: 委托跨度
  - `MCPListToolsSpanData`: MCP 工具列表跨度
  - `CustomSpanData`: 自定义跨度

#### 追踪控制
- **`trace()`**: 创建追踪上下文
- **`agent_span()` / `function_span()` 等**: 创建特定类型跨度
- **`add_trace_processor()` / `set_trace_processors()`**: 添加追踪处理器
- **`set_tracing_disabled()`**: 全局禁用追踪

### 8. 模型接口 (Models)

#### `Model` 接口
- **功能**: 定义模型调用的抽象接口
- **方法**:
  - `get_response()`: 获取完整响应
  - `stream_response()`: 流式响应

#### `ModelProvider` 接口
- **功能**: 模型提供者，根据名称获取模型
- **内置提供者**:
  - `OpenAIProvider`: OpenAI 模型提供者
  - `MultiProvider`: 多提供者聚合

#### 具体模型实现
- **`OpenAIResponsesModel`**: OpenAI Responses API
- **`OpenAIChatCompletionsModel`**: OpenAI Chat Completions API
- **`LiteLLMModel`**: 通过 LiteLLM 支持多厂商模型

### 9. 输出与结果

#### `RunResult`
- **包含**:
  - `input`: 输入内容
  - `new_items`: 生成的新条目
  - `raw_responses`: 原始响应
  - `final_output`: 最终输出
  - `input/output_guardrail_results`: 防护结果
  - `tool_input/output_guardrail_results`: 工具防护结果

#### `RunResultStreaming`
- **功能**: 流式运行结果
- **方法**: `stream_events()` 获取事件流

#### 流式事件 (`StreamEvent`)
- **类型**:
  - `RawResponsesStreamEvent`: 原始响应事件
  - `RunItemStreamEvent`: 运行条目事件
  - `AgentUpdatedStreamEvent`: Agent 更新事件

### 10. 生命周期钩子 (Lifecycle)

#### `AgentHooks`
- **功能**: Agent 级别的生命周期回调
- **钩子**: `on_agent_start`, `on_agent_end` 等

#### `RunHooks`
- **功能**: 运行级别的生命周期回调
- **钩子**: `on_run_start`, `on_run_end`, `on_turn_start`, `on_turn_end` 等

### 11. 动态提示 (Prompts)

#### `Prompt` 类
- **功能**: 动态提示配置
- **特性**: 支持从外部源动态生成提示

#### `DynamicPromptFunction`
- **功能**: 动态生成提示的函数
- **使用**: 与 `Prompt` 结合使用

### 12. 计算机与编辑器工具

#### `Computer` / `AsyncComputer`
- **功能**: 计算机环境抽象
- **方法**: `click()`, `screenshot()`, `keypress()` 等

#### `ApplyPatchEditor`
- **功能**: 文件编辑器抽象
- **方法**: `apply_patch()` 应用补丁

### 13. 语音功能 (Voice)

#### `VoicePipeline`
- **功能**: 语音输入输出管道
- **组件**:
  - `AudioInput`: 音频输入源
  - `STTModel`: 语音转文本
  - `TTSModel`: 文本转语音
  - `VoiceWorkflow`: 语音工作流

#### 语音工作流
- **`SingleAgentVoiceWorkflow`**: 单 Agent 语音工作流
- **`VoiceWorkflowBase`**: 语音工作流基类

### 14. 异常处理

#### 主要异常类型
- **`AgentsException`**: 基础异常
- **`InputGuardrailTripwireTriggered`**: 输入防护触发
- **`OutputGuardrailTripwireTriggered`**: 输出防护触发
- **`ToolInputGuardrailTripwireTriggered`**: 工具输入防护触发
- **`ToolOutputGuardrailTripwireTriggered`**: 工具输出防护触发
- **`MaxTurnsExceeded`**: 最大轮次超出
- **`ModelBehaviorError`**: 模型行为错误
- **`UserError`**: 用户错误
- **`RunErrorDetails`**: 运行错误详情

### 15. 配置与初始化

#### 全局配置函数
- **`set_default_openai_key()`**: 设置默认 OpenAI API 密钥
- **`set_default_openai_client()`**: 设置默认 OpenAI 客户端
- **`set_default_openai_api()`**: 设置默认 API 类型 (chat_completions/responses)
- **`set_tracing_export_api_key()`**: 设置追踪导出密钥
- **`enable_verbose_stdout_logging()`**: 启用详细日志

## 相关依赖包

### 核心依赖
- **`openai`**: OpenAI API 客户端
- **`pydantic`**: 数据验证和序列化
- **`typing_extensions`**: 类型扩展支持

### MCP 相关
- **`mcp`**: Model Context Protocol SDK
- **`anyio`**: 异步 I/O 库

### 扩展依赖
- **`litellm`**: 多厂商模型支持 (可选)
- **`redis`**: Redis 会话存储 (可选)
- **`sqlalchemy`**: SQL 数据库支持 (可选)
- **`dapr`**: Dapr 分布式应用运行时 (可选)

## 典型使用场景

### 1. 单 Agent 简单对话
```python
from agents import Agent, Runner

agent = Agent(
    name="助手",
    instructions="你是一个有帮助的助手",
    tools=[...]  # 可选工具
)

result = await Runner.run(agent, "你好")
```

### 2. 多 Agent 协作
```python
from agents import Agent, handoff, Runner

triage_agent = Agent(
    name="路由代理",
    instructions="根据用户需求路由到合适的代理",
    handoffs=[
        handoff(billing_agent),
        handoff(tech_support_agent)
    ]
)

result = await Runner.run(triage_agent, "我的账单有问题")
```

### 3. 带工具的 Agent
```python
from agents import Agent, function_tool, Runner

@function_tool
def get_weather(city: str) -> str:
    """获取城市天气"""
    return f"{city} 今天晴朗"

agent = Agent(
    name="天气助手",
    instructions="使用工具查询天气",
    tools=[get_weather]
)
```

### 4. 带防护的 Agent
```python
from agents import Agent, input_guardrail, GuardrailFunctionOutput

@input_guardrail
def safety_check(context, agent, input):
    if "敏感词" in input:
        return GuardrailFunctionOutput(output_info="检测到敏感内容", tripwire_triggered=True)
    return GuardrailFunctionOutput(output_info="安全", tripwire_triggered=False)

agent = Agent(
    name="安全助手",
    input_guardrails=[safety_check]
)
```

### 5. 带会话历史的 Agent
```python
from agents import Agent, SQLiteSession, Runner

session = SQLiteSession(session_id="user_123")
agent = Agent(name="对话助手")

result = await Runner.run(agent, "第一次对话", session=session)
result2 = await Runner.run(agent, "记住上次对话", session=session)
```

### 6. MCP 服务器集成
```python
from agents import Agent, MCPServerStdio

mcp_server = MCPServerStdio(
    name="文件系统",
    command="npx",
    args=["-y", "@modelcontextprotocol/server-filesystem", "/tmp"]
)

agent = Agent(
    name="文件助手",
    mcp_servers=[mcp_server]
)
```

### 7. 流式输出
```python
from agents import Agent, Runner

agent = Agent(name="流式助手")

result = Runner.run_streamed(agent, "请详细解释...")
async for event in result.stream_events():
    print(event)
```

### 8. 语音交互
```python
from agents import SingleAgentVoiceWorkflow, VoicePipelineConfig

workflow = SingleAgentVoiceWorkflow(agent=agent)
pipeline = VoicePipelineConfig(
    input_device="microphone",
    output_device="speaker"
)
await workflow.run(pipeline)
```

## 最佳实践

1. **使用 `@function_tool` 装饰器**: 自动处理参数验证和错误处理
2. **配置 `output_type`**: 确保 Agent 输出符合预期格式
3. **合理使用 `handoffs`**: 实现多 Agent 协作和职责分离
4. **添加防护机制**: 使用 `input_guardrails` 和 `output_guardrails`
5. **启用追踪**: 用于调试和监控 Agent 行为
6. **使用会话管理**: 保持对话上下文
7. **配置 `tool_use_behavior`**: 控制工具调用后的流程
8. **使用 MCP**: 集成外部工具和服务
9. **处理异常**: 捕获和处理各种 Agent 异常
10. **测试不同模型**: 使用 `MultiProvider` 测试不同模型

## 总结

OpenAI Agents SDK 提供了一个完整的框架，用于构建复杂的 AI Agent 系统。它支持从简单的单 Agent 对话到复杂的多 Agent 协作、工具集成、安全防护、会话管理、语音交互等多种场景。通过模块化的设计，开发者可以灵活组合各种功能，构建满足特定需求的 AI 应用。