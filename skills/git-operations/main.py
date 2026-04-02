#!/usr/bin/env python3
"""Git 批量操作技能."""

import argparse
import json
import subprocess
import sys
from pathlib import Path


def run_git_command(repo_path: str, *args) -> dict:
    """在指定仓库路径运行 git 命令."""
    try:
        result = subprocess.run(
            ["git", "-C", repo_path, *args],
            capture_output=True,
            text=True,
            check=False,
        )
        return {
            "success": result.returncode == 0,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
            "exit_code": result.returncode,
        }
    except FileNotFoundError:
        return {
            "success": False,
            "stderr": "git command not found",
            "exit_code": 127,
        }


def find_git_repos(root_dir: str) -> list:
    """查找根目录下所有 Git 仓库."""
    root = Path(root_dir).expanduser().resolve()
    repos = []
    for path in root.iterdir():
        if path.is_dir() and (path / ".git").exists():
            repos.append(str(path))
    return repos


def main():
    parser = argparse.ArgumentParser(description="Git batch operations skill")
    parser.add_argument("root_dir", help="Root directory containing git repos")
    parser.add_argument(
        "--operation",
        choices=["status", "pull", "commit-push"],
        default="status",
        help="Operation to perform",
    )
    parser.add_argument("--message", default="Auto commit", help="Commit message")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    repos = find_git_repos(args.root_dir)
    results = []

    for repo in repos:
        if args.operation == "status":
            out = run_git_command(repo, "status", "--short")
        elif args.operation == "pull":
            out = run_git_command(repo, "pull")
        elif args.operation == "commit-push":
            run_git_command(repo, "add", ".")
            commit = run_git_command(repo, "commit", "-m", args.message)
            if commit["success"]:
                out = run_git_command(repo, "push")
            else:
                out = commit
        else:
            out = {"success": False, "stderr": "Unknown operation"}

        results.append({"repo": repo, **out})

    success_count = sum(1 for r in results if r["success"])
    output = {
        "repositories": results,
        "success_count": success_count,
        "fail_count": len(results) - success_count,
        "exit_code": 0 if success_count == len(results) else 1,
    }

    if args.json:
        print(json.dumps(output, indent=2, ensure_ascii=False))
    else:
        print(f"Processed {len(results)} repo(s): {success_count} OK, {output['fail_count']} failed")
        for r in results:
            status = "OK" if r["success"] else "FAIL"
            print(f"  [{status}] {r['repo']}")
            if r.get("stdout"):
                for line in r["stdout"].splitlines():
                    print(f"    {line}")
            if r.get("stderr"):
                for line in r["stderr"].splitlines():
                    print(f"    ERR: {line}")

    sys.exit(output["exit_code"])


if __name__ == "__main__":
    main()
