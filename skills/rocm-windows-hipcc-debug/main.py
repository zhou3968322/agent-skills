#!/usr/bin/env python3
"""ROCm Windows HIPCC Debug Skill

帮助在 Windows PowerShell 下正确执行 hipcc / clang++ 的超长 -cc1 命令，
绕过 PowerShell 参数解析限制。
"""

import argparse
import json
import os
import shlex
import subprocess
import sys

# 确保 Windows 下 stdout 使用 UTF-8，避免中文输出乱码
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import tempfile
from pathlib import Path


def _default_hip_path() -> str:
    return os.environ.get("HIP_PATH", r"C:\hipSDK")


def diagnose_hip_env(hip_path: str = None) -> dict:
    if hip_path is None:
        hip_path = _default_hip_path()
    """诊断 HIP/ROCm 环境状态."""
    results = {
        "hip_path": hip_path,
        "binaries": {},
        "env_vars": {},
        "simple_compile_ok": False,
    }

    binaries = ["hipcc.exe", "clang++.exe", "clang.exe"]
    for b in binaries:
        p = Path(hip_path) / "bin" / b
        results["binaries"][b] = p.exists()

    for ev in ["HIP_PATH", "HIP_PLATFORM", "ROCM_PATH"]:
        results["env_vars"][ev] = os.environ.get(ev, "")

    test_cpp = Path(tempfile.gettempdir()) / "test_hip.cpp"
    test_cpp.write_text(
        '#include <hip/hip_runtime.h>\nint main(){ return 0; }\n',
        encoding="utf-8",
    )
    test_exe = Path(tempfile.gettempdir()) / "test_hip.exe"
    if test_exe.exists():
        test_exe.unlink()

    try:
        proc = subprocess.run(
            [str(Path(hip_path) / "bin" / "hipcc.exe"), str(test_cpp), "-o", str(test_exe)],
            capture_output=True,
            text=True,
            timeout=60,
        )
        results["simple_compile_ok"] = proc.returncode == 0 and test_exe.exists()
        results["simple_compile_stdout"] = proc.stdout
        results["simple_compile_stderr"] = proc.stderr
    except Exception as e:
        results["simple_compile_error"] = str(e)

    return results


def convert_to_response_file(command_line: str, rsp_path: str = None) -> dict:
    """将超长 clang++ -cc1 命令转换为 response file."""
    if rsp_path is None:
        rsp_path = os.path.join(tempfile.gettempdir(), "hipcc_args.rsp")

    try:
        tokens = shlex.split(command_line)
    except ValueError as e:
        return {"error": True, "message": f"Failed to parse command: {e}"}

    if not tokens:
        return {"error": True, "message": "Empty command"}

    compiler = tokens[0]
    args = tokens[1:]

    lines = []
    for arg in args:
        if " " in arg:
            lines.append(f'"{arg}"')
        else:
            lines.append(arg)

    Path(rsp_path).write_text("\n".join(lines), encoding="utf-8")

    return {
        "compiler": compiler,
        "rsp_path": rsp_path,
        "argument_count": len(args),
        "powershell_command": f'& "{compiler}" @"{rsp_path}"',
        "cmd_command": f'"{compiler}" @{rsp_path}',
    }


def generate_stop_parsing_command(command_line: str) -> dict:
    """生成使用 --% 的 PowerShell 命令."""
    try:
        tokens = shlex.split(command_line)
    except ValueError as e:
        return {"error": True, "message": f"Failed to parse command: {e}"}

    if not tokens:
        return {"error": True, "message": "Empty command"}

    compiler = tokens[0]
    rest = command_line[len(compiler):].strip()

    ps_cmd = f'& "{compiler}" --% {rest}'
    return {
        "compiler": compiler,
        "powershell_command": ps_cmd,
    }


def main():
    parser = argparse.ArgumentParser(
        description="ROCm Windows HIPCC Debug Skill - 绕过 PowerShell 参数解析限制"
    )
    parser.add_argument(
        "--diagnose", action="store_true", help="诊断 HIP 环境"
    )
    parser.add_argument(
        "--to-rsp", metavar="CMD", help="将命令转换为 response file"
    )
    parser.add_argument(
        "--to-stop-parsing", metavar="CMD", help="生成 --%% 版本的 PowerShell 命令"
    )
    parser.add_argument(
        "--hip-path", default=_default_hip_path(), help="HIP SDK 路径（默认从 HIP_PATH 环境变量获取）"
    )
    parser.add_argument(
        "--query-flags", action="store_true", help="输出 HIPCC 常用调试参数速查表"
    )
    parser.add_argument(
        "--json", action="store_true", help="JSON 输出"
    )
    args = parser.parse_args()

    if not any([args.diagnose, args.to_rsp, args.to_stop_parsing, args.query_flags]):
        parser.print_help()
        sys.exit(1)

    results = {}

    if args.diagnose:
        results["diagnosis"] = diagnose_hip_env(args.hip_path)

    if args.to_rsp:
        results["response_file"] = convert_to_response_file(args.to_rsp)

    if args.to_stop_parsing:
        results["stop_parsing"] = generate_stop_parsing_command(args.to_stop_parsing)

    if args.query_flags:
        flags_md = Path(__file__).with_name("HIPCC_OPTIONS.md")
        flags_content = flags_md.read_text(encoding="utf-8") if flags_md.exists() else "HIPCC_OPTIONS.md not found."
        results["query_flags"] = {
            "file": str(flags_md),
            "content": flags_content,
        }

    if args.json:
        json_bytes = json.dumps(results, indent=2, ensure_ascii=False).encode("utf-8")
        sys.stdout.buffer.write(json_bytes)
        sys.stdout.buffer.write(b"\n")
    else:
        if "diagnosis" in results:
            d = results["diagnosis"]
            print("=== HIP Environment Diagnosis ===")
            print(f"HIP Path: {d['hip_path']}")
            for b, ok in d["binaries"].items():
                status = "OK" if ok else "MISSING"
                print(f"  [{status}] {b}")
            print("Environment:")
            for k, v in d["env_vars"].items():
                print(f"  {k}={v}")
            compile_status = "OK" if d["simple_compile_ok"] else "FAIL"
            print(f"Simple compile test: {compile_status}")
            if not d["simple_compile_ok"] and "simple_compile_stderr" in d:
                print(d["simple_compile_stderr"])

        if "response_file" in results:
            r = results["response_file"]
            if r.get("error"):
                print(f"Error: {r['message']}")
            else:
                print("\n=== Response File Generated ===")
                print(f"Path: {r['rsp_path']}")
                print(f"Arguments: {r['argument_count']}")
                print("Run with PowerShell:")
                print(f"  {r['powershell_command']}")

        if "stop_parsing" in results:
            s = results["stop_parsing"]
            if s.get("error"):
                print(f"Error: {s['message']}")
            else:
                print("\n=== Stop-Parsing PowerShell Command ===")
                print(f"  {s['powershell_command']}")

        if "query_flags" in results:
            print("\n=== HIPCC Common Flags Cheatsheet ===")
            print(results["query_flags"]["content"])

    has_error = any(
        v.get("error")
        for k, v in results.items()
        if isinstance(v, dict)
    )
    sys.exit(1 if has_error else 0)


if __name__ == "__main__":
    main()
