"""Tests for code-analysis skill."""

import ast
import tempfile
from pathlib import Path

from main import analyze_file, calculate_cyclomatic_complexity


SAMPLE_CODE = """
def simple():
    return 1

def complex_func(x):
    if x > 0:
        if x > 10:
            return 2
        elif x > 5:
            return 3
        else:
            return 4
    return 0
"""


def test_calculate_cyclomatic_complexity():
    tree = ast.parse(SAMPLE_CODE)
    funcs = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
    assert calculate_cyclomatic_complexity(funcs[0]) == 1
    assert calculate_cyclomatic_complexity(funcs[1]) == 5


def test_analyze_file():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as f:
        f.write(SAMPLE_CODE)
        f.flush()
        path = f.name

    result = analyze_file(path, threshold=3)
    assert result["exit_code"] == 0
    assert result["high_risk_count"] == 1
    assert result["functions"][1]["name"] == "complex_func"

    Path(path).unlink()
