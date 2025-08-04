import streamlit as st
import pandas as pd
import requests
import datetime
import time
import numpy as np
import plotly.graph_objects as go
import ta  # technical analysis

# ========== 设置页面 ==========
st.set_page_config(page_title="📈 加密貨幣分析助手", layout="wide")

st.title("📈 加密貨幣分析助手（Beta）")
st.caption("分析週期：1小時｜追蹤幣種：BTC / ETH / SOL")

# ========== 公共函數 ==========
@st.cache_data(ttl=3600)
def get_price_history(coin_id):
    try:
        url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart"
        params = {
            "vs_currency": "usd",
            "days": "1",
            "interval": "hourly"
        }
        res = requests.get(url, params=params)
        res.raise_for_status()
        data = res.json()
        prices = data['prices']
        df = pd.DataFrame(prices, columns=['timestamp', 'price'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        df['price'] = df['price'].astype(float)
        return df
    except Exception as e:
        return f"歷史數據獲取錯誤：{str(e)}"

def analyze_with_indicators(df):
    try:
        df = df.copy()
        df['sma'] = ta.trend.sma_indicator(df['price'], window=5)
        df['ema'] = ta.trend.ema_indicator(df['price'], window=5)
        df['rsi'] = ta.momentum.rsi(df['price'], window=14)
        macd = ta.trend.macd(df['price'])
        df['macd'] = macd.macd()
        df['macd_signal'] = macd.macd_signal()
        bb = ta.volatility.BollingerBands(df['price'], window=20, window_dev=2)
        df['bb_upper'] = bb.bollinger_hband()
        df['bb_lower'] = bb.bollinger_lband()

        # 綜合指標生成買賣建議
        last = df.iloc[-1]
        score = 0
        total = 0

        # RSI 指標
        if last['rsi'] < 30:
            score += 1
        elif last['rsi'] > 70:
            score -= 1
        total += 1

        # MACD 指標
        if last['macd'] > last['macd_signal']:
            score += 1
        else:
            score -= 1
        total += 1

        # 均線
        if last['price'] > last['sma']:
            score += 1
        else:
            score -= 1
        total += 1

        if last['price'] > last['ema']:
            score += 1
        else:
            score -= 1
        total += 1

        # 布林帶
        if last['price'] < last['bb_lower']:
            score += 1
        elif last['price'] > last['bb_upper']:
            score -= 1
        total += 1

        # 預測概率
        buy_probability = (score + total) / (2 * total)
        buy_probability = max(0, min(1, buy_probability))
        return df, round(buy_probability * 100, 2)
    except Exception as e:
        return None, f"分析錯誤：{str(e)}"

def plot_chart(df, coin_symbol):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df.index, y=df['price'], mode='lines', name='Price'))
    fig.add_trace(go.Scatter(x=df.index, y=df['sma'], mode='lines', name='SMA'))
    fig.add_trace(go.Scatter(x=df.index, y=df['ema'], mode='lines', name='EMA'))
    fig.update_layout(title=f"{coin_symbol.upper()} 價格與指標", xaxis_title="時間", yaxis_title="價格 (USD)")
    return fig

# ========== 幣種處理 ==========
coin_map = {
    "bitcoin": "BTC",
    "ethereum": "ETH",
    "solana": "SOL"
}

for coin_id, coin_symbol in coin_map.items():
    st.markdown(f"## {coin_symbol}")
    df = get_price_history(coin_id)
    if isinstance(df, str):
        st.error(f"{coin_symbol} 數據無法顯示｜{df}")
        continue
    df_result, suggestion = analyze_with_indicators(df)
    if isinstance(suggestion, str):
        st.error(suggestion)
        continue

    st.plotly_chart(plot_chart(df_result, coin_symbol), use_container_width=True)
    st.metric(label=f"{coin_symbol} 買入建議概率", value=f"{suggestion} %")
