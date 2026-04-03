# HIPCC 常用选项速查表

> 基于 `C:\hipSDK\bin\hipcc.exe --help`（底层为 clang++）整理。遇到编译失败、链接失败、或需要调整参数时，可优先查询本表。

---

## 1. 调试与排障（Debug / Troubleshooting）

| 选项 | 作用 | 典型场景 |
|------|------|----------|
| `-v` | **显示详细命令**：打印 hipcc 实际调用的所有子命令（clang++ -cc1、lld 等） | 编译失败时查看底层到底执行了什么 |
| `-###` | **只打印命令不执行**：与 `-v` 类似，但不会真正运行 | 确认参数传递是否正确，避免误操作 |
| `--save-temps` / `--save-temps=cwd` / `--save-temps=obj` | **保留中间文件**：保存预处理、LLVM IR、汇编等临时文件 | 需要分析 `.ii`、`.bc`、`.s` 中间产物 |
| `-E` | **仅预处理**：输出预处理后的源代码 | 排查宏展开、头文件包含问题 |
| `-P` | **配合 `-E` 使用**：去掉 linemarker（`#line`） | 生成干净的可读预处理文件 |
| `-H` | **显示头文件包含链**：输出每个 `#include` 的嵌套深度 | 排查头文件冲突、找不到头文件、循环包含 |
| `-dM` | **配合 `-E` 使用**：只输出所有已定义的宏 | 检查宏定义是否正确 |
| `-Xclang <arg>` | **将参数直接传给 clang -cc1** | 需要传递 clang 前端专有选项 |
| `-Xarch_host <arg>` | **只传给 host 编译** | host 端需要单独加选项 |
| `-Xarch_device <arg>` | **只传给 device 编译** | device 端需要单独加选项 |

---

## 2. Warning 控制

| 选项 | 作用 | 典型场景 |
|------|------|----------|
| `-w` | **关闭所有 warning** | 临时屏蔽大量警告，专注看 error |
| `-Werror` | **所有 warning 视为 error** | CI 强制零警告 |
| `-Wno-error` | **warning 不视为 error** | 临时放宽，允许带警告编译通过 |
| `-W<warning>` | **开启特定 warning** | 如 `-Wall`、`-Wextra` |
| `-Wno-<warning>` | **关闭特定 warning** | 如 `-Wno-unused-variable` |
| `-Qunused-arguments` | **不报告未使用的参数** | 某些参数只在特定阶段使用，避免误报 |

---

## 3. HIP / ROCm 路径与架构

| 选项 | 作用 | 典型场景 |
|------|------|----------|
| `--offload-arch=<arch>` | **指定 GPU 架构** | 如 `gfx908`、`gfx90a`、`gfx1030`。可多次指定以编译多架构 |
| `--hip-path=<path>` | **指定 HIP 运行时路径** | 系统有多个 HIP 安装时使用 |
| `--rocm-path=<path>` | **指定 ROCm 安装路径** | 自动链接所需 bitcode 库 |
| `--hip-link` | **链接 HIP offload bundles** | 最终链接阶段需要 |
| `-no-hip-rt` | **不链接 HIP 运行时库** | 做纯设备代码编译或特殊链接时 |
| `-nogpuinc` | **不添加 CUDA/HIP 默认 include 路径** | 完全自定义头文件路径 |
| `-nohipwrapperinc` | **不包含默认 HIP wrapper 头文件** | 避免 wrapper 头引入冲突 |

---

## 4. 编译模式（Host / Device 分离）

| 选项 | 作用 | 典型场景 |
|------|------|----------|
| `--offload-host-device` | **同时编译 host 和 device**（默认） | 常规单源异构编译 |
| `--offload-host-only` | **仅编译 host 端** | 只想生成 host 对象文件 |
| `--offload-device-only` | **仅编译 device 端** | 只想生成 device 对象文件 / bundle |
| `-fgpu-rdc` | **生成可重定位设备代码**（relocatable device code） | 多文件 device 代码需要跨文件调用时 |
| `-fno-gpu-rdc` | 关闭 RDC 模式 | 默认行为，编译更快但不可跨文件调用 device 函数 |

---

## 5. 设备库与链接

| 选项 | 作用 | 典型场景 |
|------|------|----------|
| `--offloadlib` | **链接 device libraries** | GPU device 编译时自动链接标准库 |
| `--no-offloadlib` | **不链接 device libraries** | 最小化编译或自定义 device 库时 |
| `--hip-device-lib=<value>` | 指定 HIP device library | 使用非默认 device bitcode 库 |
| `--gpu-bundle-output` | **打包 device 编译输出** | 生成可被 host 链接的 bundle |
| `--no-gpu-bundle-output` | 不打包 device 输出 | 查看原始 device 对象 |

---

## 6. 其他常用选项

| 选项 | 作用 | 典型场景 |
|------|------|----------|
| `-c` | **只编译不链接** | 生成 `.o` 对象文件 |
| `-S` | **只编译到汇编** | 生成 `.s` 汇编文件 |
| `-emit-llvm` | **输出 LLVM IR**（`.ll` 或 `.bc`） | 分析 LLVM 中间表示 |
| `-std=<value>` | 指定 C++ 标准 | 如 `-std=c++17`、`-std=c++20` |
| `--target=<triple>` | 指定目标 triple | 交叉编译时使用 |
| `-mcode-object-version=<N>` | 指定 AMDGPU code object 版本 | AMDGPU 专有，默认通常为 6 |

---

## 7. 快速排查流程（Agent Checklist）

当用户遇到 hipcc 编译问题时，可按以下顺序检查：

1. **加 `-v` 或 `-###` 看实际命令**：确认参数是否被正确传递到底层 clang++。
2. **加 `--save-temps` 保留中间文件**：检查预处理输出（`.ii`）或 LLVM IR（`.bc`）。
3. **确认 `--offload-arch` 是否正确**：错误架构会导致 `error: unknown target CPU` 或运行时找不到 kernel。
4. **检查头文件路径**：使用 `-H` 查看包含链，确认是否引用了错误的 HIP 头文件。
5. **分离 host/device 编译**：分别使用 `--offload-host-only` 和 `--offload-device-only` 缩小问题范围。
6. **是否缺少 `--hip-link`**：如果报错 `undefined reference to __hipRegisterFatBinary` 等，多半是最终链接时没加 `--hip-link`。
7. **PowerShell 超长命令**：若 `-v` 输出的 `-cc1` 命令在 PowerShell 中直接执行报错，使用本 Skill 的 `--to-rsp` 或 `--to-stop-parsing` 功能。

---

## 参考

- 完整 hipcc help 输出已保存至：`D:\projects\hipcc_help.txt`
- 查询完整选项可用：`C:\hipSDK\bin\hipcc.exe --help | findstr <keyword>`
