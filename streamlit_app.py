import streamlit as st
import yfinance as yf
import pandas as pd
import ta
import time

st.set_page_config(page_title="加密货币分析", layout="wide")
st.title("💰 加密货币多周期合约分析")

# 自动刷新每15分钟
if int(time.time()) % 900 < 5:
    st.rerun()

# 币种和周期
symbols = {
    "BTC-USD": "比特币",
    "ETH-USD": "以太坊",
    "SOL-USD": "Solana"
}
intervals = {
    "15m": ("15分钟", "1d"),
    "1h": ("1小时", "2d"),
    "4h": ("4小时", "7d"),
    "1d": ("24小时", "30d")
}

# 转换成一维Series的安全函数
def safe_series(data, index, name):
    return pd.Series(data.flatten() if hasattr(data, 'flatten') else data, index=index, name=name)

# 计算指标
def calculate_indicators(df):
    close = df["Close"]

    df['SMA_12'] = safe_series(
        ta.trend.SMAIndicator(close=close, window=12).sma_indicator().to_numpy(),
        index=df.index,
        name="SMA_12"
    )
    df['EMA_12'] = safe_series(
        ta.trend.EMAIndicator(close=close, window=12).ema_indicator().to_numpy(),
        index=df.index,
        name="EMA_12"
    )
    df['RSI'] = safe_series(
        ta.momentum.RSIIndicator(close=close, window=14).rsi().to_numpy(),
        index=df.index,
        name="RSI"
    )

    macd = ta.trend.MACD(close=close)
    df['MACD'] = safe_series(macd.macd().to_numpy(), index=df.index, name="MACD")
    df['MACD_signal'] = safe_series(macd.macd_signal().to_numpy(), index=df.index, name="MACD_signal")

    bb = ta.volatility.BollingerBands(close=close, window=20, window_dev=2)
    df['BB_upper'] = safe_series(bb.bollinger_hband().to_numpy(), index=df.index, name="BB_upper")
    df['BB_lower'] = safe_series(bb.bollinger_lband().to_numpy(), index=df.index, name="BB_lower")

    return df

# 生成建议
def generate_suggestion(df):
    latest = df.iloc[-1]
    suggestions = []

    if latest['RSI'] < 30:
        suggestions.append("RSI 显示超卖")
    elif latest['RSI'] > 70:
        suggestions.append("RSI 显示超买")

    if latest['Close'] > latest['EMA_12']:
        suggestions.append("价格高于EMA，趋势向上")
    else:
        suggestions.append("价格低于EMA，趋势向下")

    if latest['MACD'] > latest['MACD_signal']:
        suggestions.append("MACD 显示买入信号")
    else:
        suggestions.append("MACD 显示卖出信号")

    return "，".join(suggestions)

# 显示分析结果
def display_analysis(symbol, name, interval, period):
    try:
        df = yf.download(symbol, interval=interval, period=period)
        if df.empty or 'Close' not in df:
            st
