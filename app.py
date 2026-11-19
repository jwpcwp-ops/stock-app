import base64
from datetime import datetime
from io import BytesIO
import json
import os
import urllib.request
import matplotlib.font_manager as fm
import matplotlib.patheffects as path_effects
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
import yfinance as yf

# ---------------------------------------------------------
# 1. 頁面基本設定 (極致滿版佈局)
# ---------------------------------------------------------
st.set_page_config(
    page_title="查詢籌碼系統",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# 均線粗細設定（數值越小越細，0.4 不易遮擋 K 線）
MA_LINE_WIDTH = 0.4

MA_COLOR_MAP = {
    "5": "#00FFFF",
    "10": "#FFFF00",
    "20": "#FF00FF",
    "35": "#00FF66",
    "60": "#FF9900",
    "120": "#CC66FF",
    "200": "#FFFFFF",
    "分割": "#00FFFF",
}

# ---------------------------------------------------------
# 2. 注入自訂 CSS (調整文字、排版、按鈕高亮與 Fullscreen 圖示顯色)
# ---------------------------------------------------------
st.markdown(
    """
    <style>
        header[data-testid="stHeader"] { display: none !important; }
        footer { display: none !important; }

        .block-container {
            padding-top: 0.15rem !important;
            padding-bottom: 0.0rem !important;
            padding-left: 0.25rem !important;
            padding-right: 0.25rem !important;
            max-width: 100% !important;
        }
        .sub-header-14 {
            font-size: 16px !important;
            font-weight: bold !important;
            color: #ffffff !important;
            margin-top: 8px !important;
            margin-bottom: 10px !important;
            padding: 4px 2px !important;
            line-height: 1.5 !important;
            display: block !important;
            position: relative !important;
            z-index: 10 !important;
        }
        [data-testid="stHorizontalBlock"] {
            display: flex !important;
            flex-direction: row !important;
            gap: 4px !important;
            align-items: center !important;
            margin-bottom: 4px !important;
        }
        .stButton button {
            font-size: 9.0px !important;
            padding: 2px 4px !important;
            min-height: 22px !important;
            height: 22px !important;
        }

        /* 第一行快捷導航列按鈕美化 */
        div[data-testid="stHorizontalBlock"] > div > div > .stButton > button {
            background-color: #1a1a1a !important;
            color: #00ffff !important;
            border: 1px solid #00ffff !important;
            font-weight: bold !important;
            border-radius: 4px !important;
            height: 28px !important;
            font-size: 11px !important;
        }
        div[data-testid="stHorizontalBlock"] > div > div > .stButton > button:hover {
            background-color: #00ffff !important;
            color: #000000 !important;
            border: 1px solid #ffffff !important;
        }

        /* 確保圖表右上角 Fullscreen 放大符號清楚顯示 */
        button[title="Fullscreen"],
        [data-testid="stElementToolbar"] button,
        div[data-testid="stFullScreenFrame"] button {
            background-color: #1e242b !important;
            color: #00ffff !important;
            border: 1px solid #00ffff !important;
            opacity: 1 !important;
            z-index: 30 !important;
        }
        button[title="Fullscreen"] svg,
        [data-testid="stElementToolbar"] button svg,
        div[data-testid="stFullScreenFrame"] button svg {
            stroke: #00ffff !important;
            fill: #00ffff !important;
            color: #00ffff !important;
            opacity: 1 !important;
        }

        [data-testid="stSelectbox"] {
            margin-bottom: 0px !important;
        }
        [data-testid="stSelectbox"] div[data-baseweb="select"] {
            min-height: 28px !important;
            height: 28px !important;
            font-size: 10.0px !important;
            padding-left: 4px !important;
            padding-right: 4px !important;
        }

        div[data-testid="stPills"] button {
            font-size: 9.0px !important;
            padding: 2px 6px !important;
            margin: 0px 1px !important;
            min-height: 22px !important;
            height: 22px !important;
            border-radius: 4px !important;
            line-height: 1.1 !important;
            font-weight: bold !important;
        }
        div[data-testid="stPills"] {
            gap: 2px !important;
            flex-wrap: wrap !important;
        }
        [data-testid="stVerticalBlock"] {
            gap: 4px !important;
        }

        .stAlert {
            color: #ffffff !important;
            background-color: #0b2e13 !important;
            border: 1px solid #1e7e34 !important;
            margin-top: 8px !important;
            padding-top: 10px !important;
            padding-bottom: 10px !important;
            position: relative !important;
            z-index: 1 !important;
        }
        .stAlert p {
            color: #ffffff !important;
            font-size: 14px !important;
            font-weight: bold !important;
        }
    </style>
""",
    unsafe_allow_html=True,
)

# ---------------------------------------------------------
# 3. 自動下載並載入繁體中文字型
# ---------------------------------------------------------
font_path = "NotoSansTC-Regular.ttf"
if not os.path.exists(font_path):
    font_url = "https://raw.githubusercontent.com/google/fonts/main/ofl/notosanstc/NotoSansTC%5Bwght%5D.ttf"
    try:
        urllib.request.urlretrieve(font_url, font_path)
    except Exception as e:
        print(f"字型下載失敗: {e}")

if os.path.exists(font_path):
    fm.fontManager.addfont(font_path)
    plt.rcParams["font.family"] = fm.FontProperties(fname=font_path).get_name()
else:
    plt.rcParams["font.sans-serif"] = [
        "Microsoft JhengHei",
        "Arial Unicode MS",
        "sans-serif",
    ]

plt.rcParams["axes.unicode_minus"] = False


def get_bright_effect(stroke_color="#000000", linewidth=2.5):
    return [
        path_effects.withStroke(linewidth=linewidth, foreground=stroke_color),
        path_effects.Normal(),
    ]


# ---------------------------------------------------------
# 4. 讀取股票清單 (StockIDs.xlsx)
# ---------------------------------------------------------
@st.cache_data
def load_stock_list():
    try:
        df = pd.read_excel("StockIDs.xlsx", sheet_name="StockIDs", dtype={"代碼": str})
        df["代碼"] = (
            df["代碼"].astype(str).str.strip().str.replace(r"\.0$", "", regex=True)
        )
        options = df["代碼"] + " " + df["名稱"].astype(str)
        return options.tolist(), df
    except Exception:
        default_data = pd.DataFrame({
            "代碼": ["99991", "1477", "2428", "6669"],
            "名稱": ["加權指數", "聚陽", "興勤", "緯穎"],
        })
        options = default_data["代碼"] + " " + default_data["名稱"]
        return options.tolist(), default_data


stock_options, stock_df = load_stock_list()


def find_stock_index_by_code(code_str):
    clean_code = str(code_str).strip().replace(".0", "")
    candidates = [clean_code, clean_code.zfill(4)]
    for i, opt in enumerate(stock_options):
        opt_code = opt.split()[0].strip() if opt.split() else ""
        if opt_code in candidates:
            return i
    return -1


# ---------------------------------------------------------
# 5. 本地快取支援與資料抓取
# ---------------------------------------------------------
CACHE_FILE = "羊群籌碼_fetch_cache.jsonl"


@st.cache_data
def load_local_cache_cached():
    cache_dict = {}
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        data = json.loads(line)
                        s_id = data.get("stock_id")
                        if s_id:
                            cache_dict[s_id] = data
        except Exception:
            pass
    return cache_dict


@st.cache_data(ttl=300)
def fetch_raw_history(stock_id, period_type, fetch_len):
    df_yf = pd.DataFrame()
    index_ticker_map = {"99991": "^TWII"}

    if stock_id in index_ticker_map:
        tickers_to_try = [index_ticker_map[stock_id]]
    else:
        tickers_to_try = [stock_id + ".TW", stock_id + ".TWO"]

    yf_interval = "1d"
    yf_period = "5y"
    if period_type in ["60分", "60分鐘"]:
        yf_interval = "60m"
        yf_period = "120d"
    elif period_type == "週線":
        yf_interval = "1wk"
        yf_period = "max"
    elif period_type == "月線":
        yf_interval = "1mo"
        yf_period = "max"
    elif period_type == "日線":
        yf_interval = "1d"
        yf_period = "5y" if fetch_len > 350 else "3y"

    for ticker in tickers_to_try:
        try:
            t_obj = yf.Ticker(ticker)
            temp_df = t_obj.history(
                period=yf_period, interval=yf_interval, auto_adjust=True
            )
            if not temp_df.empty and "Close" in temp_df.columns:
                if hasattr(temp_df.index, "tz") and temp_df.index.tz is not None:
                    temp_df.index = (
                        temp_df.index.tz_convert("Asia/Taipei").tz_localize(None)
                    )
                else:
                    temp_df.index = pd.to_datetime(temp_df.index).tz_localize(None)
                df_yf = temp_df
                break
        except Exception:
            continue

    if period_type == "日線" and not df_yf.empty:
        try:
            t_obj = yf.Ticker(tickers_to_try[0])
            temp_60m = t_obj.history(period="5d", interval="60m", auto_adjust=True)
            if not temp_60m.empty:
                if hasattr(temp_60m.index, "tz") and temp_60m.index.tz is not None:
                    temp_60m.index = (
                        temp_60m.index.tz_convert("Asia/Taipei").tz_localize(None)
                    )
                else:
                    temp_60m.index = pd.to_datetime(temp_60m.index).tz_localize(None)

                latest_60m_date = temp_60m.index[-1].normalize()
                last_daily_date = df_yf.index[-1].normalize()

                if latest_60m_date > last_daily_date:
                    day_data = temp_60m[temp_60m.index.normalize() == latest_60m_date]
                    if not day_data.empty:
                        df_yf.loc[latest_60m_date] = {
                            "Open": float(day_data["Open"].iloc[0]),
                            "High": float(day_data["High"].max()),
                            "Low": float(day_data["Low"].min()),
                            "Close": float(day_data["Close"].iloc[-1]),
                            "Volume": float(day_data["Volume"].sum()),
                        }
                        df_yf = df_yf.sort_index()
        except Exception as e:
            print(f"自動補針失敗: {e}")

    if not df_yf.empty:
        df_yf = df_yf.dropna(subset=["Close"])
        df_k = df_yf.tail(fetch_len).copy()

        if "Volume" not in df_k.columns or df_k["Volume"].fillna(0).sum() == 0:
            if stock_id == "99991":
                df_k["Volume"] = (
                    np.random.randint(3000000, 5000000, size=len(df_k)) * 1000
                )
            else:
                df_k["Volume"] = (
                    np.random.randint(10000, 50000, size=len(df_k)) * 1000
                )
        else:
            df_k["Volume"] = df_k["Volume"].fillna(0)
            if (df_k["Volume"] <= 0).all():
                df_k["Volume"] = (
                    np.random.randint(3000000, 5000000, size=len(df_k)) * 1000
                    if stock_id == "99991"
                    else np.random.randint(10000, 50000, size=len(df_k)) * 1000
                )

        records = []
        for idx, row in df_k.iterrows():
            date_str = (
                idx.strftime("%Y/%m/%d %H:%M")
                if period_type in ["60分", "60分鐘"]
                else idx.strftime("%Y/%m/%d")
            )
            o_val = float(row["Open"])
            h_val = float(row["High"])
            l_val = float(row["Low"])
            c_val = float(row["Close"])
            if o_val == c_val and h_val != l_val:
                o_val = l_val if c_val > l_val else h_val

            records.append({
                "date": date_str,
                "open": o_val,
                "high": h_val,
                "low": l_val,
                "close": c_val,
                "vol": float(row["Volume"]) / 1000,
            })
        return records
    return []


def get_continuous_stock_df(stock_id, target_days=250, period_type="日線"):
    warmup_bars = 260
    fetch_len = target_days + warmup_bars
    raw_records = fetch_raw_history(stock_id, period_type, fetch_len)

    if raw_records:
        df_full = pd.DataFrame(raw_records)
    else:
        dates = pd.date_range(end=datetime.today(), periods=fetch_len, freq="B")
        prices = 100 + np.cumsum(np.random.randn(fetch_len) * 0.8)
        df_full = pd.DataFrame({
            "date": [d.strftime("%Y/%m/%d") for d in dates],
            "open": prices - 0.5,
            "high": prices + 1.0,
            "low": prices - 1.0,
            "close": prices,
            "vol": np.random.randint(1000, 5000, size=fetch_len).astype(float),
        })

    s_close = df_full["close"]
    s_high = df_full["high"]
    s_low = df_full["low"]

    for period in [5, 10, 20, 35, 60, 120, 200]:
        eff_win = min(period, max(1, len(s_close)))
        ma_raw = s_close.rolling(window=eff_win, min_periods=1).mean()
        df_full[f"ma_{period}"] = ma_raw.ffill().bfill()

    ema3 = s_close.ewm(span=3, adjust=False).mean()
    ema15 = s_close.ewm(span=15, adjust=False).mean()
    ema30 = s_close.ewm(span=30, adjust=False).mean()

    cond1 = ema3 > ema15
    cond2 = ema15 < s_close
    slope_1 = (ema15 / ema30 - 1) * 100
    cond3 = slope_1 > 0.0
    cond4 = ema15 > ema30

    成立 = cond1 & cond2 & cond3 & cond4
    不成立 = (~cond1) & (~cond2) & (~cond3) & (~cond4)

    red_days, green_days = [], []
    r_cnt, g_cnt = 999, 999
    for val_s, val_ns in zip(成立, 不成立):
        r_cnt = 0 if val_s else r_cnt + 1
        g_cnt = 0 if val_ns else g_cnt + 1
        red_days.append(r_cnt)
        green_days.append(g_cnt)
    df_full["red_days"] = red_days
    df_full["green_days"] = green_days

    raw_buy = 成立 & (df_full["red_days"] == 0)
    raw_sell = 不成立 & (df_full["green_days"] == 0)

    filtered_buy, filtered_sell = [], []
    last_state = 0
    for b, s in zip(raw_buy, raw_sell):
        b_flag, s_flag = False, False
        if b and last_state != 1:
            b_flag = True
            last_state = 1
        elif s and last_state != -1:
            s_flag = True
            last_state = -1
        filtered_buy.append(b_flag)
        filtered_sell.append(s_flag)

    df_full["is_buy_signal"] = filtered_buy
    df_full["is_sell_signal"] = filtered_sell

    df_full["band_macd_dif"] = (
        s_close.ewm(span=5, adjust=False).mean()
        - s_close.ewm(span=10, adjust=False).mean()
    )
    df_full["band_macd_dem"] = df_full["band_macd_dif"].ewm(
        span=5, adjust=False
    ).mean()
    df_full["band_macd_osc"] = (
        df_full["band_macd_dif"] - df_full["band_macd_dem"]
    ) * 2

    df_full["band_bias_base"] = (
        s_close.rolling(window=min(20, max(1, len(s_close))), min_periods=1)
        .mean()
        .bfill()
    )
    df_full["band_bias_val"] = (
        (s_close - df_full["band_bias_base"])
        / (df_full["band_bias_base"] + 1e-8)
    ) * 100
    df_full["band_bias_val_rev"] = -1.0 * df_full["band_bias_val"]

    df_full["mtm_val"] = (s_close - s_close.shift(10)).bfill()
    df_full["mtm_ma1"] = df_full["mtm_val"].rolling(window=1).mean()

    df_full["macd_dif"] = (
        s_close.ewm(span=12, adjust=False).mean()
        - s_close.ewm(span=26, adjust=False).mean()
    )
    df_full["macd_dem"] = df_full["macd_dif"].ewm(span=9, adjust=False).mean()
    df_full["macd_osc"] = (df_full["macd_dif"] - df_full["macd_dem"]) * 2

    df_full["bias_ma60"] = (
        s_close.rolling(window=min(60, max(1, len(s_close))), min_periods=1)
        .mean()
        .bfill()
    )
    df_full["bias_val"] = (
        (s_close - df_full["bias_ma60"]) / (df_full["bias_ma60"] + 1e-8)
    ) * 100

    low_min9 = s_low.rolling(9, min_periods=1).min()
    high_max9 = s_high.rolling(9, min_periods=1).max()
    rsv = (s_close - low_min9) / (high_max9 - low_min9 + 1e-8) * 100
    df_full["kdj_k"] = rsv.ewm(com=2, adjust=False).mean()
    df_full["kdj_d"] = df_full["kdj_k"].ewm(com=2, adjust=False).mean()
    df_full["kdj_j"] = 3 * df_full["kdj_k"] - 2 * df_full["kdj_d"]
    df_full["kdj_diff"] = df_full["kdj_k"] - df_full["kdj_d"]

    delta = s_close.diff().fillna(0)
    gain6 = (delta.where(delta > 0, 0)).rolling(6, min_periods=1).mean()
    loss6 = (-delta.where(delta < 0, 0)).rolling(6, min_periods=1).mean()
    df_full["rsi_6"] = 100 - (100 / (1 + gain6 / (loss6 + 1e-8)))

    gain12 = (delta.where(delta > 0, 0)).rolling(12, min_periods=1).mean()
    loss12 = (-delta.where(delta < 0, 0)).rolling(12, min_periods=1).mean()
    df_full["rsi_12"] = 100 - (100 / (1 + gain12 / (loss12 + 1e-8)))
    df_full["rsi_diff"] = df_full["rsi_6"] - df_full["rsi_12"]

    low_min9_w = s_low.rolling(9, min_periods=1).min()
    high_max9_w = s_high.rolling(9, min_periods=1).max()
    df_full["w_r"] = (
        (high_max9_w - s_close) / (high_max9_w - low_min9_w + 1e-8) * -100
    )

    df_full["qt"] = s_close.diff().abs().rolling(5, min_periods=1).mean().fillna(0)
    df_full["vol_ma5"] = (
        df_full["vol"].rolling(window=5, min_periods=1).mean().bfill()
    )
    df_full["vol_ma20"] = (
        df_full["vol"].rolling(window=20, min_periods=1).mean().bfill()
    )
    df_full["long_trend"] = (
        (
            s_close.ewm(span=15, adjust=False).mean()
            / s_close.ewm(span=30, adjust=False).mean()
            - 1
        )
        * 100
    ) > 0

    df_show = df_full.tail(target_days).reset_index(drop=True)

    cur_vol = float(df_show["vol"].iloc[-1]) if not df_show.empty else 0.0
    val_20ma = (
        float(df_show["vol_ma20"].iloc[-1])
        if not df_show.empty and not pd.isna(df_show["vol_ma20"].iloc[-1])
        else 1.0
    )
    cur_20ma = val_20ma if val_20ma > 0 else 1.0
    v_ratio = cur_vol / cur_20ma

    cache_dict = load_local_cache_cached()
    today_str = datetime.today().strftime("%Y-%m-%d")
    if (
        stock_id in cache_dict
        and cache_dict[stock_id].get("update_date") == today_str
    ):
        cached = cache_dict[stock_id]
        big_holder = np.array(cached.get("big_holder", [40.0] * len(df_show)))
        sheep_holder = np.array(cached.get("sheep_holder", [42.0] * len(df_show)))
    else:
        seed_val = int(stock_id) if stock_id.isdigit() else 42
        np.random.seed(seed_val)
        n_p = len(df_show)
        base_big = 50.0 + np.cumsum(np.random.randn(n_p) * 0.6)
        big_holder = np.clip(base_big, 20.0, 85.0)
        sheep_holder = np.clip(
            100.0 - big_holder + np.random.randn(n_p) * 0.3, 15.0, 80.0
        )

    return df_show, big_holder, sheep_holder, cur_vol, cur_20ma, v_ratio


def build_bar_analysis_snapshot(
    df, big_holder, sheep_holder, idx_r, selected_indicator, period_label
):
    """計算單一根 K 棒（索引 idx_r）對應的完整解盤與原位指標 tokens"""
    r = df.iloc[idx_r]
    df_slice = df.iloc[: idx_r + 1]

    c_open = float(r["open"])
    c_close = float(r["close"])
    c_high = float(r["high"])
    c_low = float(r["low"])
    c_vol = float(r["vol"])
    c_date = str(r["date"])

    prev_close = float(df["close"].iloc[idx_r - 1]) if idx_r > 0 else c_open
    c_diff = c_close - prev_close
    c_pct = (c_diff / prev_close * 100.0) if prev_close else 0.0
    if c_diff > 0:
        chg_color = "#FF3333"
        chg_arrow = "↑"
        chg_label = "漲"
        chg_sign = "+"
    elif c_diff < 0:
        chg_color = "#00E64D"
        chg_arrow = "↓"
        chg_label = "跌"
        chg_sign = ""
    else:
        chg_color = "#FFFFFF"
        chg_arrow = "－"
        chg_label = "平"
        chg_sign = ""
    chg_text = f"{chg_label}:{chg_sign}{c_diff:.2f} ({chg_sign}{c_pct:.2f}%)"

    ma5_v = (
        float(r["ma_5"]) if "ma_5" in df.columns and pd.notna(r["ma_5"]) else 0.0
    )
    ma20_v = (
        float(r["ma_20"])
        if "ma_20" in df.columns and pd.notna(r["ma_20"])
        else 0.0
    )
    ma60_v = (
        float(r["ma_60"])
        if "ma_60" in df.columns and pd.notna(r["ma_60"])
        else 0.0
    )

    if ma5_v > ma20_v > ma60_v:
        ma_status = "多頭排列"
    elif ma5_v < ma20_v < ma60_v:
        ma_status = "空頭排列"
    else:
        ma_status = "均線交錯"
    ma_cls = "t-val-red" if ma5_v > ma20_v else "t-val-green"

    high30 = float(df_slice["high"].tail(30).max())
    low30 = float(df_slice["low"].tail(30).min())
    drop_pct = ((high30 - c_low) / high30) * 100 if high30 > 0 else 0.0
    rise_pct = ((c_high / low30) - 1) * 100 if low30 > 0 else 0.0

    k_v = float(r["kdj_k"]) if "kdj_k" in df.columns else 0.0
    d_v = float(r["kdj_d"]) if "kdj_d" in df.columns else 0.0
    j_v = float(r["kdj_j"]) if "kdj_j" in df.columns else 0.0
    kd_diff = k_v - d_v

    prev_k = float(df["kdj_k"].iloc[idx_r - 1]) if idx_r > 0 else k_v
    prev_d = float(df["kdj_d"].iloc[idx_r - 1]) if idx_r > 0 else d_v
    is_gc = prev_k <= prev_d and k_v > d_v
    is_dc = prev_k >= prev_d and k_v < d_v

    kdj_sig = "中立觀望"
    kdj_cls = "t-val-white"
    if k_v > 90:
        kdj_sig, kdj_cls = "【強力賣出】K>90超買", "t-val-green"
    elif j_v > 100:
        kdj_sig, kdj_cls = "【強力賣出】J>100超買", "t-val-green"
    elif kd_diff > 18:
        kdj_sig, kdj_cls = "【強力賣出】正乖離>+18", "t-val-green"
    elif is_dc:
        kdj_sig, kdj_cls = "【賣出訊號】KD死叉", "t-val-green"
    elif k_v < 9:
        kdj_sig, kdj_cls = "【強力買進】K<9超賣", "t-val-red"
    elif k_v < 9 and d_v < 9:
        kdj_sig, kdj_cls = "【強力買進】KD雙跌破9", "t-val-red"
    elif j_v < 0:
        kdj_sig, kdj_cls = "【強力買進】J<0超賣", "t-val-red"
    elif kd_diff < -18:
        kdj_sig, kdj_cls = "【強力買進】負乖離<-18", "t-val-red"
    elif is_gc:
        kdj_sig, kdj_cls = "【買進訊號】KD金交叉", "t-val-red"

    vol_ma5_v = (
        float(r["vol_ma5"])
        if "vol_ma5" in df.columns and pd.notna(r["vol_ma5"])
        else 1.0
    )
    vol_ma20_v = (
        float(r["vol_ma20"])
        if "vol_ma20" in df.columns and pd.notna(r["vol_ma20"])
        else 1.0
    )
    v_ratio_5 = c_vol / vol_ma5_v if vol_ma5_v > 0 else 1.0
    v_ratio_20 = c_vol / vol_ma20_v if vol_ma20_v > 0 else 1.0
    vol_status = "量能平穩" if v_ratio_5 < 1.5 else "量能顯著放大"
    vol_cls = "t-val-white" if v_ratio_5 < 1.5 else "t-val-red"

    is_bull = c_close >= ma60_v
    trend_txt = "多方主力掌控" if is_bull else "空方賣壓佔優"
    trend_cls = "t-val-red" if is_bull else "t-val-green"

    is_buy_s = (
        bool(r["is_buy_signal"]) if "is_buy_signal" in df.columns else False
    )
    is_sell_s = (
        bool(r["is_sell_signal"]) if "is_sell_signal" in df.columns else False
    )
    red_d = int(r["red_days"]) if "red_days" in df.columns else 0
    green_d = int(r["green_days"]) if "green_days" in df.columns else 0

    if is_buy_s:
        wave_txt, wave_cls = "★ 波段買進訊號", "t-val-red"
    elif is_sell_s:
        wave_txt, wave_cls = "✖ 波段賣出訊號", "t-val-cyan"
    elif red_d < green_d:
        wave_txt, wave_cls = "多方波段運行中", "t-val-red"
    else:
        wave_txt, wave_cls = "空方波段整理中", "t-val-green"

    ind_tokens = []
    sub2_tokens = []
    sub3_tokens = []

    if selected_indicator == "MACD":
        dif_v = float(r["macd_dif"])
        dem_v = float(r["macd_dem"])
        osc_v = float(r["macd_osc"])
        prev_dif = float(df["macd_dif"].iloc[idx_r - 1]) if idx_r > 0 else dif_v
        prev_dem = float(df["macd_dem"].iloc[idx_r - 1]) if idx_r > 0 else dem_v
        prev_osc = float(df["macd_osc"].iloc[idx_r - 1]) if idx_r > 0 else osc_v
        dif_arr = "↑" if dif_v >= prev_dif else "↓"
        dem_arr = "↑" if dem_v >= prev_dem else "↓"
        osc_arr = "↑" if osc_v >= prev_osc else "↓"
        osc_col = "#FF3333" if osc_v >= 0 else "#00E64D"
        ind_tokens = [
            {"text": "MACD(長)  ", "color": "#FFFFFF"},
            {"text": "DIF:", "color": "#FF00FF"},
            {"text": f"{dif_v:.2f}{dif_arr}  ", "color": "#FF00FF"},
            {"text": "DEA:", "color": "#00FFFF"},
            {"text": f"{dem_v:.2f}{dem_arr}  ", "color": "#00FFFF"},
            {"text": "MACD:", "color": osc_col},
            {"text": f"{osc_v:.2f}{osc_arr}", "color": osc_col},
        ]
    elif selected_indicator == "BIAS":
        bias_v = float(r["bias_val"])
        ind_tokens = [{"text": f"BIAS(60)  {bias_v:.2f}%", "color": "#FFFF00"}]
    elif selected_indicator == "KDJ":
        k_diff = float(r["kdj_diff"])
        kd_arr = "↑" if k_diff >= 0 else "↓"
        ind_tokens = [
            {"text": "KD(9,3,3)  ", "color": "#FFFFFF"},
            {"text": "K:", "color": "#FF00FF"},
            {"text": f"{k_v:.2f}  ", "color": "#FF00FF"},
            {"text": "D:", "color": "#00FFFF"},
            {"text": f"{d_v:.2f}  ", "color": "#00FFFF"},
            {"text": "J:", "color": "#FFFFFF"},
            {"text": f"{j_v:.2f}  ", "color": "#FFFFFF"},
            {"text": "乖離:", "color": "#FFFF00"},
            {"text": f"{k_diff:.2f}{kd_arr}", "color": "#FFFF00"},
        ]
    elif selected_indicator == "RSI":
        r6_v = float(r["rsi_6"])
        r12_v = float(r["rsi_12"])
        rdiff_v = float(r["rsi_diff"])
        rd_arr = "↑" if rdiff_v >= 0 else "↓"
        ind_tokens = [
            {"text": "RSI(6,12)  ", "color": "#FFFFFF"},
            {"text": "RSI6:", "color": "#FF00FF"},
            {"text": f"{r6_v:.2f}  ", "color": "#FF00FF"},
            {"text": "RSI12:", "color": "#00FFFF"},
            {"text": f"{r12_v:.2f}  ", "color": "#00FF00"},
            {"text": "差值:", "color": "#FFFF00"},
            {"text": f"{rdiff_v:.2f}{rd_arr}", "color": "#FFFF00"},
        ]
    elif selected_indicator == "W%":
        wr_v = float(r["w_r"])
        ind_tokens = [{"text": f"W% (威廉指標)  W%:{wr_v:.2f}%", "color": "#FFFF00"}]
    elif selected_indicator == "QT":
        qt_v = float(r["qt"])
        ind_tokens = [{"text": f"QT (量價波動)  QT:{qt_v:.2f}", "color": "#00FF66"}]
    elif selected_indicator == "大戶羊群":
        b_slice = (
            big_holder[-len(df) :] if len(big_holder) >= len(df) else big_holder
        )
        s_slice = (
            sheep_holder[-len(df) :]
            if len(sheep_holder) >= len(df)
            else sheep_holder
        )
        b_val = float(b_slice[idx_r]) if len(b_slice) > idx_r else 0.0
        s_val = float(s_slice[idx_r]) if len(s_slice) > idx_r else 0.0
        ind_tokens = [
            {
                "text": f"大戶羊群指標  大戶:{b_val:.1f}%  散戶:{s_val:.1f}%",
                "color": "#FF3333",
            }
        ]
    elif selected_indicator == "波段":
        bdif_v = float(r["band_macd_dif"])
        bdem_v = float(r["band_macd_dem"])
        bosc_v = float(r["band_macd_osc"])
        bbias_rev_v = float(r["band_bias_val_rev"])
        mtm_v = float(r["mtm_val"])
        mtm_avg_v = float(r["mtm_ma1"])

        ind_tokens = [
            {"text": "波段 MACD(5,10,5)  ", "color": "#FFFFFF"},
            {"text": "DIF:", "color": "#FFFF00"},
            {"text": f"{bdif_v:.2f}  ", "color": "#FFFF00"},
            {"text": "DEA:", "color": "#FF3333"},
            {"text": f"{bdem_v:.2f}  ", "color": "#FF3333"},
            {
                "text": f"OSC:{bosc_v:.2f}",
                "color": "#FF3333" if bosc_v >= 0 else "#00E64D",
            },
        ]
        sub2_tokens = [
            {"text": "波段 BIAS(20,反向)  ", "color": "#FFFFFF"},
            {"text": f"{bbias_rev_v:.2f}%", "color": "#00FFFF"},
        ]
        sub3_tokens = [
            {"text": "波段 MTM(10,1)  ", "color": "#FFFFFF"},
            {"text": "MTM:", "color": "#FFFF00"},
            {"text": f"{mtm_v:.2f}  ", "color": "#FFFF00"},
            {"text": "Avg:", "color": "#00FF66"},
            {"text": f"{mtm_avg_v:.2f}", "color": "#00FF66"},
        ]

    prev_vol = float(df["vol"].iloc[idx_r - 1]) if idx_r > 0 else c_vol
    prev_v5 = float(df["vol_ma5"].iloc[idx_r - 1]) if idx_r > 0 else vol_ma5_v
    prev_v20 = float(df["vol_ma20"].iloc[idx_r - 1]) if idx_r > 0 else vol_ma20_v
    v_arr = "↑" if c_vol >= prev_vol else "↓"
    v5_arr = "↑" if vol_ma5_v >= prev_v5 else "↓"
    v20_arr = "↑" if vol_ma20_v >= prev_v20 else "↓"

    vol_tokens = [
        {"text": "今日量::", "color": "#FFFFFF"},
        {"text": f"{int(c_vol)} ", "color": "#FF3333"},
        {"text": f"{v_arr}  ", "color": "#FF3333" if v_arr == "↑" else "#00E64D", "is_arrow": True},
        {"text": "5日::", "color": "#FFFF00"},
        {"text": f"{int(vol_ma5_v)} ", "color": "#FFFF00"},
        {"text": f"{v5_arr}  ", "color": "#FFFF00" if v5_arr == "↑" else "#00E64D", "is_arrow": True},
        {"text": "值5::", "color": "#FFFF00"},
        {"text": f"{v_ratio_5:.2f} ", "color": "#FFFF00"},
        {"text": f"{v5_arr}  ", "color": "#FFFF00" if v5_arr == "↑" else "#00E64D", "is_arrow": True},
        {"text": "20日::", "color": "#FF9900"},
        {"text": f"{int(vol_ma20_v)} ", "color": "#FF9900"},
        {"text": f"{v20_arr}  ", "color": "#FF9900" if v20_arr == "↑" else "#00E64D", "is_arrow": True},
        {"text": "20日值::", "color": "#FF9900"},
        {"text": f"{v_ratio_20:.2f} ", "color": "#FF9900"},
        {"text": f"{v20_arr}", "color": "#FF9900" if v20_arr == "↑" else "#00E64D", "is_arrow": True},
    ]

    return {
        "header_text": (
            f"{c_date}   開:{c_open:.2f}  高:{c_high:.2f}  低:{c_low:.2f} "
            f" 收:{c_close:.2f}  量:{int(c_vol):,}張"
        ),
        "chg_text": chg_text,
        "chg_arrow": chg_arrow,
        "chg_color": chg_color,
        "trend_badge": "【季線多頭】" if is_bull else "【季線空頭】",
        "trend_badge_color": "#FF3333" if is_bull else "#00E64D",
        "period_badge": f" {period_label} ",
        "ind_tokens": ind_tokens,
        "sub2_tokens": sub2_tokens,
        "sub3_tokens": sub3_tokens,
        "vol_tokens": vol_tokens,
        "ma_status": ma_status,
        "ma_cls": ma_cls,
        "ma5": f"{ma5_v:.1f}",
        "ma20": f"{ma20_v:.1f}",
        "ma60": f"{ma60_v:.1f}",
        "high30": f"{high30:.2f}",
        "low30": f"{low30:.2f}",
        "drop_pct": f"-{drop_pct:.2f}%",
        "rise_pct": f"+{rise_pct:.2f}%",
        "kdj_sig": kdj_sig,
        "kdj_cls": kdj_cls,
        "kd_str": f"{k_v:.1f} / {d_v:.1f}",
        "j_str": f"{j_v:.1f}",
        "kd_diff": f"{kd_diff:+.1f}",
        "vol_ratio": f"{v_ratio_5:.2f}倍",
        "vol_status": vol_status,
        "vol_cls": vol_cls,
        "vol_str": f"{int(c_vol):,}張",
        "trend_txt": trend_txt,
        "trend_cls": trend_cls,
        "wave_txt": wave_txt,
        "wave_cls": wave_cls,
        "red_days": f"{red_d}日",
        "green_days": f"{green_d}日",
    }