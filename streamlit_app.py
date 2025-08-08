import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import ta
from datetime import datetime, timedelta

st.set_page_config(page_title="加密货币分析", layout="wide")

# 计算技术指标
def calculate_indicators(df):
    try:
        close = df['Close']
        high = df['High']
        low = df['Low']

        # 确保数据足够，否则填充 NaN
        def safe_indicator(func, *args, **kwargs):
            try:
                result = func(*args, **kwargs)
                return result
            except Exception:
                return pd.Series([np.nan] * len(df), index=df.index)

        df['SMA_20'] = safe_indicator(ta.trend.SMAIndicator, close, 20).sma_indicator()
        df['EMA_20'] = safe_indicator(ta.trend.EMAIndicator, close, 20).ema_indicator()
        df['RSI_14'] = safe_indicator(ta.momentum.RSIIndicator, close, 14).rsi()
        macd = safe_indicator(ta.trend.MACD, close)
        if isinstance(macd, ta.trend.MACD):
            df['MACD'] = macd.macd()
            df['MACD_signal'] = macd.macd_signal()
        else:
            df['MACD'] = np.nan
            df['MACD_signal'] = np.nan
        bb = safe_indicator(ta.volatility.BollingerBands, close, 20, 2)
        if isinstance(bb, ta.volatility.BollingerBands):
            df['BB_up'] = bb.bollinger_hband()
            df['BB_low'] = bb.bollinger_lband()
        else:
            df['BB_up'] = np.nan
            df['BB_low'] = np.nan

        return df
    except Exception as e:
        st.error(f"❌ 指标计算失败: {e}")
        return df

# 获取历史数据
def get_crypto_data(symbol, interval, period):
    try:
        df = yf.download(symbol, interval=interval, period=period)
        if df.empty:
            raise ValueError("返回的数据为空")
        df = df.reset_index()
        return df
    except Exception as e:
        st.error(f"❌ 数据获取失败: {e}")
        return pd.DataFrame()

# 分析并显示结果
def display_analysis(symbol, name, interval, period):
    st.subheader(f"{name} ({symbol}) - {interval} 分析")
    df = get_crypto_data(symbol, interval, period)
    if df.empty:
        st.warning("⚠ 无法获取数据")
        return

    df = calculate_indicators(df)

    # 显示图表
    st.line_chart(df.set_index('Datetime')['Close'])

    # 买卖建议（简单示例）
    try:
        latest = df.iloc[-1]
        score = 0
        total = 0
        if not pd.isna(latest['Close']) and not pd.isna(latest['SMA_20']):
            score += int(latest['Close'] > latest['SMA_20'])
            total += 1
        if not pd.isna(latest['RSI_14']):
            score += int(latest['RSI_14'] > 50)
            total += 1
        if not pd.isna(latest['MACD']) and not pd.isna(latest['MACD_signal']):
            score += int(latest['MACD'] > latest['MACD_signal'])
            total += 1

        if total > 0:
            prob = round(score / total * 100, 2)
            st.write(f"📊 上涨概率: {prob}%")
        else:
            st.write("📊 无法计算概率（数据不足）")
    except Exception as e:
        st.error(f"❌ 分析失败: {e}")

# 页面布局
st.title("📈 加密货币多周期分析（实时数据）")

cryptos = {
    "BTC-USD": "比特币",
    "ETH-USD": "以太坊",
    "SOL-USD": "Solana"
}

intervals = [
    ("15m", "1d"),
    ("1h", "7d"),
    ("4h", "1mo"),
    ("1d", "3mo")
]

for symbol, name in cryptos.items():
    for interval, period in intervals:
        display_analysis(symbol, name, interval, period)
