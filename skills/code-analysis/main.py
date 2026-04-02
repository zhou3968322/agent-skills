#!/usr/bin/env python3
"""代码分析技能 - 计算圈复杂度并标记高风险函数."""

import argparse
import ast
import json
import sys
from pathlib import Path


def calculate_cyclomatic_complexity(node: ast.AST) -> int:
    """简单计算 AST 节点的圈复杂度."""
    complexity = 1
    for child in ast.walk(node):
        if isinstance(child, (ast.If, ast.While, ast.For, ast.ExceptHandler,
                              ast.With, ast.Assert, ast.comprehension)):
            complexity += 1
        elif isinstance(child, ast.BoolOp):
            complexity += len(child.values) - 1
    return complexity


def analyze_file(file_path: str, threshold: int = 10) -> dict:
    """分析单个 Python 文件的复杂度."""
    path = Path(file_path)
    if not path.exists():
        return {"error": True, "message": f"File not found: {file_path}", "code": 2}

    try:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
    except SyntaxError as e:
        return {"error": True, "message": f"Syntax error: {e}", "code": 3}

    functions = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            cc = calculate_cyclomatic_complexity(node)
            functions.append({
                "name": node.name,
                "line": node.lineno,
                "complexity": cc,
                "risk": "high" if cc > threshold else "low"
            })

    high_risk = [f for f in functions if f["risk"] == "high"]
    return {
        "file": str(path),
        "functions": functions,
        "high_risk_count": len(high_risk),
        "exit_code": 0
    }


def main():
    parser = argparse.ArgumentParser(description="Code analyzer skill")
    parser.add_argument("file_path", help="Target file or directory")
    parser.add_argument("--threshold", type=int, default=10, help="Complexity threshold")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    target = Path(args.file_path)
    results = []

    if target.is_dir():
        for py_file in target.rglob("*.py"):
            results.append(analyze_file(str(py_file), args.threshold))
    else:
        results.append(analyze_file(str(target), args.threshold))

    output = {
        "files_analyzed": len(results),
        "results": results,
        "exit_code": max(r.get("exit_code", 0) for r in results)
    }

    if args.json:
        print(json.dumps(output, indent=2, ensure_ascii=False))
    else:
        print(f"Analyzed {output['files_analyzed']} file(s)")
        for r in results:
            if r.get("error"):
                print(f"  ERROR: {r['message']}")
                continue
            print(f"  {r['file']}: {len(r['functions'])} functions, {r['high_risk_count']} high-risk")
            for fn in r["functions"]:
                if fn["risk"] == "high":
                    print(f"    ! {fn['name']} (line {fn['line']}) complexity={fn['complexity']}")

    sys.exit(output["exit_code"])


if __name__ == "__main__":
    main()
