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
# 代码分析
./skills/code-analysis/main.py ./src --json

# arXiv 论文查询
python skills/arxiv-reader/scripts/arxiv_client.py --id 2604.05843 --type brief

# 股票分析
python skills/stock-analysis/scripts/fetch_stock_data.py --stock_code 000001

# LLM API 调用
python skills/llm-api-client/scripts/llm_client.py --provider openai --model gpt-4 --message "Hello"
```

## 技能目录

### 开发工具

| 技能名称 | 能力描述 | 平台支持 | MCP |
|---------|---------|---------|-----|
| `code-analyzer` | 代码质量分析、复杂度计算 | All | ✅ |
| `git-batch` | 多仓库批量操作 | All | ✅ |
| `testing-automation` | 智能测试发现与执行 | All | ❌ |
| `file-processing` | 文件处理工具集 | All | ❌ |
| `rocm-windows-hipcc-debug` | ROCm/hipcc Windows 调试 | Windows | ❌ |

### 数据与网络

| 技能名称 | 能力描述 | 平台支持 | MCP |
|---------|---------|---------|-----|
| `arxiv-reader` | arXiv 论文获取与分析 | All | ❌ |
| `stock-analysis` | 股票技术分析（MA/MACD/RSI/缺口） | All | ❌ |
| `llm-api-client` | 统一 LLM API 客户端（OpenAI/Anthropic/豆包等） | All | ❌ |
| `nas-file-download` | NAS 文件下载 | All | ❌ |
| `nas-file-batch-download` | NAS 批量文件下载 | All | ❌ |

### 财务分析

| 技能名称 | 能力描述 | 平台支持 | MCP |
|---------|---------|---------|-----|
| `variance-analysis` | 财务差异分析、驱动因素分解、瀑布分析（Anthropic 官方） | All | ❌ |
| `financial-statements` | GAAP 标准财务报表生成、期间对比分析（Anthropic 官方） | All | ❌ |

### 办公协作

| 技能名称 | 能力描述 | 平台支持 | MCP |
|---------|---------|---------|-----|
| `feishu-calendar` | 飞书日历与日程管理 | All | ❌ |
| `feishu-bitable` | 飞书多维表格数据管理 | All | ❌ |

### 系统管理

| 技能名称 | 能力描述 | 平台支持 | MCP |
|---------|---------|---------|-----|
| `system-admin` | 系统管理工具集 | All | ❌ |

---

## 技能详情

### arxiv-reader
基于 [data.rag.ac.cn](https://data.rag.ac.cn) 的免费 arXiv API，支持获取论文元数据、摘要、全文。

```bash
# 获取论文元数据
python skills/arxiv-reader/scripts/arxiv_client.py --token YOUR_TOKEN --id 2604.05843 --type brief

# Python 调用
from skills.arxiv_reader.scripts.arxiv_client import ArxivClient
client = ArxivClient(token="your-token")
meta = client.get_brief("2604.05843")
```

### stock-analysis
股票个股分析，支持多数据源自动切换（新浪财经/东方财富），计算技术指标和支撑位压力位。

```bash
# 获取数据并分析
python skills/stock-analysis/scripts/fetch_stock_data.py --stock_code 002639 --days 30
python skills/stock-analysis/scripts/analyze_stock.py --data_file stock_data_002639.json
```

### llm-api-client
统一 REST API 客户端，支持多种 LLM 提供商：OpenAI、Anthropic、Google Gemini、Volcengine（豆包）等。

```bash
# 调用豆包模型
python skills/llm-api-client/scripts/llm_client.py \
  --provider volcengine \
  --model doubao-seed-2-0-pro-260215 \
  --message "你好"

# Python 调用
from skills.llm_api_client.scripts.llm_client import LLMClient
client = LLMClient(provider="openai", api_key="sk-...")
response = client.complete(messages=[...], model="gpt-4")
```

### feishu-calendar
飞书日历与日程管理，支持日程创建、查询、忙闲状态查询等功能。

> 使用此技能需要飞书应用授权，详见 [SKILL.md](skills/feishu-calendar/SKILL.md)

### feishu-bitable
飞书多维表格（Bitable）管理，支持 27 种字段类型、高级筛选、批量操作。

> 使用此技能需要飞书应用授权，详见 [SKILL.md](skills/feishu-bitable/SKILL.md)

### variance-analysis
【Anthropic 官方】专业的财务差异分析工具。将财务差异分解为驱动因素，提供叙述性解释和瀑布分析。

- 支持 Price/Volume 分解、Rate/Mix 分解、Headcount/Compensation 分解
- 生成 materiality thresholds 和调查优先级
- 提供 text-based waterfall 格式和预算vs实际vs预测对比框架

详见 [SKILL.md](skills/variance-analysis/SKILL.md)

### financial-statements
【Anthropic 官方】专业的财务报表生成工具。生成符合 GAAP 标准的损益表、资产负债表和现金流量表。

- 支持 ASC 220 / ASC 210 / ASC 230 标准的报表格式
- 包含常见期末调整（accruals、折旧摊销、坏账准备等）
- 提供 flux analysis methodology 和差异分解方法

详见 [SKILL.md](skills/financial-statements/SKILL.md)

---

## 技能开发规范

每个技能目录必须包含 `SKILL.md` 元数据文件（YAML frontmatter + Markdown 说明）：

```markdown
---
name: your-skill-name
description: 简短明确的功能描述，说明何时使用此技能
---

# 技能名称

## 功能概述
...
```

**可选资源目录**:
- `scripts/` - 可执行脚本（Python/Bash 等）
- `references/` - 参考文档
- `assets/` - 模板文件

**平台适配指南**:
- 纯 Python 逻辑放 `scripts/*.py`（跨平台）
- 系统特定命令提供适配层
- 复杂依赖项在 SKILL.md 中声明

---

## 环境要求

- **Python**: 3.9+ (推荐 3.11)
- **PowerShell**: 7.0+ (Windows)
- **Bash**: 4.0+ (Linux/macOS)

### 依赖安装

```bash
# 股票分析依赖
pip install requests numpy pandas

# LLM API 客户端依赖
pip install openai anthropic google-generativeai requests

# arXiv 阅读器依赖
pip install requests
```

---

## 贡献新技能

1. 在 `skills/` 下创建新目录
2. 编写 `SKILL.md` 元数据和说明文档
3. 实现主逻辑脚本（支持 `--json` 输出便于 Agent 解析）
4. 更新 `registry.json` 注册表
5. 更新 `README.md` 技能目录

详见 [CONTRIBUTING.md](CONTRIBUTING.md)

---

## 许可证

Apache 2.0 — 允许商业使用，需保留声明
