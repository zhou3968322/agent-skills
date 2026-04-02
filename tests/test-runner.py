#!/usr/bin/env python3
"""技能自动化测试框架 - 发现并运行所有技能级测试."""

import json
import subprocess
import sys
from pathlib import Path

SKILLS_DIR = Path(__file__).parent.parent / "skills"


def discover_skill_tests() -> list:
    """发现所有包含 test_skill.py 的技能目录."""
    tests = []
    for skill_dir in SKILLS_DIR.iterdir():
        if skill_dir.is_dir() and skill_dir.name.startswith("_"):
            continue
        test_file = skill_dir / "test_skill.py"
        if test_file.exists():
            tests.append((skill_dir.name, test_file))
    return tests


def run_skill_test(skill_name: str, test_file: Path) -> dict:
    """使用 pytest 运行单个技能测试."""
    result = subprocess.run(
        [sys.executable, "-m", "pytest", str(test_file), "-v", "--tb=short"],
        capture_output=True,
        text=True,
    )
    return {
        "skill": skill_name,
        "passed": result.returncode == 0,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "exit_code": result.returncode,
    }


def main():
    print("Discovering skill tests...\n")
    tests = discover_skill_tests()
    if not tests:
        print("No skill tests found.")
        sys.exit(0)

    results = []
    all_passed = True
    for name, path in tests:
        print(f"Running tests for skill: {name}")
        res = run_skill_test(name, path)
        results.append(res)
        if not res["passed"]:
            all_passed = False
            print(f"  FAILED (exit {res['exit_code']})")
            if res["stderr"]:
                print(res["stderr"])
        else:
            print(f"  PASSED")

    print(f"\n{'='*40}")
    print(f"Total: {len(results)}, Passed: {sum(1 for r in results if r['passed'])}, Failed: {sum(1 for r in results if not r['passed'])}")
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
