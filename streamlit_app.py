import streamlit as st
import pandas as pd
import requests
import datetime
import pytz
import plotly.graph_objects as go
import ta

st.set_page_config(page_title="📈 加密幣分析助手（CoinCap 測試版）", layout="wide")
st.title("📈 加密幣分析助手（CoinCap 測試版）")
st.caption("分析週期：1 小時｜追蹤幣種：BTC / ETH / SOL")

COINS = {
    "bitcoin": "BTC",
    "ethereum": "ETH",
    "solana": "SOL"
}

def get_hk_time():
    return datetime.datetime.now(pytz.timezone("Asia/Hong_Kong")).strftime("%Y-%m-%d %H:%M:%S")

@st.cache_data(ttl=600)
def get_history(coin_id):
    url = f"https://api.coincap.io/v2/assets/{coin_id}/history"
    params = {"interval": "h1"}
    try:
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        json = r.json()
        data = json.get("data", [])
        df = pd.DataFrame(data)
        df["timestamp"] = pd.to_datetime(df["time"], unit="ms")
        df.set_index("timestamp", inplace=True)
        df["price"] = pd.to_numeric(df["priceUsd"])
        return df[["price"]]
    except Exception as e:
        return str(e)

def analyze(df):
    df = df.copy()
    df["sma"] = ta.trend.sma_indicator(df["price"], window=5)
    df["ema"] = ta.trend.ema_indicator(df["price"], window=5)
    df["rsi"] = ta.momentum.rsi(df["price"], window=14)
    macd = ta.trend.macd(df["price"])
    df["macd"] = macd.macd()
    df["signal"] = macd.macd_signal()
    bb = ta.volatility.BollingerBands(df["price"], window=20, window_dev=2)
    df["bb_upper"] = bb.bollinger_hband()
    df["bb_lower"] = bb.bollinger_lband()

    last = df.iloc[-1]
    score = 0; total = 5

    if last["rsi"] < 30: score += 1
    elif last["rsi"] > 70: score -= 1
    score += 1 if last["macd"] > last["signal"] else -1
    score += 1 if last["price"] > last["sma"] else -1
    score += 1 if last["price"] > last["ema"] else -1
    if last["price"] < last["bb_lower"]: score += 1
    elif last["price"] > last["bb_upper"]: score -= 1

    buy_prob = max(0, min(1, (score + total) / (2 * total)))
    return df, round(buy_prob * 100, 2)

def plot_df(df, symbol):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df.index, y=df["price"], name="Price"))
    fig.add_trace(go.Scatter(x=df.index, y=df["sma"], name="SMA"))
    fig.add_trace(go.Scatter(x=df.index, y=df["ema"], name="EMA"))
    fig.update_layout(title=f"{symbol} 價格與技術指標", xaxis_title="時間", yaxis_title="USD")
    return fig

for cid, sym in COINS.items():
    st.subheader(sym)
    df = get_history(cid)
    if isinstance(df, str):
        st.error(f"{sym} 數據獲取錯誤：{df}")
        continue
    df2, prob = analyze(df)
    st.plotly_chart(plot_df(df2, sym), use_container_width=True)
    st.metric(label=f"{sym} 買入建議概率", value=f"{prob} %")

st.caption(f"最後更新時間（香港）: {get_hk_time()}")
