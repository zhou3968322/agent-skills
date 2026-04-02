# Contributing to Agent Skills

感谢你对 Agent Skills 的兴趣！本仓库定位为 **AI Agent 可调用技能集合**，所有贡献需遵循统一的元数据与输出规范。

## 技能开发规范

### 1. 目录结构

每个技能必须位于 `skills/<skill-name>/` 下，包含：

```text
skills/<skill-name>/
├── skill.json          # 技能元数据（必填）
├── main.py             # 跨平台主入口（推荐）
├── test_skill.py       # 技能级测试
├── README.md           # 技能说明
├── win/                # Windows 特定实现（可选）
└── unix/               # Linux/macOS 特定实现（可选）
```

### 2. 命名规则

- 技能目录名：**kebab-case**，动词优先
  - 好例子：`fix-code-style`、`analyze-complexity`、`batch-git-pull`
  - 坏例子：`utils`、`helper_v2`、`CodeAnalyzer`

### 3. skill.json 必填字段

参考 `skills/_template/skill.json`。必须包含：

- `skill_meta.name` - 唯一标识
- `skill_meta.version` - 语义化版本
- `skill_meta.description` - 一句话描述
- `execution.entry` - 入口文件
- `input_schema` / `output_schema` - JSON Schema 定义
- `platform_compatibility` - 平台支持声明

### 4. 输出格式规范

**所有技能必须支持 `--json` 参数**，输出结构化 JSON，便于 Agent 解析。

成功示例：
```json
{
  "success": true,
  "data": { ... },
  "exit_code": 0
}
```

错误示例：
```json
{
  "error": true,
  "message": "文件不存在: /path/to/file",
  "code": 2
}
```

### 5. 平台适配

- 纯 Python 逻辑优先放在 `main.py`（天然跨平台）
- 必须调用系统命令时，提供适配层：
  - Windows 实现放 `win/*.ps1`
  - Unix 实现放 `unix/*.sh`
  - `main.py` 负责根据 `sys.platform` 分发

### 6. 测试要求

- 每个技能至少包含一个 `test_skill.py`
- 使用 `pytest` 编写
- 测试不应依赖真实的外部环境（使用 mock 或临时文件）

### 7. 提交 PR 前 checklist

- [ ] 已复制 `skills/_template/` 并填写元数据
- [ ] 已实现主逻辑，支持 `--json` 输出
- [ ] 已添加 `test_skill.py`
- [ ] 已更新 `registry.json`
- [ ] 本地运行 `python tests/test-runner.py` 通过
- [ ] 本地运行 `python scripts/check_platform_tags.py` 通过
