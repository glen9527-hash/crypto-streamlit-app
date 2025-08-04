import streamlit as st
import pandas as pd
import requests
import datetime
import pytz
import ta

# 幣種配置
ASSETS = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "SOL": "solana"
}

# 取得香港時間
def get_hk_time():
    return datetime.datetime.now(pytz.timezone('Asia/Hong_Kong')).strftime('%Y-%m-%d %H:%M:%S')

# 從 CoinGecko 取得歷史價格資料（每小時，過去24小時）
def get_price_data(asset_id):
    url = f"https://api.coingecko.com/api/v3/coins/{asset_id}/market_chart"
    params = {
        "vs_currency": "usd",
        "days": "1",
        "interval": "hourly"
    }
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        prices = data['prices']
        df = pd.DataFrame(prices, columns=["timestamp", "price"])
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        df.set_index("timestamp", inplace=True)
        return df
    except Exception as e:
        return None

# 計算技術指標並綜合給出買/賣建議機率
def analyze(df):
    df = df.copy()
    df['SMA'] = ta.trend.sma_indicator(df['price'], window=5)
    df['EMA'] = ta.trend.ema_indicator(df['price'], window=5)
    df['RSI'] = ta.momentum.rsi(df['price'], window=14)
    macd = ta.trend.macd(df['price'])
    df['MACD'] = macd.macd_diff()
    bb = ta.volatility.BollingerBands(df['price'], window=20, window_dev=2)
    df['BB_high'] = bb.bollinger_hband()
    df['BB_low'] = bb.bollinger_lband()

    # 簡單規則：5項指標中有幾項偏向上漲
    latest = df.iloc[-1]
    score = 0
    total = 5

    if latest['price'] > latest['SMA']:
        score += 1
    if latest['price'] > latest['EMA']:
        score += 1
    if latest['RSI'] < 30:
        score += 1
    if latest['MACD'] > 0:
        score += 1
    if latest['price'] < latest['BB_low']:
        score += 1

    buy_prob = round(score / total * 100, 2)
    sell_prob = round(100 - buy_prob, 2)
    return buy_prob, sell_prob, df

# Streamlit 主介面
st.title("📈 加密貨幣分析助手（基礎版）")
st.markdown("分析週期：1小時｜追蹤幣種：BTC / ETH / SOL")

for symbol, asset_id in ASSETS.items():
    st.subheader(f"💰 {symbol}")

    df = get_price_data(asset_id)
    if df is None:
        st.error(f"{symbol} 數據獲取失敗，請稍後重試。")
        continue

    buy_prob, sell_prob, df = analyze(df)

    st.metric("📊 買入機率", f"{buy_prob} %")
    st.metric("📉 賣出機率", f"{sell_prob} %")
    st.line_chart(df['price'])

# 顯示更新時間（香港）
st.caption(f"最後更新時間（香港）：{get_hk_time()}")
