import streamlit as st
import pandas as pd
import numpy as np
import datetime
import pytz
from binance.client import Client
from ta.trend import SMAIndicator, EMAIndicator, MACD
from ta.momentum import RSIIndicator
from ta.volatility import BollingerBands

# Binance API 凭证（仅本地测试时使用）
API_KEY = "TW9RoJwf2EP2jIhm8h0NJtqBNxDnbo6lGMBfyalYkm4B2bqU0QmddRHGXaSEaY1J"
API_SECRET = "u7g7ZahxwAbuMvDtWbsBx4QXVBkqjsSpTfFKKl7GrQk7PE7p8qJ7VZSRXJiBSF7S"

# 初始化 Binance 客户端
client = Client(API_KEY, API_SECRET)

# 支持的币种
symbols = {
    'BTC': 'BTCUSDT',
    'ETH': 'ETHUSDT',
    'SOL': 'SOLUSDT'
}

st.title("📈 加密貨幣合約分析（基礎版）")
st.write("自動獲取價格、分析技術指標並給出買賣建議")

# 设定时区为香港时间
hk_tz = pytz.timezone("Asia/Hong_Kong")
now = datetime.datetime.now(hk_tz)
st.write("當前香港時間：", now.strftime("%Y-%m-%d %H:%M:%S"))

# 分析每个币种
for name, symbol in symbols.items():
    try:
        # 获取历史K线数据（1小时，过去24条）
        klines = client.get_klines(symbol=symbol, interval=Client.KLINE_INTERVAL_1HOUR, limit=24)
        df = pd.DataFrame(klines, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_asset_volume', 'num_trades',
            'taker_buy_base', 'taker_buy_quote', 'ignore'
        ])
        df['close'] = pd.to_numeric(df['close'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)

        # 计算常用技术指标
        df['SMA20'] = SMAIndicator(df['close'], window=20).sma_indicator()
        df['EMA20'] = EMAIndicator(df['close'], window=20).ema_indicator()
        df['RSI'] = RSIIndicator(df['close'], window=14).rsi()
        macd = MACD(df['close'])
        df['MACD'] = macd.macd_diff()
        bb = BollingerBands(df['close'], window=20)
        df['BB_upper'] = bb.bollinger_hband()
        df['BB_lower'] = bb.bollinger_lband()

        # 当前价格
        current_price = df['close'].iloc[-1]

        # 简单规则建议（你可以替换为更复杂的逻辑）
        latest_rsi = df['RSI'].iloc[-1]
        latest_macd = df['MACD'].iloc[-1]
        price = df['close'].iloc[-1]
        sma = df['SMA20'].iloc[-1]
        ema = df['EMA20'].iloc[-1]

        # 计算建议概率（示例算法）
        score = 0
        if price > sma: score += 1
        if price > ema: score += 1
        if latest_macd > 0: score += 1
        if latest_rsi < 30: score += 1
        elif latest_rsi > 70: score -= 1

        probability = round((score + 1) / 5 * 100, 2)
        suggestion = "買入" if probability > 60 else "賣出" if probability < 40 else "觀望"

        # 展示結果
        st.subheader(f"📊 {name}")
        st.write(f"當前價格：${current_price:.2f}")
        st.write(f"買入建議概率：{probability}%")
        st.line_chart(df[['close', 'SMA20', 'EMA20']].dropna())

    except Exception as e:
        st.error(f"{name} 數據獲取錯誤：{e}")
