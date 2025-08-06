import streamlit as st
import pandas as pd
import yfinance as yf
import matplotlib.pyplot as plt
import ta
from datetime import datetime, timedelta

# 页面配置
st.set_page_config(page_title="Crypto 分析应用", layout="wide")

st.title("💰 加密貨幣合約分析應用（基礎版）")

# 选择币种
coins = {
    "BTC": "BTC-USD",
    "ETH": "ETH-USD",
    "SOL": "SOL-USD"
}
selected_coin = st.selectbox("選擇幣種", list(coins.keys()))

symbol = coins[selected_coin]

# 获取历史数据（过去24小时，每小时数据）
def get_data(symbol):
    try:
        end = datetime.utcnow()
        start = end - timedelta(hours=24)
        df = yf.download(symbol, start=start, end=end, interval="1h", progress=False)

        if df.empty or 'Close' not in df.columns:
            st.error(f"{selected_coin} 數據獲取錯誤｜無法獲取歷史價格資料。")
            return None

        df = df[['Close']].copy()
        df.reset_index(inplace=True)
        df.columns = ['Time', 'Close']
        return df
    except Exception as e:
        st.error(f"{selected_coin} 數據獲取錯誤｜{e}")
        return None

# 计算技术指标
def calculate_indicators(df):
    try:
        df['SMA_12'] = ta.trend.sma_indicator(close=df['Close'], window=12)
        df['EMA_12'] = ta.trend.ema_indicator(close=df['Close'], window=12)
        df['RSI'] = ta.momentum.rsi(close=df['Close'], window=14)
        macd = ta.trend.MACD(close=df['Close'])
        df['MACD'] = macd.macd()
        df['MACD_signal'] = macd.macd_signal()
        bb = ta.volatility.BollingerBands(close=df['Close'], window=20)
        df['BB_upper'] = bb.bollinger_hband()
        df['BB_lower'] = bb.bollinger_lband()
        return df
    except Exception as e:
        st.error(f"{selected_coin} 技術指標計算錯誤｜{e}")
        return df

# 简单买卖建议逻辑
def generate_suggestion(df):
    try:
        latest = df.iloc[-1]
        if pd.isna(latest['RSI']) or pd.isna(latest['SMA_12']) or pd.isna(latest['EMA_12']):
            return "數據不足，無法生成建議。", 0.0

        score = 0
        if latest['RSI'] < 30: score += 1
        if latest['Close'] > latest['SMA_12']: score += 1
        if latest['MACD'] > latest['MACD_signal']: score += 1
        if latest['Close'] < latest['BB_lower']: score += 1

        # 概率建议（简单加权）
        probability = (score / 4.0) * 100
        suggestion = f"建議：{'買入' if probability > 60 else '觀望'}"
        return suggestion, round(probability, 2)
    except Exception as e:
        return f"建議生成失敗：{e}", 0.0

# 主流程
df = get_data(symbol)
if df is not None:
    df = calculate_indicators(df)

    st.subheader(f"📈 {selected_coin} 價格走勢（最近 24 小時）")
    fig, ax = plt.subplots(figsize=(12, 4))
    ax.plot(df['Time'], df['Close'], label='價格')
    ax.set_xlabel('時間')
    ax.set_ylabel('價格（USD）')
    ax.legend()
    st.pyplot(fig)

    st.subheader(f"💰 {selected_coin} 分析結果")
    suggestion, probability = generate_suggestion(df)
    st.write(f"📊 概率：**{probability}%**")
    st.write(suggestion)

    st.subheader("📄 原始數據與技術指標")
    st.dataframe(df.tail(10))
