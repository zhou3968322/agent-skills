# Agent Skills

**Agent 可调用技能集合** — 将日常开发脚本转化为 AI Agent 的标准化工具能力。

支持 MCP (Model Context Protocol)、Function Calling 及传统 CLI 调用。

[![MCP](https://img.shields.io/badge/MCP-Compatible-blue)](https://modelcontextprotocol.io)
[![Python](https://img.shields.io/badge/Python-3.9%2B-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/License-Apache%202.0-green.svg)](LICENSE)

## 核心理念

**Skill as Code**: 每一个脚本都是一个可被发现、可组合、可验证的 Agent 能力单元。

```
传统脚本: python fix_code.py ./src
Agent 技能: "请帮我优化 code-analyzer 指出的所有复杂度超标的函数"
```

## 快速集成

### 作为 MCP Server 使用（推荐）
```json
// claude_desktop_config.json 或类似配置
{
  "mcpServers": {
    "dev-tools": {
      "command": "python",
      "args": ["-m", "mcp.server", "agent-skills/mcp-servers/server-config.json"]
    }
  }
}
```

### 作为 Python 包使用
```bash
pip install -e .
from agent_skills import load_skill

skill = load_skill("code-analyzer")
result = skill.execute(file_path="./src", metrics=["complexity"])
```

### 直接脚本调用
```bash
# 保持向后兼容
./skills/code-analysis/main.py ./src --json
```

## 技能目录

| 技能名称 | 能力描述 | 平台支持 | MCP |
|---------|---------|---------|-----|
| `code-analyzer` | 代码质量分析、复杂度计算 | All | ✅ |
| `git-batch` | 多仓库批量操作 | All | ✅ |
| `test-runner` | 智能测试发现与执行 | All | ✅ |
| `env-setup` | 开发环境一键配置 | Win/Linux | ✅ |
| `log-parser` | 结构化日志分析 | All | ✅ |

## 技能开发规范

每个技能必须包含 `skill.json` 元数据文件：

```json
{
  "skill_meta": {
    "name": "your-skill-name",
    "version": "1.0.0",
    "description": "简短明确的功能描述"
  },
  "execution": {
    "type": "python",
    "entry": "main.py"
  },
  "input_schema": { ... },
  "output_schema": { ... }
}
```

**平台适配指南**：
- 纯 Python 逻辑放 `main.py`（跨平台）
- 系统特定命令放 `win/` 或 `unix/` 子目录
- 使用 `subprocess` 调用 shell 脚本时提供适配层

## 环境要求

- **Python**: 3.9+ (推荐 3.11)
- **PowerShell**: 7.0+ (Windows)
- **Bash**: 4.0+ (Linux/macOS)

## 贡献新技能

1. 复制 `skills/_template/` 目录
2. 填写 `skill.json` 元数据
3. 实现主逻辑（支持 `--json` 输出便于 Agent 解析）
4. 添加测试用例至 `tests/skills/`
5. 更新 `registry.json`

详见 [CONTRIBUTING.md](CONTRIBUTING.md)

## 许可证

Apache 2.0 — 允许商业使用，需保留声明
