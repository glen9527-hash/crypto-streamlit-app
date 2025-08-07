import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import ta
import matplotlib.pyplot as plt
import time

st.set_page_config(page_title="加密货币合约分析", layout="wide")

# ================== 参数配置 ==================
symbols = {
    "BTC": ("BTC-USD", "比特币"),
    "ETH": ("ETH-USD", "以太坊"),
    "SOL": ("SOL-USD", "索拉纳")
}
intervals = {
    "15分钟": ("15m", "0.5d"),
    "1小时": ("1h", "1d"),
    "4小时": ("1h", "4d"),
    "24小时": ("1h", "7d")
}
# ================== 技术指标计算 ==================
def calculate_indicators(df):
    close = df['Close']
    df['SMA_12'] = ta.trend.SMAIndicator(close=close, window=12).sma_indicator()
    df['EMA_12'] = ta.trend.EMAIndicator(close=close, window=12).ema_indicator()
    df['RSI'] = ta.momentum.RSIIndicator(close=close, window=14).rsi()
    macd = ta.trend.MACD(close=close)
    df['MACD'] = macd.macd()
    df['MACD_signal'] = macd.macd_signal()
    bb = ta.volatility.BollingerBands(close=close, window=20, window_dev=2)
    df['BB_upper'] = bb.bollinger_hband()
    df['BB_lower'] = bb.bollinger_lband()
    return df

# ================== 建议分析 ==================
def generate_suggestion(df):
    latest = df.iloc[-1]
    score = 0
    total = 0

    # SMA & EMA 趋势
    if latest['Close'] > latest['SMA_12']:
        score += 1
    total += 1
    if latest['Close'] > latest['EMA_12']:
        score += 1
    total += 1

    # RSI 判断
    if latest['RSI'] < 30:
        score += 1  # 超卖，可能买入机会
    elif latest['RSI'] > 70:
        score -= 1  # 超买，可能卖出风险
    total += 1

    # MACD 判断
    if latest['MACD'] > latest['MACD_signal']:
        score += 1
    total += 1

    # 布林带判断
    if latest['Close'] < latest['BB_lower']:
        score += 1
    elif latest['Close'] > latest['BB_upper']:
        score -= 1
    total += 1

    # 计算概率
    prob = round((score / total + 1) / 2 * 100, 2)  # 转换为 0~100%
    return prob

# ================== 显示分析 ==================
def display_analysis(symbol, name, interval_key, period):
    st.subheader(f"💰 {name}（{interval_key}）")
    yf_symbol, _ = symbols[symbol]
    interval, lookback = intervals[interval_key]

    try:
        df = yf.download(yf_symbol, interval=interval, period=lookback)
        if df.empty:
            st.warning("⚠️ 无法获取数据。")
            return

        df = df.dropna()
        df = calculate_indicators(df)
        suggestion = generate_suggestion(df)
        latest_price = df['Close'].iloc[-1]

        st.metric(label="📊 最新价格", value=f"${latest_price:.2f}")
        st.metric(label="🧠 买入建议概率", value=f"{suggestion:.2f} %")

        fig, ax = plt.subplots()
        ax.plot(df.index, df['Close'], label='价格')
        ax.plot(df.index, df['SMA_12'], label='SMA_12')
        ax.plot(df.index, df['EMA_12'], label='EMA_12')
        ax.fill_between(df.index, df['BB_lower'], df['BB_upper'], color='gray', alpha=0.2, label='布林带')
        ax.legend()
        st.pyplot(fig)

    except Exception as e:
        st.error(f"❌ 数据获取失败：{str(e)}")

# ================== 自动刷新 & 主体 ==================
placeholder = st.empty()
refresh_interval = 15 * 60  # 15 分钟

while True:
    with placeholder.container():
        st.title("📈 加密货币多周期合约分析")

        for symbol, (yf_symbol, name) in symbols.items():
            st.markdown(f"## 🔹 {name}（{symbol}）")
            cols = st.columns(2)
            for idx, (interval_key, (interval, lookback)) in enumerate(intervals.items()):
                with cols[idx % 2]:
                    display_analysis(symbol, name, interval_key, lookback)

        st.info(f"⏳ 页面将在 15 分钟后自动刷新（当前时间：{time.strftime('%Y-%m-%d %H:%M:%S')}）")

    st.experimental_rerun()
