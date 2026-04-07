# NAS File Download Skill

从 Synology NAS 下载文件到本地目录。

## 依赖安装

```bash
pip install synology-api
```

## 使用方法

### 命令行方式

```bash
# 基本用法
python main.py -H <NAS_HOST> -u <USERNAME> -p <PASSWORD> -r <REMOTE_PATH>

# 指定 NAS 地址和输出目录
python main.py -H <NAS_HOST> -P 5001 -u <USERNAME> -p <PASSWORD> -r /shared/data.zip -o ./downloads

# 使用 HTTP (非 HTTPS)
python main.py -H <NAS_HOST> -u <USERNAME> -p <PASSWORD> -r /shared/file.zip --insecure
```

### 参数说明

| 参数 | 简写 | 说明 | 默认值 |
|------|------|------|--------|
| `--nas-host` | `-H` | NAS IP 地址或主机名 | 必填 |
| `--nas-port` | `-P` | NAS 端口 | 5001 |
| `--user` | `-u` | 用户名 | 必填 |
| `--password` | `-p` | 密码 | 必填 |
| `--remote-path` | `-r` | NAS 文件路径 | 必填 |
| `--output-dir` | `-o` | 本地保存目录 | 当前目录 |
| `--insecure` | - | 使用 HTTP | HTTPS |

### 作为 Python 模块调用

```python
from main import download_from_nas

result = download_from_nas(
    nas_host="<NAS_HOST>",
    nas_port="5001",
    user="<USERNAME>",
    password="<PASSWORD>",
    remote_path="/shared/file.zip",
    output_dir="./downloads"
)

print(result)
# {
#     "success": True,
#     "file_path": "D:/projects/downloads/file.zip",
#     "file_size": 12345678,
#     "message": "Download completed: file.zip (12345678 bytes)"
# }
```

## 示例

```bash
# 下载单个文件
python main.py -H 192.168.1.100 -u admin -p secret -r /shared/data.zip

# 下载到指定目录
python main.py -H 192.168.1.100 -u admin -p secret -r /shared/data.zip -o C:/temp
```

## 注意事项

- 首次使用需要安装 `synology-api` 库
- 默认使用 HTTPS 连接（忽略自签名证书警告）
- 下载的文件会保留原文件名
- 如果本地文件已存在，会被覆盖
