# NAS File Batch Download Skill

从 NAS 批量下载文件，支持 JSON 配置解析、自动解压和目录合并。

## 依赖安装

```bash
pip install paramiko
```

## 使用方法

### 环境变量配置（推荐）

```bash
# 设置环境变量
export NAS_HOST=<your_nas_host>
export NAS_PORT=22
export NAS_USER=<your_username>
export NAS_PASSWD=<your_password>

# 然后运行命令（无需重复输入连接信息）
python main.py --config-json SW_LSCLR_BinaryMsg.json
python main.py --config-json SW_LSCLR_BinaryMsg.json --id 579
```

### 默认行为（推荐）

下载最新版本，自动解压并合并到 `temp_<binaryId>/hipSDK`：

```bash
python main.py --config-json SW_LSCLR_BinaryMsg.json --extract
```

执行流程：
1. 自动检测最新 binary ID（如 601）
2. 下载文件到 `./temp_601/` 目录
3. 解压所有 zip 文件
4. 合并到 `./temp_601/hipSDK/` 目录
5. 删除解压后的源目录（保留 zip）

### 1. 从 JSON 配置文件下载

支持两种 JSON 格式：

#### 格式 A: SW_LSCLR 格式（自动解析 commit-id）

```bash
# 下载最新版本到 temp_<binaryId>/ 目录
python main.py --config-json SW_LSCLR_BinaryMsg.json --extract

# 下载指定版本到 temp_579/ 目录
python main.py --config-json SW_LSCLR_BinaryMsg.json --id 579 --extract

# 下载并保留 zip 文件（默认删除）
python main.py --config-json SW_LSCLR_BinaryMsg.json --extract --keep-zip

# 下载、解压并合并到目标目录
python main.py --config-json SW_LSCLR_BinaryMsg.json --id 579 \
               --extract --merge-to ../target \
               -H <NAS_HOST> -u <USERNAME> -p <PASSWORD>
```

#### 格式 B: 自定义文件列表

```json
{
    "files": [
        {"remote": "/shared/file1.zip", "local": "file1.zip"},
        {"remote": "/shared/file2.zip", "local": "file2.zip"}
    ]
}
```

```bash
python main.py --config-json files.json -H <NAS_HOST> -u <USERNAME> -p <PASSWORD>
```

### 2. 直接指定文件列表

```bash
python main.py -H <NAS_HOST> -u <USERNAME> -p <PASSWORD> \
               -r "/shared/file1.zip,/shared/file2.zip" \
               -o ./downloads
```

### 3. 高级用法

```bash
# 指定 SFTP 端口（默认 22）
python main.py -H <NAS_HOST> -P 2222 -u <USERNAME> -p <PASSWORD> ...

# 下载后解压但不保留 zip
python main.py ... --extract -o ./output

# 下载后解压并合并到 hipSDK 目录
python main.py ... --extract --merge-to C:/hipSDK

# 下载后解压但保留 zip 文件
python main.py ... --extract --keep-zip

# 安静模式
python main.py ... -q
```

## 参数说明

| 参数 | 简写 | 说明 | 默认值 | 环境变量 |
|------|------|------|--------|----------|
| `--host` | `-H` | NAS 主机地址 | 必填 | `NAS_HOST` |
| `--port` | `-P` | SFTP 端口 | 22 | `NAS_PORT` |
| `--user` | `-u` | 用户名 | 必填 | `NAS_USER` |
| `--password` | `-p` | 密码 | 必填 | `NAS_PASSWD` |
| `--config-json` | | JSON 配置文件路径 | | |
| `--id` | | 二进制 ID（默认最新） | | |
| `--remote-files` | `-r` | 逗号分隔的文件路径 | | |
| `--output` | `-o` | 输出目录 | `./downloads` | |
| `--extract` | | 解压 zip 文件 | false | |
| `--keep-zip` | | 保留 zip 文件 | false | |
| `--merge-to` | | 合并到目标目录 | | |
| `--quiet` | `-q` | 安静模式 | false | |

## 作为 Python 模块调用

```python
from main import batch_download, load_json_config, SftpDownloader

# 加载配置
config = load_json_config("SW_LSCLR_BinaryMsg.json", binary_id=579)

# 连接 NAS 并解析文件列表
downloader = SftpDownloader("<NAS_HOST>", 22, "<USER>", "<PASS>")
downloader.connect()
files = resolve_files_from_config(config, downloader)
downloader.disconnect()

# 批量下载
results = batch_download(
    host="<NAS_HOST>",
    port=22,
    username="<USER>",
    password="<PASS>",
    files=files,
    output_dir="./downloads",
    extract=True,
    keep_zip=False,
    merge_to="../target",
    verbose=True
)
```

## 输出示例

```
Loading config: SW_LSCLR_BinaryMsg.json
Using binary_id: 579
Found 4 files to download

[1/4] rocm_systems-lst-43-64d7c3d71fcdb170a893b3e237e853771685279a.zip
  Remote: /shared/aws_binary/SW_LSCLR/rocm_systems-lst/43-64d7c3d71fcdb170a893b3e237e853771685279a.zip
  [OK] Downloaded (3366545 bytes)

[2/4] llvm-lst-xxx.zip
  ...

============================================================
Extracting archives...
  Extracting: rocm_systems-lst-43-xxx.zip
  Removed: rocm_systems-lst-43-xxx.zip

============================================================
Merging to: ../target
  [OK] Merged comgr-install
  [OK] Merged llvm-lst-install
  [OK] Merged rocm_systems-install
Merge completed!

============================================================
Download Summary:
  Success: 4/4
  Failed: 0
  Output: D:\projects\downloads\579
```

## 目录结构

所有文件都在 `temp_<binaryId>/` 目录下：

### 默认执行后的结构

```
script-directory/
└── temp_601/                     # temp_<binaryId> 目录
    ├── hipSDK/                  # 合并后的目标目录
    │   ├── bin/
    │   ├── include/
    │   ├── lib/
    │   └── ...
    └── (zip files deleted)      # 默认删除压缩包
```

### 使用 `--keep-zip` 后的结构

```
temp_601/                         # temp_<binaryId> 目录
├── hipSDK/                      # 合并后的 hipSDK
│   ├── bin/
│   ├── include/
│   └── ...
├── 287-xxx.zip                  # 保留的压缩包
├── 32-xxx.zip
├── 42-xxx.zip
└── 46-xxx.zip
```

## 注意事项

- 首次使用需要安装 `paramiko` 库
- SFTP 连接使用默认端口 22
- 支持自动重连和错误处理
- 合并目录时会递归合并子目录
- 解压后会自动识别常见的安装目录结构
- 默认合并目标为 `temp/hipSDK`，可自定义
