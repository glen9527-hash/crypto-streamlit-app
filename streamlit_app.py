import streamlit as st
import pandas as pd
import yfinance as yf
import ta
import datetime

# 页面设置
st.set_page_config(page_title="Crypto 分析基础版", layout="wide")
st.title("🔍 加密货币合约分析基础版")
st.write("分析周期：每小时｜历史范围：过去 24 小时")

# 设定分析币种与映射
symbol_map = {
    "BTC": "BTC-USD",
    "ETH": "ETH-USD",
    "SOL": "SOL-USD"
}

selected_symbols = ["BTC", "ETH", "SOL"]

# 指标计算函数
def calculate_indicators(df):
    if df.empty or len(df) < 26:
        return df, "历史数据不足，无法计算技术指标。"

    df['SMA_12'] = ta.trend.SMAIndicator(close=df['Close'], window=12).sma_indicator()
    df['EMA_12'] = ta.trend.EMAIndicator(close=df['Close'], window=12).ema_indicator()
    df['RSI'] = ta.momentum.RSIIndicator(close=df['Close'], window=14).rsi()
    macd = ta.trend.MACD(close=df['Close'])
    df['MACD'] = macd.macd_diff()
    bb = ta.volatility.BollingerBands(close=df['Close'])
    df['BB_bbm'] = bb.bollinger_mavg()

    return df.dropna(), None

# 生成建议概率
def generate_trade_signal(df):
    last = df.iloc[-1]
    score = 0
    if last['Close'] > last['SMA_12']: score += 1
    if last['Close'] > last['EMA_12']: score += 1
    if last['RSI'] < 30: score += 1
    if last['MACD'] > 0: score += 1
    if last['Close'] < last['BB_bbm']: score += 1
    buy_prob = round(score / 5 * 100, 2)
    sell_prob = round(100 - buy_prob, 2)
    return buy_prob, sell_prob

# 获取历史数据
@st.cache_data(ttl=3600)
def get_data(symbol):
    try:
        end = datetime.datetime.now()
        start = end - datetime.timedelta(hours=24)
        df = yf.download(symbol_map[symbol], start=start, end=end, interval='1h')
        df = df[['Open', 'High', 'Low', 'Close', 'Volume']]
        df.reset_index(inplace=True)
        return df, None
    except Exception as e:
        return pd.DataFrame(), str(e)

# 主分析循环
for sym in selected_symbols:
    st.subheader(f"{sym} 分析")
    df, err = get_data(sym)
    if err or df.empty:
        st.error(f"{sym} 数据无法获取｜错误：{err}")
        continue

    df, indicator_err = calculate_indicators(df)
    if indicator_err:
        st.warning(indicator_err)
        continue

    buy_prob, sell_prob = generate_trade_signal(df)

    st.write(f"📈 买入建议概率：`{buy_prob}%` ｜ 📉 卖出建议概率：`{sell_prob}%`")

    st.line_chart(df.set_index("Datetime")[["Close"]])
