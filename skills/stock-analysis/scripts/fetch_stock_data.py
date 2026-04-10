#!/usr/bin/env python3
"""
股票数据获取脚本 - 支持多数据源自动切换
数据源：新浪财经、东方财富、雪球
"""

import argparse
import json
import sys
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import requests
import pandas as pd
import numpy as np


class DataSourceError(Exception):
    """数据源错误"""
    pass


class StockDataFetcher:
    """股票数据获取器"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.0'
        })
    
    def normalize_code(self, stock_code: str) -> Tuple[str, str]:
        """
        标准化股票代码
        返回: (交易所代码, 纯数字代码)
        """
        code = stock_code.upper().strip()
        
        # 港股
        if '.HK' in code:
            return 'HK', code.replace('.HK', '')
        
        # 美股
        if code.isalpha():
            return 'US', code
        
        # A股处理
        code = code.replace('SH', '').replace('SZ', '').replace('.', '')
        
        # 判断交易所
        if code.startswith('6') or code.startswith('5') or code.startswith('9'):
            return 'SH', code  # 上交所
        elif code.startswith('0') or code.startswith('3') or code.startswith('2') or code.startswith('4'):
            return 'SZ', code  # 深交所
        else:
            return 'SH', code  # 默认上交所
    
    def fetch_from_sina(self, stock_code: str, days: int = 30) -> Optional[Dict]:
        """从新浪财经获取数据"""
        try:
            exchange, pure_code = self.normalize_code(stock_code)
            
            if exchange == 'US':
                # 美股
                symbol = f"gb_{pure_code.lower()}"
            elif exchange == 'HK':
                # 港股
                symbol = f"hk{pure_code}"
            else:
                # A股
                symbol = f"{exchange.lower()}{pure_code}"
            
            # 获取实时行情
            url = f"https://hq.sinajs.cn/list={symbol}"
            response = self.session.get(url, timeout=10)
            response.encoding = 'gb2312'
            
            if 'hq_str_' not in response.text or '=""' in response.text:
                return None
            
            # 解析实时数据
            data_str = response.text.split('="')[1].split('"')[0]
            fields = data_str.split(',')
            
            if exchange == 'US':
                # 美股格式: 名称,价格,涨跌幅,日期,时间...
                current_price = float(fields[1]) if len(fields) > 1 else 0
                name = fields[0] if fields else pure_code
                prev_close = current_price * 0.99  # 估算
            elif exchange == 'HK':
                # 港股格式
                name = fields[1] if len(fields) > 1 else pure_code
                current_price = float(fields[6]) if len(fields) > 6 else 0
                prev_close = float(fields[3]) if len(fields) > 3 else 0
            else:
                # A股格式: 名称,今日开盘价,昨日收盘价,当前价...
                name = fields[0] if fields else pure_code
                current_price = float(fields[3]) if len(fields) > 3 else 0
                prev_close = float(fields[2]) if len(fields) > 2 else 0
            
            change_pct = ((current_price - prev_close) / prev_close * 100) if prev_close > 0 else 0
            
            # 获取历史K线数据（使用腾讯财经接口）
            hist_data = self._fetch_history_tencent(pure_code, exchange, days)
            
            return {
                'stock_code': stock_code,
                'name': name,
                'current_price': current_price,
                'prev_close': prev_close,
                'change_pct': round(change_pct, 2),
                'data_source': 'sina',
                'history': hist_data,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"新浪财经数据源失败: {e}", file=sys.stderr)
            return None
    
    def _fetch_history_tencent(self, code: str, exchange: str, days: int) -> List[Dict]:
        """从腾讯财经获取历史数据"""
        try:
            if exchange == 'US':
                symbol = f"us{code}"
            elif exchange == 'HK':
                symbol = f"hk{code}"
            else:
                symbol = f"{exchange.lower()}{code}"
            
            # 腾讯财经日线数据
            url = f"http://web.ifzq.gtimg.cn/appstock/finance/day/{symbol}"
            response = self.session.get(url, timeout=10)
            data = response.json()
            
            # 解析历史数据
            key = f"{symbol}day"
            if 'data' in data and key in data['data']:
                raw_data = data['data'][key]
                history = []
                
                for item in raw_data[-days:]:
                    # 格式: 日期,开盘价,收盘价,最低价,最高价,成交量
                    parts = item.split(',')
                    if len(parts) >= 6:
                        history.append({
                            'date': parts[0],
                            'open': float(parts[1]),
                            'close': float(parts[2]),
                            'low': float(parts[3]),
                            'high': float(parts[4]),
                            'volume': int(parts[5])
                        })
                
                return history
            
            return []
            
        except Exception as e:
            print(f"历史数据获取失败: {e}", file=sys.stderr)
            return []
    
    def fetch_from_eastmoney(self, stock_code: str, days: int = 30) -> Optional[Dict]:
        """从东方财富获取数据"""
        try:
            exchange, pure_code = self.normalize_code(stock_code)
            
            # 东方财富 API
            if exchange == 'US':
                secid = f"105.{pure_code}"
            elif exchange == 'HK':
                secid = f"116.{pure_code}"
            elif exchange == 'SH':
                secid = f"1.{pure_code}"
            else:
                secid = f"0.{pure_code}"
            
            # 获取实时行情
            url = f"http://push2.eastmoney.com/api/qt/stock/get"
            params = {
                'secid': secid,
                'fields': 'f43,f44,f45,f46,f47,f48,f57,f58,f60,f170'
            }
            
            response = self.session.get(url, params=params, timeout=10)
            data = response.json()
            
            if 'data' not in data or not data['data']:
                return None
            
            stock_data = data['data']
            
            # 解析字段
            name = stock_data.get('f58', pure_code)
            current_price = stock_data.get('f43', 0) / 100 if stock_data.get('f43') else 0
            prev_close = stock_data.get('f60', 0) / 100 if stock_data.get('f60') else 0
            change_pct = stock_data.get('f170', 0) / 100 if stock_data.get('f170') else 0
            
            # 获取历史K线
            hist_data = self._fetch_history_eastmoney(secid, days)
            
            return {
                'stock_code': stock_code,
                'name': name,
                'current_price': current_price,
                'prev_close': prev_close,
                'change_pct': round(change_pct, 2),
                'data_source': 'eastmoney',
                'history': hist_data,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"东方财富数据源失败: {e}", file=sys.stderr)
            return None
    
    def _fetch_history_eastmoney(self, secid: str, days: int) -> List[Dict]:
        """从东方财富获取历史K线"""
        try:
            url = "http://push2his.eastmoney.com/api/qt/stock/kline/get"
            params = {
                'secid': secid,
                'fields1': 'f1,f2,f3,f4,f5,f6',
                'fields2': 'f51,f52,f53,f54,f55,f56,f57',
                'klt': '101',  # 日线
                'fqt': '0',
                'end': '20500101',
                'lmt': days
            }
            
            response = self.session.get(url, params=params, timeout=10)
            data = response.json()
            
            history = []
            if 'data' in data and data['data'] and 'klines' in data['data']:
                for line in data['data']['klines']:
                    # 格式: 日期,开盘,收盘,最低,最高,成交量,成交额,振幅,涨跌幅,涨跌额,换手率
                    parts = line.split(',')
                    if len(parts) >= 6:
                        history.append({
                            'date': parts[0],
                            'open': float(parts[1]),
                            'close': float(parts[2]),
                            'low': float(parts[3]),
                            'high': float(parts[4]),
                            'volume': int(float(parts[5]))
                        })
            
            return history
            
        except Exception as e:
            print(f"历史数据获取失败: {e}", file=sys.stderr)
            return []
    
    def fetch_from_xueqiu(self, stock_code: str, days: int = 30) -> Optional[Dict]:
        """从雪球获取数据"""
        try:
            exchange, pure_code = self.normalize_code(stock_code)
            
            # 雪球代码格式
            if exchange == 'US':
                symbol = f"{pure_code.upper()}"
            elif exchange == 'HK':
                symbol = f"{pure_code.zfill(5)}.HK"
            elif exchange == 'SH':
                symbol = f"SH{pure_code}"
            else:
                symbol = f"SZ{pure_code}"
            
            # 需要雪球 cookie，这里简化处理
            # 雪球接口需要登录，作为备用数据源使用简化版本
            url = f"https://stock.xueqiu.com/v5/stock/chart/minute.json"
            
            # 由于雪球需要认证，这里返回None触发下一个数据源
            return None
            
        except Exception as e:
            print(f"雪球数据源失败: {e}", file=sys.stderr)
            return None
    
    def fetch(self, stock_code: str, days: int = 30, source: Optional[str] = None) -> Dict:
        """
        获取股票数据，支持多数据源自动切换
        
        Args:
            stock_code: 股票代码
            days: 历史数据天数
            source: 指定数据源 (sina/eastmoney/xueqiu)，None则自动切换
        """
        sources = []
        if source:
            sources = [source]
        else:
            sources = ['sina', 'eastmoney', 'xueqiu']
        
        errors = []
        
        for src in sources:
            try:
                if src == 'sina':
                    result = self.fetch_from_sina(stock_code, days)
                elif src == 'eastmoney':
                    result = self.fetch_from_eastmoney(stock_code, days)
                elif src == 'xueqiu':
                    result = self.fetch_from_xueqiu(stock_code, days)
                else:
                    continue
                
                if result and result.get('current_price', 0) > 0:
                    return result
                    
            except Exception as e:
                errors.append(f"{src}: {e}")
                continue
        
        # 所有数据源都失败
        raise DataSourceError(f"所有数据源均失败: {'; '.join(errors)}")


def main():
    parser = argparse.ArgumentParser(description='获取股票数据')
    parser.add_argument('--stock_code', required=True, help='股票代码')
    parser.add_argument('--days', type=int, default=30, help='历史数据天数')
    parser.add_argument('--source', choices=['sina', 'eastmoney', 'xueqiu'], 
                       help='数据源（不指定则自动切换）')
    parser.add_argument('--output', '-o', help='输出文件路径')
    
    args = parser.parse_args()
    
    try:
        fetcher = StockDataFetcher()
        data = fetcher.fetch(args.stock_code, args.days, args.source)
        
        # 输出结果
        output_json = json.dumps(data, ensure_ascii=False, indent=2)
        
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(output_json)
            print(f"数据已保存到: {args.output}")
        else:
            print(output_json)
            
    except DataSourceError as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"未知错误: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
