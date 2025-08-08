# streamlit_app.py
import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import time
from datetime import datetime, timedelta
import pytz

# ========== 页面配置 ==========
st.set_page_config(page_title="加密货币多周期分析（基础版）", layout="wide")
st.title("📈 加密货币多周期分析（BTC / ETH / SOL）")
st.caption("每 15 分钟更新一次；周期：15m / 1h / 4h / 24h；输出多指标综合概率（中文）")

# ========== 自动刷新控制（每15分钟刷新一次）==========
REFRESH_SECONDS = 15 * 60
now_ts = time.time()
last = st.session_state.get("last_auto_refresh", 0)
if now_ts - last > REFRESH_SECONDS:
    # 更新标记并重跑一次以触发数据重新获取
    st.session_state["last_auto_refresh"] = now_ts
    st.experimental_rerun()

# ========== 工具函数 ==========
def hk_time_str():
    return datetime.now(pytz.timezone("Asia/Hong_Kong")).strftime("%Y-%m-%d %H:%M:%S")

def fetch_yf(symbol: str, interval: str, period: str) -> pd.DataFrame:
    """
    用 yfinance 获取指定 ticker、interval、period 的历史数据。
    为 4h/24h 做必要的重采样（yfinance 不直接支持 4h）。
    返回 DataFrame，索引为 DatetimeIndex，包含 'close' 列。
    """
    # 做一次容错请求
    try:
        df = yf.download(tickers=symbol, interval=interval, period=period, progress=False, threads=False)
    except Exception as e:
        raise RuntimeError(f"yfinance 下载失败：{e}")

    if df is None or df.empty:
        return pd.DataFrame()  # 空 DF 表示失败

    # 确保有 Close 列
    if 'Close' not in df.columns:
        return pd.DataFrame()

    df = df[['Close']].copy()
    # 规范列名与索引
    df = df.rename(columns={'Close': 'close'})
    if not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index)
    # remove tz
    df.index = df.index.tz_convert(None) if hasattr(df.index, 'tz') and df.index.tz is not None else df.index

    return df

def resample_df(df: pd.DataFrame, rule: str) -> pd.DataFrame:
    """将数据重采样为给定频率（rule，例如 '4H' 或 '1D'），返回包含 close 列的 DataFrame"""
    # 若 df 为空
    if df is None or df.empty:
        return pd.DataFrame()
    # 重采样取 last close
    res = df.resample(rule).agg({'close': 'last'}).dropna()
    return res

# 指标实现（全部使用 pandas/numpy，兼容性稳定）
def compute_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    输入 df 必须包含 DatetimeIndex 与 'close' 列
    返回同 index 的 df，包含以下新列：SMA, EMA, RSI, MACD, MACD_signal, BB_mid, BB_up, BB_low
    """
    df = df.copy()
    close = df['close'].astype(float)

    # SMA/EMA（以 20 作为中短期示例）
    df['SMA_20'] = close.rolling(window=20, min_periods=1).mean()
    df['EMA_20'] = close.ewm(span=20, adjust=False).mean()

    # RSI (14)
    delta = close.diff()
    up = delta.clip(lower=0)
    down = -1 * delta.clip(upper=0)
    # Wilder's smoothing
    roll_up = up.rolling(window=14, min_periods=14).mean()
    roll_down = down.rolling(window=14, min_periods=14).mean()
    rs = roll_up / roll_down.replace(0, np.nan)
    df['RSI_14'] = 100 - (100 / (1 + rs))
    # fill initial RSI with NaN (we'll dropna later)

    # MACD (12,26,9)
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    df['MACD'] = ema12 - ema26
    df['MACD_signal'] = df['MACD'].ewm(span=9, adjust=False).mean()

    # Bollinger Bands (20, 2)
    df['BB_mid'] = close.rolling(window=20, min_periods=1).mean()
    df['BB_std'] = close.rolling(window=20, min_periods=1).std()
    df['BB_up'] = df['BB_mid'] + 2 * df['BB_std']
    df['BB_low'] = df['BB_mid'] - 2 * df['BB_std']

    # 清理：仍保留所有列，但在评估前会 dropna
    return df

def score_from_indicators(df: pd.DataFrame) -> float:
    """
    基于单个周期的指标生成 0-100 的买入概率（简单加权规则）
    规则（示例，可后续调整或学习）：
      - SMA/EMA 趋势：+1 若 close > SMA20；+1 若 close > EMA20
      - RSI: +1 若 RSI < 30 (超卖)， -1 若 RSI > 70 (超买)
      - MACD: +1 若 MACD > signal else -1
      - BB: +1 若 close < BB_low (强力支撑/反弹)， -1 若 close > BB_up
    把总分映射到 0-100（更高表示更偏买入）
    """
    # 先 dropna（保证各指标对齐）
    df2 = df.dropna(subset=['SMA_20','EMA_20','RSI_14','MACD','MACD_signal','BB_up','BB_low','close'])
    if df2.empty:
        return None  # 数据不足

    last = df2['close'].iloc[-1]
    rsi = df2['RSI_14'].iloc[-1]
    sma = df2['SMA_20'].iloc[-1]
    ema = df2['EMA_20'].iloc[-1]
    macd = df2['MACD'].iloc[-1]
    macd_sig = df2['MACD_signal'].iloc[-1]
    bb_up = df2['BB_up'].iloc[-1]
    bb_low = df2['BB_low'].iloc[-1]

    score = 0
    # SMA/EMA
    score += 1 if last > sma else -1
    score += 1 if last > ema else -1
    # RSI
    if rsi < 30:
        score += 1
    elif rsi > 70:
        score -= 1
    # MACD
    score += 1 if macd > macd_sig else -1
    # Bollinger
    if last < bb_low:
        score += 1
    elif last > bb_up:
        score -= 1

    # 5 条规则，每条评分 -1 或 +1 -> 最小 -5 最大 +5
    # 将 score 映射到 0-100： prob = (score + 5) / 10 * 100
    prob = (score + 5) / 10 * 100
    # clip
    prob = max(0.0, min(100.0, prob))
    return round(prob, 2)

# ========== 主逻辑：多周期、多币种分析并显示 ==========
# 固定币种：BTC / ETH / SOL
tickers = {
    "BTC": "BTC-USD",
    "ETH": "ETH-USD",
    "SOL": "SOL-USD"
}

# 周期设定：对于 4h/1d 使用 1h 或 15m 的更细粒度拉取后做 resample
# periods 为 yfinance 的 period 参数（保证足够历史数据）
interval_settings = {
    "15m": {"yf_interval": "15m", "yf_period": "3d", "resample": None, "label": "15 分钟"},
    "1h":  {"yf_interval": "1h",  "yf_period": "7d", "resample": None, "label": "1 小时"},
    "4h":  {"yf_interval": "1h",  "yf_period": "30d", "resample": "4H", "label": "4 小时"},
    "24h": {"yf_interval": "1d",  "yf_period": "365d", "resample": None, "label": "24 小时"}
}

col1, col2 = st.columns([3,1])
with col2:
    st.markdown("**状态**")
    st.write(f"香港时间：{hk_time_str()}")
    st.write(f"上次自动刷新：{datetime.fromtimestamp(st.session_state.get('last_auto_refresh', now_ts)).strftime('%Y-%m-%d %H:%M:%S')}")
    if st.button("手动刷新"):
        st.session_state["last_auto_refresh"] = time.time()
        st.experimental_rerun()

# 展示每个币的分析
for name, ticker in tickers.items():
    st.markdown(f"---\n### 🔹 {name}")
    cols = st.columns(len(interval_settings))
    for i, (key, cfg) in enumerate(interval_settings.items()):
        with cols[i]:
            label = cfg['label']
            st.subheader(label)
            try:
                # 先抓较细颗粒度数据
                raw = fetch_yf(ticker, cfg['yf_interval'], cfg['yf_period'])
                if raw.empty:
                    st.warning("数据获取失败或为空")
                    continue

                # 若需重采样（4H）
                if cfg['resample']:
                    # raw 的索引为 DatetimeIndex; 确保 index 类型并重采样
                    raw.index = pd.to_datetime(raw.index)
                    df_res = resample_df(raw, cfg['resample'])
                else:
                    df_res = raw.copy()

                # 检查数据量
                if df_res.shape[0] < 20:
                    st.warning("数据点过少，无法计算指标")
                    continue

                # 计算指标（会返回带指标列的 DataFrame）
                df_ind = compute_indicators(df_res)

                # 获取最新价 & 计算概率
                latest_price = df_ind['close'].iloc[-1]
                prob = score_from_indicators(df_ind)
                if prob is None:
                    st.info("数据不足以计算概率")
                else:
                    st.metric(label="最新价 (USD)", value=f"${latest_price:,.2f}")
                    st.metric(label="买入综合概率", value=f"{prob:.2f}%")

                # 小图：价格 + SMA/EMA
                plot_df = df_ind[['close','SMA_20','EMA_20']].dropna()
                if not plot_df.empty:
                    st.line_chart(plot_df.tail(200))
                else:
                    st.info("图表数据不足")

            except Exception as e:
                st.error(f"处理失败：{e}")

st.caption("说明：本工具为教学/测试用途，建议仅用于参考。若要接入实盘交易，请做好风控与权限设置。")
