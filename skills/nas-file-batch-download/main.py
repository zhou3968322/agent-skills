#!/usr/bin/env python3
"""
NAS File Batch Download Skill
从 Synology NAS 批量下载文件到本地目录，支持 JSON 配置、解压和合并

Usage:
    # 从 JSON 文件读取配置下载
    python main.py --config-json <path> --id <binary_id> -H <host> -u <user> -p <pass>
    
    # 直接指定文件列表下载
    python main.py -H <host> -u <user> -p <pass> -r "/path/file1.zip,/path/file2.zip"
    
    # 下载后解压并合并到目标目录
    python main.py --config-json <path> --id <binary_id> --extract --merge-to ../target
"""

import os
import sys
import argparse
import json
import shutil
import zipfile
from pathlib import Path
from typing import List, Dict, Optional


class SftpDownloader:
    """SFTP 下载器"""
    
    def __init__(self, host: str, port: int, username: str, password: str):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self._sftp = None
        self._transport = None
        
    def connect(self):
        """建立 SFTP 连接"""
        try:
            import paramiko
            self._transport = paramiko.Transport((self.host, self.port))
            self._transport.connect(username=self.username, password=self.password)
            self._sftp = paramiko.SFTPClient.from_transport(self._transport)
            return True
        except Exception as e:
            print(f"[ERROR] SFTP connection failed: {e}")
            return False
    
    def disconnect(self):
        """关闭 SFTP 连接"""
        if self._sftp:
            self._sftp.close()
        if self._transport:
            self._transport.close()
    
    def listdir(self, remote_dir: str) -> List[str]:
        """列出远程目录文件"""
        try:
            return self._sftp.listdir(remote_dir)
        except Exception as e:
            print(f"[ERROR] Failed to list directory {remote_dir}: {e}")
            return []
    
    def download(self, remote_path: str, local_path: str) -> bool:
        """下载单个文件"""
        try:
            # 确保本地目录存在
            Path(local_path).parent.mkdir(parents=True, exist_ok=True)
            self._sftp.get(remote_path, local_path)
            return True
        except Exception as e:
            print(f"[ERROR] Download failed {remote_path}: {e}")
            return False


def load_json_config(json_path: str, binary_id: Optional[int] = None) -> Dict:
    """
    从 JSON 文件加载下载配置
    
    支持两种格式:
    1. 自定义格式: {"files": [{"remote": "...", "local": "..."}]}
    2. SW_LSCLR 格式: {"RECORDS": [{"id": 1, "component": "commit-id"}]}
    """
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    result = {
        "files": [],
        "lib_mapping": {},
        "remote_base_dir": "",
        "valid_libs": []
    }
    
    # 检查是否是 SW_LSCLR 格式
    if "RECORDS" in data or any(str(k).isdigit() for k in data.keys()):
        # 找到指定的 binary_id 或最新版本
        if binary_id is None:
            # 从顶层键和 RECORDS 数组获取所有有效 ID
            valid_ids = [int(k) for k in data.keys() if str(k).isdigit()]
            if "RECORDS" in data:
                valid_ids.extend([r["id"] for r in data["RECORDS"] if "id" in r])
            binary_id = max(valid_ids) if valid_ids else None
            if binary_id:
                print(f"Auto-detected latest binary_id: {binary_id}")
        
        if binary_id is None:
            raise ValueError("No valid binary_id found in JSON")
        
        binary_id_str = str(binary_id)
        record = None
        
        # 优先从顶层键查找
        if binary_id_str in data:
            record = data[binary_id_str]
        # 再从 RECORDS 数组查找
        elif "RECORDS" in data:
            for r in data["RECORDS"]:
                if r.get("id") == binary_id:
                    record = r
                    break
        
        if not record:
            raise ValueError(f"binary_id={binary_id} not found in JSON")
        
        # 组件名到目录名的映射
        result["lib_mapping"] = {
            "llvm_lst": "llvm-lst",
            "devlib_lst": "devlib-lst",
            "comgr_lst": "comgr-lst",
            "rocm_systems_lst": "rocm_systems-lst",
            "hipamd_lst": "hipamd-lst",
            "rocclr_lst": "rocclr-lst",
            "hip_lst": "hip-lst",
            "rocblas_lst": "rocblas-lst",
            "hipblas_lst": "hipblas-lst",
            "rocprim_lst": "rocprim-lst",
            "hipprim_lst": "hipprim-lst",
            "rocrand_lst": "rocrand-lst",
            "hiprand_lst": "hiprand-lst",
            "rocsolver_lst": "rocsolver-lst",
            "hipsolver_lst": "hipsolver-lst",
            "rocsparse_lst": "rocsparse-lst",
            "hipsparse_lst": "hipsparse-lst",
            "rocfft_lst": "rocfft-lst",
            "hipfft_lst": "hipfft-lst",
        }
        result["valid_libs"] = ["comgr-lst", "devlib-lst", "llvm-lst", "rocm_systems-lst"]
        result["remote_base_dir"] = "/shared/aws_binary/SW_LSCLR"
        result["binary_id"] = binary_id
        result["record"] = record
        
    elif "files" in data:
        # 自定义格式
        result["files"] = data["files"]
    
    return result


def resolve_files_from_config(
    config: Dict,
    downloader: SftpDownloader
) -> List[Dict]:
    """
    根据配置解析实际要下载的文件列表
    对于 SW_LSCLR 格式，需要在远程目录中查找匹配 commit-id 的文件
    """
    files = config.get("files", [])
    
    if not files and "record" in config:
        # SW_LSCLR 格式，需要查找远程文件
        record = config["record"]
        lib_mapping = config["lib_mapping"]
        valid_libs = config["valid_libs"]
        base_dir = config["remote_base_dir"]
        skip_fields = ["id", "cur_change", "change_owner"]
        
        for key, value in record.items():
            if key in skip_fields or not value or value == " ":
                continue
            
            # 检查是否是有效的 commit-id 格式
            if "-" not in str(value):
                continue
            
            lib_name = lib_mapping.get(key, key.replace("_", "-"))
            
            # 如果指定了 valid_libs，只下载这些库
            if valid_libs and lib_name not in valid_libs:
                continue
            
            remote_dir = f"{base_dir}/{lib_name}"
            remote_files = downloader.listdir(remote_dir)
            
            # 查找包含 commit-id 的 zip 文件
            for f in remote_files:
                if value in f and f.endswith('.zip'):
                    files.append({
                        "remote": f"{remote_dir}/{f}",
                        "local": f,
                        "lib_name": lib_name,
                        "commit_id": value
                    })
                    break
    
    return files


def extract_archive(zip_path: str, extract_to: str, remove_after: bool = False) -> bool:
    """解压 zip 文件"""
    try:
        print(f"  Extracting: {Path(zip_path).name}")
        with zipfile.ZipFile(zip_path, 'r') as zf:
            zf.extractall(extract_to)
        
        if remove_after:
            os.remove(zip_path)
            print(f"  Removed: {Path(zip_path).name}")
        
        return True
    except Exception as e:
        print(f"  [ERROR] Extraction failed: {e}")
        return False


def merge_directories(src_dir: str, dst_dir: str):
    """递归合并目录"""
    src_path = Path(src_dir)
    dst_path = Path(dst_dir)
    
    if not src_path.exists():
        return
    
    dst_path.mkdir(parents=True, exist_ok=True)
    
    for item in src_path.iterdir():
        src_item = item
        dst_item = dst_path / item.name
        
        if item.is_dir():
            merge_directories(str(src_item), str(dst_item))
        else:
            dst_item.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_item, dst_item)


def batch_download(
    host: str,
    port: int,
    username: str,
    password: str,
    files: List[Dict],
    output_dir: str,
    extract: bool = False,
    keep_zip: bool = True,
    merge_to: Optional[str] = None,
    verbose: bool = True
) -> List[Dict]:
    """
    批量下载文件
    
    Args:
        host: NAS 主机
        port: SFTP 端口
        username: 用户名
        password: 密码
        files: 文件列表，每项包含 remote 和 local
        output_dir: 输出目录
        extract: 是否解压
        keep_zip: 是否保留 zip 文件
        merge_to: 解压后合并到的目标目录
        verbose: 是否打印详细信息
    
    Returns:
        下载结果列表
    """
    # 创建下载器
    downloader = SftpDownloader(host, port, username, password)
    
    if not downloader.connect():
        return [{"success": False, "message": "Failed to connect to NAS"}]
    
    output_path = Path(output_dir).resolve()
    output_path.mkdir(parents=True, exist_ok=True)
    
    results = []
    downloaded_files = []
    
    try:
        for i, file_info in enumerate(files, 1):
            remote = file_info["remote"]
            local = file_info["local"]
            local_path = str(output_path / local)
            
            if verbose:
                print(f"\n[{i}/{len(files)}] {local}")
                print(f"  Remote: {remote}")
            
            success = downloader.download(remote, local_path)
            
            if success:
                size = Path(local_path).stat().st_size
                results.append({
                    "success": True,
                    "remote": remote,
                    "local": local_path,
                    "size": size,
                    "message": f"Downloaded ({size} bytes)"
                })
                downloaded_files.append((local_path, local))
                if verbose:
                    print(f"  [OK] Downloaded ({size} bytes)")
            else:
                results.append({
                    "success": False,
                    "remote": remote,
                    "local": local_path,
                    "message": "Download failed"
                })
                if verbose:
                    print(f"  [FAIL] Download failed")
    finally:
        downloader.disconnect()
    
    # 解压文件
    if extract and downloaded_files:
        if verbose:
            print(f"\n{'='*60}")
            print("Extracting archives...")
        
        for local_path, filename in downloaded_files:
            if filename.endswith('.zip'):
                extract_archive(local_path, str(output_path), remove_after=not keep_zip)
    
    # 合并目录
    cleanup_sources = []
    if merge_to and Path(output_path).exists():
        if verbose:
            print(f"\n{'='*60}")
            print(f"Merging to: {merge_to}")
        
        merge_to_path = Path(merge_to).resolve()
        merge_to_path.mkdir(parents=True, exist_ok=True)
        
        # 合并常见的子目录
        for subdir in ["comgr-install", "devlib-lst-install", "llvm-lst-install", "rocm_systems-install"]:
            src = output_path / subdir
            if src.exists():
                for item in src.iterdir():
                    merge_directories(str(item), str(merge_to_path / item.name))
                cleanup_sources.append(src)  # 标记待清理
                if verbose:
                    print(f"  [OK] Merged {subdir}")
        
        if verbose:
            print(f"Merge completed!")
    
    # 清理解压后的源目录
    if merge_to and cleanup_sources:
        if verbose:
            print(f"\n{'='*60}")
            print("Cleaning up extracted directories...")
        for src in cleanup_sources:
            if src.exists():
                shutil.rmtree(src)
                if verbose:
                    print(f"  [OK] Removed {src.name}")
    
    # 打印汇总
    if verbose:
        success_count = sum(1 for r in results if r["success"])
        print(f"\n{'='*60}")
        print("Download Summary:")
        print(f"  Success: {success_count}/{len(files)}")
        print(f"  Failed: {len(files) - success_count}")
        print(f"  Output: {output_path}")
        if merge_to:
            print(f"  Merged to: {Path(merge_to).resolve()}")
    
    return results


def main():
    parser = argparse.ArgumentParser(
        description='Batch download files from NAS with JSON config support',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Update JSON file from NAS
    python main.py --update-json /shared/aws_binary/SW_LSCLR/SW_LSCLR_BinaryMsg.json -H <host> -u <user> -p <pass>
    
    # Using environment variables for credentials
    export NAS_HOST=<host>
    export NAS_PORT=22
    export NAS_USER=<username>
    export NAS_PASSWD=<password>
    python main.py --config-json SW_LSCLR_BinaryMsg.json
    
    # Download latest version (auto-detect max ID)
    python main.py --config-json SW_LSCLR_BinaryMsg.json -H <host> -u <user> -p <pass>
    
    # Download specific binary ID to ./186 directory
    python main.py --config-json SW_LSCLR_BinaryMsg.json --id 186 -H <host> -u <user> -p <pass>
    
    # Download to custom directory
    python main.py --config-json SW_LSCLR_BinaryMsg.json --id 186 -o my_binaries -H <host> -u <user> -p <pass>
    
    # Download and keep zip files
    python main.py --config-json SW_LSCLR_BinaryMsg.json --id 186 --extract --keep-zip -H <host> -u <user> -p <pass>
    
    # Download with extract and merge to hipSDK
    python main.py --config-json config.json --extract --merge-to ../target -H <host> -u <user> -p <pass>
    
    # Direct file list download
    python main.py -H <host> -u <user> -p <pass> -r "/path/file1.zip,/path/file2.zip"
        """
    )
    
    # NAS 连接参数（支持环境变量）
    parser.add_argument('-H', '--host', 
                        default=os.environ.get('NAS_HOST'),
                        help='NAS host (or set NAS_HOST env var)')
    parser.add_argument('-P', '--port', 
                        type=int, 
                        default=int(os.environ.get('NAS_PORT', 22)),
                        help='SFTP port (default: 22 or NAS_PORT env var)')
    parser.add_argument('-u', '--user', 
                        default=os.environ.get('NAS_USER'),
                        help='Username (or set NAS_USER env var)')
    parser.add_argument('-p', '--password', 
                        default=os.environ.get('NAS_PASSWD'),
                        help='Password (or set NAS_PASSWD env var)')
    
    # 配置参数
    parser.add_argument('--config-json', help='JSON config file path')
    parser.add_argument('--id', type=int, help='Binary ID to download (default: latest)')
    parser.add_argument('-r', '--remote-files', help='Comma-separated remote file paths')
    parser.add_argument('-o', '--output', default='./downloads', help='Output directory')
    
    # 操作参数
    parser.add_argument('--extract', action='store_true', help='Extract zip files after download')
    parser.add_argument('--keep-zip', action='store_true', help='Keep zip files after extraction')
    parser.add_argument('--merge-to', help='Merge extracted files to target directory')
    parser.add_argument('-q', '--quiet', action='store_true', help='Quiet mode')
    parser.add_argument('--update-json', metavar='REMOTE_PATH',
                        help='Download/Update JSON file from NAS (specify remote path)')
    
    args = parser.parse_args()
    
    verbose = not args.quiet
    files = []
    
    # merge_to 将在知道 binary_id 后设置
    
    # 处理仅更新 JSON 文件
    if args.update_json:
        if not args.host or not args.user or not args.password:
            print("[ERROR] NAS connection info required for updating JSON")
            return 1
        
        print(f"Downloading JSON from: {args.update_json}")
        downloader = SftpDownloader(args.host, args.port, args.user, args.password)
        if not downloader.connect():
            print("[ERROR] Failed to connect to NAS")
            return 1
        
        local_path = Path(args.update_json).name
        success = downloader.download(args.update_json, str(local_path))
        downloader.disconnect()
        
        if success:
            print(f"[OK] JSON downloaded to: {local_path}")
            return 0
        else:
            print("[ERROR] Failed to download JSON")
            return 1
    
    # 验证必需参数
    if not args.host:
        print("[ERROR] NAS host is required. Provide via --host or NAS_HOST environment variable.")
        return 1
    if not args.user:
        print("[ERROR] Username is required. Provide via --user or NAS_USER environment variable.")
        return 1
    if not args.password:
        print("[ERROR] Password is required. Provide via --password or NAS_PASSWD environment variable.")
        return 1
    
    # 从 JSON 加载配置
    if args.config_json:
        json_path = args.config_json
        
        # 如果文件不存在，尝试从 NAS 下载
        if not Path(json_path).exists():
            # 尝试默认远程路径
            default_remote = "/shared/aws_binary/SW_LSCLR/SW_LSCLR_BinaryMsg.json"
            if json_path.endswith("SW_LSCLR_BinaryMsg.json") or json_path == "SW_LSCLR_BinaryMsg.json":
                remote_json = default_remote
            else:
                remote_json = None
            
            if remote_json:
                print(f"Local JSON not found: {json_path}")
                print(f"Downloading from NAS: {remote_json}")
                
                downloader = SftpDownloader(args.host, args.port, args.user, args.password)
                if not downloader.connect():
                    print("[ERROR] Failed to connect to NAS")
                    return 1
                
                success = downloader.download(remote_json, str(json_path))
                downloader.disconnect()
                
                if success:
                    print(f"[OK] JSON downloaded to: {json_path}")
                else:
                    print("[ERROR] Failed to download JSON from NAS")
                    return 1
            else:
                print(f"[ERROR] JSON file not found: {json_path}")
                return 1
        
        if verbose:
            print(f"Loading config: {json_path}")
        
        try:
            config = load_json_config(json_path, args.id)
            
            # 如果用户没有指定输出目录，使用 temp_<binaryId> 作为目录名
            detected_id = config.get('binary_id')
            if args.output == './downloads' and detected_id:
                args.output = f"temp_{detected_id}"
            
            # 设置默认 merge 目标为 <output>/hipSDK
            merge_to = args.merge_to
            if merge_to is None and args.extract:
                merge_to = f"{args.output}/hipSDK"
            
            if args.id and "binary_id" in config:
                print(f"Using binary_id: {config['binary_id']}")
            
            # 需要先连接才能解析文件列表
            downloader = SftpDownloader(args.host, args.port, args.user, args.password)
            if not downloader.connect():
                print("[ERROR] Failed to connect to NAS")
                return 1
            
            files = resolve_files_from_config(config, downloader)
            downloader.disconnect()
            
            if verbose:
                print(f"Found {len(files)} files to download")
        
        except Exception as e:
            print(f"[ERROR] Failed to load config: {e}")
            return 1
    
    # 从命令行参数解析
    elif args.remote_files:
        paths = [p.strip() for p in args.remote_files.split(',') if p.strip()]
        files = [{"remote": p, "local": Path(p).name} for p in paths]
        # 非 JSON 模式下使用默认 merge 目标
        merge_to = args.merge_to
        if merge_to is None and args.extract:
            merge_to = "temp/hipSDK"
    
    else:
        print("[ERROR] Please provide --config-json or --remote-files")
        return 1
    
    if not files:
        print("[ERROR] No files to download")
        return 1
    
    # 执行批量下载
    results = batch_download(
        host=args.host,
        port=args.port,
        username=args.user,
        password=args.password,
        files=files,
        output_dir=args.output,
        extract=args.extract,
        keep_zip=args.keep_zip,
        merge_to=merge_to,
        verbose=verbose
    )
    
    success_count = sum(1 for r in results if r["success"])
    return 0 if success_count > 0 else 1


if __name__ == '__main__':
    sys.exit(main())
