import streamlit as st
import requests
import time
from datetime import datetime
import pytz

# 設定頁面標題
st.set_page_config(page_title="📈 加密貨幣分析助手", layout="wide")

# 定義幣種與Binance永續合約交易對
symbols = {
    "BTC": "BTCUSDT",
    "ETH": "ETHUSDT",
    "SOL": "SOLUSDT"
}

# 顯示標題
st.title("📈 加密貨幣分析助手（Beta）")
st.write("分析週期：**1 分鐘**｜追蹤幣種：BTC / ETH / SOL")

# 設定香港時區
hk_tz = pytz.timezone('Asia/Hong_Kong')
now_hk = datetime.utcnow().replace(tzinfo=pytz.utc).astimezone(hk_tz)
st.write(f"更新時間（香港）：{now_hk.strftime('%Y-%m-%d %H:%M:%S')}")

# Binance永續合約API端點
BASE_URL = "https://fapi.binance.com/fapi/v1/ticker/price"

# 用於記錄錯誤的幣種
error_symbols = []

# 顯示價格
st.subheader("🔍 最新價格（Binance 永續合約）")
for name, symbol in symbols.items():
    try:
        # 發送API請求
        st.write(f"正在請求 {name} ({symbol}) 的價格...")
        response = requests.get(BASE_URL, params={"symbol": symbol}, timeout=30)
        response.raise_for_status()  # 檢查HTTP狀態碼
        data = response.json()
        
        # 顯示API響應以便調試
        st.write(f"API 響應：{data}")
        
        # 檢查並提取價格
        if 'price' in data:
            price = float(data['price'])
            st.write(f"✅ {name} 現價：**${price:,.2f}**")
        else:
            error_symbols.append(name)
            st.write(f"❌ {name} 的API響應中缺少 'price' 字段")
    except requests.exceptions.RequestException as e:
        error_symbols.append(name)
        st.write(f"❌ 無法獲取 {name} 價格：{e}")
        if 'response' in locals():
            st.write(f"API 響應狀態碼：{response.status_code}")
            st.write(f"API 響應內容：{response.text}")
    except Exception as e:
        error_symbols.append(name)
        st.write(f"❌ 處理 {name} 時發生錯誤：{e}")
    
    # 添加延遲以避免超過API請求限制
    time.sleep(1)

# 顯示總體錯誤提示
if error_symbols:
    st.warning("⚠️ 以下幣種價格獲取失敗：" + " / ".join(error_symbols))
