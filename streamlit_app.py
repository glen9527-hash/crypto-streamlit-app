import streamlit as st
import requests
import datetime

st.set_page_config(page_title="Crypto Signal Bot", layout="centered")

st.title("📈 加密貨幣分析助手（Beta）")
st.write("分析週期：1小時｜追蹤幣種：BTC / ETH / SOL")

@st.cache_data(ttl=180)  # 每3分鐘刷新
def fetch_price(symbol):
    url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}USDT"
    response = requests.get(url)
    if response.status_code == 200:
        return float(response.json()["price"])
    else:
        return None

def mock_signal(symbol, price):
    # 模擬簡單訊號產出（實際之後可接入技術分析API）
    return f"{symbol}: 現價 {price:.2f}，1H RSI 過熱（模擬），建議觀望或設空單策略"

for symbol in ["BTC", "ETH", "SOL"]:
    price = fetch_price(symbol)
    if price:
        st.subheader(f"{symbol} 分析建議")
        st.info(mock_signal(symbol, price))
    else:
        st.warning(f"無法獲取 {symbol} 價格")

st.caption(f"更新時間：{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
