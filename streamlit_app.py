import streamlit as st
import requests
import pandas as pd
import pytz
from datetime import datetime
import ta

st.set_page_config(page_title="📈 加密貨幣分析助手", layout="wide")
st.title("📈 加密貨幣分析助手（Beta）")
st.markdown("分析週期：1小時｜追蹤幣種：**BTC / ETH / SOL**")

# 顯示香港時間
hk_time = datetime.now(pytz.timezone("Asia/Hong_Kong")).strftime("%Y-%m-%d %H:%M:%S")
st.markdown(f"更新時間（香港）：{hk_time}")

# 幣種對應的 CoinGecko ID
coin_ids = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "SOL": "solana"
}

# 獲取 CoinGecko 小時價格資料
def fetch_hourly_data(coin_id):
    url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart"
    params = {
        "vs_currency": "usd",
        "days": "1",
        "interval": "hourly"
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        prices = data["prices"]
        df = pd.DataFrame(prices, columns=["timestamp", "price"])
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        df.set_index("timestamp", inplace=True)
        return df

    except Exception as e:
        st.error(f"{coin_id.upper()} 歷史數據獲取錯誤：{e}")
        return None

# 分析技術指標與建議
def analyze_indicators(df):
    result = {}

    df["SMA20"] = ta.trend.sma_indicator(df["price"], window=20)
    df["EMA20"] = ta.trend.ema_indicator(df["price"], window=20)
    df["RSI"] = ta.momentum.rsi(df["price"], window=14)
    macd = ta.trend.macd(df["price"])
    df["MACD"] = macd.macd()
    df["MACD_signal"] = macd.macd_signal()
    bb = ta.volatility.BollingerBands(df["price"])
    df["BB_upper"] = bb.bollinger_hband()
    df["BB_lower"] = bb.bollinger_lband()

    last = df.iloc[-1]

    # 簡單邏輯生成建議
    score = 0
    explanation = []

    # RSI
    if last["RSI"] < 30:
        score += 1
        explanation.append("RSI < 30（超賣）")
    elif last["RSI"] > 70:
        score -= 1
        explanation.append("RSI > 70（超買）")

    # MACD
    if last["MACD"] > last["MACD_signal"]:
        score += 1
        explanation.append("MACD 多頭")
    else:
        score -= 1
        explanation.append("MACD 空頭")

    # 價格 vs SMA
    if last["price"] > last["SMA20"]:
        score += 1
        explanation.append("價格高於 SMA20")
    else:
        score -= 1
        explanation.append("價格低於 SMA20")

    # 價格是否突破布林帶
    if last["price"] < last["BB_lower"]:
        score += 1
        explanation.append("價格低於布林下軌")
    elif last["price"] > last["BB_upper"]:
        score -= 1
        explanation.append("價格高於布林上軌")

    # 分數轉換為建議
    if score >= 2:
        suggestion = "✅ 建議：**買入**（機率：約 70%）"
    elif score <= -2:
        suggestion = "❌ 建議：**賣出**（機率：約 70%）"
    else:
        suggestion = "⚠️ 建議：**觀望**（機率：約 50%）"

    result["score"] = score
    result["explanation"] = explanation
    result["suggestion"] = suggestion
    return result, df

# 主體流程
for symbol, coin_id in coin_ids.items():
    with st.expander(f"🔍 {symbol} 分析結果"):
        df = fetch_hourly_data(coin_id)
        if df is not None:
            result, df_with_indicators = analyze_indicators(df)
            st.line_chart(df_with_indicators[["price", "SMA20", "EMA20"]].dropna(), height=300)
            st.markdown("📊 技術指標說明：")
            for line in result["explanation"]:
                st.markdown(f"- {line}")
            st.markdown(result["suggestion"])
        else:
            st.error(f"{symbol} 數據無法顯示")
