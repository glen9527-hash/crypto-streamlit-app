import streamlit as st
import pandas as pd
import yfinance as yf
import ta
from datetime import datetime, timedelta

st.set_page_config(page_title="加密货币多周期分析", layout="wide")

# 计算技术指标
def calculate_indicators(df):
    close = df['Close'].squeeze()  # 转成一维
    high = df['High'].squeeze()
    low = df['Low'].squeeze()

    df['SMA_12'] = ta.trend.SMAIndicator(close=close, window=12).sma_indicator()
    df['EMA_12'] = ta.trend.EMAIndicator(close=close, window=12).ema_indicator()
    df['RSI'] = ta.momentum.RSIIndicator(close=close, window=14).rsi()
    macd = ta.trend.MACD(close=close)
    df['MACD'] = macd.macd()
    df['MACD_signal'] = macd.macd_signal()
    bb = ta.volatility.BollingerBands(close=close)
    df['BB_high'] = bb.bollinger_hband()
    df['BB_low'] = bb.bollinger_lband()
    return df

# 综合分析
def analyze(df):
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
    if latest['MACD'] > latest['MACD_signal']:
        score += 1
    if latest['Close'] > latest['BB_high']:
        score -= 1
    elif latest['Close'] < latest['BB_low']:
        score += 1
    prob = (score + 3) / 6 * 100  # 0~100 概率
    return prob, latest['Close']

# 显示分析结果
def display_analysis(symbol, name, interval, period):
    try:
        df = yf.download(symbol, interval=interval, period=period)
        if df.empty:
            st.error(f"❌ 无法获取 {name} 数据")
            return
        df = calculate_indicators(df)
        prob, price = analyze(df)
        st.subheader(f"{name} - {interval} 周期")
        st.write(f"最新价格：{price:.2f} USD")
        st.write(f"上涨概率：{prob:.2f}%")
        st.line_chart(df['Close'])
    except Exception as e:
        st.error(f"❌ 数据获取失败：{e}")

st.title("加密货币多周期技术分析")
st.caption(f"最后刷新时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

cryptos = {
    "BTC-USD": "比特币",
    "ETH-USD": "以太坊",
    "SOL-USD": "Solana"
}

intervals = {
    "15m": "15分钟",
    "1h": "1小时",
    "4h": "4小时",
    "1d": "24小时"
}

for symbol, name in cryptos.items():
    for interval, label in intervals.items():
        display_analysis(symbol, name, interval, "7d")

# 自动刷新
st_autorefresh = st.empty()
