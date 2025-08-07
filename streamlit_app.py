import streamlit as st
import yfinance as yf
import pandas as pd
import ta
import time
from datetime import datetime

st.set_page_config(page_title="加密货币分析", layout="wide")
st.title("💰 加密货币多周期合约分析")

# 设置自动刷新（每15分钟 = 900秒）
if int(time.time()) % 900 == 0:
    st.experimental_rerun()

# 币种与周期设置
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

# 计算技术指标函数
def calculate_indicators(df):
    close = df['Close']

    sma = ta.trend.SMAIndicator(close=close, window=12).sma_indicator()
    df['SMA_12'] = sma.squeeze() if hasattr(sma, 'squeeze') else sma

    ema = ta.trend.EMAIndicator(close=close, window=12).ema_indicator()
    df['EMA_12'] = ema.squeeze() if hasattr(ema, 'squeeze') else ema

    rsi = ta.momentum.RSIIndicator(close=close, window=14).rsi()
    df['RSI'] = rsi.squeeze() if hasattr(rsi, 'squeeze') else rsi

    macd_indicator = ta.trend.MACD(close=close)
    macd = macd_indicator.macd()
    macd_signal = macd_indicator.macd_signal()
    df['MACD'] = macd.squeeze() if hasattr(macd, 'squeeze') else macd
    df['MACD_signal'] = macd_signal.squeeze() if hasattr(macd_signal, 'squeeze') else macd_signal

    bb = ta.volatility.BollingerBands(close=close, window=20, window_dev=2)
    bb_upper = bb.bollinger_hband()
    bb_lower = bb.bollinger_lband()
    df['BB_upper'] = bb_upper.squeeze() if hasattr(bb_upper, 'squeeze') else bb_upper
    df['BB_lower'] = bb_lower.squeeze() if hasattr(bb_lower, 'squeeze') else bb_lower

    return df

# 分析建议函数
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

# 显示分析函数
def display_analysis(symbol, name, interval, period):
    try:
        df = yf.download(symbol, interval=interval, period=period)
        if df.empty:
            st.error(f"❌ 无法获取 {name} 的 {interval} 数据")
            return

        df = calculate_indicators(df)
        latest_price = df['Close'].iloc[-1]
        suggestion = generate_suggestion(df)

        st.subheader(f"{name} - {intervals[interval][0]} 周期")
        st.metric(label="最新价格", value=f"${latest_price:,.2f}")
        st.write(f"📊 分析建议：{suggestion}")
        st.line_chart(df[['Close', 'SMA_12', 'EMA_12']].dropna())

    except Exception as e:
        st.error(f"❌ 数据获取失败：{e}")

# 主体逻辑 - 每个币种遍历周期
for symbol, name in symbols.items():
    st.markdown(f"## 💰 {name} 分析結果")
    for interval, (label, period) in intervals.items():
        display_analysis(symbol, name, interval, period)
