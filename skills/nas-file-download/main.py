#!/usr/bin/env python3
"""
NAS File Download Skill
从 Synology NAS 下载文件到本地目录

Usage:
    python main.py --user admin --password secret --remote-path /folder/file.zip
    python main.py -u admin -p secret -r /ARCH/data.zip -o ./downloads
"""

import os
import sys
import argparse
from pathlib import Path


def download_from_nas(nas_host: str, nas_port: str, user: str, password: str,
                      remote_path: str, output_dir: str = ".", secure: bool = True) -> dict:
    """
    从 Synology NAS 下载文件
    
    Args:
        nas_host: NAS IP 地址
        nas_port: NAS 端口
        user: 用户名
        password: 密码
        remote_path: NAS 上的文件路径
        output_dir: 本地保存目录
        secure: 是否使用 HTTPS
    
    Returns:
        dict: 包含 success, file_path, file_size, message 的结果字典
    """
    try:
        from synology_api.filestation import FileStation
        import requests
        import urllib3
    except ImportError:
        return {
            "success": False,
            "file_path": None,
            "file_size": 0,
            "message": "Error: synology-api not installed. Run: pip install synology-api requests"
        }
    
    # 禁用 SSL 警告
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    # 确保输出目录存在
    dest_dir = Path(output_dir).resolve()
    dest_dir.mkdir(parents=True, exist_ok=True)
    
    # 获取文件名
    file_name = Path(remote_path).name
    local_file = dest_dir / file_name
    
    print(f"Connecting to NAS {nas_host}:{nas_port}...")
    
    try:
        # 初始化 FileStation 连接
        fs = FileStation(
            nas_host,
            nas_port,
            user,
            password,
            secure=secure,
            cert_verify=False  # 忽略自签名证书警告
        )
        
        print(f"Downloading {remote_path}...")
        print(f"Save to: {local_file}")
        
        # 尝试方法1: 使用 get_file API
        try:
            result = fs.get_file(
                path=remote_path,
                mode='download',
                dest_path=str(dest_dir)
            )
            
            if local_file.exists():
                file_size = local_file.stat().st_size
                return {
                    "success": True,
                    "file_path": str(local_file),
                    "file_size": file_size,
                    "message": f"Download completed: {file_name} ({file_size} bytes)"
                }
        except Exception as e:
            print(f"Method 1 failed: {e}")
        
        # 尝试方法2: 直接通过 HTTP 下载
        print("Trying alternative download method...")
        
        # 构建下载 URL
        protocol = "https" if secure else "http"
        download_url = f"{protocol}://{nas_host}:{nas_port}/webapi/entry.cgi"
        
        # 获取 session id (可能是 _sid 或 session)
        sid = getattr(fs, '_sid', None) or getattr(fs, 'session', None)
        if not sid:
            # 尝试从 session 对象获取
            session_obj = getattr(fs, 'session', None)
            if session_obj:
                sid = getattr(session_obj, 'sid', None)
        
        print(f"Using session ID: {sid[:20]}..." if sid and len(str(sid)) > 20 else f"Using session ID: {sid}")
        
        params = {
            'api': 'SYNO.FileStation.Download',
            'version': '2',
            'method': 'download',
            'path': remote_path,
            'mode': 'download',
            '_sid': sid
        }
        
        response = requests.get(
            download_url,
            params=params,
            verify=False,
            stream=True,
            timeout=300
        )
        response.raise_for_status()
        
        # 保存文件
        with open(local_file, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        
        # 检查文件是否下载成功
        if local_file.exists():
            file_size = local_file.stat().st_size
            return {
                "success": True,
                "file_path": str(local_file),
                "file_size": file_size,
                "message": f"Download completed: {file_name} ({file_size} bytes)"
            }
        else:
            return {
                "success": False,
                "file_path": None,
                "file_size": 0,
                "message": "File not found after download"
            }
            
    except Exception as e:
        return {
            "success": False,
            "file_path": None,
            "file_size": 0,
            "message": f"Download failed: {str(e)}"
        }


def main():
    parser = argparse.ArgumentParser(description='Download file from Synology NAS')
    parser.add_argument('--nas-host', '-H', default='10.2.8.100',
                        help='NAS IP address (default: 10.2.8.100)')
    parser.add_argument('--nas-port', '-P', default='5001',
                        help='NAS port (default: 5001)')
    parser.add_argument('--user', '-u', required=True,
                        help='NAS username')
    parser.add_argument('--password', '-p', required=True,
                        help='NAS password')
    parser.add_argument('--remote-path', '-r', required=True,
                        help='File path on NAS, e.g., /folder/file.zip')
    parser.add_argument('--output-dir', '-o', default='.',
                        help='Local output directory (default: current directory)')
    parser.add_argument('--insecure', action='store_true',
                        help='Use HTTP instead of HTTPS')
    
    args = parser.parse_args()
    
    result = download_from_nas(
        nas_host=args.nas_host,
        nas_port=args.nas_port,
        user=args.user,
        password=args.password,
        remote_path=args.remote_path,
        output_dir=args.output_dir,
        secure=not args.insecure
    )
    
    print(result["message"])
    
    return 0 if result["success"] else 1


if __name__ == '__main__':
    sys.exit(main())
