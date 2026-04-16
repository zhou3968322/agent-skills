#!/usr/bin/env python3
"""
arXiv Paper API Client
基于 data.rag.ac.cn 的免费 arXiv API
"""

import argparse
import json
import os
import sys
from typing import Dict, List, Optional

import requests


class ArxivAPIError(Exception):
    """arXiv API 错误"""
    pass


class ArxivClient:
    """arXiv API 客户端"""
    
    BASE_URL = "https://data.rag.ac.cn/arxiv/"
    
    def __init__(self, token: Optional[str] = None):
        """
        初始化客户端
        
        Args:
            token: API Token，如果不提供则从环境变量 ARXIV_API_TOKEN 读取
        """
        self.token = token or os.environ.get("ARXIV_API_TOKEN")
        if not self.token:
            raise ValueError(
                "API Token 是必需的。请提供 token 参数或设置 ARXIV_API_TOKEN 环境变量。"
                "注册获取 Token: https://data.rag.ac.cn/register"
            )
        
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'arxiv-reader-client/1.0'
        })
    
    def _make_request(self, params: Dict) -> Dict:
        """发送 API 请求"""
        try:
            response = self.session.get(
                self.BASE_URL,
                params=params,
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            if response.status_code == 401:
                raise ArxivAPIError("Token 无效或已过期，请检查 Token 是否正确")
            elif response.status_code == 404:
                raise ArxivAPIError(f"论文未找到，请检查 arXiv ID 是否正确")
            else:
                raise ArxivAPIError(f"API 请求失败: {e}")
        except requests.exceptions.RequestException as e:
            raise ArxivAPIError(f"网络请求失败: {e}")
    
    def get_brief(self, arxiv_id: str) -> Dict:
        """
        获取论文元数据（推荐）
        
        Args:
            arxiv_id: arXiv 论文 ID，如 "2604.05843"
        
        Returns:
            包含 title, tldr, keywords, publish_at, citations, src_url, github_url 的字典
        """
        params = {
            "type": "brief",
            "arxiv_id": arxiv_id,
            "token": self.token
        }
        return self._make_request(params)
    
    def get_raw(self, arxiv_id: str) -> Dict:
        """
        获取完整论文内容
        
        Args:
            arxiv_id: arXiv 论文 ID
        
        Returns:
            包含完整 Markdown 格式论文内容的字典
        """
        params = {
            "type": "raw",
            "arxiv_id": arxiv_id,
            "token": self.token
        }
        return self._make_request(params)
    
    def get_head(self, arxiv_id: str) -> Dict:
        """
        获取论文摘要信息
        
        Args:
            arxiv_id: arXiv 论文 ID
        
        Returns:
            包含 title, abstract, authors, sections, categories, publish_at 的字典
        """
        params = {
            "type": "head",
            "arxiv_id": arxiv_id,
            "token": self.token
        }
        return self._make_request(params)
    
    def get_section(self, arxiv_id: str, section: str) -> Dict:
        """
        获取论文特定章节
        
        Args:
            arxiv_id: arXiv 论文 ID
            section: 章节名称，如 "Introduction", "Methods", "Results"
        
        Returns:
            包含指定章节内容的字典
        """
        params = {
            "type": "section",
            "arxiv_id": arxiv_id,
            "section": section,
            "token": self.token
        }
        return self._make_request(params)
    
    def batch_get_brief(self, arxiv_ids: List[str]) -> List[Dict]:
        """
        批量获取论文元数据
        
        Args:
            arxiv_ids: arXiv 论文 ID 列表
        
        Returns:
            论文元数据列表
        """
        results = []
        for arxiv_id in arxiv_ids:
            try:
                data = self.get_brief(arxiv_id)
                results.append(data)
            except ArxivAPIError as e:
                results.append({"arxiv_id": arxiv_id, "error": str(e)})
        return results


def format_brief(data: Dict) -> str:
    """格式化 brief 输出"""
    lines = []
    lines.append("=" * 60)
    lines.append(f"标题: {data.get('title', 'N/A')}")
    lines.append("=" * 60)
    
    if data.get('tldr'):
        lines.append(f"\n📄 TLDR: {data['tldr']}")
    
    if data.get('keywords'):
        lines.append(f"\n🔑 关键词: {', '.join(data['keywords'])}")
    
    if data.get('publish_at'):
        lines.append(f"\n📅 发表日期: {data['publish_at']}")
    
    if data.get('citations') is not None:
        lines.append(f"📊 引用数: {data['citations']}")
    
    if data.get('src_url'):
        lines.append(f"\n📥 PDF: {data['src_url']}")
    
    if data.get('github_url'):
        lines.append(f"💻 GitHub: {data['github_url']}")
    
    return "\n".join(lines)


def format_head(data: Dict) -> str:
    """格式化 head 输出"""
    lines = []
    lines.append("=" * 60)
    lines.append(f"标题: {data.get('title', 'N/A')}")
    lines.append("=" * 60)
    
    if data.get('authors'):
        lines.append(f"\n👥 作者: {', '.join(data['authors'])}")
    
    if data.get('categories'):
        lines.append(f"\n🏷️  分类: {', '.join(data['categories'])}")
    
    if data.get('publish_at'):
        lines.append(f"\n📅 发表日期: {data['publish_at']}")
    
    if data.get('sections'):
        lines.append(f"\n📑 章节: {', '.join(data['sections'])}")
    
    if data.get('abstract'):
        lines.append(f"\n📝 摘要:\n{data['abstract']}")
    
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description='arXiv Paper API Client - 免费获取 arXiv 论文',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 获取论文元数据
  python arxiv_client.py --token YOUR_TOKEN --id 2604.05843 --type brief
  
  # 获取完整论文
  python arxiv_client.py --token YOUR_TOKEN --id 2604.05843 --type raw
  
  # 从环境变量读取 token
  python arxiv_client.py --id 2604.05843 --type brief
  
  # 批量获取
  python arxiv_client.py --token YOUR_TOKEN --id 2604.05843,2401.12345 --type brief
        """
    )
    parser.add_argument('--token', '-t', help='API Token (或设置 ARXIV_API_TOKEN 环境变量)')
    parser.add_argument('--id', '-i', required=True, help='arXiv 论文 ID (支持多个用逗号分隔)')
    parser.add_argument('--type', choices=['brief', 'raw', 'head', 'section'], 
                       default='brief', help='查询类型 (默认: brief)')
    parser.add_argument('--section', '-s', help='章节名称 (仅 section 类型需要)')
    parser.add_argument('--output', '-o', help='输出文件路径 (JSON 格式)')
    parser.add_argument('--pretty', '-p', action='store_true', help='美化输出')
    
    args = parser.parse_args()
    
    # 解析 ID 列表
    arxiv_ids = [id.strip() for id in args.id.split(',')]
    
    try:
        client = ArxivClient(token=args.token)
        
        results = []
        for arxiv_id in arxiv_ids:
            try:
                if args.type == 'brief':
                    data = client.get_brief(arxiv_id)
                    if args.pretty and len(arxiv_ids) == 1:
                        print(format_brief(data))
                    else:
                        results.append(data)
                
                elif args.type == 'raw':
                    data = client.get_raw(arxiv_id)
                    if args.pretty and len(arxiv_ids) == 1:
                        print(f"标题: {data.get('title', 'N/A')}")
                        print(f"\n{data.get('content', '')[:2000]}...")
                    else:
                        results.append(data)
                
                elif args.type == 'head':
                    data = client.get_head(arxiv_id)
                    if args.pretty and len(arxiv_ids) == 1:
                        print(format_head(data))
                    else:
                        results.append(data)
                
                elif args.type == 'section':
                    if not args.section:
                        print("错误: --section 参数是必需的 (当 type=section 时)", file=sys.stderr)
                        sys.exit(1)
                    data = client.get_section(arxiv_id, args.section)
                    results.append(data)
                
            except ArxivAPIError as e:
                print(f"错误 [ID: {arxiv_id}]: {e}", file=sys.stderr)
                results.append({"arxiv_id": arxiv_id, "error": str(e)})
        
        # 输出 JSON
        if not args.pretty or len(arxiv_ids) > 1:
            output = json.dumps(results if len(results) > 1 else results[0], 
                              ensure_ascii=False, indent=2)
            
            if args.output:
                with open(args.output, 'w', encoding='utf-8') as f:
                    f.write(output)
                print(f"结果已保存到: {args.output}")
            else:
                print(output)
    
    except ValueError as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n已取消", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
