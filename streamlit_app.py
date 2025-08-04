import streamlit as st
import pandas as pd
import yfinance as yf
import datetime
import ta

# 页面标题
st.set_page_config(page_title="加密貨幣分析應用（基礎版）", layout="wide")
st.title("📊 加密貨幣合約分析工具（基礎版）")

# 映射幣種到 yfinance ticker
symbol_map = {
    'BTC': 'BTC-USD',
    'ETH': 'ETH-USD',
    'SOL': 'SOL-USD'
}

# 用於抓取歷史數據
@st.cache_data(ttl=3600)
def get_data(symbol):
    try:
        end = datetime.datetime.now()
        start = end - datetime.timedelta(hours=48)  # ✅ 改為 48 小時
        df = yf.download(symbol_map[symbol], start=start, end=end, interval='1h')
        df = df[['Open', 'High', 'Low', 'Close', 'Volume']]
        df.reset_index(inplace=True)
        return df, None
    except Exception as e:
        return pd.DataFrame(), str(e)

# 技術指標計算
def calculate_indicators(df):
    df['SMA_12'] = ta.trend.sma_indicator(df['Close'], window=12)
    df['EMA_12'] = ta.trend.ema_indicator(df['Close'], window=12)
    df['RSI'] = ta.momentum.rsi(df['Close'], window=14)
    macd = ta.trend.MACD(df['Close'])
    df['MACD'] = macd.macd()
    df['MACD_Signal'] = macd.macd_signal()
    boll = ta.volatility.BollingerBands(df['Close'])
    df['BB_High'] = boll.bollinger_hband()
    df['BB_Low'] = boll.bollinger_lband()
    return df

# 買賣建議生成（簡化模型）
def generate_recommendation(df):
    latest = df.iloc[-1]
    score = 0

    if latest['Close'] > latest['SMA_12']:
        score += 1
    if latest['Close'] > latest['EMA_12']:
        score += 1
    if latest['RSI'] < 30:
        score += 1
    elif latest['RSI'] > 70:
        score -= 1
    if latest['MACD'] > latest['MACD_Signal']:
        score += 1
    if latest['Close'] < latest['BB_Low']:
        score += 1
    elif latest['Close'] > latest['BB_High']:
        score -= 1

    probability = round((score + 3) / 6 * 100, 2)  # 轉換為 0–100 的機率
    return probability

# 主界面
for symbol in ['BTC', 'ETH', 'SOL']:
    st.header(f"💰 {symbol} 分析結果")

    df, error = get_data(symbol)
    if error:
        st.error(f"{symbol} 數據無法顯示｜歷史數據獲取錯誤：{error}")
        continue

    if df.empty or len(df) < 26:
        st.warning(f"{symbol} 的數據不足以進行技術分析（需要至少 26 條紀錄）")
        continue

    df = calculate_indicators(df)

    # 顯示圖表
    st.line_chart(df.set_index('Datetime')[['Close', 'SMA_12', 'EMA_12']])

    # 顯示建議
    probability = generate_recommendation(df)
    st.subheader(f"📈 建議買入機率：{probability} %")
    st.markdown("---")
