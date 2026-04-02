# 将 hipcc/clang 的长参数列表转换为 response file，绕过 PowerShell 解析限制
param(
    [string]$OutFile = "$env:TEMP\hipcc_args.rsp",
    [string]$Compiler = "C:\hipSDK\bin\clang++.exe",
    [string]$SourceFile = "C:/work/projects/rocblas-examples/hipblas-test/example_hgemm_hip_half.cpp",
    [string]$OutputFile = "$env:TEMP\example_hgemm_hip_half.o"
)

# 基础参数（hipcc 展开后的 -cc1 参数示例，可根据需要修改）
$argsList = @(
    "-cc1"
    "-triple", "pangu-lst-lsthsa"
    "-aux-triple", "x86_64-pc-windows-msvc"
    "-emit-obj"
    "-mincremental-linker-compatible"
    "-disable-free"
    "-clear-ast-before-backend"
    "-main-file-name", "example_hgemm_hip_half.cpp"
    "-mrelocation-model", "static"
    "-mframe-pointer", "all"
    "-relaxed-aliasing"
    "-fdenormal-fp-math-f32=preserve-sign,preserve-sign"
    "-fno-rounding-math"
    "-mconstructor-aliases"
    "-aux-target-cpu", "x86-64"
    "-aux-target-feature", "+f16c"
    "-fcuda-is-device"
    "-fcuda-allow-variadic-functions"
    "-fvisibility=hidden"
    "-fapply-global-visibility-to-externs"
    "-mlink-builtin-bitcode", "C:\hipSDK\pangu\bitcode\hip.bc"
    "-mlink-builtin-bitcode", "C:\hipSDK\pangu\bitcode\ocml.bc"
    "-mlink-builtin-bitcode", "C:\hipSDK\pangu\bitcode\ockl.bc"
    "-mlink-builtin-bitcode", "C:\hipSDK\pangu\bitcode\oclc_daz_opt_on.bc"
    "-mlink-builtin-bitcode", "C:\hipSDK\pangu\bitcode\oclc_unsafe_math_off.bc"
    "-mlink-builtin-bitcode", "C:\hipSDK\pangu\bitcode\oclc_finite_only_off.bc"
    "-mlink-builtin-bitcode", "C:\hipSDK\pangu\bitcode\oclc_correctly_rounded_sqrt_on.bc"
    "-mlink-builtin-bitcode", "C:\hipSDK\pangu\bitcode\oclc_wavefrontsize64_off.bc"
    "-mlink-builtin-bitcode", "C:\hipSDK\pangu\bitcode\oclc_isa_version_g100.bc"
    "-mlink-builtin-bitcode", "C:\hipSDK\pangu\bitcode\oclc_abi_version_500.bc"
    "-target-cpu", "g100"
    "-debugger-tuning=gdb"
    "-fdebug-compilation-dir=C:\work\projects\rocblas-examples\build"
    "-v"
    "-fcoverage-compilation-dir=C:\work\projects\rocblas-examples\build"
    "-resource-dir", "C:\hipSDK\lib\clang\21"
    "-idirafter", "C:\hipSDK\include"
    "-include", "__clang_hip_runtime_wrapper.h"
    "-isystem", "C:/hipSDK/include"
    "-D", "HIP_PLATFORM=amd"
    "-D", "NDEBUG"
    "-I", "C:\hipSDK\include"
    "-O3"
    "-w"
    "--std=c++17"
    "-fhip-new-launch-api"
    "-fms-extensions"
    "-fms-compatibility"
    "-fcxx-exceptions"
    "-fexceptions"
    "-vectorize-loops"
    "-vectorize-slp"
    "-o", $OutputFile
    "-x", "hip"
    $SourceFile
)

# 将参数写入 response file，每个参数单独一行，带空格的路径用引号包裹
$rspLines = $argsList | ForEach-Object {
    if ($_ -match '\s') {
        '"{0}"' -f $_
    } else {
        $_
    }
}

$rspLines | Out-File -FilePath $OutFile -Encoding ascii
Write-Host "Response file created: $OutFile" -ForegroundColor Green
Write-Host "`nNow run:" -ForegroundColor Cyan
Write-Host "  & `"$Compiler`" `@`"$OutFile`"" -ForegroundColor Yellow
