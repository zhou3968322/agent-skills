#!/usr/bin/env python3
"""
股票财务数据获取脚本 - 支持多数据源自动切换
数据源：东方财富、新浪财经
获取内容：财务报表、财务指标、主要财务数据
"""

import argparse
import json
import sys
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import requests


class DataSourceError(Exception):
    """数据源错误"""
    pass


class FinancialDataFetcher:
    """财务数据获取器"""
    
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
        elif code.startswith('8') or code.startswith('4'):
            return 'BJ', code  # 北交所
        else:
            return 'SH', code  # 默认上交所
    
    def fetch_from_eastmoney(self, stock_code: str) -> Optional[Dict]:
        """从东方财富获取财务数据"""
        try:
            exchange, pure_code = self.normalize_code(stock_code)
            
            # 东方财富 API 使用的 secid
            if exchange == 'US':
                secid = f"105.{pure_code}"
            elif exchange == 'HK':
                secid = f"116.{pure_code}"
            elif exchange == 'SH':
                secid = f"1.{pure_code}"
            elif exchange == 'BJ':
                secid = f"0.{pure_code}"
            else:
                secid = f"0.{pure_code}"
            
            result = {
                'stock_code': stock_code,
                'exchange': exchange,
                'pure_code': pure_code,
                'data_source': 'eastmoney',
                'fetch_time': datetime.now().isoformat()
            }
            
            # 1. 获取公司基本资料
            company_info = self._fetch_company_info_eastmoney(secid)
            result['company_info'] = company_info
            
            # 2. 获取主要财务指标
            financial_indicators = self._fetch_financial_indicators_eastmoney(secid)
            result['financial_indicators'] = financial_indicators
            
            # 3. 获取财务报表数据（利润表、资产负债表、现金流量表）
            financial_reports = self._fetch_financial_reports_eastmoney(secid)
            result['financial_reports'] = financial_reports
            
            # 4. 获取估值指标
            valuation = self._fetch_valuation_eastmoney(secid)
            result['valuation'] = valuation
            
            return result
            
        except Exception as e:
            print(f"东方财富财务数据获取失败: {e}", file=sys.stderr)
            return None
    
    def _fetch_company_info_eastmoney(self, secid: str) -> Dict:
        """从东方财富获取公司基本资料"""
        try:
            url = "http://push2.eastmoney.com/api/qt/stock/get"
            params = {
                'secid': secid,
                'fields': 'f57,f58,f84,f85,f116,f117,f162,f163,f164,f165,f166,f167,f168,f169,f170,f171'
            }
            
            response = self.session.get(url, params=params, timeout=10)
            data = response.json()
            
            if 'data' not in data or not data['data']:
                return {}
            
            stock_data = data['data']
            
            # 解析字段（东方财富字段需要除以100或根据类型处理）
            return {
                'stock_code': stock_data.get('f57', ''),
                'stock_name': stock_data.get('f58', ''),
                'total_shares': stock_data.get('f84', 0),  # 总股本（万股）
                'float_shares': stock_data.get('f85', 0),  # 流通股本（万股）
                'total_market_cap': round(stock_data.get('f116', 0) / 100000000, 2) if stock_data.get('f116') else 0,  # 总市值（亿元）
                'float_market_cap': round(stock_data.get('f117', 0) / 100000000, 2) if stock_data.get('f117') else 0,  # 流通市值（亿元）
            }
            
        except Exception as e:
            print(f"公司资料获取失败: {e}", file=sys.stderr)
            return {}
    
    def _fetch_financial_indicators_eastmoney(self, secid: str) -> Dict:
        """从东方财富获取主要财务指标"""
        try:
            # 获取最新财务指标
            url = "http://f10.eastmoney.com/NewFinanceAnalysis/MainTargetAjax"
            params = {
                'type': '0',  # 0-按报告期，1-按年度，2-按单季度
                'code': secid
            }
            
            response = self.session.get(url, params=params, timeout=15)
            data = response.json()
            
            if 'data' not in data or not data['data']:
                return {}
            
            # 获取最新的财务数据
            latest = data['data'][0] if data['data'] else {}
            
            # 解析关键财务指标
            indicators = {
                'report_date': latest.get('rq', ''),  # 报告期
                'eps': self._parse_float(latest.get('jbmgsy')),  # 基本每股收益（元）
                'eps_diluted': self._parse_float(latest.get('kfmgsy')),  # 稀释每股收益（元）
                'bps': self._parse_float(latest.get('mgjzc')),  # 每股净资产（元）
                'operating_cash_flow_per_share': self._parse_float(latest.get('mgjyxjll')),  # 每股经营现金流（元）
                'roe': self._parse_float(latest.get('jqjzcsyl')),  # 净资产收益率（%）- 加权
                'roe_diluted': self._parse_float(latest.get('tbjzcsyl')),  # 净资产收益率（%）- 摊薄
                'gross_margin': self._parse_float(latest.get('xsmll')),  # 销售毛利率（%）
                'net_margin': self._parse_float(latest.get('xsjll')),  # 销售净利率（%）
                'debt_ratio': self._parse_float(latest.get('zcfzl')),  # 资产负债率（%）
                'current_ratio': self._parse_float(latest.get('ldbl')),  # 流动比率
                'quick_ratio': self._parse_float(latest.get('sdbl')),  # 速动比率
                'inventory_turnover': self._parse_float(latest.get('chzzl')),  # 存货周转率（次）
                'receivables_turnover': self._parse_float(latest.get('yszkzzl')),  # 应收账款周转率（次）
                'total_asset_turnover': self._parse_float(latest.get('zzczzl')),  # 总资产周转率（次）
                'operating_revenue': self._parse_float(latest.get('yyysr')),  # 营业总收入（亿元）
                'operating_revenue_yoy': self._parse_float(latest.get('ysrzzl')),  # 营业总收入同比增长率（%）
                'net_profit': self._parse_float(latest.get('gsjlr')),  # 归属净利润（亿元）
                'net_profit_yoy': self._parse_float(latest.get('jlrtbzz')),  # 净利润同比增长率（%）
                'deducted_net_profit': self._parse_float(latest.get('kfjlr')),  # 扣非净利润（亿元）
                'deducted_net_profit_yoy': self._parse_float(latest.get('kfjlrtbzz')),  # 扣非净利润同比增长率（%）
            }
            
            # 添加历史趋势数据（最近4个季度）
            history = []
            for item in data['data'][:4]:
                history.append({
                    'report_date': item.get('rq', ''),
                    'eps': self._parse_float(item.get('jbmgsy')),
                    'roe': self._parse_float(item.get('jqjzcsyl')),
                    'net_profit_yoy': self._parse_float(item.get('jlrtbzz')),
                    'operating_revenue_yoy': self._parse_float(item.get('ysrzzl')),
                })
            indicators['history'] = history
            
            return indicators
            
        except Exception as e:
            print(f"财务指标获取失败: {e}", file=sys.stderr)
            return {}
    
    def _fetch_financial_reports_eastmoney(self, secid: str) -> Dict:
        """从东方财富获取财务报表摘要"""
        try:
            reports = {
                'income_statement': self._fetch_income_statement_eastmoney(secid),
                'balance_sheet': self._fetch_balance_sheet_eastmoney(secid),
                'cash_flow': self._fetch_cash_flow_eastmoney(secid)
            }
            return reports
        except Exception as e:
            print(f"财务报表获取失败: {e}", file=sys.stderr)
            return {}
    
    def _fetch_income_statement_eastmoney(self, secid: str) -> List[Dict]:
        """获取利润表摘要"""
        try:
            url = "http://f10.eastmoney.com/NewFinanceAnalysis/lrbAjax"
            params = {
                'companyType': '4',  # 默认通用类型
                'reportDateType': '0',
                'code': secid
            }
            
            response = self.session.get(url, params=params, timeout=15)
            data = response.json()
            
            if 'data' not in data:
                return []
            
            result = []
            for item in data['data'][:4]:  # 最近4个报告期
                result.append({
                    'report_date': item.get('REPORT_DATE', ''),
                    'operating_revenue': self._parse_float(item.get('TOTAL_OPERATE_INCOME')),  # 营业收入
                    'operating_cost': self._parse_float(item.get('OPERATE_INCOME')),  # 营业成本
                    'operating_profit': self._parse_float(item.get('OPERATE_PROFIT')),  # 营业利润
                    'total_profit': self._parse_float(item.get('TOTAL_PROFIT')),  # 利润总额
                    'net_profit': self._parse_float(item.get('NETPROFIT')),  # 净利润
                    'parent_net_profit': self._parse_float(item.get('PARENT_NETPROFIT')),  # 归属母公司净利润
                })
            
            return result
            
        except Exception as e:
            print(f"利润表获取失败: {e}", file=sys.stderr)
            return []
    
    def _fetch_balance_sheet_eastmoney(self, secid: str) -> List[Dict]:
        """获取资产负债表摘要"""
        try:
            url = "http://f10.eastmoney.com/NewFinanceAnalysis/zcfzbAjax"
            params = {
                'companyType': '4',
                'reportDateType': '0',
                'code': secid
            }
            
            response = self.session.get(url, params=params, timeout=15)
            data = response.json()
            
            if 'data' not in data:
                return []
            
            result = []
            for item in data['data'][:4]:
                result.append({
                    'report_date': item.get('REPORT_DATE', ''),
                    'total_assets': self._parse_float(item.get('TOTAL_ASSETS')),  # 总资产
                    'total_liabilities': self._parse_float(item.get('TOTAL_LIABILITIES')),  # 总负债
                    'total_equity': self._parse_float(item.get('TOTAL_EQUITY')),  # 所有者权益
                    'parent_equity': self._parse_float(item.get('PARENT_EQUITY')),  # 归属母公司权益
                })
            
            return result
            
        except Exception as e:
            print(f"资产负债表获取失败: {e}", file=sys.stderr)
            return []
    
    def _fetch_cash_flow_eastmoney(self, secid: str) -> List[Dict]:
        """获取现金流量表摘要"""
        try:
            url = "http://f10.eastmoney.com/NewFinanceAnalysis/xjllbAjax"
            params = {
                'companyType': '4',
                'reportDateType': '0',
                'code': secid
            }
            
            response = self.session.get(url, params=params, timeout=15)
            data = response.json()
            
            if 'data' not in data:
                return []
            
            result = []
            for item in data['data'][:4]:
                result.append({
                    'report_date': item.get('REPORT_DATE', ''),
                    'operating_cash_flow': self._parse_float(item.get('NETCASH_OPERATE')),  # 经营活动现金流净额
                    'investing_cash_flow': self._parse_float(item.get('NETCASH_INVEST')),  # 投资活动现金流净额
                    'financing_cash_flow': self._parse_float(item.get('NETCASH_FINANCE')),  # 筹资活动现金流净额
                    'cash_increase': self._parse_float(item.get('CASH_INCREASE')),  # 现金及等价物净增加额
                })
            
            return result
            
        except Exception as e:
            print(f"现金流量表获取失败: {e}", file=sys.stderr)
            return []
    
    def _fetch_valuation_eastmoney(self, secid: str) -> Dict:
        """获取估值指标"""
        try:
            url = "http://push2.eastmoney.com/api/qt/stock/get"
            params = {
                'secid': secid,
                'fields': 'f43,f57,f58,f60,f162,f163,f164,f165,f166,f167,f168,f169,f170,f171,f173,f177'
            }
            
            response = self.session.get(url, params=params, timeout=10)
            data = response.json()
            
            if 'data' not in data or not data['data']:
                return {}
            
            stock_data = data['data']
            
            # 计算估值指标
            current_price = stock_data.get('f43', 0) / 100 if stock_data.get('f43') else 0
            
            return {
                'pe_ttm': stock_data.get('f164', 0) / 100 if stock_data.get('f164') else 0,  # 市盈率TTM
                'pe_lyr': stock_data.get('f162', 0) / 100 if stock_data.get('f162') else 0,  # 市盈率（静态）
                'pb': stock_data.get('f167', 0) / 100 if stock_data.get('f167') else 0,  # 市净率
                'ps': stock_data.get('f166', 0) / 100 if stock_data.get('f166') else 0,  # 市销率
                'pcf': stock_data.get('f168', 0) / 100 if stock_data.get('f168') else 0,  # 市现率
                'current_price': current_price,
            }
            
        except Exception as e:
            print(f"估值指标获取失败: {e}", file=sys.stderr)
            return {}
    
    def fetch_from_sina(self, stock_code: str) -> Optional[Dict]:
        """从新浪财经获取财务数据（简化版本）"""
        try:
            exchange, pure_code = self.normalize_code(stock_code)
            
            if exchange == 'US':
                return None  # 美股财务数据较为复杂，暂不实现
            elif exchange == 'HK':
                symbol = f"hk{pure_code}"
            else:
                symbol = f"{exchange.lower()}{pure_code}"
            
            # 新浪财经财务数据接口
            url = f"https://finance.sina.com.cn/realstock/company/{symbol}/finance.phtml"
            
            # 新浪财经财务数据需要解析HTML，这里作为备用方案
            # 返回简化版本
            return None
            
        except Exception as e:
            print(f"新浪财经财务数据获取失败: {e}", file=sys.stderr)
            return None
    
    def _parse_float(self, value) -> Optional[float]:
        """安全地解析浮点数"""
        if value is None or value == '-' or value == '':
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None
    
    def analyze_financial_health(self, data: Dict) -> Dict:
        """分析财务健康状况"""
        indicators = data.get('financial_indicators', {})
        valuation = data.get('valuation', {})
        
        analysis = {
            'profitability': {},
            'growth': {},
            'solvency': {},
            'valuation': {},
            'overall_score': 0,
            'risk_level': 'unknown'
        }
        
        # 1. 盈利能力分析
        roe = indicators.get('roe')
        net_margin = indicators.get('net_margin')
        gross_margin = indicators.get('gross_margin')
        
        profitability_score = 0
        if roe is not None:
            if roe > 20:
                profitability_score += 3
                analysis['profitability']['roe_level'] = 'excellent'
            elif roe > 15:
                profitability_score += 2
                analysis['profitability']['roe_level'] = 'good'
            elif roe > 10:
                profitability_score += 1
                analysis['profitability']['roe_level'] = 'average'
            else:
                analysis['profitability']['roe_level'] = 'poor'
            analysis['profitability']['roe'] = roe
        
        if net_margin is not None:
            if net_margin > 20:
                profitability_score += 2
            elif net_margin > 10:
                profitability_score += 1
            analysis['profitability']['net_margin'] = net_margin
        
        if gross_margin is not None:
            analysis['profitability']['gross_margin'] = gross_margin
        
        # 2. 成长性分析
        net_profit_yoy = indicators.get('net_profit_yoy')
        revenue_yoy = indicators.get('operating_revenue_yoy')
        
        growth_score = 0
        if net_profit_yoy is not None:
            if net_profit_yoy > 30:
                growth_score += 3
                analysis['growth']['profit_growth_level'] = 'high'
            elif net_profit_yoy > 15:
                growth_score += 2
                analysis['growth']['profit_growth_level'] = 'moderate'
            elif net_profit_yoy > 0:
                growth_score += 1
                analysis['growth']['profit_growth_level'] = 'slow'
            else:
                analysis['growth']['profit_growth_level'] = 'declining'
            analysis['growth']['net_profit_yoy'] = net_profit_yoy
        
        if revenue_yoy is not None:
            analysis['growth']['revenue_yoy'] = revenue_yoy
        
        # 3. 偿债能力分析
        debt_ratio = indicators.get('debt_ratio')
        current_ratio = indicators.get('current_ratio')
        
        solvency_score = 0
        if debt_ratio is not None:
            if debt_ratio < 40:
                solvency_score += 2
                analysis['solvency']['debt_level'] = 'low'
            elif debt_ratio < 60:
                solvency_score += 1
                analysis['solvency']['debt_level'] = 'moderate'
            else:
                analysis['solvency']['debt_level'] = 'high'
            analysis['solvency']['debt_ratio'] = debt_ratio
        
        if current_ratio is not None:
            if current_ratio > 2:
                solvency_score += 1
            analysis['solvency']['current_ratio'] = current_ratio
        
        # 4. 估值分析
        pe_ttm = valuation.get('pe_ttm')
        pb = valuation.get('pb')
        
        valuation_score = 0
        if pe_ttm is not None and pe_ttm > 0:
            if pe_ttm < 15:
                valuation_score += 2
                analysis['valuation']['pe_level'] = 'undervalued'
            elif pe_ttm < 30:
                valuation_score += 1
                analysis['valuation']['pe_level'] = 'fair'
            else:
                analysis['valuation']['pe_level'] = 'overvalued'
            analysis['valuation']['pe_ttm'] = pe_ttm
        
        if pb is not None and pb > 0:
            if pb < 2:
                valuation_score += 1
            analysis['valuation']['pb'] = pb
        
        # 5. 综合评分和风险等级
        total_score = profitability_score + growth_score + solvency_score + valuation_score
        max_score = 12  # 满分
        analysis['overall_score'] = round(total_score / max_score * 100, 1) if max_score > 0 else 0
        
        if total_score >= 9:
            analysis['risk_level'] = 'low'
        elif total_score >= 6:
            analysis['risk_level'] = 'moderate'
        elif total_score >= 3:
            analysis['risk_level'] = 'high'
        else:
            analysis['risk_level'] = 'very_high'
        
        # 6. 投资建议
        if analysis['overall_score'] >= 75:
            analysis['investment_suggestion'] = '优质标的，可关注'
        elif analysis['overall_score'] >= 50:
            analysis['investment_suggestion'] = '业绩尚可，谨慎关注'
        elif analysis['overall_score'] >= 25:
            analysis['investment_suggestion'] = '业绩一般，需进一步分析'
        else:
            analysis['investment_suggestion'] = '业绩较差，建议回避'
        
        return analysis
    
    def fetch(self, stock_code: str, source: Optional[str] = None) -> Dict:
        """
        获取财务数据，支持多数据源自动切换
        
        Args:
            stock_code: 股票代码
            source: 指定数据源 (eastmoney/sina)，None则自动切换
        """
        sources = []
        if source:
            sources = [source]
        else:
            sources = ['eastmoney', 'sina']
        
        errors = []
        
        for src in sources:
            try:
                if src == 'eastmoney':
                    result = self.fetch_from_eastmoney(stock_code)
                elif src == 'sina':
                    result = self.fetch_from_sina(stock_code)
                else:
                    continue
                
                if result and result.get('company_info'):
                    # 添加财务健康分析
                    result['financial_analysis'] = self.analyze_financial_health(result)
                    return result
                    
            except Exception as e:
                errors.append(f"{src}: {e}")
                continue
        
        # 所有数据源都失败
        raise DataSourceError(f"所有数据源均失败: {'; '.join(errors)}")


def main():
    parser = argparse.ArgumentParser(description='获取股票财务数据')
    parser.add_argument('--stock_code', required=True, help='股票代码')
    parser.add_argument('--source', choices=['eastmoney', 'sina'], 
                       help='数据源（不指定则自动切换）')
    parser.add_argument('--output', '-o', help='输出文件路径')
    parser.add_argument('--format', choices=['json', 'table'], default='json',
                       help='输出格式（默认json）')
    
    args = parser.parse_args()
    
    try:
        fetcher = FinancialDataFetcher()
        data = fetcher.fetch(args.stock_code, args.source)
        
        if args.format == 'table':
            # 表格格式输出（简化版）
            print(f"\n{'='*60}")
            print(f"股票财务数据 - {data.get('company_info', {}).get('stock_name', '')} ({args.stock_code})")
            print(f"{'='*60}")
            
            # 公司信息
            company = data.get('company_info', {})
            print(f"\n【公司信息】")
            print(f"  总股本: {company.get('total_shares', 'N/A')} 万股")
            print(f"  流通股本: {company.get('float_shares', 'N/A')} 万股")
            print(f"  总市值: {company.get('total_market_cap', 'N/A')} 亿元")
            print(f"  流通市值: {company.get('float_market_cap', 'N/A')} 亿元")
            
            # 财务指标
            indicators = data.get('financial_indicators', {})
            print(f"\n【主要财务指标】")
            print(f"  报告期: {indicators.get('report_date', 'N/A')}")
            print(f"  每股收益(EPS): {indicators.get('eps', 'N/A')} 元")
            print(f"  每股净资产(BPS): {indicators.get('bps', 'N/A')} 元")
            print(f"  净资产收益率(ROE): {indicators.get('roe', 'N/A')}%")
            print(f"  销售毛利率: {indicators.get('gross_margin', 'N/A')}%")
            print(f"  销售净利率: {indicators.get('net_margin', 'N/A')}%")
            print(f"  资产负债率: {indicators.get('debt_ratio', 'N/A')}%")
            print(f"  营业收入: {indicators.get('operating_revenue', 'N/A')} 亿元")
            print(f"  营收同比增长: {indicators.get('operating_revenue_yoy', 'N/A')}%")
            print(f"  归母净利润: {indicators.get('net_profit', 'N/A')} 亿元")
            print(f"  净利润同比增长: {indicators.get('net_profit_yoy', 'N/A')}%")
            
            # 估值指标
            valuation = data.get('valuation', {})
            print(f"\n【估值指标】")
            print(f"  市盈率(TTM): {valuation.get('pe_ttm', 'N/A')}")
            print(f"  市盈率(静态): {valuation.get('pe_lyr', 'N/A')}")
            print(f"  市净率: {valuation.get('pb', 'N/A')}")
            print(f"  市销率: {valuation.get('ps', 'N/A')}")
            
            # 财务分析
            analysis = data.get('financial_analysis', {})
            print(f"\n【财务健康分析】")
            print(f"  综合评分: {analysis.get('overall_score', 'N/A')}/100")
            print(f"  风险等级: {analysis.get('risk_level', 'N/A')}")
            print(f"  投资建议: {analysis.get('investment_suggestion', 'N/A')}")
            
            print(f"\n{'='*60}")
            print(f"数据来源: {data.get('data_source', 'N/A')}")
            print(f"{'='*60}\n")
            
        else:
            # JSON格式输出
            output_json = json.dumps(data, ensure_ascii=False, indent=2)
            
            if args.output:
                with open(args.output, 'w', encoding='utf-8') as f:
                    f.write(output_json)
                print(f"财务数据已保存到: {args.output}")
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
