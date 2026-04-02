"""Tests for rocm-windows-hipcc-debug skill."""

import os
import tempfile
from pathlib import Path

from main import convert_to_response_file, generate_stop_parsing_command


def test_convert_to_response_file():
    cmd = r'"C:\hipSDK\bin\clang++.exe" -cc1 -triple pangu-lst-lsthsa -aux-target-feature +f16c -o "C:\out.o" -x hip test.cpp'
    with tempfile.NamedTemporaryFile(mode="w", suffix=".rsp", delete=False) as f:
        rsp_path = f.name

    result = convert_to_response_file(cmd, rsp_path=rsp_path)
    assert not result.get("error")
    assert result["compiler"] == r"C:\hipSDK\bin\clang++.exe"
    assert result["argument_count"] == 10
    assert "--%" not in result["powershell_command"]
    assert f'@"{rsp_path}"' in result["powershell_command"]

    content = Path(rsp_path).read_text(encoding="utf-8")
    assert "-cc1" in content
    assert "+f16c" in content
    os.unlink(rsp_path)


def test_generate_stop_parsing_command():
    cmd = r'"C:\hipSDK\bin\clang++.exe" -cc1 -triple pangu-lst-lsthsa'
    result = generate_stop_parsing_command(cmd)
    assert not result.get("error")
    assert "--%" in result["powershell_command"]
    assert "pangu-lst-lsthsa" in result["powershell_command"]


def test_generate_stop_parsing_long_command():
    cmd = r'"C:\hipSDK\bin\clang++.exe" -cc1 -triple pangu-lst-lsthsa -aux-triple x86_64-pc-windows-msvc -fdenormal-fp-math-f32=preserve-sign,preserve-sign'
    result = generate_stop_parsing_command(cmd)
    assert not result.get("error")
    assert "preserve-sign,preserve-sign" in result["powershell_command"]
