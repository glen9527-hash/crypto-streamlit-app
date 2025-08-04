import streamlit as st
import pandas as pd
import numpy as np
import datetime
from binance.client import Client
from binance.exceptions import BinanceAPIException
import plotly.graph_objs as go

# 页面标题
st.set_page_config(page_title="加密貨幣分析基礎版", layout="wide")
st.title("📊 加密貨幣分析基礎版")

# 內嵌 Binance API Key（僅測試用）
API_KEY = "6beNcnbZ5gQ9WslIW8xFcz9YsnpuzeFqvzTPzRUbp281K1pNkEqLsAWdjaNO8A72"
API_SECRET = "qawLXPN4yJWOj0XvoJH5ncy3bXdC7bNlVPV1gxDDvdPeLehQk1mc3jDCWuJI2p62"

# 初始化 Binance 客戶端
client = None
try:
    client = Client(API_KEY, API_SECRET)
    client.ping()
    st.success("✅ 成功連接 Binance API")
except BinanceAPIException as e:
    st.error("❌ Binance API 錯誤，請確認 Key 是否有效")
    st.stop()
except Exception as e:
    st.error(f"❌ API 初始化失敗：{e}")
    st.stop()

# 幣種與時間設定
symbol = st.selectbox("選擇幣種", ["BTCUSDT", "ETHUSDT", "SOLUSDT"])
interval = "1h"
lookback_hours = 24

# 取得歷史K線數據
def get_klines(symbol, interval, lookback):
    try:
        klines = client.get_klines(symbol=symbol, interval=interval, limit=lookback)
        df = pd.DataFrame(klines, columns=[
            "timestamp", "open", "high", "low", "close", "volume",
            "close_time", "quote_asset_volume", "number_of_trades",
            "taker_buy_base_volume", "taker_buy_quote_volume", "ignore"
        ])
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        df.set_index("timestamp", inplace=True)
        df = df[["open", "high", "low", "close", "volume"]].astype(float)
        return df
    except Exception as e:
        st.error(f"❌ 獲取 K 線數據失敗：{e}")
        return None

df = get_klines(symbol, interval, lookback_hours)
if df is None:
    st.stop()

# 添加技術指標
def add_indicators(df):
    df["SMA20"] = df["close"].rolling(window=20).mean()
    df["EMA20"] = df["close"].ewm(span=20).mean()

    delta = df["close"].diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.rolling(window=14).mean()
    avg_loss = loss.rolling(window=14).mean()
    rs = avg_gain / avg_loss
    df["RSI"] = 100 - (100 / (1 + rs))

    exp1 = df["close"].ewm(span=12).mean()
    exp2 = df["close"].ewm(span=26).mean()
    df["MACD"] = exp1 - exp2
    df["Signal"] = df["MACD"].ewm(span=9).mean()

    df["Upper"] = df["close"].rolling(window=20).mean() + 2 * df["close"].rolling(window=20).std()
    df["Lower"] = df["close"].rolling(window=20).mean() - 2 * df["close"].rolling(window=20).std()
    return df

df = add_indicators(df)

# 買賣建議概率
def generate_signal(df):
    last = df.iloc[-1]
    score = 0
    if last["close"] > last["SMA20"]:
        score += 1
    if last["RSI"] < 30:
        score += 1
    if last["MACD"] > last["Signal"]:
        score += 1
    if last["close"] < last["Lower"]:
        score += 1
    buy_prob = round((score / 4) * 100, 2)
    return buy_prob

buy_probability = generate_signal(df)

# 顯示圖表
st.subheader(f"{symbol} - 最近 {lookback_hours} 小時價格走勢")
fig = go.Figure()
fig.add_trace(go.Scatter(x=df.index, y=df["close"], mode='lines', name='收盤價'))
fig.add_trace(go.Scatter(x=df.index, y=df["SMA20"], mode='lines', name='SMA20'))
fig.add_trace(go.Scatter(x=df.index, y=df["EMA20"], mode='lines', name='EMA20'))
fig.update_layout(height=500)
st.plotly_chart(fig, use_container_width=True)

# 顯示買入建議概率
st.metric(label="📈 買入建議概率", value=f"{buy_probability} %")
