# code-analyzer Skill

分析 Python 代码复杂度与潜在问题。

## 用法

```bash
python main.py ./src --json
```

## 参数

- `file_path`: 目标文件或目录
- `--threshold`: 圈复杂度阈值（默认 10）
- `--json`: JSON 输出

## 指标

- 圈复杂度（Cyclomatic Complexity）
- 高风险函数标记
