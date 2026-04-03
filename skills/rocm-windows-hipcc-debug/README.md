# rocm-windows-hipcc-debug Skill

诊断并解决 Windows PowerShell 下执行 hipcc / clang++ 超长 `-cc1` 命令时遇到的解析失败问题。

## 问题背景

在 Windows PowerShell 中直接复制 hipcc 内部展开的 `clang++.exe -cc1 ...` 命令时，
PowerShell 会对特殊字符（如 `,`、`+`、`=`）进行错误解析，导致命令无法运行。

## 功能

1. **环境诊断** (`--diagnose`)：检查 HIP SDK 安装、关键二进制文件、环境变量，并执行简单编译测试
2. **生成 Response File** (`--to-rsp`)：将超长命令转换为 `@file.rsp` 格式，完全绕过 PowerShell 解析
3. **生成 Stop-Parsing 命令** (`--to-stop-parsing`)：在命令中插入 `--%`，让 PowerShell 原样传递后续参数

## 用法

### 诊断环境
```powershell
python main.py --diagnose
```

### 将超长命令转为 Response File
```powershell
python main.py --to-rsp '"C:\hipSDK\bin\clang++.exe" -cc1 -triple pangu-lst-lsthsa ...'
```

### 生成 --% 版本的 PowerShell 命令
```powershell
python main.py --to-stop-parsing '"C:\hipSDK\bin\clang++.exe" -cc1 -triple pangu-lst-lsthsa ...'
```

### JSON 输出
加上 `--json` 参数即可获得结构化输出，便于 Agent 解析。

## HIPCC 参数速查

本 Skill 目录下还包含 [`HIPCC_OPTIONS.md`](./HIPCC_OPTIONS.md)，汇总了 hipcc 常见的调试、Warning 控制、路径/架构指定、Host-Device 分离编译等选项。遇到编译失败或需要调整参数时，可优先查阅。

## 平台支持
- **Windows**：原生支持
- **Linux / macOS**：不适用（此 skill 专用于 Windows PowerShell 环境）
