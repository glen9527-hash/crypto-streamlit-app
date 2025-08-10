# streamlit_app.py
import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import pytz
from datetime import datetime, timedelta

# ---------- 页面配置 ----------
st.set_page_config(page_title="加密貨幣多周期分析（yfinance）", layout="wide")
st.title("📈 加密貨幣多周期分析（BTC / ETH / SOL）")
st.caption("数据源：yfinance ｜ 自动刷新：每15分钟 ｜ 周期：15m / 1h / 4h / 24h")

# ---------- 自动刷新（每15分钟） ----------
# interval 单位毫秒
st.experimental_autorefresh(interval=15 * 60 * 1000, key="autorefresh")

# ---------- 辅助函数 ----------
def now_hk():
    return datetime.now(pytz.timezone("Asia/Hong_Kong")).strftime("%Y-%m-%d %H:%M:%S")

def safe_fetch(ticker: str, interval: str, period: str) -> pd.DataFrame:
    """
    使用 yfinance 获取数据并返回 DataFrame，包含 DatetimeIndex 与 'close' 列。
    interval: yfinance 支持的 interval，如 '15m','1h','1d'
    period: yfinance period，如 '3d','7d','30d','1y'
    """
    try:
        df = yf.download(tickers=ticker, interval=interval, period=period, progress=False, threads=False)
    except Exception as e:
        raise RuntimeError(f"yfinance 下载失败：{e}")

    if df is None or df.empty:
        return pd.DataFrame()

    # 保证有 Close 列并转换成统一命名
    if 'Close' not in df.columns:
        return pd.DataFrame()

    df = df[['Close']].rename(columns={'Close': 'close'})
    df.index = pd.to_datetime(df.index)
    # remove tz info to avoid alignment issues
    if df.index.tz is not None:
        df.index = df.index.tz_convert(None)

    return df

def resample_if_needed(df: pd.DataFrame, rule: str) -> pd.DataFrame:
    """
    对 df（以 DatetimeIndex 且含 close 列）做重采样，rule 例如 '4H' 或 '1D'
    """
    if df is None or df.empty:
        return pd.DataFrame()
    res = df.resample(rule).agg({'close': 'last'}).dropna()
    return res

# 指标实现（pandas / numpy）
def compute_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    输入 df 必须包含 DatetimeIndex 与 'close' 列
    返回 df（带指标列）
    """
    df = df.copy()
    close = df['close'].astype(float)

    # SMA / EMA
    df['SMA_20'] = close.rolling(window=20, min_periods=1).mean()
    df['EMA_20'] = close.ewm(span=20, adjust=False).mean()

    # RSI(14) - 使用 Wilder 平滑的近似（简单实现）
    delta = close.diff()
    up = delta.clip(lower=0)
    down = -1 * delta.clip(upper=0)
    roll_up = up.rolling(window=14, min_periods=14).mean()
    roll_down = down.rolling(window=14, min_periods=14).mean()
    rs = roll_up / roll_down.replace(0, np.nan)
    df['RSI_14'] = 100 - (100 / (1 + rs))

    # MACD (12,26) and signal(9)
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    df['MACD'] = ema12 - ema26
    df['MACD_signal'] = df['MACD'].ewm(span=9, adjust=False).mean()

    # Bollinger Bands (20, 2)
    df['BB_mid'] = close.rolling(window=20, min_periods=1).mean()
    df['BB_std'] = close.rolling(window=20, min_periods=1).std()
    df['BB_up'] = df['BB_mid'] + 2 * df['BB_std']
    df['BB_low'] = df['BB_mid'] - 2 * df['BB_std']

    return df

def score_from_df(df: pd.DataFrame) -> (float, str):
    """
    计算单周期的综合买入概率（0-100）和一句中文建议
    规则示例（可后续迭代/加权/学习）：
      - close > SMA20：+1
      - close > EMA20：+1
      - RSI <30：+1 ； RSI>70：-1
      - MACD > signal：+1 else -1
      - close < BB_low：+1 ; close > BB_up：-1
    得到 score ∈ [-5, +5]，映射到 [0,100]
    """
    # 先对关键列做 dropna 保证 index 对齐
    keys = ['close','SMA_20','EMA_20','RSI_14','MACD','MACD_signal','BB_up','BB_low']
    df2 = df.dropna(subset=keys)
    if df2.empty:
        return None, "数据不足，无法计算"

    last = df2.iloc[-1]
    score = 0
    # SMA / EMA
    score += 1 if last['close'] > last['SMA_20'] else -1
    score += 1 if last['close'] > last['EMA_20'] else -1
    # RSI
    if last['RSI_14'] < 30:
        score += 1
    elif last['RSI_14'] > 70:
        score -= 1
    # MACD
    score += 1 if last['MACD'] > last['MACD_signal'] else -1
    # BB
    if last['close'] < last['BB_low']:
        score += 1
    elif last['close'] > last['BB_up']:
        score -= 1

    prob = (score + 5) / 10 * 100
    prob = max(0.0, min(100.0, round(prob, 2)))

    # 简单中文建议
    if prob >= 70:
        advice = "偏向买入（高概率）"
    elif prob >= 55:
        advice = "倾向买入"
    elif prob >= 45:
        advice = "观望"
    elif prob >= 30:
        advice = "倾向卖出"
    else:
        advice = "偏向卖出（高概率）"

    return prob, advice

# ---------- 主展示逻辑 ----------
st.sidebar.header("📌 配置")
st.sidebar.markdown("自动每 15 分钟刷新。")

st.write(f"**香港时间**：{now_hk()}")

tickers = {
    "BTC": "BTC-USD",
    "ETH": "ETH-USD",
    "SOL": "SOL-USD"
}

# interval settings: use yf_interval and yf_period; if need resample use 'resample' key
interval_settings = {
    "15m": {"yf_interval": "15m", "yf_period": "7d", "resample": None, "label": "15 分钟"},
    "1h":  {"yf_interval": "60m", "yf_period": "30d", "resample": None, "label": "1 小时"},
    "4h":  {"yf_interval": "60m", "yf_period": "90d", "resample": "4H", "label": "4 小时"},  # 从 1h 重采样到 4H
    "24h": {"yf_interval": "1d",  "yf_period": "730d", "resample": None, "label": "24 小时"}
}

# 页面展示：每个币种横排显示各周期（列宽受限，自动换行）
for name, ticker in tickers.items():
    st.markdown("---")
    st.header(f"🔹 {name}  ({ticker})")
    cols = st.columns(len(interval_settings))
    for i, (period_key, cfg) in enumerate(interval_settings.items()):
        with cols[i]:
            st.subheader(cfg['label'])
            try:
                raw = safe_fetch(ticker, cfg['yf_interval'], cfg['yf_period'])
                if raw.empty:
                    st.warning("数据获取失败或为空")
                    continue

                # 如果需要重采样（例如 4H），先确保索引为 DatetimeIndex
                if cfg['resample']:
                    raw.index = pd.to_datetime(raw.index)
                    df_res = resample_if_needed(raw, cfg['resample'])
                else:
                    df_res = raw.copy()

                if df_res.empty or df_res.shape[0] < 10:
                    st.info("数据点过少，无法计算指标")
                    continue

                # 计算指标（使用 pandas）
                df_ind = compute_indicators(df_res)

                # 计算概率与建议
                prob, advice = score_from_df(df_ind)
                if prob is None:
                    st.info("数据不足，无法给出概率")
                else:
                    # 最新价格（取 df_res 最后一行）
                    latest_price = df_ind['close'].iloc[-1]
                    st.metric(label="最新价格 (USD)", value=f"${latest_price:,.2f}")
                    st.metric(label="买入综合概率", value=f"{prob:.2f}%")
                    st.write(f"建议：**{advice}**")

                # 小图：价格 + SMA/EMA
                plot_df = df_ind[['close','SMA_20','EMA_20']].dropna()
                if not plot_df.empty:
                    st.line_chart(plot_df.tail(200))
                else:
                    st.info("图表数据不足以绘制均线")

            except Exception as e:
                st.error(f"处理失败：{e}")

st.caption("提示：本工具为测试/参考用，不构成投资建议。需要实盘自动交易请严格做好权限和风控。")
