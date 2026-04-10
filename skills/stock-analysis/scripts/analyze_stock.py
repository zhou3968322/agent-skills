#!/usr/bin/env python3
"""
股票技术分析脚本 - 计算技术指标、支撑位、压力位、缺口分析
"""

import argparse
import json
import sys
from typing import Dict, List, Optional, Tuple
from datetime import datetime

import numpy as np
import pandas as pd


class StockAnalyzer:
    """股票技术分析器"""
    
    def __init__(self, data: Dict):
        self.data = data
        self.history = data.get('history', [])
        self.df = self._prepare_dataframe()
    
    def _prepare_dataframe(self) -> pd.DataFrame:
        """准备数据框"""
        if not self.history:
            return pd.DataFrame()
        
        df = pd.DataFrame(self.history)
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date')
        return df
    
    def calculate_ma(self, periods: List[int] = [5, 10, 20, 60]) -> Dict[str, float]:
        """计算移动平均线"""
        if self.df.empty:
            return {}
        
        ma_values = {}
        for period in periods:
            if len(self.df) >= period:
                ma = self.df['close'].rolling(window=period).mean().iloc[-1]
                ma_values[f'MA{period}'] = round(ma, 2)
        
        return ma_values
    
    def calculate_macd(self, fast: int = 12, slow: int = 26, signal: int = 9) -> Dict:
        """计算 MACD 指标"""
        if self.df.empty or len(self.df) < slow:
            return {}
        
        close = self.df['close']
        
        # 计算 EMA
        ema_fast = close.ewm(span=fast, adjust=False).mean()
        ema_slow = close.ewm(span=slow, adjust=False).mean()
        
        # MACD 线
        macd_line = ema_fast - ema_slow
        
        # 信号线
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        
        # MACD 柱状图
        histogram = macd_line - signal_line
        
        return {
            'macd': round(macd_line.iloc[-1], 4),
            'signal': round(signal_line.iloc[-1], 4),
            'histogram': round(histogram.iloc[-1], 4),
            'trend': 'bullish' if histogram.iloc[-1] > 0 else 'bearish'
        }
    
    def calculate_rsi(self, period: int = 14) -> Dict:
        """计算 RSI 指标"""
        if self.df.empty or len(self.df) < period + 1:
            return {}
        
        close = self.df['close']
        
        # 计算价格变化
        delta = close.diff()
        
        # 分离上涨和下跌
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        # 计算 RS 和 RSI
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        current_rsi = rsi.iloc[-1]
        
        # 判断状态
        if current_rsi > 70:
            status = 'overbought'
        elif current_rsi < 30:
            status = 'oversold'
        else:
            status = 'neutral'
        
        return {
            'rsi': round(current_rsi, 2),
            'period': period,
            'status': status
        }
    
    def find_support_resistance(self, window: int = 20) -> Dict:
        """寻找支撑位和压力位"""
        if self.df.empty or len(self.df) < window:
            return {}
        
        recent = self.df.tail(window)
        
        # 近期最低价作为支撑位参考
        support_levels = []
        resistance_levels = []
        
        # 使用近期高低点
        recent_lows = recent['low'].nsmallest(3).values
        recent_highs = recent['high'].nlargest(3).values
        
        current_price = self.df['close'].iloc[-1]
        
        # 找出低于当前价格的支撑位
        for low in recent_lows:
            if low < current_price * 1.05:  # 允许5%的误差
                support_levels.append(round(low, 2))
        
        # 找出高于当前价格的压力位
        for high in recent_highs:
            if high > current_price * 0.95:  # 允许5%的误差
                resistance_levels.append(round(high, 2))
        
        # 添加均线作为动态支撑/压力
        ma_values = self.calculate_ma()
        for ma_name, ma_value in ma_values.items():
            if ma_value < current_price:
                support_levels.append(ma_value)
            else:
                resistance_levels.append(ma_value)
        
        # 去重并排序
        support_levels = sorted(list(set(support_levels)), reverse=True)
        resistance_levels = sorted(list(set(resistance_levels)))
        
        return {
            'current_price': round(current_price, 2),
            'support_levels': support_levels[:5],  # 取前5个
            'resistance_levels': resistance_levels[:5],
            'nearest_support': support_levels[0] if support_levels else None,
            'nearest_resistance': resistance_levels[0] if resistance_levels else None
        }
    
    def find_gaps(self) -> List[Dict]:
        """
        识别缺口（向上缺口和向下缺口）
        向上缺口：当日最低价 > 昨日最高价（跳空高开）
        向下缺口：当日最高价 < 昨日最低价（跳空低开）
        """
        if self.df.empty or len(self.df) < 2:
            return []
        
        gaps = []
        df = self.df.copy()
        
        for i in range(1, len(df)):
            prev_high = df.iloc[i-1]['high']
            prev_low = df.iloc[i-1]['low']
            curr_high = df.iloc[i]['high']
            curr_low = df.iloc[i]['low']
            curr_open = df.iloc[i]['open']
            curr_close = df.iloc[i]['close']
            
            # 向上缺口（跳空高开）
            if curr_low > prev_high:
                gap_size = curr_low - prev_high
                gap_pct = (gap_size / prev_high) * 100
                
                gaps.append({
                    'date': df.iloc[i]['date'].strftime('%Y-%m-%d'),
                    'type': 'up',
                    'type_desc': '向上缺口',
                    'prev_high': round(prev_high, 2),
                    'prev_low': round(prev_low, 2),
                    'curr_high': round(curr_high, 2),
                    'curr_low': round(curr_low, 2),
                    'gap_size': round(gap_size, 2),
                    'gap_pct': round(gap_pct, 2),
                    'support_level': round(prev_high, 2),  # 缺口上沿作为支撑
                    'is_filled': curr_close <= prev_high  # 是否已回补
                })
            
            # 向下缺口（跳空低开）
            elif curr_high < prev_low:
                gap_size = prev_low - curr_high
                gap_pct = (gap_size / prev_low) * 100
                
                gaps.append({
                    'date': df.iloc[i]['date'].strftime('%Y-%m-%d'),
                    'type': 'down',
                    'type_desc': '向下缺口',
                    'prev_high': round(prev_high, 2),
                    'prev_low': round(prev_low, 2),
                    'curr_high': round(curr_high, 2),
                    'curr_low': round(curr_low, 2),
                    'gap_size': round(gap_size, 2),
                    'gap_pct': round(gap_pct, 2),
                    'resistance_level': round(prev_low, 2),  # 缺口下沿作为压力
                    'is_filled': curr_close >= prev_low  # 是否已回补
                })
        
        # 按日期倒序，取最近10个缺口
        gaps.reverse()
        return gaps[:10]
    
    def analyze_volume(self) -> Dict:
        """分析成交量"""
        if self.df.empty or len(self.df) < 5:
            return {}
        
        recent_volume = self.df['volume'].tail(5).mean()
        avg_volume = self.df['volume'].mean()
        
        return {
            'recent_avg_volume': int(recent_volume),
            'total_avg_volume': int(avg_volume),
            'volume_ratio': round(recent_volume / avg_volume, 2) if avg_volume > 0 else 1.0,
            'trend': 'increasing' if recent_volume > avg_volume else 'decreasing'
        }
    
    def analyze_trend(self) -> Dict:
        """分析趋势"""
        if self.df.empty or len(self.df) < 20:
            return {'trend': 'unknown'}
        
        # 计算短期和长期趋势
        close = self.df['close']
        
        short_ma = close.tail(5).mean()
        long_ma = close.tail(20).mean()
        
        # 判断趋势
        if short_ma > long_ma * 1.02:
            trend = 'uptrend'
        elif short_ma < long_ma * 0.98:
            trend = 'downtrend'
        else:
            trend = 'sideways'
        
        # 判断均线排列
        ma_values = self.calculate_ma()
        if len(ma_values) >= 3:
            ma_list = [ma_values.get(f'MA{p}') for p in [5, 10, 20] if ma_values.get(f'MA{p}')]
            if len(ma_list) >= 3 and ma_list[0] > ma_list[1] > ma_list[2]:
                ma_arrangement = 'bullish'  # 多头排列
            elif len(ma_list) >= 3 and ma_list[0] < ma_list[1] < ma_list[2]:
                ma_arrangement = 'bearish'  # 空头排列
            else:
                ma_arrangement = 'mixed'  # 缠绕
        else:
            ma_arrangement = 'unknown'
        
        return {
            'trend': trend,
            'ma_arrangement': ma_arrangement,
            'short_ma': round(short_ma, 2),
            'long_ma': round(long_ma, 2)
        }
    
    def generate_prediction(self) -> Dict:
        """生成未来3天走势预测"""
        trend = self.analyze_trend()
        macd = self.calculate_macd()
        rsi = self.calculate_rsi()
        sr = self.find_support_resistance()
        gaps = self.find_gaps()
        
        # 综合评分
        bullish_signals = 0
        bearish_signals = 0
        
        # 趋势信号
        if trend.get('trend') == 'uptrend':
            bullish_signals += 2
        elif trend.get('trend') == 'downtrend':
            bearish_signals += 2
        
        # 均线排列
        if trend.get('ma_arrangement') == 'bullish':
            bullish_signals += 1
        elif trend.get('ma_arrangement') == 'bearish':
            bearish_signals += 1
        
        # MACD 信号
        if macd.get('trend') == 'bullish':
            bullish_signals += 1
        elif macd.get('trend') == 'bearish':
            bearish_signals += 1
        
        # RSI 信号
        if rsi.get('status') == 'oversold':
            bullish_signals += 1  # 超卖可能反弹
        elif rsi.get('status') == 'overbought':
            bearish_signals += 1  # 超买可能回调
        
        # 缺口分析
        recent_gaps = [g for g in gaps if not g.get('is_filled')][:3]
        for gap in recent_gaps:
            if gap['type'] == 'up':
                bullish_signals += 0.5  # 向上缺口支撑
            else:
                bearish_signals += 0.5  # 向下缺口压力
        
        # 计算概率
        total = bullish_signals + bearish_signals
        if total == 0:
            up_prob = down_prob = 33
            sideways_prob = 34
        else:
            up_prob = round(bullish_signals / total * 100)
            down_prob = round(bearish_signals / total * 100)
            sideways_prob = 100 - up_prob - down_prob
        
        # 判断最强预测
        if up_prob > down_prob and up_prob > sideways_prob:
            prediction = 'up'
            strength = 'strong' if up_prob > 60 else 'moderate'
        elif down_prob > up_prob and down_prob > sideways_prob:
            prediction = 'down'
            strength = 'strong' if down_prob > 60 else 'moderate'
        else:
            prediction = 'sideways'
            strength = 'moderate'
        
        return {
            'prediction': prediction,
            'strength': strength,
            'probabilities': {
                'up': up_prob,
                'down': down_prob,
                'sideways': sideways_prob
            },
            'key_factors': {
                'trend': trend.get('trend'),
                'ma_arrangement': trend.get('ma_arrangement'),
                'macd_trend': macd.get('trend'),
                'rsi_status': rsi.get('status'),
                'recent_gaps': len(recent_gaps)
            },
            'support_resistance': sr,
            'recommendation': self._generate_recommendation(prediction, strength, sr)
        }
    
    def _generate_recommendation(self, prediction: str, strength: str, sr: Dict) -> Dict:
        """生成操作建议"""
        current_price = sr.get('current_price', 0)
        nearest_support = sr.get('nearest_support')
        nearest_resistance = sr.get('nearest_resistance')
        
        if prediction == 'up':
            action = 'buy' if strength == 'strong' else 'hold'
            stop_loss = nearest_support if nearest_support else current_price * 0.95
            take_profit = nearest_resistance if nearest_resistance else current_price * 1.1
        elif prediction == 'down':
            action = 'sell' if strength == 'strong' else 'reduce'
            stop_loss = nearest_resistance if nearest_resistance else current_price * 1.05
            take_profit = nearest_support if nearest_support else current_price * 0.9
        else:
            action = 'wait'
            stop_loss = current_price * 0.95
            take_profit = current_price * 1.05
        
        return {
            'action': action,
            'stop_loss': round(stop_loss, 2) if stop_loss else None,
            'take_profit': round(take_profit, 2) if take_profit else None,
            'target_range': [
                round(nearest_support, 2) if nearest_support else round(current_price * 0.95, 2),
                round(nearest_resistance, 2) if nearest_resistance else round(current_price * 1.05, 2)
            ]
        }
    
    def analyze(self) -> Dict:
        """执行完整分析"""
        if self.df.empty:
            return {'error': 'No data available for analysis'}
        
        return {
            'stock_info': {
                'code': self.data.get('stock_code'),
                'name': self.data.get('name'),
                'current_price': self.data.get('current_price'),
                'change_pct': self.data.get('change_pct'),
                'data_source': self.data.get('data_source'),
                'analysis_time': datetime.now().isoformat()
            },
            'moving_averages': self.calculate_ma(),
            'macd': self.calculate_macd(),
            'rsi': self.calculate_rsi(),
            'support_resistance': self.find_support_resistance(),
            'gaps': self.find_gaps(),
            'volume_analysis': self.analyze_volume(),
            'trend_analysis': self.analyze_trend(),
            'prediction': self.generate_prediction()
        }


def main():
    parser = argparse.ArgumentParser(description='股票技术分析')
    parser.add_argument('--data_file', required=True, help='股票数据文件路径(JSON格式)')
    parser.add_argument('--output', '-o', help='输出文件路径')
    
    args = parser.parse_args()
    
    try:
        # 读取数据文件
        with open(args.data_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 执行分析
        analyzer = StockAnalyzer(data)
        result = analyzer.analyze()
        
        # 输出结果
        output_json = json.dumps(result, ensure_ascii=False, indent=2)
        
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(output_json)
            print(f"分析结果已保存到: {args.output}")
        else:
            print(output_json)
            
    except FileNotFoundError:
        print(f"错误: 找不到数据文件 '{args.data_file}'", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"错误: 数据文件格式无效", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"分析错误: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
