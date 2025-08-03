import streamlit as st
import requests
import pandas as pd
from datetime import datetime
import pytz

# 設定頁面標題與基本配置
st.set_page_config(page_title="加密貨幣分析助手", layout="centered")
st.title("📈 加密貨幣分析助手（Beta）")
st.caption("分析週期：1小時｜追蹤幣種：BTC / ETH / SOL")

# 幣種與CoinGecko對應ID
symbols = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "SOL": "solana"
}

# 設定香港時區
tz_hk = pytz.timezone("Asia/Hong_Kong")
now_hk = datetime.now(tz_hk).strftime("%Y-%m-%d %H:%M:%S")

# 顯示更新時間
st.markdown(f"🕒 更新時間：{now_hk}")

# 價格顯示區域
for symbol, coingecko_id in symbols.items():
    try:
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={coingecko_id}&vs_currencies=usd"
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        price = data[coingecko_id]["usd"]
        st.success(f"{symbol} 最新價格：${price:,.2f} USD")
    except Exception as e:
        st.error(f"❌ 無法獲取 {symbol} 價格｜錯誤訊息：{str(e)}")
