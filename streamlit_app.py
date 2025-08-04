import streamlit as st
from binance.client import Client
from datetime import datetime, timedelta
import pandas as pd
import pytz
import time
import numpy as np

# 设置 Binance API Key 和 Secret（测试用）
API_KEY = "sT2x41WY7G3ANAcFUA7hRV2lgWppCI0kFuTqkpTcpWk6ue2VlAq1BgNzXmwFJoQx"
API_SECRET = "mpefxQi8YBTgc2LT9mzHGYIKe3mWNc2lAOI6ICboJ3AEnq9F8GmdMr6jCrnCpKrJ"

# 初始化 Binance 客户端
client = Client(API_KEY, API_SECRET)

# 设置香港时区
hk_tz = pytz.timezone("Asia/Hong_Kong")

# Streamlit 页面标题
st.set_page_config(page_title="加密货币合约分析 - 基础版", layout="wide")
st.title("📊 加密货币合约分析工具（基础版）")

# 可选币种与时间周期
symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
intervals = {"1小时": Client.KLINE_INTERVAL_1HOUR}

selected_symbol = st.selectbox("选择币种", symbols)
selected_interval = "1小时"
interval = intervals[selected_interval]

# 获取历史K线数据
def get_klines(symbol, interval, lookback=24):
    try:
        klines = client.get_klines(symbol=symbol, interval=interval, limit=lookback)
        df = pd.DataFrame(klines, columns=[
            "timestamp", "open", "high", "low", "close", "volume",
            "close_time", "quote_asset_volume", "number_of_trades",
            "taker_buy_base_volume", "taker_buy_quote_volume", "ignore"
        ])
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms").dt.tz_localize("UTC").dt.tz_convert(hk_tz)
        df["close"] = df["close"].astype(float)
        return df[["timestamp", "close"]]
    except Exception as e:
        st.error(f"❌ 无法获取行情数据，请确认 API 是否有效。\n\n错误详情：{e}")
        return None

# 计算技术指标
def calculate_indicators(df):
    df["SMA_5"] = df["close"].rolling(window=5).mean()
    df["SMA_10"] = df["close"].rolling(window=10).mean()
    df["EMA_5"] = df["close"].ewm(span=5).mean()
    df["EMA_10"] = df["close"].ewm(span=10).mean()
    delta = df["close"].diff()
    gain = np.where(delta > 0, delta, 0)
    loss = np.where(delta < 0, -delta, 0)
    avg_gain = pd.Series(gain).rolling(window=14).mean()
    avg_loss = pd.Series(loss).rolling(window=14).mean()
    rs = avg_gain / avg_loss
    df["RSI"] = 100 - (100 / (1 + rs))
    return df

# 综合买卖建议
def generate_signal(df):
    try:
        last_row = df.iloc[-1]
        score = 0
        if last_row["SMA_5"] > last_row["SMA_10"]:
            score += 1
        if last_row["EMA_5"] > last_row["EMA_10"]:
            score += 1
        if last_row["RSI"] < 30:
            score += 1
        elif last_row["RSI"] > 70:
            score -= 1
        probability = int((score + 1) * 33.3)
        return max(0, min(100, probability))
    except Exception as e:
        st.error(f"❌ 生成信号失败：{e}")
        return None

# 主体逻辑
df = get_klines(selected_symbol, interval)
if df is not None:
    df = calculate_indicators(df)

    st.subheader("📈 当前行情走势（最近24小时）")
    st.line_chart(df.set_index("timestamp")[["close", "SMA_5", "SMA_10", "EMA_5", "EMA_10"]])

    st.subheader("🧠 综合买卖建议（仅供参考）")
    probability = generate_signal(df)
    if probability is not None:
        st.metric(label="买入建议概率", value=f"{probability}%")
