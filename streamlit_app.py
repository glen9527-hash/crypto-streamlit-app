import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import datetime
import pytz
import ta

# 设置页面标题
st.set_page_config(page_title="加密货币技术分析", layout="wide")

# 显示标题
st.title("📊 加密货币技术分析基础版")
st.markdown("分析周期：每小时 | 回看时间：24 小时 | 使用数据源：Yahoo Finance")

# 设置香港时区
hk_tz = pytz.timezone('Asia/Hong_Kong')
now = datetime.datetime.now(hk_tz)
st.write(f"香港时间：{now.strftime('%Y-%m-%d %H:%M:%S')}")

# 币种映射（Yahoo Finance）
symbol_map = {
    "BTC": "BTC-USD",
    "ETH": "ETH-USD",
    "SOL": "SOL-USD"
}

def get_data_yfinance(symbol):
    try:
        df = yf.download(
            symbol_map[symbol],
            period="1d",
            interval="1h"
        )
        if df.empty:
            return None, f"{symbol} 數據獲取錯誤：無數據"
        df.dropna(inplace=True)
        df.reset_index(inplace=True)
        return df, None
    except Exception as e:
        return None, f"{symbol} 數據獲取錯誤：{e}"

def calculate_indicators(df):
    # 加入常用技術指標
    df['SMA_12'] = ta.trend.sma_indicator(df['Close'], window=12)
    df['EMA_12'] = ta.trend.ema_indicator(df['Close'], window=12)
    df['RSI_14'] = ta.momentum.rsi(df['Close'], window=14)
    macd = ta.trend.macd(df['Close'])
    df['MACD'] = macd.macd_diff()
    bb = ta.volatility.BollingerBands(df['Close'])
    df['BB_bbm'] = bb.bollinger_mavg()
    df['BB_bbh'] = bb.bollinger_hband()
    df['BB_bbl'] = bb.bollinger_lband()
    return df

def generate_signal(df):
    latest = df.iloc[-1]

    signals = []

    # RSI 超买/超卖
    if latest['RSI_14'] < 30:
        signals.append("buy")
    elif latest['RSI_14'] > 70:
        signals.append("sell")

    # MACD 正负判断
    if latest['MACD'] > 0:
        signals.append("buy")
    elif latest['MACD'] < 0:
        signals.append("sell")

    # 均线判断
    if latest['EMA_12'] > latest['SMA_12']:
        signals.append("buy")
    else:
        signals.append("sell")

    # 布林带判断
    if latest['Close'] < latest['BB_bbl']:
        signals.append("buy")
    elif latest['Close'] > latest['BB_bbh']:
        signals.append("sell")

    # 统计 buy vs sell
    buy_count = signals.count("buy")
    sell_count = signals.count("sell")
    total = buy_count + sell_count
    if total == 0:
        return 0.5  # 中性
    else:
        return round(buy_count / total, 2)

# 主体部分
col1, col2, col3 = st.columns(3)
for i, coin in enumerate(["BTC", "ETH", "SOL"]):
    df, error = get_data_yfinance(coin)
    with [col1, col2, col3][i]:
        st.subheader(coin)
        if error:
            st.error(error)
        else:
            df = calculate_indicators(df)
            prob = generate_signal(df)
            st.write("買入建議概率：", f"{int(prob * 100)}%")
            st.line_chart(df.set_index("Datetime")["Close"])
