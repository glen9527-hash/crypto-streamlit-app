# streamlit_app.py
import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import time
import pytz
from datetime import datetime

# ---------- 配置 ----------
st.set_page_config(page_title="加密貨幣多周期分析（含 TP/SL）", layout="wide")
st.title("📈 加密貨幣多周期分析（BTC / ETH / SOL）")
st.caption("数据源：yfinance ｜ 自动刷新：每15分钟 ｜ 输出包含买/卖/止盈/止损建议（中文）")

# ---------- 自动刷新（兼容性实现） ----------
REFRESH_SECONDS = 15 * 60
if "last_refresh" not in st.session_state:
    st.session_state["last_refresh"] = time.time()
if time.time() - st.session_state["last_refresh"] > REFRESH_SECONDS:
    st.session_state["last_refresh"] = time.time()
    st.experimental_rerun()

# ---------- 工具函数 ----------
def now_hk():
    return datetime.now(pytz.timezone("Asia/Hong_Kong")).strftime("%Y-%m-%d %H:%M:%S")

def safe_fetch(ticker: str, yf_interval: str, yf_period: str) -> pd.DataFrame:
    """从 yfinance 获取数据，返回有 DatetimeIndex 与 'close' 列的 DataFrame"""
    try:
        df = yf.download(tickers=ticker, interval=yf_interval, period=yf_period, progress=False, threads=False)
    except Exception as e:
        raise RuntimeError(f"yfinance 下载失败：{e}")
    if df is None or df.empty or 'Close' not in df.columns:
        return pd.DataFrame()
    df = df[['Close']].rename(columns={'Close': 'close'})
    df.index = pd.to_datetime(df.index)
    # 去时区信息以避免后续对齐问题
    if df.index.tz is not None:
        df.index = df.index.tz_convert(None)
    return df

def resample_to(df: pd.DataFrame, rule: str) -> pd.DataFrame:
    """基于 close 列把 df 重采样到 rule（如 '4H'）并返回"""
    if df is None or df.empty:
        return pd.DataFrame()
    df_res = df.resample(rule).agg({'close':'last'}).dropna()
    return df_res

# ---------- 指标计算（全部用 pandas/numpy，确保返回一维 Series） ----------
def compute_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    输入 df 必须包含 DatetimeIndex 和 'close' 列
    返回同 index 的 df，包含 SMA_20, EMA_20, RSI_14, MACD, MACD_signal, BB_mid/BB_up/BB_low, ATR_14
    """
    df = df.copy()
    close = df['close'].astype(float)

    # SMA / EMA
    df['SMA_20'] = close.rolling(window=20, min_periods=1).mean()
    df['EMA_20'] = close.ewm(span=20, adjust=False).mean()

    # RSI(14)
    delta = close.diff()
    up = delta.clip(lower=0)
    down = -1 * delta.clip(upper=0)
    roll_up = up.rolling(window=14, min_periods=14).mean()
    roll_down = down.rolling(window=14, min_periods=14).mean()
    rs = roll_up / roll_down.replace(0, np.nan)
    df['RSI_14'] = 100 - (100 / (1 + rs))

    # MACD (12,26,9)
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    df['MACD'] = ema12 - ema26
    df['MACD_signal'] = df['MACD'].ewm(span=9, adjust=False).mean()

    # Bollinger Bands (20,2)
    df['BB_mid'] = close.rolling(window=20, min_periods=1).mean()
    df['BB_std'] = close.rolling(window=20, min_periods=1).std()
    df['BB_up'] = df['BB_mid'] + 2 * df['BB_std']
    df['BB_low'] = df['BB_mid'] - 2 * df['BB_std']

    # ATR(14) - 用于止损距离
    # 为计算 ATR 需要 High/Low/Close；yfinance fetch here only close; we approximate ATR using close diff as fallback
    # If real ATR needed, we would fetch OHLC. For robustness, use rolling true range approx:
    tr = pd.Series(np.abs(delta), index=df.index)
    df['ATR_14'] = tr.rolling(window=14, min_periods=1).mean()

    return df

# ---------- 评分与交易价位建议（基于 ATR 和 布林带） ----------
def score_and_tradeplan(df: pd.DataFrame):
    """
    返回 (probability_percent, advice_text, trade_plan_dict)
    trade_plan_dict 包含：entry_buy, stop_loss_buy, take_profit_buy, entry_sell, stop_loss_sell, take_profit_sell
    注意：trade_plan 为建议，仅供参考
    """
    # 先对关键列 dropna（只要最后一行有足够数据即可）
    keys = ['close','SMA_20','EMA_20','RSI_14','MACD','MACD_signal','BB_up','BB_low','ATR_14']
    df2 = df.dropna(subset=keys)
    if df2.empty:
        return None, "数据不足，无法计算", {}

    last = df2.iloc[-1]
    price = float(last['close'])
    score = 0
    # SMA/EMA
    score += 1 if price > last['SMA_20'] else -1
    score += 1 if price > last['EMA_20'] else -1
    # RSI
    if last['RSI_14'] < 30:
        score += 1
    elif last['RSI_14'] > 70:
        score -= 1
    # MACD
    score += 1 if last['MACD'] > last['MACD_signal'] else -1
    # Bollinger
    if price < last['BB_low']:
        score += 1
    elif price > last['BB_up']:
        score -= 1

    # 映射到概率
    prob = (score + 5) / 10 * 100
    prob = float(max(0.0, min(100.0, round(prob,2))))

    # 建议文本
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

    # 交易计划：使用 ATR 作为波动单位，止损设置为 1.5 * ATR（可调整），止盈为 2x 风险
    atr = float(last['ATR_14']) if not np.isnan(last['ATR_14']) and last['ATR_14']>0 else max(0.01, price*0.005)  # fallback to 0.5% if ATR zero
    sl_dist = 1.5 * atr
    tp_dist = 2.0 * sl_dist  # 风险回报 1:2

    # 买入计划（如果做多）：entry 当前价，stop_loss = max(bb_low, price - sl_dist)
    stop_loss_buy = max(last['BB_low'], price - sl_dist)
    take_profit_buy = price + tp_dist

    # 卖出/做空计划
    stop_loss_sell = min(last['BB_up'], price + sl_dist)
    take_profit_sell = price - tp_dist

    trade_plan = {
        'entry_buy': round(price, 6),
        'stop_loss_buy': round(stop_loss_buy, 6),
        'take_profit_buy': round(take_profit_buy, 6),
        'entry_sell': round(price, 6),
        'stop_loss_sell': round(stop_loss_sell, 6),
        'take_profit_sell': round(take_profit_sell, 6),
        'atr': round(atr, 8),
        'bb_low': round(float(last['BB_low']), 8),
        'bb_up': round(float(last['BB_up']), 8)
    }

    return prob, advice, trade_plan

# ---------- 主展示（多币种多周期） ----------
st.sidebar.header("状态")
st.sidebar.write(f"香港时间：{now_hk()}")
st.sidebar.write("自动每 15 分钟刷新一次（或点页面刷新）")

tickers = {
    "BTC": "BTC-USD",
    "ETH": "ETH-USD",
    "SOL": "SOL-USD"
}

# yfinance 参数：取足够历史保证指标计算稳定
interval_cfg = {
    "15m": {"yf_interval":"15m","yf_period":"7d","resample":None,"label":"15 分钟"},
    "1h":  {"yf_interval":"60m","yf_period":"30d","resample":None,"label":"1 小时"},
    "4h":  {"yf_interval":"60m","yf_period":"90d","resample":"4H","label":"4 小时"},  # 从 1h 重采样
    "24h": {"yf_interval":"1d","yf_period":"1095d","resample":None,"label":"24 小时"}
}

# 布局：每币一块
for coin_name, ticker in tickers.items():
    st.markdown("---")
    st.header(f"🔹 {coin_name} ({ticker})")
    cols = st.columns(len(interval_cfg))
    for idx, (k, cfg) in enumerate(interval_cfg.items()):
        with cols[idx]:
            st.subheader(cfg['label'])
            try:
                raw = safe_fetch(ticker, cfg['yf_interval'], cfg['yf_period'])
                if raw.empty:
                    st.warning("数据获取失败或为空")
                    continue
                # 若需重采样（例如 4H）
                if cfg['resample']:
                    raw.index = pd.to_datetime(raw.index)
                    df_period = resample_to(raw, cfg['resample'])
                else:
                    df_period = raw.copy()

                if df_period.empty or df_period.shape[0] < 20:
                    st.info("数据点不足，无法计算指标")
                    continue

                df_ind = compute_indicators(df_period)

                prob, advice, plan = score_and_tradeplan(df_ind)
                if prob is None:
                    st.info("数据不足，无法给出概率/交易计划")
                    continue

                # 显示结果
                latest_price = df_ind['close'].iloc[-1]
                st.metric(label="最新价格 (USD)", value=f"${latest_price:,.6f}")
                st.metric(label="买入综合概率", value=f"{prob:.2f}%")
                st.write(f"建议：**{advice}**")

                # 显示交易计划
                st.markdown("**交易计划（示例）**")
                st.write(f"多头入场（BUY）: 建议入场 {plan['entry_buy']}, 止损 {plan['stop_loss_buy']}, 止盈 {plan['take_profit_buy']}")
                st.write(f"空头入场（SELL）: 建议入场 {plan['entry_sell']}, 止损 {plan['stop_loss_sell']}, 止盈 {plan['take_profit_sell']}")
                st.write(f"ATR(14)：{plan['atr']} ｜ 布林下轨：{plan['bb_low']} ｜ 布林上轨：{plan['bb_up']}")

                # 小图（价格 + SMA/EMA）
                plot_df = df_ind[['close','SMA_20','EMA_20']].dropna()
                if not plot_df.empty:
                    st.line_chart(plot_df.tail(200))
                else:
                    st.info("图表数据不足以绘制均线")

            except Exception as e:
                st.error(f"处理失败：{e}")

st.caption("说明：以上建议为示例策略输出，仅供参考。真实交易需严格风控与回测。")
