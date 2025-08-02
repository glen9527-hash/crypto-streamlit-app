import streamlit as st
import requests
from datetime import datetime, timedelta
import pytz

# 設定頁面標題
st.set_page_config(page_title="📈 加密貨幣分析助手", layout="wide")

# 幣種與對應的Binance合約交易對
symbols = {
    "BTC": "BTCUSDT",
    "ETH": "ETHUSDT",
    "SOL": "SOLUSDT"
}

# 顯示標題
st.title("📈 加密貨幣分析助手（Beta）")
st.write("分析週期：**1 小時**｜追蹤幣種：BTC / ETH / SOL")

# 設定香港時區
hk_tz = pytz.timezone('Asia/Hong_Kong')
now_hk = datetime.utcnow().replace(tzinfo=pytz.utc).astimezone(hk_tz)
st.write(f"更新時間（香港）：{now_hk.strftime('%Y-%m-%d %H:%M:%S')}")

# Binance API endpoint
BASE_URL = "https://fapi.binance.com/fapi/v1/ticker/price"

# 用來顯示錯誤狀態
error_symbols = []

# 顯示每個幣種的價格
st.subheader("🔍 最新價格（Binance 永續合約）")
for name, symbol in symbols.items():
    try:
        response = requests.get(BASE_URL, params={"symbol": symbol}, timeout=10)
        response.raise_for_status()
        data = response.json()
        price = float(data['price'])
        st.write(f"✅ {name} 現價：**${price:,.2f}**")
    except Exception as e:
        error_symbols.append(name)
        st.write(f"❌ 無法獲取 {name} 價格：{e}")

# 顯示總體錯誤提示
if error_symbols:
    st.warning("⚠️ 以下幣種價格獲取失敗：" + " / ".join(error_symbols))
