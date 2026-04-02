# 诊断 HIP/ROCm 在 PowerShell 中的环境
$ErrorActionPreference = "Continue"

Write-Host "=== HIP SDK 诊断 ===" -ForegroundColor Cyan

# 1. 检查 hipcc 和 clang++ 是否存在
$paths = @(
    "C:\hipSDK\bin\hipcc.exe",
    "C:\hipSDK\bin\clang++.exe",
    "C:\hipSDK\bin\clang.exe"
)
foreach ($p in $paths) {
    if (Test-Path $p) {
        Write-Host "[OK] $p" -ForegroundColor Green
    } else {
        Write-Host [MISSING] $p -ForegroundColor Red
    }
}

# 2. 检查关键环境变量
Write-Host "`n=== 环境变量 ==="
$envs = @("HIP_PATH", "HIP_PLATFORM", "ROCM_PATH", "PATH")
foreach ($e in $envs) {
    $val = [Environment]::GetEnvironmentVariable($e)
    Write-Host "$e = $val"
}

# 3. 尝试直接运行 hipcc --version
Write-Host "`n=== hipcc --version ==="
try {
    & C:\hipSDK\bin\hipcc.exe --version 2>&1 | Write-Host
} catch {
    Write-Host "ERROR: $_" -ForegroundColor Red
}

# 4. 尝试直接运行 clang++ --version
Write-Host "`n=== clang++ --version ==="
try {
    & C:\hipSDK\bin\clang++.exe --version 2>&1 | Write-Host
} catch {
    Write-Host "ERROR: $_" -ForegroundColor Red
}

# 5. 测试一个最简单的 hip 编译命令
Write-Host "`n=== 测试最简单的 hip 编译 ==="
$testFile = "$env:TEMP\test_hip.cpp"
"#include <hip/hip_runtime.h>`nint main() { return 0; }" | Out-File -FilePath $testFile -Encoding ascii
try {
    & C:\hipSDK\bin\hipcc.exe $testFile -o "$env:TEMP\test_hip.exe" --verbose 2>&1 | Write-Host
    if (Test-Path "$env:TEMP\test_hip.exe") {
        Write-Host "[OK] 简单编译通过" -ForegroundColor Green
    } else {
        Write-Host "[FAIL] 简单编译失败，未生成 exe" -ForegroundColor Red
    }
} catch {
    Write-Host "ERROR: $_" -ForegroundColor Red
}

# 6. 如果使用 CMake，检查是否有 compile_commands.json
Write-Host "`n=== 检查 compile_commands.json ==="
$ccJson = "C:\work\projects\rocblas-examples\build\compile_commands.json"
if (Test-Path $ccJson) {
    Write-Host "Found: $ccJson" -ForegroundColor Green
} else {
    Write-Host "Not found: $ccJson" -ForegroundColor Yellow
}
