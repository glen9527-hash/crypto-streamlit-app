import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import time
import datetime as dt

# ========== 自动刷新逻辑 ==========
refresh_interval = 15 * 60  # 15分钟
if "last_refresh" not in st.session_state:
    st.session_state.last_refresh = time.time()
elapsed = time.time() - st.session_state.last_refresh
if elapsed > refresh_interval:
    st.session_state.last_refresh = time.time()
    st.experimental_rerun()

# ========== 页面设置 ==========
st.set_page_config(page_title="加密货币分析", layout="wide")
st.title("📊 加密货币多周期分析 (yfinance 数据源)")

# 币种映射（yfinance 代码）
symbols = {
    "BTC": "BTC-USD",
    "ETH": "ETH-USD",
    "SOL": "SOL-USD"
}

# 分析周期映射（yfinance interval 参数）
intervals = {
    "15分钟": "15m",
    "1小时": "1h",
    "4小时": "4h",
    "24小时": "1d"
}

# 技术指标函数
def calculate_indicators(df):
    df["SMA_20"] = df["Close"].rolling(window=20).mean()
    df["EMA_20"] = df["Close"].ewm(span=20, adjust=False).mean()
    delta = df["Close"].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df["RSI_14"] = 100 - (100 / (1 + rs))
    df["EMA_12"] = df["Close"].ewm(span=12, adjust=False).mean()
    df["EMA_26"] = df["Close"].ewm(span=26, adjust=False).mean()
    df["MACD"] = df["EMA_12"] - df["EMA_26"]
    df["MACD_signal"] = df["MACD"].ewm(span=9, adjust=False).mean()
    df["BB_mid"] = df["SMA_20"]
    df["BB_up"] = df["SMA_20"] + 2 * df["Close"].rolling(window=20).std()
    df["BB_low"] = df["SMA_20"] - 2 * df["Close"].rolling(window=20).std()
    return df

# 综合买卖建议
def get_signal(df):
    latest = df.iloc[-1]
    score = 0
    if latest["Close"] > latest["SMA_20"]:
        score += 1
    if latest["MACD"] > latest["MACD_signal"]:
        score += 1
    if latest["RSI_14"] < 30:
        score += 1
    elif latest["RSI_14"] > 70:
        score -= 1
    if latest["Close"] < latest["BB_low"]:
        score += 1
    elif latest["Close"] > latest["BB_up"]:
        score -= 1
    probability = round((score + 5) * 10, 2)  # 转成百分比
    if score >= 2:
        action = "买入"
    elif score <= -2:
        action = "卖出"
    else:
        action = "观望"
    return action, probability

# 循环分析
for coin, ticker in symbols.items():
    st.subheader(f"💰 {coin} 分析")
    cols = st.columns(len(intervals))
    for i, (label, yf_interval) in enumerate(intervals.items()):
        try:
            # 下载数据
            if yf_interval in ["15m", "1h"]:
                period = "7d"  # yfinance 限制
            elif yf_interval == "4h":
                period = "1mo"
            else:
                period = "3mo"
            df = yf.download(ticker, period=period, interval=yf_interval)
            df = df[["Open", "High", "Low", "Close", "Volume"]]
            df = calculate_indicators(df.dropna())
            action, prob = get_signal(df)

            with cols[i]:
                st.markdown(f"**{label} 周期**")
                st.line_chart(df["Close"])
                st.write(f"建议: **{action}**")
                st.write(f"概率: **{prob}%**")
        except Exception as e:
            with cols[i]:
                st.error(f"数据获取失败: {e}")
