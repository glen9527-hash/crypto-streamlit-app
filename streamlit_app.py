import streamlit as st
import requests
from datetime import datetime, timedelta
import pytz

# Binance API endpoint
BASE_URL = 'https://api.binance.com/api/v3/ticker/price'

# 支援的幣種
SUPPORTED_SYMBOLS = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT']
SYMBOL_NAME_MAP = {
    'BTCUSDT': 'BTC',
    'ETHUSDT': 'ETH',
    'SOLUSDT': 'SOL'
}

# 時間轉換為香港時間
def get_hk_time():
    tz = pytz.timezone('Asia/Hong_Kong')
    return datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")

# 獲取價格
def get_price(symbol):
    try:
        response = requests.get(BASE_URL, params={'symbol': symbol}, timeout=5)
        response.raise_for_status()
        data = response.json()
        return float(data['price'])
    except requests.exceptions.RequestException as e:
        return f"網絡錯誤：{str(e)}"
    except ValueError:
        return "返回數據格式錯誤"
    except KeyError:
        return "返回資料缺少 'price' 欄位"
    except Exception as e:
        return f"未知錯誤：{str(e)}"

# Streamlit 介面
st.set_page_config(page_title="加密貨幣分析助手", layout="wide")
st.title("📈 加密貨幣分析助手（Beta）")

st.markdown("分析週期：1小時｜追蹤幣種：BTC / ETH / SOL")
st.markdown("---")

# 顯示價格
for symbol in SUPPORTED_SYMBOLS:
    price = get_price(symbol)
    if isinstance(price, float):
        st.success(f"✅ {SYMBOL_NAME_MAP[symbol]} 現價：${price:,.2f} USD")
    else:
        st.error(f"❌ 無法獲取 {SYMBOL_NAME_MAP[symbol]} 價格｜錯誤訊息：{price}")

# 顯示更新時間
st.markdown("---")
st.caption(f"更新時間：{get_hk_time()}")
