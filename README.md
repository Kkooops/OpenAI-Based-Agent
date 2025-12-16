# 基于 OpenAI Agents SDK 搭建的 Mini Agent

这是一个使用 **OpenAI Agents SDK** 搭建的最小可用（Mini）智能体项目。

> ⚠️ 提示：`src/system_prompt.md` 不会提交到 Git，需在本地自行创建，否则无法正常运行。

## 快速开始

```bash
git clone <your-repo-url>.git
cd OpenAI-Based-Agent

# 安装依赖（示例：使用 uv）
uv sync
# 或使用 pip
# pip install -e .
```

## 必要配置

1. **创建 `src/system_prompt.md`**（示例内容，自行按需修改）：

   ```bash
   cat > src/system_prompt.md << 'EOF'
   You are an AI coding assistant running in a CLI environment.

   Your working directory is: {work_dir}

   # Abilities
   - You can run bash commands.
   - You can read, write and edit files within the working directory.

   # Safety
   - Never operate outside of {work_dir}.
   - Always read a file before editing it.

   EOF
   ```

2. **配置 OpenAI / Azure OpenAI**（建议改成环境变量）：

   ```bash
   export OPENAI_BASE_URL="https://<your-endpoint>.openai.azure.com/openai/v1/"
   export OPENAI_API_KEY="<your-api-key>"
   ```

   并在 `src/cli.py` 中改为类似：

   ```python
   import os
   from openai import AsyncOpenAI

   openaiClient = AsyncOpenAI(
       base_url=os.environ["OPENAI_BASE_URL"],
       api_key=os.environ["OPENAI_API_KEY"],
   )
   ```

## 运行

```bash
python -m src.cli
```

启动后会进入交互式 CLI：在 `You:` 后输入指令即可让 Agent 使用 bash / read_file / write_file / edit_file 等工具操作当前项目。
