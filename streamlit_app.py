import streamlit as st
import yfinance as yf
import pandas as pd
import time
import ta
import matplotlib.pyplot as plt

# 页面配置
st.set_page_config(page_title="💹 加密货币分析", layout="wide")

# 定义分析函数
def get_crypto_data(symbol, interval, period):
    try:
        df = yf.download(tickers=symbol, interval=interval, period=period, progress=False)
        df = df.dropna()
        df['Close'] = df['Close'].astype(float)
        return df
    except Exception as e:
        st.error(f"{symbol} 数据获取失败：{e}")
        return None

def calculate_indicators(df):
    # 技术指标计算
    df['SMA_12'] = ta.trend.sma_indicator(df['Close'], window=12)
    df['EMA_12'] = ta.trend.ema_indicator(df['Close'], window=12)
    df['RSI'] = ta.momentum.rsi(df['Close'], window=14)
    macd = ta.trend.macd_diff(df['Close'])
    df['MACD'] = macd
    bollinger = ta.volatility.BollingerBands(df['Close'])
    df['Bollinger_Upper'] = bollinger.bollinger_hband()
    df['Bollinger_Lower'] = bollinger.bollinger_lband()
    return df

def generate_signal(df):
    latest = df.iloc[-1]
    score = 0
    total = 5

    # 简单打分规则
    if latest['Close'] > latest['SMA_12']:
        score += 1
    if latest['Close'] > latest['EMA_12']:
        score += 1
    if latest['RSI'] < 30:
        score += 1
    if latest['MACD'] > 0:
        score += 1
    if latest['Close'] < latest['Bollinger_Lower']:
        score += 1

    probability = round((score / total) * 100, 2)
    return probability

def display_analysis(symbol, name, interval, period):
    st.markdown(f"## 💰 {name} 分析結果（周期：{period}）")
    df = get_crypto_data(symbol, interval, period)
    if df is not None and len(df) > 30:
        df = calculate_indicators(df)
        signal = generate_signal(df)
        st.write(f"📈 当前价格：{df['Close'].iloc[-1]:.2f} USD")
        st.write(f"✅ 买入概率：`{signal}%`")

        fig, ax = plt.subplots(figsize=(12, 4))
        ax.plot(df['Close'], label='Close')
        ax.plot(df['SMA_12'], label='SMA 12')
        ax.plot(df['EMA_12'], label='EMA 12')
        ax.set_title(f'{name} 走势图')
        ax.legend()
        st.pyplot(fig)
    else:
        st.error(f"{name} 数据不足，无法计算")

# 自动刷新每15分钟
st_autorefresh = st.experimental_rerun if time.localtime().tm_min % 15 == 0 else None

# 币种与周期设置
assets = {
    "BTC": ("BTC-USD", "Bitcoin"),
    "ETH": ("ETH-USD", "Ethereum"),
    "SOL": ("SOL-USD", "Solana"),
}

interval_map = {
    "15分钟": ("15m", "1d"),
    "1小时": ("1h", "5d"),
    "4小时": ("1h", "10d"),
    "24小时": ("1h", "30d"),
}

# UI 选择
selected_interval = st.selectbox("选择分析周期", list(interval_map.keys()))

for key in assets:
    symbol, name = assets[key]
    interval, period = interval_map[selected_interval]
    display_analysis(symbol, name, interval, period)
