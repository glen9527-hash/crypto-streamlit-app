import streamlit as st
import pandas as pd
import yfinance as yf
import ta
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import pytz
import time

st.set_page_config(page_title="加密货币分析", layout="wide")

def get_data(symbol, interval, period):
    df = yf.download(tickers=symbol, interval=interval, period=period)
    df = df.dropna()
    df = df.reset_index()
    df['Datetime'] = pd.to_datetime(df['Datetime']).dt.tz_localize(None)
    return df

def calculate_indicators(df):
    close = df['Close']
    df['SMA_12'] = ta.trend.SMAIndicator(close=close, window=12).sma_indicator()
    df['EMA_12'] = ta.trend.EMAIndicator(close=close, window=12).ema_indicator()
    df['RSI'] = ta.momentum.RSIIndicator(close=close, window=14).rsi()
    df['MACD'] = ta.trend.MACD(close=close).macd_diff()
    boll = ta.volatility.BollingerBands(close=close, window=20, window_dev=2)
    df['Bollinger_Upper'] = boll.bollinger_hband()
    df['Bollinger_Lower'] = boll.bollinger_lband()
    return df

def generate_signal(df):
    latest = df.iloc[-1]
    score = 0
    total = 0

    if latest['Close'] > latest['SMA_12']:
        score += 1
    total += 1

    if latest['Close'] > latest['EMA_12']:
        score += 1
    total += 1

    if latest['RSI'] < 30:
        score += 1
    elif latest['RSI'] > 70:
        score -= 1
    total += 1

    if latest['MACD'] > 0:
        score += 1
    else:
        score -= 1
    total += 1

    if latest['Close'] < latest['Bollinger_Lower']:
        score += 1
    elif latest['Close'] > latest['Bollinger_Upper']:
        score -= 1
    total += 1

    probability = round((score / total + 1) / 2, 2)
    return probability

def display_analysis(symbol, name, interval, period):
    df = get_data(symbol, interval, period)
    df = calculate_indicators(df)
    prob = generate_signal(df)
    hk_time = datetime.utcnow() + timedelta(hours=8)
    current_price = df['Close'].iloc[-1]

    st.subheader(f"💰 {name} 分析結果")
    st.markdown(f"**當前香港時間：** {hk_time.strftime('%Y-%m-%d %H:%M:%S')}")
    st.markdown(f"**最新價格：** ${current_price:.2f}")
    st.markdown(f"**買入建議機率：** {prob * 100:.1f}%")

    fig, ax = plt.subplots()
    ax.plot(df['Datetime'], df['Close'], label='Close Price')
    ax.plot(df['Datetime'], df['SMA_12'], label='SMA 12')
    ax.plot(df['Datetime'], df['EMA_12'], label='EMA 12')
    ax.set_title(f"{name} 價格走勢")
    ax.legend()
    st.pyplot(fig)

coins = {
    "BTC-USD": "Bitcoin",
    "ETH-USD": "Ethereum",
    "SOL-USD": "Solana"
}

intervals = {
    "15分钟": ("15m", "1d"),
    "1小时": ("1h", "2d"),
    "4小时": ("1h", "7d"),
    "24小时": ("1h", "30d")
}

selected_interval = st.selectbox("選擇分析週期", list(intervals.keys()), index=1)

refresh_interval = 60 * 15  # 15分鐘
last_refresh = st.session_state.get("last_refresh", 0)
now = time.time()

if now - last_refresh > refresh_interval:
    st.session_state["last_refresh"] = now

for symbol, name in coins.items():
    interval, period = intervals[selected_interval]
    display_analysis(symbol, name, interval, period)
