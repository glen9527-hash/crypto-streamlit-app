import streamlit as st
import pandas as pd
import numpy as np
import talib
import yfinance as yf
from datetime import datetime, timedelta
import pytz

# Streamlit 设置
st.set_page_config(page_title="加密货币分析", layout="wide")

# 自动刷新，每15分钟更新一次
st_autorefresh = st.runtime.legacy_caching.hashing.hash_funcs
st.runtime.legacy_caching.clear_cache()

# 币种映射（yfinance代码）
symbol_map = {
    "BTC": "BTC-USD",
    "ETH": "ETH-USD",
    "SOL": "SOL-USD"
}

# 获取香港时间
def get_hk_time():
    tz = pytz.timezone('Asia/Hong_Kong')
    return datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")

# 获取历史数据
def get_data(symbol, period="1d", interval="1h"):
    try:
        data = yf.download(symbol_map[symbol], period=period, interval=interval)
        data.reset_index(inplace=True)
        data.rename(columns={"Close": "close", "Open": "open", "High": "high", "Low": "low", "Volume": "volume"}, inplace=True)
        return data
    except Exception as e:
        st.error(f"{symbol} 数据获取失败: {e}")
        return None

# 技术指标计算
def calculate_indicators(df):
    close = df["close"].values

    df["SMA_20"] = talib.SMA(close, timeperiod=20)
    df["EMA_20"] = talib.EMA(close, timeperiod=20)
    df["RSI_14"] = talib.RSI(close, timeperiod=14)

    macd, macd_signal, macd_hist = talib.MACD(close, fastperiod=12, slowperiod=26, signalperiod=9)
    df["MACD"] = macd
    df["MACD_signal"] = macd_signal

    bb_up, bb_mid, bb_low = talib.BBANDS(close, timeperiod=20, nbdevup=2, nbdevdn=2, matype=0)
    df["BB_up"] = bb_up.ravel()
    df["BB_low"] = bb_low.ravel()

    return df

# 买卖建议
def generate_signal(df):
    latest = df.iloc[-1]
    last_price = latest["close"]

    # 简单信号逻辑
    buy_signal = latest["RSI_14"] < 30 and latest["MACD"] > latest["MACD_signal"]
    sell_signal = latest["RSI_14"] > 70 and latest["MACD"] < latest["MACD_signal"]

    stop_loss = round(last_price * 0.98, 2)
    take_profit = round(last_price * 1.03, 2)

    if buy_signal:
        return f"建议买入 | 当前价格: {last_price:.2f} | 止损: {stop_loss} | 止盈: {take_profit}"
    elif sell_signal:
        return f"建议卖出 | 当前价格: {last_price:.2f} | 止损: {stop_loss} | 止盈: {take_profit}"
    else:
        return f"建议观望 | 当前价格: {last_price:.2f} | 止损: {stop_loss} | 止盈: {take_profit}"

# 页面标题
st.title("📈 加密货币多周期分析")
st.write(f"更新时间（香港）: {get_hk_time()}")

# 币种循环
for symbol in ["BTC", "ETH", "SOL"]:
    st.subheader(f"{symbol} 分析结果")
    col1, col2 = st.columns(2)

    with col1:
        df = get_data(symbol, period="1d", interval="1h")
        if df is not None and not df.empty:
            df = calculate_indicators(df)
            st.dataframe(df.tail(10))

    with col2:
        if df is not None and not df.empty:
            st.write(generate_signal(df))
