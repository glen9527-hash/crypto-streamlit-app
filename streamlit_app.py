import streamlit as st
import pandas as pd
import yfinance as yf
import ta
from datetime import datetime, timedelta

st.set_page_config(page_title="加密货币分析", layout="wide")

# 获取数据
def get_crypto_data(symbol, interval, period):
    try:
        df = yf.download(tickers=symbol, interval=interval, period=period)
        if df.empty:
            raise ValueError("未获取到数据")
        df = df.reset_index()
        df['close'] = df['Close'].squeeze()  # 转成一维
        return df
    except Exception as e:
        st.error(f"❌ 数据获取失败: {e}")
        return None

# 计算指标
def calculate_indicators(df):
    try:
        close = df['close']

        df['SMA_20'] = ta.trend.SMAIndicator(close=close, window=20).sma_indicator()
        df['EMA_20'] = ta.trend.EMAIndicator(close=close, window=20).ema_indicator()
        df['RSI_14'] = ta.momentum.RSIIndicator(close=close, window=14).rsi()

        macd = ta.trend.MACD(close)
        df['MACD'] = macd.macd()
        df['MACD_signal'] = macd.macd_signal()

        bb = ta.volatility.BollingerBands(close)
        df['BB_up'] = bb.bollinger_hband()
        df['BB_low'] = bb.bollinger_lband()

        return df
    except Exception as e:
        st.error(f"❌ 指标计算失败: {e}")
        return None

# 综合分析
def analyze(df):
    try:
        last = df.iloc[-1]  # 取最后一行的指标值

        score = 0
        if last['SMA_20'] > last['EMA_20']:
            score += 1
        if last['RSI_14'] < 30:
            score += 1
        if last['MACD'] > last['MACD_signal']:
            score += 1
        if last['close'] < last['BB_low']:
            score += 1

        if score >= 3:
            return "建议买入", score / 4
        elif score <= 1:
            return "建议卖出", (4 - score) / 4
        else:
            return "观望", 0.5
    except Exception as e:
        st.error(f"❌ 分析失败: {e}")
        return "无法分析", 0

# 显示结果
def display_analysis(symbol, name, interval, period):
    df = get_crypto_data(symbol, interval, period)
    if df is None:
        return

    df = calculate_indicators(df)
    if df is None:
        return

    advice, prob = analyze(df)

    st.subheader(f"{name} ({symbol}) - 最新价格: {df['close'].iloc[-1]:.2f} USD")
    st.write(f"📊 建议: **{advice}** | 概率: **{prob*100:.1f}%**")
    st.line_chart(df[['close', 'SMA_20', 'EMA_20']])

# 自动刷新
st_autorefresh = st.experimental_rerun if 'rerun' in dir(st) else None
if st_autorefresh:
    st_autorefresh(interval=15 * 60 * 1000, key="refresh")

st.title("📈 加密货币多周期分析")

period_map = {
    "15m": ("15m", "1d"),
    "1h": ("1h", "7d"),
    "4h": ("4h", "1mo"),
    "1d": ("1d", "3mo")
}

for label, (interval, period) in period_map.items():
    st.markdown(f"### ⏱ 周期: {label}")
    col1, col2, col3 = st.columns(3)
    with col1:
        display_analysis("BTC-USD", "比特币", interval, period)
    with col2:
        display_analysis("ETH-USD", "以太坊", interval, period)
    with col3:
        display_analysis("SOL-USD", "Solana", interval, period)
