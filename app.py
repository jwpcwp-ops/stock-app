import base64
from datetime import datetime
from io import BytesIO
import json
import os
import ssl
import urllib.request
import certifi
import matplotlib.font_manager as fm
import matplotlib.patheffects as path_effects
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
import yfinance as yf

# ---------------------------------------------------------
# 1. 頁面基本設定與常數定義 (極致滿版佈局)
# ---------------------------------------------------------
st.set_page_config(
    page_title="查詢籌碼系統",
    layout="wide",
    initial_sidebar_state="collapsed",
)

MA_LINE_WIDTH = 0.4
IND_LINE_WIDTH = 0.6

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

FEIHU_BAR_STEPS = [6, 11, 18, 29, 45, 69, 105, 159, 240, 361, 543, 816]

MINUTE_PERIOD_LABELS = {
    "5分",
    "5分鐘",
    "10分",
    "10分鐘",
    "15分",
    "15分鐘",
    "30分",
    "30分鐘",
    "60分",
    "60分鐘",
}

INDICATOR_BUTTONS = ["波段", "組合", "組合1", "BIAS", "QT", "集保"]

ALL_STRATEGIES = [
    "主力底部吃貨",
    "突破前高",
    "MACD 選股",
    "金剛指標",
    "均線與MACD篩選",
    "波段買點",
    "多空轉折信號",
    "5均線匯集",
    "底部量大強漲",
]

BG_COLOR = "#000000"
PANEL_BG = "#000000"
GRID_COLOR = "#333333"
BAR_UP_COLOR = "#FF3333"
BAR_DOWN_COLOR = "#00E64D"
CACHE_FILE = "羊群籌碼_fetch_cache.jsonl"
SIGNAL_CSV_PATH = "自選股_羊群籌碼_最新訊號.csv"
EXCEL_FILENAME = "大戶持股最新分析總表.xlsx"
OUTPUT_CSV = "smart_selected_output.csv"

# ---------------------------------------------------------
# 2. 注入自訂 CSS
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
            gap: 3px !important;
            align-items: center !important;
            margin-bottom: 4px !important;
        }
        .stButton button {
            font-size: 9.5px !important;
            padding: 1px 2px !important;
            min-width: 0px !important;
            min-height: 22px !important;
            height: 22px !important;
        }
        
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
            min-height: 26px !important;
            height: 26px !important;
            font-size: 10.5px !important;
            padding-left: 4px !important;
            padding-right: 4px !important;
        }

        div[data-testid="stPills"] button {
            font-size: 10.0px !important;
            padding: 2px 7px !important;
            margin: 0px 1px !important;
            min-height: 22px !important;
            height: 22px !important;
            border-radius: 4px !important;
            line-height: 1.1 !important;
            font-weight: bold !important;
            white-space: nowrap !important;
        }
        div[data-testid="stPills"] {
            gap: 3px !important;
            flex-wrap: nowrap !important;
            overflow-x: auto !important;
        }
        [data-testid="stVerticalBlock"] {
            gap: 4px !important;
        }
        
        .stAlert {
            color: #F0B84B !important;
            background-color: #0b0d10 !important;
            border: 1px solid #334155 !important;
            margin-top: 8px !important;
            padding-top: 10px !important;
            padding-bottom: 10px !important;
            position: relative !important;
            z-index: 1 !important;
        }
        .stAlert p {
            color: #F0B84B !important;
            font-size: 14px !important;
            font-weight: bold !important;
        }

        div[data-testid="stHorizontalBlock"]:has(.gold-row-anchor) {
            width: auto !important;
            max-width: none !important;
            min-width: 0 !important;
            display: flex !important;
            flex-direction: row !important;
            align-items: center !important;
            justify-content: flex-start !important;
            gap: 5px !important;
            flex-wrap: nowrap !important;
            margin-top: 4px !important;
            margin-bottom: 6px !important;
            padding: 0 !important;
            background-color: transparent !important;
            border: none !important;
            box-sizing: border-box !important;
        }
        div[data-testid="stHorizontalBlock"]:has(.gold-row-anchor) > div[data-testid="column"],
        div[data-testid="stHorizontalBlock"]:has(.gold-row-anchor) > div[data-testid="stColumn"] {
            flex: 0 0 auto !important;
            width: auto !important;
            min-width: 0 !important;
            max-width: none !important;
            padding: 0 !important;
            margin: 0 !important;
            display: flex !important;
            align-items: center !important;
            height: 30px !important;
        }
        div[data-testid="stHorizontalBlock"]:has(.gold-row-anchor) div[data-testid="stVerticalBlock"],
        div[data-testid="stHorizontalBlock"]:has(.gold-row-anchor) div[data-testid="stElementContainer"],
        div[data-testid="stHorizontalBlock"]:has(.gold-row-anchor) div[data-testid="stMarkdownContainer"],
        div[data-testid="stHorizontalBlock"]:has(.gold-row-anchor) div[data-testid="stSelectbox"],
        div[data-testid="stHorizontalBlock"]:has(.gold-row-anchor) div[data-testid="stButton"] {
            margin: 0 !important;
            padding: 0 !important;
            min-height: 30px !important;
            height: 30px !important;
            display: flex !important;
            align-items: center !important;
        }
        div[data-testid="stHorizontalBlock"]:has(.gold-row-anchor) div[data-testid="stMarkdownContainer"] p {
            margin: 0 !important;
            padding: 0 !important;
            line-height: 30px !important;
            display: flex !important;
            align-items: center !important;
        }
        .gold-status-text {
            color: #F0B84B !important;
            font-size: 13.5px !important;
            font-weight: 800 !important;
            line-height: 30px !important;
            height: 30px !important;
            white-space: nowrap !important;
            display: inline-flex !important;
            align-items: center !important;
            margin: 0 2px 0 0 !important;
        }
        .gold-tag-box {
            display: inline-flex !important;
            align-items: center !important;
            justify-content: center !important;
            height: 30px !important;
            min-height: 30px !important;
            padding: 0 8px !important;
            border-radius: 5px !important;
            font-size: 13px !important;
            font-weight: 800 !important;
            line-height: 28px !important;
            white-space: nowrap !important;
            box-sizing: border-box !important;
            margin: 0 !important;
        }
        .gold-dw-label {
            background-color: #111827 !important;
            color: #F8FAFC !important;
            border: 1px solid #374151 !important;
        }
        .gold-tag-idle {
            background-color: #161b22 !important;
            color: #F1F5F9 !important;
            border: 1px solid #3f4b5b !important;
        }
        .gold-tag-active {
            background-color: rgba(56, 178, 196, 0.25) !important;
            color: #38B2C4 !important;
            border: 1px solid #38B2C4 !important;
        }
        div[data-testid="stHorizontalBlock"]:has(.gold-row-anchor) .st-key-dw_choice_select {
            width: 64px !important;
            min-width: 64px !important;
            max-width: 64px !important;
        }
        div[data-testid="stHorizontalBlock"]:has(.gold-row-anchor) .st-key-dw_vol_mult {
            width: 86px !important;
            min-width: 86px !important;
            max-width: 86px !important;
        }
        div[data-testid="stHorizontalBlock"]:has(.gold-row-anchor) .st-key-dw_val_up_sel {
            width: 76px !important;
            min-width: 76px !important;
            max-width: 76px !important;
        }

        div[data-testid="stHorizontalBlock"]:has(.gold-row-anchor) div[data-baseweb="select"] {
            min-height: 30px !important;
            height: 30px !important;
            width: 100% !important;
            margin: 0 !important;
        }
        div[data-testid="stHorizontalBlock"]:has(.gold-row-anchor) div[data-baseweb="select"] > div {
            min-height: 30px !important;
            height: 30px !important;
            width: 100% !important;
            font-size: 13.5px !important;
            font-weight: 800 !important;
            line-height: 28px !important;
            padding-top: 0 !important;
            padding-bottom: 0 !important;
            padding-left: 8px !important;
            padding-right: 6px !important;
            background-color: #161b22 !important;
            border-color: #3f4b5b !important;
            border-radius: 5px !important;
            box-sizing: border-box !important;
            display: flex !important;
            align-items: center !important;
            justify-content: space-between !important;
        }
        div[data-testid="stHorizontalBlock"]:has(.gold-row-anchor) div[data-baseweb="select"] > div > div:first-child {
            flex: 1 1 auto !important;
            min-width: 0 !important;
            overflow: visible !important;
            text-overflow: clip !important;
            padding: 0 !important;
            margin: 0 !important;
        }
        div[data-testid="stHorizontalBlock"]:has(.gold-row-anchor) .st-key-dw_choice_select div[data-baseweb="select"] > div > div:first-child,
        div[data-testid="stHorizontalBlock"]:has(.gold-row-anchor) .st-key-dw_choice_select div[data-baseweb="select"] > div > div:first-child div {
            color: #FACC15 !important;
        }
        div[data-testid="stHorizontalBlock"]:has(.gold-row-anchor) div[data-baseweb="select"] span,
        div[data-testid="stHorizontalBlock"]:has(.gold-row-anchor) div[data-baseweb="select"] div {
            font-size: 13.5px !important;
            font-weight: 800 !important;
            white-space: nowrap !important;
        }
        div[data-testid="stHorizontalBlock"]:has(.gold-row-anchor) div[data-baseweb="select"] svg {
            display: block !important;
            visibility: visible !important;
            opacity: 1 !important;
            width: 15px !important;
            height: 15px !important;
            min-width: 15px !important;
            margin-left: 2px !important;
            flex-shrink: 0 !important;
            fill: currentColor !important;
        }

        div[data-testid="stHorizontalBlock"]:has(.gold-row-anchor) .st-key-btn_refresh_dw_vol button {
            height: 30px !important;
            min-height: 30px !important;
            padding: 0 9px !important;
            margin: 0 !important;
            font-size: 13px !important;
            font-weight: 800 !important;
            line-height: 28px !important;
            white-space: nowrap !important;
            width: auto !important;
            background-color: #161b22 !important;
            color: #F1F5F9 !important;
            border: 1px solid #3f4b5b !important;
            border-radius: 5px !important;
            box-sizing: border-box !important;
            display: inline-flex !important;
            align-items: center !important;
        }
        div[data-testid="stHorizontalBlock"]:has(.gold-row-anchor) .st-key-btn_refresh_dw_vol button:hover {
            background-color: #242c37 !important;
            color: #00ffff !important;
            border-color: #00ffff !important;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------
# 3. 字型與通用輔助函式
# ---------------------------------------------------------
FONT_PATH = "NotoSansTC-Regular.ttf"
if not os.path.exists(FONT_PATH):
    font_url = "https://raw.githubusercontent.com/google/fonts/main/ofl/notosanstc/NotoSansTC%5Bwght%5D.ttf"
    try:
        urllib.request.urlretrieve(font_url, FONT_PATH)
    except Exception as e:
        print(f"字型下載失敗: {e}")

if os.path.exists(FONT_PATH):
    fm.fontManager.addfont(FONT_PATH)
    plt.rcParams["font.family"] = fm.FontProperties(fname=FONT_PATH).get_name()
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


def _clean_code(val):
    s = str(val).strip().replace(".0", "")
    return s.zfill(4) if s.isdigit() else s


def _code_candidates(val):
    clean_id = str(val).strip().replace(".0", "")
    cands = [clean_id]
    if clean_id.isdigit():
        cands.extend([clean_id.zfill(4), str(int(clean_id))])
    return cands


def _norm_col(c):
    return "".join(str(c).replace("\r", "").replace("\n", "").split())


def _pyramid_link(code_str):
    return f"https://norway.twsthr.info/StockHolders.aspx?stock={_clean_code(code_str)}"


def _parse_pos_float(val):
    if val is None:
        return None
    s = str(val).replace(",", "").strip()
    if not s or s in ("-", "--", "N/A", "nan", "None"):
        return None
    try:
        fv = float(s)
        return fv if np.isfinite(fv) else None
    except Exception:
        return None


def _build_ssl_context():
    try:
        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        return ssl.create_default_context()


def _fetch_json_url(url, headers=None, timeout=8):
    req = urllib.request.Request(
        url,
        headers=headers
        or {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Accept": "application/json, text/plain, */*",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout, context=_build_ssl_context()) as resp:
        raw_txt = resp.read().decode("utf-8", errors="ignore")
        return json.loads(raw_txt)


def _normalize_yf_df_index(df_in):
    if df_in is None or df_in.empty:
        return df_in
    out = df_in.copy()
    if hasattr(out.index, "tz") and out.index.tz is not None:
        out.index = out.index.tz_convert("Asia/Taipei").tz_localize(None)
    else:
        out.index = pd.to_datetime(out.index).tz_localize(None)
    return out


# ---------------------------------------------------------
# 4. 股票清單與導航輔助
# ---------------------------------------------------------
@st.cache_data
def load_stock_list():
    try:
        df = pd.read_excel(
            "StockIDs.xlsx", sheet_name="StockIDs", dtype={"代碼": str}
        )
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
ID_TO_NAME = dict(
    zip(
        stock_df["代碼"].astype(str).str.strip().str.zfill(4),
        stock_df["名稱"].astype(str).str.strip(),
    )
)


def find_stock_index_by_code(code_str):
    candidates = _code_candidates(code_str)
    for i, opt in enumerate(stock_options):
        opt_code = opt.split()[0].strip() if opt.split() else ""
        if opt_code in candidates:
            return i
    return -1


def _jump_to_chart_with_code(picked_code, picked_name=""):
    clean_c = _clean_code(picked_code)
    matched_idx = find_stock_index_by_code(clean_c)
    if matched_idx != -1:
        st.session_state.selected_index = matched_idx
    else:
        custom_opt = f"{clean_c} {picked_name}".strip()
        if custom_opt not in stock_options:
            stock_options.insert(0, custom_opt)
        st.session_state.selected_index = 0
    st.session_state.stock_select_version += 1
    st.session_state.default_indicator_override = "集保"
    st.session_state.app_mode_state = "📈 個股籌碼圖表"
    st.rerun()


# ---------------------------------------------------------
# 5. 本地快取、行情抓取與基本面查詢
# ---------------------------------------------------------
@st.cache_data
def load_local_cache_cached():
    cache_dict = {}
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue
                    data = json.loads(line)
                    s_id = str(data.get("stock_id", "")).strip()
                    if s_id:
                        for cand in _code_candidates(s_id):
                            cache_dict.setdefault(cand, data)
        except Exception:
            pass
    return cache_dict


def extract_tdcc_arrays(cache_item):
    if not cache_item:
        return [], [], []
    if "tdcc_series" in cache_item and cache_item["tdcc_series"]:
        series = cache_item["tdcc_series"]
        w_dates = [str(x.get("date", "")) for x in series]
        big_h = [float(x.get("big", 0.0)) for x in series]
        sheep_h = [float(x.get("retail", 0.0)) for x in series]
        return big_h, sheep_h, w_dates
    big_h = [float(x) for x in cache_item.get("big_holder", [])]
    sheep_h = [float(x) for x in cache_item.get("sheep_holder", [])]
    w_dates = [str(x) for x in cache_item.get("w_dates", [])]
    return big_h, sheep_h, w_dates


def get_holder_series_for_stock(stock_id, n_periods, cache_dict=None):
    if cache_dict is None:
        cache_dict = load_local_cache_cached()
    clean_id = str(stock_id).strip().replace(".0", "")
    matched_key = next(
        (k for k in _code_candidates(clean_id) if k in cache_dict), None
    )
    if matched_key is not None:
        b_arr, s_arr, w_dates = extract_tdcc_arrays(cache_dict[matched_key])
        if len(b_arr) > 0 and len(s_arr) > 0:
            b_list = [float(v) for v in b_arr]
            s_list = [float(v) for v in s_arr]
            if len(b_list) >= n_periods:
                return (
                    np.array(b_list[-n_periods:], dtype=float),
                    np.array(s_list[-n_periods:], dtype=float),
                    w_dates[-n_periods:] if w_dates else [],
                    True,
                )
            pad_len = n_periods - len(b_list)
            b_out = np.concatenate(
                [np.full(pad_len, b_list[0], dtype=float), np.array(b_list, dtype=float)]
            )
            s_out = np.concatenate(
                [np.full(pad_len, s_list[0], dtype=float), np.array(s_list, dtype=float)]
            )
            return b_out, s_out, w_dates, True

    seed_val = int(clean_id) if clean_id.isdigit() else 42
    rng = np.random.default_rng(seed_val)
    steps = rng.normal(0.0, 0.5, size=max(1, n_periods))
    big_h = np.clip(48.0 + np.cumsum(steps), 20.0, 85.0)
    sheep_h = np.clip(
        95.0 - big_h + rng.normal(0.0, 0.8, size=max(1, n_periods)), 15.0, 145.0
    )
    w_dates = (
        pd.date_range(end=datetime.today(), periods=max(1, n_periods), freq="W")
        .strftime("%Y-%m-%d")
        .tolist()
    )
    return big_h, sheep_h, w_dates, False


def _aggregate_minute_bars(df_src, group_size=2):
    if df_src is None or df_src.empty or group_size <= 1:
        return df_src
    rows = []
    for start_i in range(0, len(df_src), group_size):
        chunk = df_src.iloc[start_i : start_i + group_size]
        if chunk.empty:
            continue
        rows.append({
            "idx": chunk.index[0],
            "Open": float(chunk["Open"].iloc[0]),
            "High": float(chunk["High"].max()),
            "Low": float(chunk["Low"].min()),
            "Close": float(chunk["Close"].iloc[-1]),
            "Volume": float(chunk["Volume"].fillna(0).sum()),
        })
    return pd.DataFrame(rows).set_index("idx") if rows else pd.DataFrame()


def _period_yf_params(period_type, fetch_len):
    period_map = {
        "5分": ("5m", "60d", 1, fetch_len),
        "5分鐘": ("5m", "60d", 1, fetch_len),
        "10分": ("5m", "60d", 2, fetch_len * 2 + 4),
        "10分鐘": ("5m", "60d", 2, fetch_len * 2 + 4),
        "15分": ("15m", "60d", 1, fetch_len),
        "15分鐘": ("15m", "60d", 1, fetch_len),
        "30分": ("30m", "60d", 1, fetch_len),
        "30分鐘": ("30m", "60d", 1, fetch_len),
        "60分": ("60m", "120d", 1, fetch_len),
        "60分鐘": ("60m", "120d", 1, fetch_len),
        "週線": ("1wk", "max", 1, fetch_len),
        "周": ("1wk", "max", 1, fetch_len),
        "月線": ("1mo", "max", 1, fetch_len),
    }
    if period_type in period_map:
        return period_map[period_type]
    return ("1d", "5y" if fetch_len > 350 else "3y", 1, fetch_len)


@st.cache_data(ttl=300)
def fetch_raw_history(stock_id, period_type, fetch_len):
    df_yf = pd.DataFrame()
    tickers_to_try = (
        ["^TWII"] if stock_id == "99991" else [f"{stock_id}.TW", f"{stock_id}.TWO"]
    )
    yf_interval, yf_period, agg_factor, raw_fetch_len = _period_yf_params(
        period_type, fetch_len
    )

    for ticker in tickers_to_try:
        try:
            temp_df = yf.Ticker(ticker).history(
                period=yf_period, interval=yf_interval, auto_adjust=True
            )
            if not temp_df.empty and "Close" in temp_df.columns:
                df_yf = _normalize_yf_df_index(temp_df)
                break
        except Exception:
            continue

    if period_type in ["日線", "日"] and not df_yf.empty:
        try:
            temp_60m = _normalize_yf_df_index(
                yf.Ticker(tickers_to_try[0]).history(
                    period="5d", interval="60m", auto_adjust=True
                )
            )
            if not temp_60m.empty:
                latest_60m_date = temp_60m.index[-1].normalize()
                last_daily_date = df_yf.index[-1].normalize()
                if latest_60m_date > last_daily_date:
                    day_data = temp_60m[
                        temp_60m.index.normalize() == latest_60m_date
                    ]
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

    if df_yf.empty:
        return []

    df_yf = df_yf.dropna(subset=["Close"])
    df_src = df_yf.tail(raw_fetch_len).copy()
    df_k = (
        _aggregate_minute_bars(df_src, group_size=agg_factor).tail(fetch_len)
        if agg_factor > 1
        else df_src.tail(fetch_len).copy()
    )

    fallback_low, fallback_high = (
        (3000000, 5000000) if stock_id == "99991" else (10000, 50000)
    )
    if "Volume" not in df_k.columns or df_k["Volume"].fillna(0).sum() == 0:
        df_k["Volume"] = (
            np.random.randint(fallback_low, fallback_high, size=len(df_k)) * 1000
        )
    else:
        df_k["Volume"] = df_k["Volume"].fillna(0)
        if (df_k["Volume"] <= 0).all():
            df_k["Volume"] = (
                np.random.randint(fallback_low, fallback_high, size=len(df_k))
                * 1000
            )

    records = []
    date_fmt = "%Y/%m/%d %H:%M" if period_type in MINUTE_PERIOD_LABELS else "%Y/%m/%d"
    for idx, row in df_k.iterrows():
        o_val = float(row["Open"])
        h_val = float(row["High"])
        l_val = float(row["Low"])
        c_val = float(row["Close"])
        if o_val == c_val and h_val != l_val:
            o_val = l_val if c_val > l_val else h_val
        records.append({
            "date": idx.strftime(date_fmt),
            "open": o_val,
            "high": h_val,
            "low": l_val,
            "close": c_val,
            "vol": float(row["Volume"]) / 1000,
        })
    return records


def _norm_y_m_d(date_val):
    if not date_val:
        return ""
    try:
        if isinstance(date_val, (pd.Timestamp, datetime)):
            return pd.to_datetime(date_val).strftime("%Y/%m/%d")
    except Exception:
        pass
    s = str(date_val).strip().split(" ")[0].replace("-", "/")
    parts = s.split("/")
    if len(parts) == 3:
        try:
            y = int(parts[0])
            if y < 1911:
                y += 1911
            return f"{y:04d}/{int(parts[1]):02d}/{int(parts[2]):02d}"
        except Exception:
            pass
    return s


def _build_asof_table(events):
    rows = []
    for dt_v, num_v in events:
        nd = _norm_y_m_d(dt_v)
        if nd and num_v is not None and pd.notna(num_v):
            try:
                rows.append((nd, float(num_v)))
            except Exception:
                pass
    rows.sort(key=lambda item: item[0])
    return [item[0] for item in rows], [item[1] for item in rows]


def _lookup_asof_value(date_list, val_list, bar_date_str):
    if not date_list or not val_list:
        return None
    q_date = _norm_y_m_d(bar_date_str)
    chosen = None
    for d_item, v_item in zip(date_list, val_list):
        if d_item <= q_date:
            chosen = v_item
        else:
            break
    return chosen if chosen is not None else val_list[0]


def _extract_eps_row_from_df(df_stmt):
    if df_stmt is None or not isinstance(df_stmt, pd.DataFrame) or df_stmt.empty:
        return None
    candidate_names = [
        "Basic EPS",
        "Diluted EPS",
        "EPS",
        "BasicEPS",
        "DilutedEPS",
        "Earning Per Share",
        "Earnings Per Share",
    ]
    idx_lower_map = {str(i).strip().lower(): i for i in df_stmt.index}
    matched_row_key = None
    for cname in candidate_names:
        if cname in df_stmt.index:
            matched_row_key = cname
            break
        if cname.lower() in idx_lower_map:
            matched_row_key = idx_lower_map[cname.lower()]
            break
    if matched_row_key is None:
        for idx_item in df_stmt.index:
            s_idx = str(idx_item).lower()
            if "eps" in s_idx or "earning per share" in s_idx:
                matched_row_key = idx_item
                break
    if matched_row_key is None:
        return None

    row_s = pd.to_numeric(df_stmt.loc[matched_row_key], errors="coerce").dropna()
    if row_s.empty:
        return None
    try:
        row_s.index = pd.to_datetime(row_s.index)
        row_s = row_s.sort_index()
    except Exception:
        pass
    return row_s


def _fetch_tpex_pe_yield(stock_id):
    clean_id = str(stock_id).strip().replace(".0", "")
    if not clean_id or clean_id == "99991":
        return None, None
    code_4 = clean_id.zfill(4) if clean_id.isdigit() else clean_id
    urls = [
        "https://www.tpex.org.tw/openapi/v1/tpex_mainboard_peratio_analysis",
        "https://www.tpex.org.tw/web/stock/aftertrading/peratio_analysis/pera_result.php?l=zh-tw&o=json",
    ]
    pe_found, yld_found = None, None
    for url in urls:
        try:
            data = _fetch_json_url(url, {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)", "Accept": "application/json, text/plain, */*", "Referer": "https://www.tpex.org.tw/"})
            if isinstance(data, list):
                for item in data:
                    item_code = str(
                        item.get("SecuritiesCompanyCode")
                        or item.get("Code")
                        or item.get("股票代號")
                        or ""
                    ).strip()
                    if item_code in (clean_id, code_4):
                        pe_raw = (
                            item.get("PriceEarningRatio")
                            or item.get("PEratio")
                            or item.get("本益比")
                        )
                        yld_raw = None
                        for yk in [
                            "DividendYield",
                            "CashDividendYield",
                            "Yield",
                            "殖利率(%)",
                            "現金殖利率(%)",
                            "現金殖利率",
                            "殖利率",
                        ]:
                            if yk in item and item.get(yk) not in (None, "", "-", "--"):
                                yld_raw = item.get(yk)
                                break
                        if yld_raw is None:
                            for k_any, v_any in item.items():
                                if (
                                    "yield" in str(k_any).lower()
                                    or "殖利率" in str(k_any)
                                ) and v_any not in (None, "", "-", "--"):
                                    yld_raw = v_any
                                    break
                        pe_v = _parse_pos_float(pe_raw)
                        if pe_v is not None and pe_v <= 0:
                            pe_v = None
                        yld_v = _parse_pos_float(yld_raw)
                        if yld_v is not None and yld_v < 0:
                            yld_v = None
                        if pe_found is None and pe_v is not None:
                            pe_found = pe_v
                        if yld_found is None and yld_v is not None:
                            yld_found = yld_v
                        if pe_found is not None and yld_found is not None:
                            return pe_found, yld_found
            elif isinstance(data, dict) and data.get("aaData"):
                for r_item in data.get("aaData", []):
                    if not isinstance(r_item, list) or len(r_item) < 5:
                        continue
                    if str(r_item[0]).strip() in (clean_id, code_4):
                        pe_v = (
                            _parse_pos_float(r_item[2]) if len(r_item) > 2 else None
                        )
                        if pe_v is not None and pe_v <= 0:
                            pe_v = None
                        yld_v = None
                        for col_i in [5, 4, 6, 3]:
                            if len(r_item) > col_i:
                                cand_y = _parse_pos_float(r_item[col_i])
                                if cand_y is not None and 0 <= cand_y <= 50:
                                    yld_v = cand_y
                                    break
                        if pe_found is None and pe_v is not None:
                            pe_found = pe_v
                        if yld_found is None and yld_v is not None:
                            yld_found = yld_v
                        if pe_found is not None and yld_found is not None:
                            return pe_found, yld_found
        except Exception:
            continue
    return pe_found, yld_found


def _fetch_twse_pe_yield(stock_id):
    clean_id = str(stock_id).strip().replace(".0", "")
    if not clean_id or clean_id == "99991":
        return None, None
    code_4 = clean_id.zfill(4) if clean_id.isdigit() else clean_id
    urls = [
        "https://openapi.twse.com.tw/v1/exchangeReport/BWIBBU_ALL",
        "https://www.twse.com.tw/rwd/zh/afterTrading/BWIBBU_d?response=json",
    ]
    for url in urls:
        try:
            data = _fetch_json_url(
                url, {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
            )
            if isinstance(data, list):
                for item in data:
                    if str(item.get("Code", "")).strip() in (clean_id, code_4):
                        pe_v = _parse_pos_float(item.get("PEratio"))
                        if pe_v is not None and pe_v <= 0:
                            pe_v = None
                        yld_v = _parse_pos_float(item.get("DividendYield"))
                        if yld_v is not None and yld_v < 0:
                            yld_v = None
                        if pe_v is not None or yld_v is not None:
                            return pe_v, yld_v
            elif isinstance(data, dict) and data.get("data"):
                fields = [str(f).strip() for f in data.get("fields", [])]
                code_idx = fields.index("證券代號") if "證券代號" in fields else 0
                pe_idx = fields.index("本益比") if "本益比" in fields else -1
                yld_idx = fields.index("殖利率(%)") if "殖利率(%)" in fields else -1
                for r_item in data.get("data", []):
                    if not isinstance(r_item, list) or len(r_item) <= code_idx:
                        continue
                    if str(r_item[code_idx]).strip() in (clean_id, code_4):
                        pe_v = (
                            _parse_pos_float(r_item[pe_idx])
                            if pe_idx >= 0 and len(r_item) > pe_idx
                            else None
                        )
                        if pe_v is not None and pe_v <= 0:
                            pe_v = None
                        yld_v = (
                            _parse_pos_float(r_item[yld_idx])
                            if yld_idx >= 0 and len(r_item) > yld_idx
                            else None
                        )
                        if yld_v is not None and yld_v < 0:
                            yld_v = None
                        if pe_v is not None or yld_v is not None:
                            return pe_v, yld_v
        except Exception:
            continue
    return None, None


@st.cache_data(ttl=1800)
def fetch_stock_fundamentals(stock_id):
    result = {
        "pe_str": "--",
        "eps_str": "--",
        "eps_4q_str": "--",
        "yield_str": "--",
        "q_eps_dates": [],
        "q_eps_vals": [],
        "eps_4q_dates": [],
        "eps_4q_vals": [],
        "cash_div_dates": [],
        "cash_div_vals": [],
        "latest_cash_div": None,
    }
    clean_id = str(stock_id).strip().replace(".0", "")
    if not clean_id or clean_id == "99991":
        return result

    base_code = clean_id.zfill(4) if clean_id.isdigit() else clean_id
    tickers = [
        f"{cand}{suf}"
        for cand in [clean_id, base_code]
        for suf in [".TW", ".TWO"]
    ]
    tickers = list(dict.fromkeys(tickers))

    info, last_price, q_inc, a_inc, divs = {}, None, None, None, None
    for tk in tickers:
        try:
            t = yf.Ticker(tk)
            try:
                tmp_info = t.info or {}
            except Exception:
                tmp_info = {}
            tmp_price = (
                tmp_info.get("regularMarketPrice")
                or tmp_info.get("currentPrice")
                or tmp_info.get("previousClose")
            )
            try:
                tmp_q_inc = t.quarterly_income_stmt
            except Exception:
                tmp_q_inc = None
            try:
                tmp_a_inc = t.income_stmt
            except Exception:
                tmp_a_inc = None
            try:
                tmp_divs = t.dividends
            except Exception:
                tmp_divs = None

            if tmp_price is None:
                try:
                    h_tmp = t.history(period="5d", interval="1d", auto_adjust=True)
                    if (
                        h_tmp is not None
                        and not h_tmp.empty
                        and "Close" in h_tmp.columns
                    ):
                        tmp_price = float(h_tmp["Close"].dropna().iloc[-1])
                except Exception:
                    pass

            if (
                bool(tmp_info)
                or (tmp_q_inc is not None and not tmp_q_inc.empty)
                or (tmp_divs is not None and len(tmp_divs) > 0)
                or (tmp_price is not None)
            ):
                info, last_price, q_inc, a_inc, divs = (
                    tmp_info,
                    tmp_price,
                    tmp_q_inc,
                    tmp_a_inc,
                    tmp_divs,
                )
                break
        except Exception:
            continue

    single_eps, eps_4q = None, None
    q_eps_events, eps_4q_events = [], []

    q_row = _extract_eps_row_from_df(q_inc)
    if q_row is not None and not q_row.empty:
        vals = [float(v) for v in q_row.tolist()]
        dt_idx = list(q_row.index)
        single_eps = float(vals[-1])
        eps_4q = float(sum(vals[-4:])) if len(vals) >= 4 else float(sum(vals))
        for i_q, (q_dt, q_val) in enumerate(zip(dt_idx, vals)):
            try:
                eff_dt = (pd.to_datetime(q_dt) + pd.Timedelta(days=45)).strftime(
                    "%Y/%m/%d"
                )
            except Exception:
                eff_dt = _norm_y_m_d(q_dt)
            q_eps_events.append((eff_dt, float(q_val)))
            win_q = vals[max(0, i_q - 3) : i_q + 1]
            eps_4q_events.append((eff_dt, float(sum(win_q))))

    if single_eps is None or eps_4q is None:
        a_row = _extract_eps_row_from_df(a_inc)
        if a_row is not None and not a_row.empty:
            a_vals = [float(v) for v in a_row.tolist()]
            a_dt_idx = list(a_row.index)
            if eps_4q is None:
                eps_4q = float(a_vals[-1])
            if single_eps is None:
                single_eps = float(a_vals[-1]) / 4.0
            for a_dt, a_val in zip(a_dt_idx, a_vals):
                try:
                    eff_dt = (pd.to_datetime(a_dt) + pd.Timedelta(days=60)).strftime(
                        "%Y/%m/%d"
                    )
                except Exception:
                    eff_dt = _norm_y_m_d(a_dt)
                if not eps_4q_events:
                    eps_4q_events.append((eff_dt, float(a_val)))
                if not q_eps_events:
                    q_eps_events.append((eff_dt, float(a_val) / 4.0))

    if single_eps is None:
        for k_eps in [
            "epsCurrentQuarter",
            "epsForward",
            "trailingEps",
            "epsTrailingTwelveMonths",
        ]:
            v_raw = info.get(k_eps)
            if v_raw is not None and pd.notna(v_raw):
                try:
                    f_v = float(v_raw)
                    single_eps = (
                        f_v / 4.0
                        if k_eps in ["trailingEps", "epsTrailingTwelveMonths"]
                        else f_v
                    )
                    break
                except Exception:
                    pass

    if eps_4q is None:
        for k_ttm in ["trailingEps", "epsTrailingTwelveMonths", "forwardEps"]:
            v_raw = info.get(k_ttm)
            if v_raw is not None and pd.notna(v_raw):
                try:
                    eps_4q = float(v_raw)
                    break
                except Exception:
                    pass

    cash_div_events, annual_cash_div = [], None
    if divs is not None and len(divs) > 0:
        try:
            div_s = pd.to_numeric(divs, errors="coerce").dropna()
            if not div_s.empty:
                div_s.index = pd.to_datetime(div_s.index)
                if hasattr(div_s.index, "tz") and div_s.index.tz is not None:
                    div_s.index = div_s.index.tz_convert(
                        "Asia/Taipei"
                    ).tz_localize(None)
                div_s = div_s.sort_index()
                for d_idx in div_s.index:
                    d_norm = pd.to_datetime(d_idx).normalize()
                    win_start = d_norm - pd.Timedelta(days=365)
                    rolling_cash = float(
                        div_s[
                            (div_s.index > win_start) & (div_s.index <= d_idx)
                        ].sum()
                    )
                    cash_div_events.append((d_norm.strftime("%Y/%m/%d"), rolling_cash))
                if cash_div_events:
                    annual_cash_div = float(cash_div_events[-1][1])
                    if annual_cash_div <= 0:
                        last_div_dt = div_s.index[-1]
                        last_win_start = last_div_dt - pd.Timedelta(days=365)
                        last_yr_sum = float(
                            div_s[
                                (div_s.index > last_win_start)
                                & (div_s.index <= last_div_dt)
                            ].sum()
                        )
                        if last_yr_sum > 0:
                            annual_cash_div = last_yr_sum
                            cash_div_events[-1] = (
                                datetime.today().strftime("%Y/%m/%d"),
                                last_yr_sum,
                            )
        except Exception:
            pass

    if annual_cash_div is None:
        for k_div in ["dividendRate", "trailingAnnualDividendRate"]:
            v_raw = info.get(k_div)
            if v_raw is not None and pd.notna(v_raw):
                try:
                    annual_cash_div = float(v_raw)
                    break
                except Exception:
                    pass

    if annual_cash_div is None and last_price is not None and float(last_price) > 0:
        raw_yield = info.get("dividendYield") or info.get(
            "trailingAnnualDividendYield"
        )
        if raw_yield is not None and pd.notna(raw_yield):
            try:
                y_f = float(raw_yield)
                y_pct = y_f * 100.0 if y_f <= 0.5 else y_f
                annual_cash_div = (y_pct / 100.0) * float(last_price)
            except Exception:
                pass

    twse_pe, twse_yield = _fetch_twse_pe_yield(clean_id)
    if twse_pe is None or twse_yield is None:
        tpex_pe, tpex_yield = _fetch_tpex_pe_yield(clean_id)
        if twse_pe is None:
            twse_pe = tpex_pe
        if twse_yield is None:
            twse_yield = tpex_yield

    if last_price is None or float(last_price) <= 0:
        try:
            hist_df = fetch_raw_history(clean_id, "日線", 5)
            if hist_df:
                last_price = float(hist_df[-1]["close"])
        except Exception:
            pass

    if (
        eps_4q is None
        and twse_pe is not None
        and twse_pe > 0
        and last_price is not None
        and float(last_price) > 0
    ):
        eps_4q = float(last_price) / float(twse_pe)
    if single_eps is None and eps_4q is not None:
        single_eps = float(eps_4q) / 4.0
    if (
        annual_cash_div is None
        and twse_yield is not None
        and twse_yield >= 0
        and last_price is not None
        and float(last_price) > 0
    ):
        annual_cash_div = (float(twse_yield) / 100.0) * float(last_price)

    today_str = datetime.today().strftime("%Y/%m/%d")
    if single_eps is not None and not q_eps_events:
        q_eps_events.append((today_str, float(single_eps)))
    if eps_4q is not None and not eps_4q_events:
        eps_4q_events.append((today_str, float(eps_4q)))
    if annual_cash_div is not None and not cash_div_events:
        cash_div_events.append((today_str, float(annual_cash_div)))

    pe_val = None
    if last_price is not None and eps_4q is not None and float(eps_4q) > 0:
        try:
            pe_val = float(last_price) / float(eps_4q)
        except Exception:
            pe_val = None
    if pe_val is None and twse_pe is not None and twse_pe > 0:
        pe_val = float(twse_pe)
    if pe_val is None:
        for k_pe in ["trailingPE", "forwardPE"]:
            raw_pe = info.get(k_pe)
            if raw_pe is not None and pd.notna(raw_pe):
                try:
                    v = float(raw_pe)
                    if v > 0:
                        pe_val = v
                        break
                except Exception:
                    pass

    yield_pct = None
    if annual_cash_div is not None and last_price is not None and float(last_price) > 0:
        try:
            yield_pct = (float(annual_cash_div) / float(last_price)) * 100.0
        except Exception:
            yield_pct = None
    if yield_pct is None and twse_yield is not None and twse_yield >= 0:
        yield_pct = float(twse_yield)
    if yield_pct is None:
        for k_y in ["dividendYield", "trailingAnnualDividendYield"]:
            raw_yield = info.get(k_y)
            if raw_yield is not None and pd.notna(raw_yield):
                try:
                    y_f = float(raw_yield)
                    yield_pct = y_f * 100.0 if y_f <= 0.5 else y_f
                    break
                except Exception:
                    pass

    if eps_4q is None:
        for k_alt in ["trailingEps", "forwardEps"]:
            v_alt = _parse_pos_float(info.get(k_alt))
            if v_alt is not None and v_alt > 0:
                eps_4q = v_alt
                break
    if single_eps is None and eps_4q is not None:
        single_eps = float(eps_4q) / 4.0
    if pe_val is None and last_price is not None and eps_4q is not None and float(eps_4q) > 0:
        pe_val = float(last_price) / float(eps_4q)
    if yield_pct is None and annual_cash_div is not None and last_price is not None and float(last_price) > 0:
        yield_pct = (float(annual_cash_div) / float(last_price)) * 100.0

    if pe_val is not None:
        result["pe_str"] = f"{pe_val:.2f}倍"
    if single_eps is not None:
        result["eps_str"] = f"{single_eps:.2f}元"
    if eps_4q is not None:
        result["eps_4q_str"] = f"{eps_4q:.2f}元"
    if yield_pct is not None:
        result["yield_str"] = f"{yield_pct:.2f}%"

    q_d, q_v = _build_asof_table(q_eps_events)
    e4_d, e4_v = _build_asof_table(eps_4q_events)
    cd_d, cd_v = _build_asof_table(cash_div_events)

    result.update({
        "q_eps_dates": q_d,
        "q_eps_vals": q_v,
        "eps_4q_dates": e4_d,
        "eps_4q_vals": e4_v,
        "cash_div_dates": cd_d,
        "cash_div_vals": cd_v,
        "latest_cash_div": annual_cash_div,
    })
    return result


def build_bar_fundamental_snap(fund_data, bar_date_str, bar_close_val):
    q_eps_v = _lookup_asof_value(
        fund_data.get("q_eps_dates", []),
        fund_data.get("q_eps_vals", []),
        bar_date_str,
    )
    eps_4q_v = _lookup_asof_value(
        fund_data.get("eps_4q_dates", []),
        fund_data.get("eps_4q_vals", []),
        bar_date_str,
    )
    cash_div_v = _lookup_asof_value(
        fund_data.get("cash_div_dates", []),
        fund_data.get("cash_div_vals", []),
        bar_date_str,
    )
    if cash_div_v is None:
        cash_div_v = fund_data.get("latest_cash_div")

    eps_str = (
        f"{q_eps_v:.2f}元"
        if q_eps_v is not None
        else fund_data.get("eps_str", "--")
    )
    eps_4q_str = (
        f"{eps_4q_v:.2f}元"
        if eps_4q_v is not None
        else fund_data.get("eps_4q_str", "--")
    )

    denom_eps = eps_4q_v if eps_4q_v is not None else q_eps_v
    if bar_close_val and bar_close_val > 0 and denom_eps is not None and denom_eps > 0:
        pe_str = f"{(float(bar_close_val) / float(denom_eps)):.2f}倍"
    else:
        pe_str = fund_data.get("pe_str", "--")

    if (
        bar_close_val
        and bar_close_val > 0
        and cash_div_v is not None
        and float(cash_div_v) >= 0
    ):
        yield_str = f"{(float(cash_div_v) / float(bar_close_val)) * 100.0:.2f}%"
    else:
        yield_str = fund_data.get("yield_str", "--")

    return {
        "pe_str": pe_str,
        "eps_str": eps_str,
        "eps_4q_str": eps_4q_str,
        "yield_str": yield_str,
    }


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
        df_full[f"ma_{period}"] = (
            s_close.rolling(window=eff_win, min_periods=1).mean().ffill().bfill()
        )

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

    df_full["w_r"] = (
        (high_max9 - s_close) / (high_max9 - low_min9 + 1e-8) * -100
    )

    df_full["qt"] = s_close.diff().abs().rolling(5, min_periods=1).mean().fillna(0)
    df_full["vol_ma5"] = (
        df_full["vol"].rolling(window=5, min_periods=1).mean().bfill()
    )
    df_full["vol_ma20"] = (
        df_full["vol"].rolling(window=20, min_periods=1).mean().bfill()
    )
    df_full["long_trend"] = (ema15 / ema30 - 1) * 100 > 0

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
    big_holder, sheep_holder, _, _ = get_holder_series_for_stock(
        stock_id, len(df_show), cache_dict=cache_dict
    )

    return df_show, big_holder, sheep_holder, cur_vol, cur_20ma, v_ratio


def _trend_token(label, val_txt, is_up, label_color="#FFFF00", up_color="#FF3333", dn_color="#00E64D"):
    arrow = "▲" if is_up else "▼"
    col = up_color if is_up else dn_color
    return [
        {"text": label, "color": label_color},
        {"text": f"{val_txt}{arrow}", "color": col},
    ]


def build_bar_analysis_snapshot(
    df,
    big_holder,
    sheep_holder,
    idx_r,
    selected_indicator,
    period_label,
    stock_id="",
):
    r = df.iloc[idx_r]
    c_open = float(r["open"])
    c_close = float(r["close"])
    c_high = float(r["high"])
    c_low = float(r["low"])
    c_vol = float(r["vol"])
    c_date = str(r["date"])

    prev_r = df.iloc[idx_r - 1] if idx_r > 0 else r
    p_open = float(prev_r["open"])
    p_high = float(prev_r["high"])
    p_low = float(prev_r["low"])
    p_close = float(prev_r["close"])
    p_vol = float(prev_r["vol"])

    ma5_v = float(r["ma_5"]) if "ma_5" in df.columns and pd.notna(r["ma_5"]) else 0.0
    ma20_v = float(r["ma_20"]) if "ma_20" in df.columns and pd.notna(r["ma_20"]) else 0.0
    ma60_v = float(r["ma_60"]) if "ma_60" in df.columns and pd.notna(r["ma_60"]) else 0.0

    if ma5_v > ma20_v > ma60_v:
        ma_status = "多頭排列"
    elif ma5_v < ma20_v < ma60_v:
        ma_status = "空頭排列"
    else:
        ma_status = "均線交錯"
    ma_cls = "t-val-red" if ma5_v > ma20_v else "t-val-green"

    bar_diff = c_close - p_close
    bar_chg_pct = (bar_diff / p_close * 100.0) if p_close > 0 else 0.0
    bar_amp_pct = ((c_high - c_low) / p_close * 100.0) if p_close > 0 else 0.0
    bar_chg_str = f"{bar_diff:+.2f} ({bar_chg_pct:+.2f}%)"
    bar_chg_cls = "t-val-red" if bar_diff >= 0 else "t-val-green"
    bar_amp_str = f"{bar_amp_pct:+.2f}%"

    b_slice = big_holder[-len(df) :] if len(big_holder) >= len(df) else big_holder
    s_slice = sheep_holder[-len(df) :] if len(sheep_holder) >= len(df) else sheep_holder
    b_val = float(b_slice[idx_r]) if len(b_slice) > idx_r else 0.0
    s_val = float(s_slice[idx_r]) if len(s_slice) > idx_r else 0.0

    k_v = float(r["kdj_k"]) if "kdj_k" in df.columns else 0.0
    d_v = float(r["kdj_d"]) if "kdj_d" in df.columns else 0.0
    j_v = float(r["kdj_j"]) if "kdj_j" in df.columns else 0.0
    kd_diff = k_v - d_v

    prev_k = float(df["kdj_k"].iloc[idx_r - 1]) if idx_r > 0 else k_v
    prev_d = float(df["kdj_d"].iloc[idx_r - 1]) if idx_r > 0 else d_v
    is_gc = prev_k <= prev_d and k_v > d_v
    is_dc = prev_k >= prev_d and k_v < d_v

    kdj_sig, kdj_cls = "中立觀望", "t-val-white"
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

    is_buy_s = bool(r["is_buy_signal"]) if "is_buy_signal" in df.columns else False
    is_sell_s = bool(r["is_sell_signal"]) if "is_sell_signal" in df.columns else False
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

    prev_vol = float(df["vol"].iloc[idx_r - 1]) if idx_r > 0 else c_vol
    prev_v5 = float(df["vol_ma5"].iloc[idx_r - 1]) if idx_r > 0 else vol_ma5_v
    prev_v20 = float(df["vol_ma20"].iloc[idx_r - 1]) if idx_r > 0 else vol_ma20_v
    prev_vr5 = prev_vol / prev_v5 if (idx_r > 0 and prev_v5 > 0) else v_ratio_5
    prev_vr20 = prev_vol / prev_v20 if (idx_r > 0 and prev_v20 > 0) else v_ratio_20

    vol_tokens = (
        [{"text": "成交量::", "color": "#FFFFFF"}]
        + _trend_token("", f"{int(c_vol)}", c_vol >= prev_vol, "#FFFFFF")
        + _trend_token("5日::", f"{int(vol_ma5_v)}", vol_ma5_v >= prev_v5, "#FFFF00")
        + _trend_token("值5::", f"{v_ratio_5:.2f}", v_ratio_5 >= prev_vr5, "#FFFF00")
        + _trend_token("20日::", f"{int(vol_ma20_v)}", vol_ma20_v >= prev_v20, "#FF9900")
        + _trend_token("20日值::", f"{v_ratio_20:.2f}", v_ratio_20 >= prev_vr20, "#FF9900")
    )

    kdj_tokens = [
        {"text": "KD(9,3,3)", "color": "#FFFFFF"},
        {"text": "K::", "color": "#FF00FF"},
        {"text": f"{k_v:.2f}", "color": "#FF00FF"},
        {"text": "D::", "color": "#00FFFF"},
        {"text": f"{d_v:.2f}", "color": "#00FFFF"},
        {"text": "J::", "color": "#FFFFFF"},
        {"text": f"{j_v:.2f}", "color": "#FFFFFF"},
        {"text": "乖離::", "color": "#FFFF00"},
        {"text": f"{kd_diff:.2f}{'▲' if kd_diff >= 0 else '▼'}", "color": "#FFFF00"},
    ]

    r6_v = float(r["rsi_6"])
    r12_v = float(r["rsi_12"])
    rdiff_v = float(r["rsi_diff"])
    rsi_tokens = [
        {"text": "RSI(6,12)", "color": "#FFFFFF"},
        {"text": "RSI6::", "color": "#FF00FF"},
        {"text": f"{r6_v:.2f}", "color": "#FF00FF"},
        {"text": "RSI12::", "color": "#00FFFF"},
        {"text": f"{r12_v:.2f}", "color": "#00FF00"},
        {"text": "差值::", "color": "#FFFF00"},
        {
            "text": f"{rdiff_v:.2f}{'▲' if rdiff_v >= 0 else '▼'}",
            "color": "#FFFF00",
        },
    ]

    wr_v = float(r["w_r"])
    prev_wr = float(df["w_r"].iloc[idx_r - 1]) if idx_r > 0 else wr_v
    wr_tokens = _trend_token("W%::", f"{wr_v:.2f}%", wr_v >= prev_wr, "#FFFFFF")

    dif_v = float(r["macd_dif"])
    dem_v = float(r["macd_dem"])
    osc_v = float(r["macd_osc"])
    prev_dif = float(df["macd_dif"].iloc[idx_r - 1]) if idx_r > 0 else dif_v
    prev_dem = float(df["macd_dem"].iloc[idx_r - 1]) if idx_r > 0 else dem_v
    prev_osc = float(df["macd_osc"].iloc[idx_r - 1]) if idx_r > 0 else osc_v
    osc_col = "#FF3333" if osc_v >= 0 else "#00E64D"
    macd_tokens = [
        {"text": "MACD(長)", "color": "#FFFFFF"},
        {"text": "DIF::", "color": "#FF00FF"},
        {"text": f"{dif_v:.2f}{'▲' if dif_v >= prev_dif else '▼'}", "color": "#FF00FF"},
        {"text": "DEA::", "color": "#00FFFF"},
        {"text": f"{dem_v:.2f}{'▲' if dem_v >= prev_dem else '▼'}", "color": "#00FFFF"},
        {"text": "MACD::", "color": osc_col},
        {"text": f"{osc_v:.2f}{'▲' if osc_v >= prev_osc else '▼'}", "color": osc_col},
    ]

    ind_tokens, sub2_tokens, sub3_tokens = [], [], []
    if selected_indicator == "組合":
        ind_tokens, sub2_tokens, sub3_tokens = kdj_tokens, macd_tokens, vol_tokens
    elif selected_indicator == "組合1":
        ind_tokens, sub2_tokens, sub3_tokens = kdj_tokens, rsi_tokens, wr_tokens
    elif selected_indicator == "BIAS":
        bias_v = float(r["bias_val"])
        prev_bias = float(df["bias_val"].iloc[idx_r - 1]) if idx_r > 0 else bias_v
        ind_tokens = [
            {"text": "BIAS(60)::", "color": "#FFFFFF"},
            {
                "text": f"{bias_v:.2f}%{'▲' if bias_v >= prev_bias else '▼'}",
                "color": "#FF3333" if bias_v >= 0 else "#00E64D",
            },
        ]
    elif selected_indicator == "QT":
        qt_v = float(r["qt"])
        prev_qt = float(df["qt"].iloc[idx_r - 1]) if idx_r > 0 else qt_v
        ind_tokens = [
            {"text": "QT::", "color": "#FFFFFF"},
            {
                "text": f"{qt_v:.2f}{'▲' if qt_v >= prev_qt else '▼'}",
                "color": "#FF3333" if qt_v >= prev_qt else "#00E64D",
            },
        ]
    elif selected_indicator == "集保":
        ind_tokens = [
            {"text": "大戶::", "color": "#FFFFFF"},
            {"text": f"{b_val:.1f}%", "color": "#FF3333"},
            {"text": "羊群::", "color": "#FFFFFF"},
            {"text": f"{s_val:.1f}%", "color": "#00E64D"},
        ]
    elif selected_indicator == "波段":
        bdif_v = float(r["band_macd_dif"])
        bdem_v = float(r["band_macd_dem"])
        bosc_v = float(r["band_macd_osc"])
        bbias_rev_v = float(r["band_bias_val_rev"])
        mtm_v = float(r["mtm_val"])
        mtm_avg_v = float(r["mtm_ma1"])
        ind_tokens = [
            {"text": "波段 MACD(5,10,5)", "color": "#FFFFFF"},
            {"text": "DIF::", "color": "#FFFF00"},
            {"text": f"{bdif_v:.2f}", "color": "#FFFF00"},
            {"text": "DEA::", "color": "#FF3333"},
            {"text": f"{bdem_v:.2f}", "color": "#FF3333"},
            {"text": "OSC::", "color": "#FF3333" if bosc_v >= 0 else "#00E64D"},
            {"text": f"{bosc_v:.2f}", "color": "#FF3333" if bosc_v >= 0 else "#00E64D"},
        ]
        sub2_tokens = [
            {"text": "波段 BIAS(20,反向)::", "color": "#FFFFFF"},
            {
                "text": f"{bbias_rev_v:.2f}%",
                "color": "#FF3333" if bbias_rev_v >= 0 else "#00E64D",
            },
        ]
        sub3_tokens = [
            {"text": "波段 MTM(10,1)", "color": "#FFFFFF"},
            {"text": "MTM::", "color": "#FFFF00"},
            {"text": f"{mtm_v:.2f}", "color": "#FFFF00"},
            {"text": "Avg::", "color": "#00FF66"},
            {"text": f"{mtm_avg_v:.2f}", "color": "#00FF66"},
        ]

    header_tokens = [
        {"text": f"{c_date}", "color": "#FFFFFF"},
        {"text": "開:", "color": "#FFFFFF"},
        {
            "text": f"{c_open:.2f}{'▲' if c_open >= p_open else '▼'}",
            "color": "#FF3333" if c_open >= p_open else "#00E64D",
        },
        {"text": "高:", "color": "#FFFFFF"},
        {
            "text": f"{c_high:.2f}{'▲' if c_high >= p_high else '▼'}",
            "color": "#FF3333" if c_high >= p_high else "#00E64D",
        },
        {"text": "低:", "color": "#FFFFFF"},
        {
            "text": f"{c_low:.2f}{'▲' if c_low >= p_low else '▼'}",
            "color": "#FF3333" if c_low >= p_low else "#00E64D",
        },
        {"text": "收:", "color": "#FFFFFF"},
        {
            "text": f"{c_close:.2f}{'▲' if c_close >= p_close else '▼'}",
            "color": "#FF3333" if c_close >= p_close else "#00E64D",
        },
        {"text": "量:", "color": "#FFFFFF"},
        {
            "text": (
                f"{int(c_vol):,}{'張' if stock_id != '99991' else ''}"
                f"{'▲' if c_vol >= p_vol else '▼'}"
            ),
            "color": "#FF3333" if c_vol >= p_vol else "#00E64D",
        },
    ]

    if stock_id == "99991":
        chg_pts = c_close - p_close
        chg_pct = (chg_pts / p_close * 100) if p_close > 0 else 0.0
        amp_pct = ((c_high - c_low) / p_close * 100) if p_close > 0 else 0.0
        chg_is_up = chg_pts >= 0
        header_tokens.extend([
            {"text": f"振:{amp_pct:.2f}%", "color": "#FFFF00"},
            {
                "text": (
                    f"{'漲' if chg_is_up else '跌'}({abs(chg_pts):.2f}){chg_pct:.2f}%"
                    f"{'▲' if chg_is_up else '▼'}"
                ),
                "color": "#FF3333" if chg_is_up else "#00E64D",
            },
        ])

    return {
        "header_text": (
            f"{c_date}  開:{c_open:.2f} 高:{c_high:.2f} 低:{c_low:.2f}"
            f" 收:{c_close:.2f} 量:{int(c_vol):,}"
        ),
        "header_tokens": header_tokens,
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
        "bar_chg_str": bar_chg_str,
        "bar_chg_cls": bar_chg_cls,
        "bar_amp_str": bar_amp_str,
        "big_str": f"{b_val:.1f}%",
        "sheep_str": f"{s_val:.1f}%",
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


# ---------------------------------------------------------
# 6. 策略選股與籌碼過濾輔助函式
# ---------------------------------------------------------
def _try_read_csv_with_data():
    if not os.path.exists(SIGNAL_CSV_PATH):
        return None
    for enc in ["utf-8-sig", "utf-8", "cp950", "big5"]:
        try:
            df_tmp = pd.read_csv(SIGNAL_CSV_PATH, dtype=str, encoding=enc)
            if df_tmp is None or df_tmp.empty:
                continue
            norm_m = {_norm_col(c): c for c in df_tmp.columns}
            c1w_k = next(
                (
                    norm_m[k]
                    for k in norm_m
                    if "近1週大戶變動" in k or "近1週大戶變化" in k
                ),
                None,
            )
            if not c1w_k:
                continue
            valid_nums = pd.to_numeric(
                df_tmp[c1w_k]
                .astype(str)
                .str.replace("%", "")
                .str.replace("+", "")
                .str.strip(),
                errors="coerce",
            ).dropna()
            if not valid_nums.empty:
                return df_tmp
        except Exception:
            continue
    return None


def _filter_chip_candidates(is_golden, th_val):
    results_list = []
    df_valid_csv = _try_read_csv_with_data()

    if df_valid_csv is not None:
        norm_map = {_norm_col(c): c for c in df_valid_csv.columns}
        code_c = next(
            (norm_map[k] for k in norm_map if "代號" in k or "代碼" in k), None
        )
        name_c = next((norm_map[k] for k in norm_map if "名稱" in k), None)
        sig_c = next((norm_map[k] for k in norm_map if "訊號" in k), None)
        c1w_big_c = next(
            (
                norm_map[k]
                for k in norm_map
                if "近1週大戶變動" in k or "近1週大戶變化" in k
            ),
            None,
        )
        c1w_shp_c = next(
            (
                norm_map[k]
                for k in norm_map
                if "近1週散戶變動" in k or "近1週散戶變化" in k
            ),
            None,
        )
        c4w_big_c = next(
            (
                norm_map[k]
                for k in norm_map
                if "近4週大戶變動" in k or "近4週大戶變化" in k
            ),
            None,
        )
        big_c = next((norm_map[k] for k in norm_map if "最新大戶" in k), None)
        shp_c = next((norm_map[k] for k in norm_map if "最新散戶" in k), None)
        dt_c = next(
            (norm_map[k] for k in norm_map if "最新日期" in k or "更新日期" in k),
            None,
        )

        for _, r in df_valid_csv.iterrows():
            s_id = _clean_code(r.get(code_c, ""))
            if not s_id or s_id == "99991" or s_id.lower() == "nan":
                continue
            s_sig = str(r.get(sig_c, "")).strip() if sig_c else ""
            if "無資料" in s_sig:
                continue
            try:
                v_1w_big = float(
                    str(r.get(c1w_big_c, ""))
                    .replace("%", "")
                    .replace("+", "")
                    .strip()
                )
            except Exception:
                continue
            v_1w_shp = (
                float(
                    str(r.get(c1w_shp_c, "0"))
                    .replace("%", "")
                    .replace("+", "")
                    .strip()
                )
                if c1w_shp_c
                else 0.0
            )
            v_4w_big = (
                float(
                    str(r.get(c4w_big_c, "0"))
                    .replace("%", "")
                    .replace("+", "")
                    .strip()
                )
                if c4w_big_c
                else 0.0
            )
            v_big = (
                float(str(r.get(big_c, "0")).replace("%", "").strip())
                if big_c
                else 0.0
            )
            v_shp = (
                float(str(r.get(shp_c, "0")).replace("%", "").strip())
                if shp_c
                else 0.0
            )
            cond = (v_1w_big >= th_val) if is_golden else (v_1w_big <= -abs(th_val))
            if cond:
                results_list.append({
                    "代碼": s_id,
                    "名稱": str(r.get(name_c, "")).strip() if name_c else "",
                    "訊號": s_sig
                    if s_sig
                    else ("大戶增" if v_1w_big > 0 else "大戶減"),
                    "近1週大戶變動": round(v_1w_big, 2),
                    "近1週散戶變動": round(v_1w_shp, 2),
                    "近4週大戶變動": round(v_4w_big, 2),
                    "最新大戶%": round(v_big, 2),
                    "最新散戶%": round(v_shp, 2),
                    "日期": str(r.get(dt_c, "")).strip() if dt_c else "",
                    "神秘金字塔": _pyramid_link(s_id),
                })
    else:
        cache_dict = load_local_cache_cached()
        for _, row in stock_df.iterrows():
            s_id = _clean_code(row["代碼"])
            s_name = str(row["名稱"]).strip()
            if s_id == "99991":
                continue
            big_h, sheep_h, w_dates, _ = get_holder_series_for_stock(
                s_id, 10, cache_dict=cache_dict
            )
            if len(big_h) < 2:
                continue
            v_big = float(big_h[-1])
            v_shp = float(sheep_h[-1]) if len(sheep_h) > 0 else 0.0
            v_1w_big = float(big_h[-1]) - float(big_h[-2])
            v_1w_shp = (
                float(sheep_h[-1]) - float(sheep_h[-2])
                if len(sheep_h) >= 2
                else 0.0
            )
            v_4w_big = (
                float(big_h[-1]) - float(big_h[-5])
                if len(big_h) >= 5
                else v_1w_big
            )
            cond = (v_1w_big >= th_val) if is_golden else (v_1w_big <= -abs(th_val))
            if cond:
                results_list.append({
                    "代碼": s_id,
                    "名稱": s_name,
                    "訊號": "大戶增(快取)" if v_1w_big > 0 else "大戶減(快取)",
                    "近1週大戶變動": round(v_1w_big, 2),
                    "近1週散戶變動": round(v_1w_shp, 2),
                    "近4週大戶變動": round(v_4w_big, 2),
                    "最新大戶%": round(v_big, 2),
                    "最新散戶%": round(v_shp, 2),
                    "日期": w_dates[-1] if w_dates else "",
                    "神秘金字塔": _pyramid_link(s_id),
                })

    results_list.sort(key=lambda x: x["近1週大戶變動"], reverse=is_golden)
    return results_list[:10]


# ---------------------------------------------------------
# 7. Session State 初始化
# ---------------------------------------------------------
DEFAULTS = {
    "selected_index": 0,
    "stock_select_version": 0,
    "selected_synth_strat": "主力底部吃貨",
    "app_mode_state": "📈 個股籌碼圖表",
    "k_bars_count": 250,
    "screened_results": [],
    "default_indicator_override": None,
    "ruler_mode_active": False,
    "chip_1w_threshold_val": 0.00,
    "ma_active_map": {
        "5": False,
        "10": False,
        "20": False,
        "35": False,
        "60": True,
        "120": False,
        "200": False,
        "分割": False,
    },
}
for _k, _v in DEFAULTS.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v.copy() if isinstance(_v, dict) else _v


def step_feihu_bars(current_bars, direction):
    if direction < 0:
        smaller = [v for v in FEIHU_BAR_STEPS if v < current_bars]
        return smaller[-1] if smaller else FEIHU_BAR_STEPS[0]
    larger = [v for v in FEIHU_BAR_STEPS if v > current_bars]
    return larger[0] if larger else FEIHU_BAR_STEPS[-1]


# ---------------------------------------------------------
# 8. 頂部導航列
# ---------------------------------------------------------
top_cols = st.columns([2.2, 1.2, 1.8, 1.8, 1.5, 1.8])

with top_cols[0]:
    if st.session_state.selected_index >= len(stock_options):
        st.session_state.selected_index = 0
    selected_stock = st.selectbox(
        "股票選單",
        stock_options,
        index=st.session_state.selected_index,
        label_visibility="collapsed",
        key=f"stock_select_box_top_{st.session_state.stock_select_version}",
    )
    try:
        st.session_state.selected_index = stock_options.index(selected_stock)
    except Exception:
        st.session_state.selected_index = 0
    stock_parts = selected_stock.split()
    stock_id = stock_parts[0]
    stock_name = stock_parts[1] if len(stock_parts) > 1 else ""

with top_cols[1]:
    actual_chart_period = st.selectbox(
        "週期",
        ["日線", "5分", "10分", "15分", "30分", "60分", "週線", "月線"],
        index=0,
        label_visibility="collapsed",
        key="select_period_dropdown_top",
    )

nav_items = [
    ("📈 個股籌碼圖表", "top_go_chart", 2),
    ("⚡ 9大策略選股", "top_go_strat", 3),
    ("📋 大戶總表", "top_go_table", 4),
    ("📊 基本面與圖表", "top_go_fund", 5),
]
for nav_label, nav_key, col_idx in nav_items:
    with top_cols[col_idx]:
        if st.button(nav_label, use_container_width=True, key=nav_key):
            st.session_state.app_mode_state = nav_label
            st.rerun()

app_mode = st.session_state.app_mode_state

# =========================================================
# 分頁一：📈 個股籌碼圖表
# =========================================================
if app_mode == "📈 個股籌碼圖表":
    third_row_cols = st.columns([1.02, 1.02, 1.16])

    with third_row_cols[0]:
        ma_items = ["5", "10", "20", "35", "60", "120", "200", "分割"]
        ma_btn_cols = st.columns(len(ma_items), gap="small")
        for idx_m, m_key in enumerate(ma_items):
            with ma_btn_cols[idx_m]:
                if st.button(
                    m_key, key=f"ma_toggle_{m_key}", use_container_width=True
                ):
                    st.session_state.ma_active_map[m_key] = (
                        not st.session_state.ma_active_map.get(m_key, False)
                    )
                    st.rerun()

        active_css_rules = []
        for m_key in ma_items:
            active_flag = st.session_state.ma_active_map.get(m_key, False)
            line_col = MA_COLOR_MAP.get(m_key, "#00FFFF")
            btn_sel = (
                f"div.st-key-ma_toggle_{m_key} button,"
                f" div[data-testid='stHorizontalBlock'] div.st-key-ma_toggle_{m_key}"
                " button"
            )
            if active_flag:
                active_css_rules.append(
                    f"""
                    {btn_sel} {{
                        background-color: {line_col} !important;
                        color: #000000 !important;
                        border: 1px solid #ffffff !important;
                        font-weight: bold !important;
                        box-shadow: 0 0 4px {line_col} !important;
                        padding: 1px 1px !important;
                        font-size: 8.5px !important;
                    }}
                    """
                )
            else:
                active_css_rules.append(
                    f"""
                    {btn_sel} {{
                        background-color: #181c22 !important;
                        color: #b8c4d0 !important;
                        border: 1px solid #3d4a5a !important;
                        font-weight: bold !important;
                        box-shadow: none !important;
                        padding: 1px 1px !important;
                        font-size: 8.5px !important;
                    }}
                    """
                )
        st.markdown(
            f"<style>{''.join(active_css_rules)}</style>", unsafe_allow_html=True
        )

    with third_row_cols[1]:
        default_ind_val = (
            st.session_state.default_indicator_override
            if st.session_state.default_indicator_override in INDICATOR_BUTTONS
            else "組合"
        )
        if st.session_state.default_indicator_override:
            st.session_state["pills_ind"] = default_ind_val
            st.session_state.default_indicator_override = None

        selected_indicator = (
            st.pills(
                "指標",
                INDICATOR_BUTTONS,
                default=default_ind_val,
                selection_mode="single",
                label_visibility="collapsed",
                key="pills_ind",
            )
            or "組合"
        )

    with third_row_cols[2]:
        row_bar_cols = st.columns([0.52, 0.52, 0.52, 0.50, 0.50, 0.85, 0.55])
        for p_idx, p_val in enumerate([120, 250, 500]):
            with row_bar_cols[p_idx]:
                is_cur = st.session_state.k_bars_count == p_val
                if st.button(
                    str(p_val), key=f"btn_preset_{p_val}", use_container_width=True
                ):
                    st.session_state.k_bars_count = p_val
                    st.rerun()
                if is_cur:
                    st.markdown(
                        f"<style>div.st-key-btn_preset_{p_val} button {{"
                        " background-color:#00ffff !important; color:#000000"
                        " !important; border:1px solid #ffffff !important;"
                        " font-weight:bold !important; }}</style>",
                        unsafe_allow_html=True,
                    )

        with row_bar_cols[3]:
            if st.button("↓縮", key="btn_zoom_in_bars", use_container_width=True):
                st.session_state.k_bars_count = step_feihu_bars(
                    st.session_state.k_bars_count, -1
                )
                st.rerun()

        with row_bar_cols[4]:
            if st.button("↑擴", key="btn_zoom_out_bars", use_container_width=True):
                st.session_state.k_bars_count = step_feihu_bars(
                    st.session_state.k_bars_count, +1
                )
                st.rerun()

        with row_bar_cols[5]:
            ruler_on = bool(st.session_state.ruler_mode_active)
            ruler_lbl = "📏 測距中" if ruler_on else "📏 尺規測距"
            if st.button(ruler_lbl, key="btn_toggle_ruler", use_container_width=True):
                st.session_state.ruler_mode_active = not ruler_on
                st.rerun()
            if ruler_on:
                st.markdown(
                    "<style>div.st-key-btn_toggle_ruler button {"
                    " background-color:#FFFF00 !important; color:#000000"
                    " !important; border:1px solid #FFFFFF !important;"
                    " font-weight:bold !important; }}</style>",
                    unsafe_allow_html=True,
                )

        with row_bar_cols[6]:
            st.markdown(
                f"<div style='color:#00FFFF; font-size:10px; font-weight:bold;"
                f" text-align:right; line-height:22px; white-space:nowrap;'>K:{st.session_state.k_bars_count}</div>",
                unsafe_allow_html=True,
            )

    k_days_choice = int(st.session_state.k_bars_count)
    ruler_mode_active = bool(st.session_state.ruler_mode_active)
    ma_map = st.session_state.ma_active_map

    df, big_holder, sheep_holder, cur_vol, cur_20ma, v_ratio = (
        get_continuous_stock_df(
            stock_id, target_days=k_days_choice, period_type=actual_chart_period
        )
    )

    ma_config = {
        k: (int(k), ma_map.get(k, k == "60"), MA_COLOR_MAP[k])
        for k in ["5", "10", "20", "35", "60", "120", "200"]
    }
    show_fib = ma_map.get("分割", False)

    n_len = len(df)
    deduct_indices = {
        p: (n_len - p if 0 <= (n_len - p) < n_len else 0)
        for p in [5, 35, 65, 120, 200]
    }

    prev_closes = df["close"].shift(1).fillna(df["open"])
    body_colors = [
        BAR_UP_COLOR if c >= o else BAR_DOWN_COLOR
        for o, c in zip(df["open"], df["close"])
    ]
    macd_bar_colors = [
        BAR_UP_COLOR if osc >= 0 else BAR_DOWN_COLOR for osc in df["macd_osc"]
    ]
    band_macd_bar_colors = [
        BAR_UP_COLOR if osc >= 0 else BAR_DOWN_COLOR
        for osc in df["band_macd_osc"]
    ]
    qt_bar_colors = [
        BAR_UP_COLOR if c >= pc else BAR_DOWN_COLOR
        for c, pc in zip(df["close"], prev_closes)
    ]

    plt.style.use("dark_background")

    is_wave_mode = selected_indicator == "波段"
    is_combo_mode = selected_indicator == "組合"
    is_combo1_mode = selected_indicator == "組合1"
    is_four_pane = is_wave_mode or is_combo_mode or is_combo1_mode
    fig = plt.figure(figsize=(10.0, 4.65))

    if is_four_pane:
        gs = fig.add_gridspec(
            4, 1, height_ratios=[2.2, 0.85, 0.85, 0.85], hspace=0.08
        )
        ax1 = fig.add_subplot(gs[0])
        ax_sub1 = fig.add_subplot(gs[1], sharex=ax1)
        ax_sub2 = fig.add_subplot(gs[2], sharex=ax1)
        ax_sub3 = fig.add_subplot(gs[3], sharex=ax1)
        axes = [ax1, ax_sub1, ax_sub2, ax_sub3]
    else:
        gs = fig.add_gridspec(3, 1, height_ratios=[2.85, 1.15, 1.25], hspace=0.10)
        ax1 = fig.add_subplot(gs[0])
        ax_sub1 = fig.add_subplot(gs[1], sharex=ax1)
        ax_sub2 = fig.add_subplot(gs[2], sharex=ax1)
        ax_sub3 = None
        axes = [ax1, ax_sub1, ax_sub2]

    for ax in [fig] + list(axes):
        ax.set_facecolor(BG_COLOR)
    fig.patch.set_facecolor(BG_COLOR)
    x = np.arange(len(df))

    ax1.set_facecolor(PANEL_BG)
    ax1.vlines(
        x,
        df["low"],
        df["high"],
        color=body_colors,
        linewidth=0.75,
        alpha=1.0,
        zorder=2,
    )
    body_bottom = np.minimum(df["open"].values, df["close"].values)
    body_height = np.maximum(
        np.abs(df["close"].values - df["open"].values), 0.01
    )
    ax1.bar(
        x,
        body_height,
        bottom=body_bottom,
        width=0.78,
        color=body_colors,
        edgecolor="none",
        linewidth=0,
        zorder=3,
    )

    x_min_bar = -1.0
    pad_right_bars = max(4, int(len(x) * 0.12))
    x_max_bar = float(len(x) + pad_right_bars)

    if not df.empty:
        p_max = float(df["high"].max())
        p_min = float(df["low"].min())
        p_range = p_max - p_min if p_max != p_min else 1.0
        ax1.set_ylim(p_min - p_range * 0.12, p_max + p_range * 0.15)
        ax1.set_xlim(x_min_bar, x_max_bar)

        high_idx = int(df["high"].values.argmax())
        low_idx = int(df["low"].values.argmin())
        high_val = float(df["high"].iloc[high_idx])
        low_val = float(df["low"].iloc[low_idx])

        t_hi = ax1.text(
            high_idx,
            high_val + p_range * 0.015,
            f"▲高:{high_val:.2f}",
            color="#FF5555",
            fontsize=7.8,
            fontweight="bold",
            ha="center",
            va="bottom",
            zorder=6,
        )
        t_hi.set_path_effects(get_bright_effect("#000000", 2.4))

        t_lo = ax1.text(
            low_idx,
            low_val - p_range * 0.015,
            f"▼低:{low_val:.2f}",
            color="#00FF88",
            fontsize=7.8,
            fontweight="bold",
            ha="center",
            va="top",
            zorder=6,
        )
        t_lo.set_path_effects(get_bright_effect("#000000", 2.4))

    for count_days, idx_pos in deduct_indices.items():
        ax1.axvline(
            x=idx_pos, color="#00FFFF", linestyle="--", linewidth=0.9, alpha=0.4
        )
        t_num = ax1.text(
            idx_pos,
            df["low"].min(),
            f"{count_days}",
            color="#00FFFF",
            fontsize=8.0,
            fontweight="bold",
            ha="center",
            va="bottom",
            alpha=1.0,
        )
        t_num.set_path_effects(get_bright_effect("#000000", 2.5))

    for _, (period, is_show, color) in ma_config.items():
        if is_show:
            ax1.plot(
                x,
                df[f"ma_{period}"].ffill().bfill().values,
                linewidth=MA_LINE_WIDTH,
                color=color,
                linestyle="-",
                alpha=1.0,
                zorder=4,
            )

    if show_fib and not df.empty:
        max_p = float(df["high"].max())
        min_p = float(df["low"].min())
        diff_p = max_p - min_p
        fib_levels = [
            (0.0, "0%", max_p),
            (0.382, "38.2%", max_p - diff_p * 0.382),
            (0.5, "50.0%", max_p - diff_p * 0.5),
            (0.618, "61.8%", max_p - diff_p * 0.618),
            (1.0, "100%", min_p),
        ]
        x_right_limit = ax1.get_xlim()[1]
        for _, label_txt, price_val in fib_levels:
            ax1.axhline(
                price_val,
                color="#00FFFF",
                linestyle=":",
                linewidth=1.1,
                alpha=0.95,
            )
            t_fib = ax1.text(
                x_right_limit - 0.8,
                price_val,
                f" {price_val:.2f} ({label_txt}) ",
                color="#FFFFFF",
                fontsize=8.0,
                fontweight="bold",
                va="center",
                ha="right",
                backgroundcolor="#111111",
            )
            t_fib.set_path_effects(get_bright_effect("#000000", 2.5))

    for i in range(len(df)):
        if df["is_buy_signal"].iloc[i]:
            low_p = float(df["low"].iloc[i])
            ax1.annotate(
                "↑",
                xy=(i, low_p),
                xytext=(i, low_p * 0.985),
                ha="center",
                va="top",
                fontsize=12,
                fontweight="bold",
                color="#CC00FF",
            )
        if df["is_sell_signal"].iloc[i]:
            high_p = float(df["high"].iloc[i])
            ax1.annotate(
                "↓",
                xy=(i, high_p),
                xytext=(i, high_p * 1.015),
                ha="center",
                va="bottom",
                fontsize=12,
                fontweight="bold",
                color="#00FFFF",
            )

    ymin_lim, ymax_lim = ax1.get_ylim()
    band_height = (ymax_lim - ymin_lim) * 0.045
    trend_colors = [
        BAR_UP_COLOR if is_bull else BAR_DOWN_COLOR
        for is_bull in df["long_trend"]
    ]
    ax1.bar(
        x,
        np.full(len(x), band_height),
        bottom=ymin_lim,
        width=1.0,
        color=trend_colors,
        edgecolor="none",
        linewidth=0,
        alpha=1.0,
        zorder=2,
    )

    if not df.empty:
        month_marks, prev_ym = [], None
        for idx_m, dt_str in enumerate(df["date"].astype(str)):
            parts = dt_str.split(" ")[0].split("/")
            if len(parts) >= 2:
                ym = f"{parts[0]}/{parts[1]}"
                if ym != prev_ym:
                    prev_ym = ym
                    try:
                        month_marks.append((idx_m, str(int(parts[1]))))
                    except Exception:
                        pass
        step_m = max(1, int(np.ceil(len(month_marks) / 14.0)))
        for m_i, (m_idx, m_lbl) in enumerate(month_marks):
            if m_i % step_m == 0:
                t_m = ax1.text(
                    m_idx,
                    ymin_lim + band_height * 0.50,
                    m_lbl,
                    color="#FFFFFF",
                    fontsize=7.2,
                    fontweight="bold",
                    ha="center",
                    va="center",
                    zorder=7,
                )
                t_m.set_path_effects(get_bright_effect("#000000", 2.0))

    def _style_axis(ax_obj, show_x=False):
        ax_obj.yaxis.tick_right()
        ax_obj.tick_params(axis="y", labelsize=6.5, pad=1.0, colors="#FFFFFF")
        plt.setp(ax_obj.get_xticklabels(), visible=show_x)
        if show_x:
            ax_obj.tick_params(axis="x", labelsize=7.5, colors="#FFFFFF")
            for lbl in ax_obj.get_xticklabels():
                lbl.set_color("#FFFFFF")
                lbl.set_fontsize(7.5)
        ax_obj.grid(
            True, which="both", linestyle="--", color=GRID_COLOR, alpha=0.5
        )

    def _plot_kdj_axis(ax_kdj):
        ax_kdj.set_facecolor(PANEL_BG)
        ax_kdj.plot(x, df["kdj_k"], linewidth=IND_LINE_WIDTH, color="#FF00FF", label="K", zorder=3)
        ax_kdj.plot(x, df["kdj_d"], linewidth=IND_LINE_WIDTH, color="#00FFFF", label="D", zorder=3)
        ax_kdj.plot(x, df["kdj_j"], linewidth=IND_LINE_WIDTH, color="#FFFFFF", label="J", zorder=3)
        ax_kdj.axhline(80, color="#FF6666", linestyle="--", linewidth=0.85, alpha=0.75, zorder=2)
        ax_kdj.axhline(20, color="#00E64D", linestyle="--", linewidth=0.85, alpha=0.75, zorder=2)
        ax_kdj.axhline(50, color="#666666", linestyle=":", linewidth=0.75, alpha=0.55, zorder=1)
        kdj_comb = np.concatenate([
            df["kdj_k"].fillna(50).values,
            df["kdj_d"].fillna(50).values,
            df["kdj_j"].fillna(50).values,
        ])
        kdj_comb = kdj_comb[np.isfinite(kdj_comb)]
        if len(kdj_comb) > 0:
            y_lo = min(0.0, float(np.min(kdj_comb)))
            y_hi = max(100.0, float(np.max(kdj_comb)))
            pad_y = max(4.0, (y_hi - y_lo) * 0.08)
            ax_kdj.set_ylim(y_lo - pad_y, y_hi + pad_y)

    def _plot_rsi_axis(ax_rsi):
        ax_rsi.set_facecolor(PANEL_BG)
        ax_rsi.plot(x, df["rsi_6"], linewidth=IND_LINE_WIDTH, color="#FF00FF", label="RSI6", zorder=3)
        ax_rsi.plot(x, df["rsi_12"], linewidth=IND_LINE_WIDTH, color="#00FFFF", label="RSI12", zorder=3)
        ax_rsi.axhline(80, color="#FF6666", linestyle="--", linewidth=0.75, alpha=0.55, zorder=2)
        ax_rsi.axhline(20, color="#00E64D", linestyle="--", linewidth=0.75, alpha=0.55, zorder=2)
        ax_rsi.axhline(50, color="#777777", linestyle=":", linewidth=0.85, zorder=1)

    def _plot_wr_axis(ax_wr):
        ax_wr.set_facecolor(PANEL_BG)
        ax_wr.plot(x, df["w_r"], linewidth=IND_LINE_WIDTH, color="#FFFF00", label="W%", zorder=3)
        ax_wr.axhline(-20, color="#FF6666", linestyle="--", linewidth=0.75, alpha=0.55, zorder=2)
        ax_wr.axhline(-80, color="#00E64D", linestyle="--", linewidth=0.75, alpha=0.55, zorder=2)
        ax_wr.axhline(-50, color="#777777", linestyle=":", linewidth=0.85, zorder=1)

    def _plot_macd_axis(ax_macd):
        ax_macd.set_facecolor(PANEL_BG)
        ax_macd.bar(x, df["macd_osc"], width=0.75, color=macd_bar_colors, edgecolor="none", linewidth=0, alpha=1.0, zorder=2)
        ax_macd.plot(x, df["macd_dif"], linewidth=0.6, color="#FF00FF", label="DIF", zorder=3)
        ax_macd.plot(x, df["macd_dem"], linewidth=0.6, color="#00FFFF", label="DEA", zorder=3)
        ax_macd.axhline(0, color="#777777", linestyle=":", linewidth=1.0)

    def _plot_vol_axis(ax_vol):
        ax_vol.set_facecolor(PANEL_BG)
        ax_vol.bar(x, df["vol"], width=0.75, color=body_colors, edgecolor="none", linewidth=0, alpha=1.0, zorder=2)
        ax_vol.plot(x, df["vol_ma5"], linewidth=0.6, color="#FFFF00", label="Vol MA5", alpha=0.95, zorder=3)
        ax_vol.plot(x, df["vol_ma20"], linewidth=0.6, color="#FF9900", label="Vol MA20", alpha=0.95, zorder=3)

    _style_axis(ax1, show_x=False)

    if is_wave_mode:
        ax_sub1.set_facecolor(PANEL_BG)
        ax_sub1.bar(x, df["band_macd_osc"], width=0.75, color=band_macd_bar_colors, edgecolor="none", linewidth=0, alpha=1.0, zorder=2)
        ax_sub1.plot(x, df["band_macd_dif"], linewidth=0.6, color="#FFFF00", label="DIF", zorder=3)
        ax_sub1.plot(x, df["band_macd_dem"], linewidth=0.6, color="#FF3333", label="MACD", zorder=3)
        ax_sub1.axhline(0, color="#777777", linestyle=":", linewidth=1.0)
        _style_axis(ax_sub1, show_x=False)

        ax_sub2.set_facecolor(PANEL_BG)
        ax_sub2.plot(x, df["band_bias_val_rev"], linewidth=0.65, color="#00FFFF", label="BIAS(反向)", zorder=3)
        ax_sub2.axhline(0, color="#777777", linestyle=":", linewidth=1.0)
        _style_axis(ax_sub2, show_x=False)

        ax_sub3.set_facecolor(PANEL_BG)
        ax_sub3.plot(x, df["mtm_val"], linewidth=0.65, color="#FFFF00", label="MTM", zorder=3)
        ax_sub3.plot(x, df["mtm_ma1"], linewidth=0.65, color="#00FF66", label="Avg", zorder=3)
        ax_sub3.axhline(0, color="#777777", linestyle=":", linewidth=1.0)
        _style_axis(ax_sub3, show_x=True)
    elif is_combo_mode:
        _plot_kdj_axis(ax_sub1)
        _style_axis(ax_sub1, show_x=False)
        _plot_macd_axis(ax_sub2)
        _style_axis(ax_sub2, show_x=False)
        _plot_vol_axis(ax_sub3)
        _style_axis(ax_sub3, show_x=True)
    elif is_combo1_mode:
        _plot_kdj_axis(ax_sub1)
        _style_axis(ax_sub1, show_x=False)
        _plot_rsi_axis(ax_sub2)
        _style_axis(ax_sub2, show_x=False)
        _plot_wr_axis(ax_sub3)
        _style_axis(ax_sub3, show_x=True)
    else:
        ax_sub1.set_facecolor(PANEL_BG)
        if selected_indicator == "BIAS":
            ax_sub1.plot(x, df["bias_val"], linewidth=0.6, color="#FFFF00", label="BIAS(60)", zorder=3)
        elif selected_indicator == "QT":
            ax_sub1.bar(x, df["qt"], width=0.75, color=qt_bar_colors, edgecolor="none", linewidth=0, alpha=1.0, zorder=2)
        elif selected_indicator == "集保":
            n_bars_now = len(x)
            b_raw = np.asarray(big_holder, dtype=float)
            s_raw = np.asarray(sheep_holder, dtype=float)
            b_plot = (
                b_raw[-n_bars_now:]
                if len(b_raw) >= n_bars_now
                else np.concatenate([
                    b_raw,
                    np.full(
                        n_bars_now - len(b_raw),
                        float(b_raw[-1]) if len(b_raw) > 0 else 45.0,
                    ),
                ])
            )
            s_plot = (
                s_raw[-n_bars_now:]
                if len(s_raw) >= n_bars_now
                else np.concatenate([
                    s_raw,
                    np.full(
                        n_bars_now - len(s_raw),
                        float(s_raw[-1]) if len(s_raw) > 0 else 45.0,
                    ),
                ])
            )
            ax_sub1.plot(x, b_plot, color="#FF3333", linewidth=1.25, linestyle="-", label="大戶(%)", zorder=4)
            ax_sub1.plot(x, s_plot, color="#00E64D", linewidth=1.25, linestyle="-", label="羊群(%)", zorder=5)
            comb = np.concatenate([b_plot, s_plot])
            comb = comb[np.isfinite(comb)]
            if len(comb) > 0:
                y_lo, y_hi = float(np.min(comb)), float(np.max(comb))
                pad = max(y_hi - y_lo, 5.0) * 0.18
                ax_sub1.set_ylim(max(0.0, y_lo - pad), y_hi + pad)
                ax_sub1.axhline(float(np.mean(comb)), color="#666666", linestyle=":", linewidth=0.9, zorder=2)

        if selected_indicator != "集保":
            ax_sub1.axhline(0, color="#777777", linestyle=":", linewidth=1.0)
        _style_axis(ax_sub1, show_x=False)

        _plot_vol_axis(ax_sub2)
        _style_axis(ax_sub2, show_x=True)

    for ax in axes:
        for spine in ax.spines.values():
            spine.set_visible(True)
            spine.set_color("#777777")
            spine.set_linewidth(1.2)

    plt.subplots_adjust(
        left=0.008, right=0.965, top=0.98, bottom=0.08, hspace=0.10
    )

    fig.canvas.draw()
    ax1_bbox = ax1.get_position()
    ax_sub1_bbox = ax_sub1.get_position()
    ax_sub2_bbox = ax_sub2.get_position()
    ax_sub3_bbox = ax_sub3.get_position() if ax_sub3 is not None else None

    ax_x0, ax_x1 = float(ax1_bbox.x0), float(ax1_bbox.x1)
    ax1_top_frac = float(1.0 - ax1_bbox.y1)
    sub1_top_frac = float(1.0 - ax_sub1_bbox.y1)
    sub2_top_frac = float(1.0 - ax_sub2_bbox.y1)
    sub3_top_frac = float(1.0 - ax_sub3_bbox.y1) if ax_sub3_bbox is not None else 0.0

    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=150, facecolor=BG_COLOR, edgecolor="none")
    plt.close(fig)
    img_b64 = base64.b64encode(buf.getvalue()).decode("utf-8")

    fund_data = fetch_stock_fundamentals(stock_id)
    payload_rows = []
    total_bars_cnt = len(df)
    for idx_r in range(total_bars_cnt):
        r = df.iloc[idx_r]
        ma_items_colored = []
        for ma_name, (period, is_show, color) in ma_config.items():
            if is_show:
                v_now = float(r[f"ma_{period}"])
                v_prev = float(df[f"ma_{period}"].iloc[idx_r - 1]) if idx_r > 0 else v_now
                arr = "▲" if v_now >= v_prev else "▼"
                ma_items_colored.append(
                    {"text": f"{ma_name}:{v_now:.1f}{arr}", "color": color}
                )

        snap = build_bar_analysis_snapshot(
            df,
            big_holder,
            sheep_holder,
            idx_r,
            selected_indicator,
            actual_chart_period,
            stock_id=stock_id,
        )
        snap.update(
            build_bar_fundamental_snap(
                fund_data, str(r["date"]), float(r["close"])
            )
        )
        payload_rows.append({
            "rev_no": total_bars_cnt - idx_r,
            "date": str(r["date"]),
            "open": round(float(r["open"]), 2),
            "high": round(float(r["high"]), 2),
            "low": round(float(r["low"]), 2),
            "close": round(float(r["close"]), 2),
            "vol": int(round(float(r["vol"]))),
            "ma_items": ma_items_colored,
            "snap": snap,
        })

    rows_json = json.dumps(payload_rows, ensure_ascii=False)
    feihu_steps_json = json.dumps(FEIHU_BAR_STEPS)
    init_snap = payload_rows[-1]["snap"] if payload_rows else {}
    for _k, _v in fund_data.items():
        init_snap.setdefault(_k, _v)

    unified_interactive_html = f"""
    <style>
      .fx-root {{
        display: flex;
        gap: 6px;
        width: 100%;
        background: #000000;
        box-sizing: border-box;
        font-family: Arial, 'Microsoft JhengHei', sans-serif;
        color: #ffffff;
      }}
      #fx-chart-wrap {{
        position: relative;
        flex: 8.2;
        min-width: 0;
        background: #000000;
        user-select: none;
        overflow: hidden;
        outline: none;
      }}
      #fx-side-wrap {{
        flex: 1.8;
        min-width: 165px;
        display: flex;
        flex-direction: column;
        gap: 3px;
        background: #000000;
      }}
      .terminal-panel {{
        background-color: #0b0b0b;
        border: 1px solid #cc0000;
        padding: 5px 8px;
        color: #ffffff;
        box-sizing: border-box;
      }}
      .terminal-title {{
        color: #ffffff;
        background-color: #0000aa;
        font-weight: bold;
        font-size: 12px;
        padding: 2px 5px;
        margin-bottom: 3px;
        text-align: center;
      }}
      .terminal-title-ruler {{
        color: #000000;
        background-color: #ffff00;
        font-weight: bold;
        font-size: 12px;
        padding: 2px 5px;
        margin-bottom: 3px;
        text-align: center;
      }}
      .t-row {{
        font-size: 11px;
        line-height: 1.3;
        margin-bottom: 1px;
        display: flex;
        justify-content: space-between;
        gap: 4px;
      }}
      .t-label {{ color: #ffff00; font-weight: bold; white-space: nowrap; }}
      .t-val-red {{ color: #ff3333; font-weight: bold; }}
      .t-val-green {{ color: #00e64d; font-weight: bold; }}
      .t-val-cyan {{ color: #00ffff; font-weight: bold; }}
      .t-val-white {{ color: #ffffff; font-weight: bold; }}
    </style>

    <div class="fx-root">
      <div id="fx-chart-wrap" tabindex="0">
        <img id="fx-base-img" src="data:image/png;base64,{img_b64}" style="width:100%; height:auto; display:block; margin:0 auto;" />
        <canvas id="fx-cross-canvas" style="position:absolute; top:0; left:0; width:100%; height:100%; cursor:crosshair;"></canvas>
      </div>

      <div id="fx-side-wrap">
        <div class="terminal-panel">
          <div class="terminal-title">【基本面快訊】</div>
          <div class="t-row"><span class="t-label">今日本益比:</span><span id="p-pe" class="t-val-cyan">{init_snap.get("pe_str", "--")}</span></div>
          <div class="t-row"><span class="t-label">EPS:</span><span id="p-eps" class="t-val-white">{init_snap.get("eps_str", "--")}</span></div>
          <div class="t-row"><span class="t-label">近4季EPS:</span><span id="p-eps4q" class="t-val-red">{init_snap.get("eps_4q_str", "--")}</span></div>
          <div class="t-row"><span class="t-label">殖利率:</span><span id="p-yield" class="t-val-green">{init_snap.get("yield_str", "--")}</span></div>
        </div>

        <div class="terminal-panel">
          <div class="terminal-title">【均線解盤】</div>
          <div class="t-row"><span class="t-label">狀態:</span><span id="p-ma-status" class="{init_snap.get("ma_cls", "t-val-white")}">{init_snap.get("ma_status", "")}</span></div>
          <div class="t-row"><span class="t-label">MA5:</span><span id="p-ma5" class="t-val-cyan">{init_snap.get("ma5", "")}</span></div>
          <div class="t-row"><span class="t-label">MA20:</span><span id="p-ma20" class="t-val-cyan">{init_snap.get("ma20", "")}</span></div>
          <div class="t-row"><span class="t-label">季60:</span><span id="p-ma60" class="t-val-cyan">{init_snap.get("ma60", "")}</span></div>
        </div>

        <div class="terminal-panel" id="p-dynamic-box">
          <div id="p-dyn-title" class="terminal-title">【當日漲跌與籌碼】</div>
          <div id="p-dyn-rows">
            <div class="t-row"><span class="t-label">當日漲跌:</span><span class="{init_snap.get("bar_chg_cls", "t-val-white")}">{init_snap.get("bar_chg_str", "--")}</span></div>
            <div class="t-row"><span class="t-label">當日振幅:</span><span class="t-val-cyan">{init_snap.get("bar_amp_str", "--")}</span></div>
            <div class="t-row"><span class="t-label">大戶持股:</span><span class="t-val-red">{init_snap.get("big_str", "--")}</span></div>
            <div class="t-row"><span class="t-label">羊群持股:</span><span class="t-val-green">{init_snap.get("sheep_str", "--")}</span></div>
          </div>
        </div>

        <div class="terminal-panel">
          <div class="terminal-title">【KDJ綜合解盤】</div>
          <div class="t-row"><span class="t-label">判定:</span><span id="p-kdj-sig" class="{init_snap.get("kdj_cls", "t-val-white")}">{init_snap.get("kdj_sig", "")}</span></div>
          <div class="t-row"><span class="t-label">K/D:</span><span id="p-kd" class="t-val-white">{init_snap.get("kd_str", "")}</span></div>
          <div class="t-row"><span class="t-label">J值:</span><span id="p-j" class="t-val-cyan">{init_snap.get("j_str", "")}</span></div>
          <div class="t-row"><span class="t-label">K-D乖離:</span><span id="p-kddiff" class="t-val-white">{init_snap.get("kd_diff", "")}</span></div>
        </div>

        <div class="terminal-panel">
          <div class="terminal-title">【成交量解盤】</div>
          <div class="t-row"><span class="t-label">5日均量比:</span><span id="p-vratio" class="{init_snap.get("vol_cls", "t-val-white")}">{init_snap.get("vol_ratio", "")}</span></div>
          <div class="t-row"><span class="t-label">現況:</span><span id="p-vstatus" class="t-val-white">{init_snap.get("vol_status", "")}</span></div>
          <div class="t-row"><span class="t-label">當日量:</span><span id="p-vval" class="t-val-cyan">{init_snap.get("vol_str", "")}</span></div>
        </div>

        <div class="terminal-panel">
          <div class="terminal-title">【多空與波段判定】</div>
          <div class="t-row"><span class="t-label">多空:</span><span id="p-trend" class="{init_snap.get("trend_cls", "t-val-white")}">{init_snap.get("trend_txt", "")}</span></div>
          <div class="t-row"><span class="t-label">波段狀態:</span><span id="p-wave" class="{init_snap.get("wave_cls", "t-val-white")}">{init_snap.get("wave_txt", "")}</span></div>
        </div>
      </div>
    </div>

    <script>
    (function() {{
      const rows = {rows_json};
      const feihuSteps = {feihu_steps_json};
      const wrap = document.getElementById("fx-chart-wrap");
      const img = document.getElementById("fx-base-img");
      const canvas = document.getElementById("fx-cross-canvas");
      const ctx = canvas.getContext("2d");

      const stockCode = {json.dumps(stock_id)};
      const stockName = {json.dumps(stock_name)};
      const isFourPane = {str(is_four_pane).lower()};
      const rulerBtnActive = {str(ruler_mode_active).lower()};
      const totalBars = rows.length;
      const xMinBar = {x_min_bar};
      const xMaxBar = {x_max_bar};
      const axX0 = {ax_x0};
      const axX1 = {ax_x1};
      const ax1TopFrac = {ax1_top_frac};
      const sub1TopFrac = {sub1_top_frac};
      const sub2TopFrac = {sub2_top_frac};
      const sub3TopFrac = {sub3_top_frac};

      let crosshairEnabled = true;
      let rulerArmed = rulerBtnActive;
      let rulerStartIdx = null;
      let rulerEndIdx = null;
      let rulerPreviewIdx = null;

      function setEl(id, text, cls) {{
        const el = document.getElementById(id);
        if (!el) return;
        el.textContent = text;
        if (cls) el.className = cls;
      }}

      function calcRangeStats(idxA, idxB) {{
        if (idxA === null || idxB === null || totalBars <= 0) return null;
        const i1 = Math.max(0, Math.min(idxA, idxB));
        const i2 = Math.min(totalBars - 1, Math.max(idxA, idxB));
        const r1 = rows[i1];
        const r2 = rows[i2];
        if (!r1 || !r2) return null;

        const startClose = Number(r1.close);
        const endClose = Number(r2.close);
        const diffPts = endClose - startClose;
        const diffPct = startClose > 0 ? (diffPts / startClose) * 100 : 0;

        let maxH = -Infinity, minL = Infinity, sumVol = 0;
        for (let k = i1; k <= i2; k++) {{
          const h = Number(rows[k].high);
          const l = Number(rows[k].low);
          const v = Number(rows[k].vol || 0);
          if (h > maxH) maxH = h;
          if (l < minL) minL = l;
          sumVol += v;
        }}

        const barCount = i2 - i1 + 1;
        const ampPct = minL > 0 ? ((maxH - minL) / minL) * 100 : 0;
        const avgVol = barCount > 0 ? Math.round(sumVol / barCount) : 0;

        return {{
          i1, i2,
          startDate: r1.date,
          endDate: r2.date,
          barCount,
          startClose,
          endClose,
          diffPts,
          diffPct,
          maxH,
          minL,
          ampPct,
          sumVol: Math.round(sumVol),
          avgVol
        }};
      }}

      function updateDynamicSidePanel(r) {{
        const titleEl = document.getElementById("p-dyn-title");
        const rowsEl = document.getElementById("p-dyn-rows");
        if (!titleEl || !rowsEl) return;

        const targetEnd = (rulerEndIdx !== null) ? rulerEndIdx : rulerPreviewIdx;
        const st = (rulerStartIdx !== null && targetEnd !== null)
          ? calcRangeStats(rulerStartIdx, targetEnd)
          : null;

        if (st) {{
          const isUp = st.diffPts >= 0;
          const chgCls = isUp ? "t-val-red" : "t-val-green";
          const sgn = isUp ? "+" : "";
          const psgn = st.diffPct >= 0 ? "+" : "";
          const ampSign = isUp ? "+" : "-";
          titleEl.className = "terminal-title-ruler";
          titleEl.textContent = `【尺規區間統計 (${{st.barCount}}K)】`;
          rowsEl.innerHTML =
            `<div class="t-row"><span class="t-label">起訖:</span><span class="t-val-cyan">${{st.startDate.slice(5)}}~${{st.endDate.slice(5)}}</span></div>` +
            `<div class="t-row"><span class="t-label">區間漲跌:</span><span class="${{chgCls}}">${{sgn}}${{st.diffPts.toFixed(2)}} (${{psgn}}${{st.diffPct.toFixed(2)}}%)</span></div>` +
            `<div class="t-row"><span class="t-label">高低/振:</span><span class="${{chgCls}}">${{st.maxH.toFixed(1)}}/${{st.minL.toFixed(1)}} (${{ampSign}}${{st.ampPct.toFixed(1)}}%)</span></div>` +
            `<div class="t-row"><span class="t-label">累量/均:</span><span class="t-val-cyan">${{st.sumVol.toLocaleString()}} / ${{st.avgVol.toLocaleString()}}</span></div>`;
        }} else {{
          const s = (r && r.snap) ? r.snap : {{}};
          titleEl.className = "terminal-title";
          titleEl.textContent = rulerArmed ? "【尺規測距：點選起訖】" : "【當日漲跌與籌碼】";
          rowsEl.innerHTML =
            `<div class="t-row"><span class="t-label">當日漲跌:</span><span class="${{s.bar_chg_cls || "t-val-white"}}">${{s.bar_chg_str || "--"}}</span></div>` +
            `<div class="t-row"><span class="t-label">當日振幅:</span><span class="t-val-cyan">${{s.bar_amp_str || "--"}}</span></div>` +
            `<div class="t-row"><span class="t-label">大戶持股:</span><span class="t-val-red">${{s.big_str || "--"}}</span></div>` +
            `<div class="t-row"><span class="t-label">羊群持股:</span><span class="t-val-green">${{s.sheep_str || "--"}}</span></div>`;
        }}
      }}

      function syncAnalysisPanel(r) {{
        if (!r || !r.snap) return;
        const s = r.snap;
        setEl("p-ma-status", s.ma_status, s.ma_cls);
        setEl("p-ma5", s.ma5);
        setEl("p-ma20", s.ma20);
        setEl("p-ma60", s.ma60);
        updateDynamicSidePanel(r);
        setEl("p-kdj-sig", s.kdj_sig, s.kdj_cls);
        setEl("p-kd", s.kd_str);
        setEl("p-j", s.j_str);
        setEl("p-kddiff", s.kd_diff);
        setEl("p-vratio", s.vol_ratio, s.vol_cls);
        setEl("p-vstatus", s.vol_status);
        setEl("p-vval", s.vol_str);
        setEl("p-trend", s.trend_txt, s.trend_cls);
        setEl("p-wave", s.wave_txt, s.wave_cls);
        setEl("p-pe", s.pe_str || "--");
        setEl("p-eps", s.eps_str || "--");
        setEl("p-eps4q", s.eps_4q_str || "--");
        setEl("p-yield", s.yield_str || "--");
      }}

      function syncSize() {{
        const w = wrap.clientWidth;
        const h = wrap.clientHeight;
        if (w > 0 && h > 0) {{
          canvas.width = w;
          canvas.height = h;
        }}
      }}

      function getImgBounds() {{
        const wRect = wrap.getBoundingClientRect();
        const iRect = img.getBoundingClientRect();
        return {{
          left: iRect.left - wRect.left,
          top: iRect.top - wRect.top,
          width: iRect.width,
          height: iRect.height
        }};
      }}

      function clientXToBarIdx(clientX, b) {{
        const plotLeft = b.left + b.width * axX0;
        const plotRight = b.left + b.width * axX1;
        const plotW = Math.max(10, plotRight - plotLeft);
        const wRect = wrap.getBoundingClientRect();
        const frac = ((clientX - wRect.left) - plotLeft) / plotW;
        const barPos = xMinBar + frac * (xMaxBar - xMinBar);
        return Math.max(0, Math.min(totalBars - 1, Math.round(barPos)));
      }}

      function barIdxToX(idx, plotLeft, plotW) {{
        const fracIdx = (idx - xMinBar) / (xMaxBar - xMinBar);
        return plotLeft + fracIdx * plotW;
      }}

      function drawOutlinedText(txt, xPos, yPos, color, fontStr, strokeW) {{
        ctx.save();
        ctx.font = fontStr;
        ctx.textBaseline = "top";
        ctx.lineWidth = strokeW || 1.3;
        ctx.strokeStyle = "#000000";
        ctx.strokeText(txt, xPos, yPos);
        ctx.fillStyle = color;
        ctx.fillText(txt, xPos, yPos);
        ctx.restore();
      }}

      function drawRulerOverlay(b) {{
        const targetB = (rulerEndIdx !== null) ? rulerEndIdx : rulerPreviewIdx;
        if (rulerStartIdx === null || targetB === null) return;
        const st = calcRangeStats(rulerStartIdx, targetB);
        if (!st) return;

        const plotLeft = b.left + b.width * axX0;
        const plotRight = b.left + b.width * axX1;
        const plotW = Math.max(10, plotRight - plotLeft);
        const topY = b.top + b.height * ax1TopFrac;
        const botY = b.top + b.height * (isFourPane ? 0.92 : 0.90);

        const xA = barIdxToX(st.i1, plotLeft, plotW);
        const xB = barIdxToX(st.i2, plotLeft, plotW);
        const boxX = Math.min(xA, xB);
        const boxW = Math.max(2, Math.abs(xB - xA));
        const isUp = st.diffPts >= 0;

        ctx.save();
        ctx.fillStyle = isUp ? "rgba(255, 51, 51, 0.14)" : "rgba(0, 230, 77, 0.14)";
        ctx.fillRect(boxX, topY, boxW, Math.max(10, botY - topY));

        ctx.strokeStyle = "#FFFF00";
        ctx.lineWidth = 1.2;
        ctx.setLineDash([5, 3]);
        [xA, xB].forEach((vx) => {{
          ctx.beginPath();
          ctx.moveTo(vx, topY);
          ctx.lineTo(vx, botY);
          ctx.stroke();
        }});
        ctx.setLineDash([]);

        const sign = isUp ? "+" : "";
        const pctSign = st.diffPct >= 0 ? "+" : "";
        const ampSign = isUp ? "+" : "-";
        const lines = [
          `【尺規測距】${{st.startDate}} → ${{st.endDate}} (${{st.barCount}}K)`,
          `區間漲跌: ${{sign}}${{st.diffPts.toFixed(2)}} (${{pctSign}}${{st.diffPct.toFixed(2)}}%)  收: ${{st.startClose.toFixed(2)}} → ${{st.endClose.toFixed(2)}}`,
          `區間高低: ${{st.maxH.toFixed(2)}} / ${{st.minL.toFixed(2)}}  振幅: ${{ampSign}}${{st.ampPct.toFixed(2)}}%`,
          `累積量: ${{st.sumVol.toLocaleString()}}  均量: ${{st.avgVol.toLocaleString()}}`
        ];

        const cardW = 355, cardH = 74;
        let cardX = Math.max(xA, xB) + 10;
        if (cardX + cardW > plotRight - 6) cardX = Math.min(xA, xB) - cardW - 10;
        if (cardX < plotLeft + 6) cardX = plotLeft + 10;
        const cardY = topY + 46;

        ctx.fillStyle = "rgba(12, 16, 24, 0.92)";
        ctx.strokeStyle = isUp ? "#FF5555" : "#00E64D";
        ctx.lineWidth = 1.4;
        ctx.fillRect(cardX, cardY, cardW, cardH);
        ctx.strokeRect(cardX, cardY, cardW, cardH);

        lines.forEach((ln, idxLine) => {{
          let col = "#FFFFFF";
          if (idxLine === 0) col = "#00FFFF";
          else if (idxLine === 1 || idxLine === 2) col = isUp ? "#FF4444" : "#00E64D";
          drawOutlinedText(ln, cardX + 8, cardY + 6 + idxLine * 16, col, "bold 11.5px Arial, 'Microsoft JhengHei', sans-serif", 1.2);
        }});
        ctx.restore();
      }}

      function drawTokensRow(tokens, startX, yPos, fontStr, baseGap) {{
        let curX = startX;
        (tokens || []).forEach((tk) => {{
          drawOutlinedText(tk.text, curX, yPos, tk.color, fontStr, 1.3);
          const w = ctx.measureText(tk.text).width;
          const isLabel = tk.text.endsWith("::") || tk.text.endsWith(":");
          curX += w + (isLabel ? 5.5 : (baseGap || 13.0));
        }});
      }}

      function renderInPlaceOverlay(r, drawLines, lineX, lineY, b) {{
        syncSize();
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        if (!r || b.width <= 0 || b.height <= 0) return;

        const plotLeft = b.left + b.width * axX0;
        const plotRight = b.left + b.width * axX1;

        if (crosshairEnabled && drawLines) {{
          ctx.save();
          ctx.strokeStyle = "#00ffff";
          ctx.lineWidth = 1;
          ctx.setLineDash([4, 3]);
          ctx.beginPath();
          ctx.moveTo(lineX, b.top);
          ctx.lineTo(lineX, b.top + b.height);
          ctx.moveTo(plotLeft, lineY);
          ctx.lineTo(plotRight, lineY);
          ctx.stroke();
          ctx.restore();
        }}

        drawRulerOverlay(b);

        const s = r.snap || {{}};
        const headerX = plotLeft + b.width * 0.010;
        const headerY = b.top + b.height * (ax1TopFrac + 0.014);
        const fontHeader = "bold 12px Arial, 'Microsoft JhengHei', sans-serif";

        const prefixTitle = `[${{stockCode}}] ${{stockName}}`;
        drawOutlinedText(prefixTitle, headerX, headerY, "#FFFFFF", fontHeader, 1.3);
        let hx = headerX + ctx.measureText(prefixTitle).width + 14.0;

        if (s.header_tokens && s.header_tokens.length > 0) {{
          s.header_tokens.forEach((ht) => {{
            drawOutlinedText(ht.text, hx, headerY, ht.color, fontHeader, 1.3);
            const isTag = ht.text.endsWith(":");
            hx += ctx.measureText(ht.text).width + (isTag ? 4.0 : 12.5);
          }});
        }} else {{
          drawOutlinedText(s.header_text || "", hx, headerY, "#FFFFFF", fontHeader, 1.3);
        }}

        drawOutlinedText(s.trend_badge || "", plotLeft + b.width * 0.72, headerY, s.trend_badge_color || "#FF3333", fontHeader, 1.3);
        drawOutlinedText(`逆序:${{r.rev_no}}`, plotLeft + b.width * 0.815, headerY, "#00FFFF", fontHeader, 1.3);

        if (r.ma_items && r.ma_items.length > 0) {{
          const maY = headerY + 20;
          let curX = headerX;
          const fontMa = "bold 12.5px Arial, 'Microsoft JhengHei', sans-serif";
          r.ma_items.forEach((m) => {{
            drawOutlinedText(m.text, curX, maY, m.color, fontMa, 1.3);
            curX += ctx.measureText(m.text).width + 15.0;
          }});
        }}

        const fontSub = "bold 13px Arial, 'Microsoft JhengHei', sans-serif";
        if (isFourPane) {{
          drawTokensRow(s.ind_tokens, headerX, b.top + b.height * (sub1TopFrac + 0.014), fontSub, 14.0);
          drawTokensRow(s.sub2_tokens, headerX, b.top + b.height * (sub2TopFrac + 0.014), fontSub, 14.0);
          drawTokensRow(s.sub3_tokens, headerX, b.top + b.height * (sub3TopFrac + 0.014), fontSub, 14.0);
        }} else {{
          drawTokensRow(s.ind_tokens, headerX, b.top + b.height * (sub1TopFrac + 0.016), fontSub, 14.0);
          drawTokensRow(s.vol_tokens, headerX, b.top + b.height * (sub2TopFrac + 0.016), fontSub, 15.0);
        }}
      }}

      function onHover(clientX, clientY) {{
        const b = getImgBounds();
        if (b.width <= 0 || b.height <= 0 || totalBars <= 0) return;

        const idx = clientXToBarIdx(clientX, b);
        const r = rows[idx];
        if (rulerStartIdx !== null && rulerEndIdx === null) rulerPreviewIdx = idx;

        const plotLeft = b.left + b.width * axX0;
        const plotRight = b.left + b.width * axX1;
        const plotW = Math.max(10, plotRight - plotLeft);
        const wRect = wrap.getBoundingClientRect();

        const lineX = barIdxToX(idx, plotLeft, plotW);
        const lineY = clientY ? (clientY - wRect.top) : (b.top + b.height * 0.35);

        renderInPlaceOverlay(r, crosshairEnabled, lineX, lineY, b);
        syncAnalysisPanel(r);
      }}

      function initDefault() {{
        const b = getImgBounds();
        if (totalBars > 0 && b.width > 0) {{
          const latest = rows[totalBars - 1];
          renderInPlaceOverlay(latest, false, 0, 0, b);
          syncAnalysisPanel(latest);
        }}
      }}

      img.addEventListener("load", initDefault);
      window.addEventListener("resize", initDefault);
      setTimeout(initDefault, 80);

      canvas.addEventListener("mousedown", function(e) {{
        if (e.button !== 0) return;
        wrap.focus();
        const b = getImgBounds();
        const idx = clientXToBarIdx(e.clientX, b);

        if (rulerArmed || e.shiftKey) {{
          if (rulerStartIdx === null || rulerEndIdx !== null) {{
            rulerStartIdx = idx;
            rulerEndIdx = null;
          }} else {{
            rulerEndIdx = idx;
          }}
          rulerPreviewIdx = idx;
          onHover(e.clientX, e.clientY);
          return;
        }}

        if (rulerStartIdx !== null && rulerEndIdx !== null) {{
          rulerStartIdx = null;
          rulerEndIdx = null;
          rulerPreviewIdx = null;
          onHover(e.clientX, e.clientY);
          return;
        }}

        crosshairEnabled = !crosshairEnabled;
        onHover(e.clientX, e.clientY);
      }});

      canvas.addEventListener("mousemove", function(e) {{
        onHover(e.clientX, e.clientY);
      }});

      canvas.addEventListener("mouseleave", function() {{
        initDefault();
      }});

      function triggerFeihuStep(dir) {{
        const curBars = totalBars;
        let nextBars = curBars;
        if (dir < 0) {{
          const smaller = feihuSteps.filter((v) => v < curBars);
          nextBars = smaller.length > 0 ? smaller[smaller.length - 1] : feihuSteps[0];
        }} else {{
          const larger = feihuSteps.filter((v) => v > curBars);
          nextBars = larger.length > 0 ? larger[0] : feihuSteps[feihuSteps.length - 1];
        }}
        if (nextBars === curBars) return;

        const targetBtnText = dir < 0 ? "↓縮" : "↑擴";
        try {{
          const parentDoc = window.parent && window.parent.document;
          if (parentDoc) {{
            const btns = Array.from(parentDoc.querySelectorAll("button"));
            const matchBtn = btns.find((b) => (b.innerText || "").trim() === targetBtnText);
            if (matchBtn) matchBtn.click();
          }}
        }} catch (err) {{
          console.log("跳動觸發:", err);
        }}
      }}

      wrap.addEventListener("keydown", function(e) {{
        if (e.key === "Escape") {{
          rulerStartIdx = null;
          rulerEndIdx = null;
          rulerPreviewIdx = null;
          initDefault();
        }} else if (e.key === "ArrowUp") {{
          e.preventDefault();
          triggerFeihuStep(+1);
        }} else if (e.key === "ArrowDown") {{
          e.preventDefault();
          triggerFeihuStep(-1);
        }}
      }});
    }})();
    </script>
    """
    components.html(unified_interactive_html, height=675, scrolling=False)

# =========================================================
# 分頁二：⚡ 9大策略選股
# =========================================================
elif app_mode == "⚡ 9大策略選股":
    strat_cols = st.columns(len(ALL_STRATEGIES))
    for idx, strat_name in enumerate(ALL_STRATEGIES):
        with strat_cols[idx]:
            is_active = st.session_state.selected_synth_strat == strat_name
            btn_label = f"🔥 {strat_name}" if is_active else strat_name
            if st.button(btn_label, key=f"strat_btn_{idx}", use_container_width=True):
                st.session_state.selected_synth_strat = strat_name
                st.rerun()

    selected_strat = st.session_state.selected_synth_strat

    vol_mult_options = [500 * (2**i) for i in range(6)]
    val_up_options = [1.4, 1.8]

    dw_choice_cur = st.session_state.get("dw_choice_select", "日")
    min_dw_vol_cur = st.session_state.get("dw_vol_mult", 500)
    min_dw_val_cur = st.session_state.get("dw_val_up_sel", 1.4)

    is_dw_active = (min_dw_vol_cur != 500) or (
        abs(float(min_dw_val_cur) - 1.4) > 1e-6
    )
    tag_cls = "gold-tag-active" if is_dw_active else "gold-tag-idle"

    if os.path.exists(OUTPUT_CSV):
        try:
            df_res = pd.read_csv(OUTPUT_CSV, dtype={"代碼": str})
        except Exception:
            df_res = pd.DataFrame(columns=["策略名稱", "代碼"])
    else:
        df_res = pd.DataFrame(columns=["策略名稱", "代碼"])

    raw_strat_df = (
        df_res[df_res["策略名稱"] == selected_strat].copy()
        if not df_res.empty and "策略名稱" in df_res.columns
        else pd.DataFrame(columns=["策略名稱", "代碼"])
    )

    has_raw_candidates = not (
        raw_strat_df.empty
        or (
            len(raw_strat_df) == 1
            and raw_strat_df.iloc[0]["代碼"] in ["無", "無符合股票"]
        )
    )

    period_arg = "週線" if dw_choice_cur == "周" else "日線"
    col_v_name = f"最新{dw_choice_cur}量(張)"
    col_val_name = f"{dw_choice_cur}量比"

    if not has_raw_candidates:
        filtered_df = pd.DataFrame(columns=["策略名稱", "代碼"])
        status_msg = f"【{selected_strat}】尚無符合"
    else:
        filtered_df = raw_strat_df.copy()
        if "代碼" in filtered_df.columns:
            filtered_df["名稱"] = (
                filtered_df["代碼"]
                .astype(str)
                .str.zfill(4)
                .map(ID_TO_NAME)
                .fillna("")
            )
            metrics_rows = []
            for _, r_item in filtered_df.iterrows():
                raw_c = str(r_item["代碼"]).strip()
                if raw_c in ["", "無", "無符合股票"]:
                    metrics_rows.append({col_v_name: None, col_val_name: None})
                    continue
                c_code = raw_c.zfill(4) if raw_c.isdigit() else raw_c
                try:
                    _, _, _, c_v, _, v_rat = get_continuous_stock_df(
                        c_code, target_days=20, period_type=period_arg
                    )
                    metrics_rows.append({
                        col_v_name: int(round(float(c_v))),
                        col_val_name: round(float(v_rat), 2),
                    })
                except Exception:
                    metrics_rows.append({col_v_name: None, col_val_name: None})

            if metrics_rows:
                filtered_df = pd.concat(
                    [
                        filtered_df.reset_index(drop=True),
                        pd.DataFrame(metrics_rows).reset_index(drop=True),
                    ],
                    axis=1,
                )
                keep_mask = pd.Series([True] * len(filtered_df))
                if col_v_name in filtered_df.columns:
                    keep_mask = keep_mask & (
                        filtered_df[col_v_name].fillna(0) > min_dw_vol_cur
                    )
                if col_val_name in filtered_df.columns:
                    keep_mask = keep_mask & (
                        filtered_df[col_val_name].fillna(0.0)
                        > float(min_dw_val_cur)
                    )
                filtered_df = filtered_df[keep_mask].reset_index(drop=True)

        status_msg = (
            f"【{selected_strat}｜{dw_choice_cur}】{len(filtered_df)}檔"
            if not filtered_df.empty
            else (
                f"【{selected_strat}｜{dw_choice_cur}】0檔"
                if has_raw_candidates
                else f"【{selected_strat}】尚無符合"
            )
        )

    f_cols = st.columns(8, gap="small")

    with f_cols[0]:
        st.markdown(
            f'<span class="gold-row-anchor"></span><div class="gold-status-text">{status_msg}</div>',
            unsafe_allow_html=True,
        )
    with f_cols[1]:
        st.markdown(
            '<div class="gold-tag-box gold-dw-label">日/周</div>',
            unsafe_allow_html=True,
        )
    with f_cols[2]:
        st.selectbox(
            "日周",
            ["日", "周"],
            index=0,
            key="dw_choice_select",
            label_visibility="collapsed",
        )
    with f_cols[3]:
        st.markdown(
            f'<div class="gold-tag-box {tag_cls}">成交量&gt;</div>',
            unsafe_allow_html=True,
        )
    with f_cols[4]:
        st.selectbox(
            "成交量倍數",
            vol_mult_options,
            index=0,
            key="dw_vol_mult",
            label_visibility="collapsed",
        )
    with f_cols[5]:
        st.markdown(
            f'<div class="gold-tag-box {tag_cls}">值&gt;</div>',
            unsafe_allow_html=True,
        )
    with f_cols[6]:
        st.selectbox(
            "值門檻",
            val_up_options,
            index=0,
            key="dw_val_up_sel",
            label_visibility="collapsed",
        )
    with f_cols[7]:
        if st.button("🔄 重整", key="btn_refresh_dw_vol"):
            fetch_raw_history.clear()
            st.rerun()

    if has_raw_candidates and not filtered_df.empty:
        event = st.dataframe(
            filtered_df,
            use_container_width=True,
            hide_index=True,
            on_select="rerun",
            selection_mode="single-row",
        )
        selected_rows = event.selection.rows if hasattr(event, "selection") else []
        if selected_rows:
            row_idx = selected_rows[0]
            raw_code = str(filtered_df.iloc[row_idx]["代碼"]).strip()
            target_name = (
                str(filtered_df.iloc[row_idx]["名稱"])
                if "名稱" in filtered_df.columns
                else ""
            )
            matched_idx = find_stock_index_by_code(raw_code)
            if (
                matched_idx != -1
                and st.session_state.selected_index != matched_idx
            ):
                st.session_state.selected_index = matched_idx
                st.session_state.stock_select_version += 1

            display_code = raw_code.zfill(4) if raw_code.isdigit() else raw_code
            st.markdown("---")
            st.markdown(
                f"👉 您目前選中：**`{display_code}` {target_name}**，請選擇要直達的功能區："
            )

            nav_col1, nav_col2, nav_col3 = st.columns(3)
            with nav_col1:
                if st.button(
                    "📈 1. 直達個股籌碼圖表",
                    key="go_chart_from_strat",
                    use_container_width=True,
                ):
                    if matched_idx != -1:
                        st.session_state.selected_index = matched_idx
                        st.session_state.stock_select_version += 1
                    st.session_state.app_mode_state = "📈 個股籌碼圖表"
                    st.rerun()
            with nav_col2:
                if st.button(
                    "📊 2. 直達基本面與圖表",
                    key="go_fund_from_strat",
                    use_container_width=True,
                ):
                    if matched_idx != -1:
                        st.session_state.selected_index = matched_idx
                        st.session_state.stock_select_version += 1
                    st.session_state.app_mode_state = "📊 基本面與圖表"
                    st.rerun()
            with nav_col3:
                if st.button(
                    "⚡ 3. 留在9大策略選股",
                    key="stay_strat",
                    use_container_width=True,
                ):
                    st.rerun()

# =========================================================
# 分頁三：📋 大戶總表 (含大戶與羊群秒速籌碼選股 + 籌碼增幅榜)
# =========================================================
elif app_mode == "📋 大戶總表":
    st.markdown(
        '<p class="sub-header-14">⚡ 大戶與羊群秒速籌碼選股（CSV 無資料時自動改抓快取/總表，取前 10 檔）</p>',
        unsafe_allow_html=True,
    )

    col_s1, col_s2, col_s3, col_s4 = st.columns([1.4, 1.3, 1.3, 1.1])
    with col_s1:
        cross_type = st.radio(
            "選擇型態",
            ["🚀 黃金交叉 (大戶增)", "⚠️ 死亡交叉 (大戶減)"],
            horizontal=True,
            label_visibility="collapsed",
            key="chip_cross_type",
        )
    with col_s2:
        thresh_input = st.number_input(
            "近1週大戶變動 (>=)",
            min_value=-20.0,
            max_value=50.0,
            value=float(st.session_state.chip_1w_threshold_val),
            step=0.05,
            format="%.2f",
            key="chip_1w_thresh_input",
        )
        st.session_state.chip_1w_threshold_val = float(thresh_input)
    with col_s3:
        run_btn = st.button(
            "🚀 執行籌碼過濾（前10檔）",
            type="primary",
            use_container_width=True,
            key="btn_run_chip_screen",
        )
    with col_s4:
        if st.button(
            "📌 重設基準 0.00",
            use_container_width=True,
            key="btn_sync_csv_thresh",
        ):
            st.session_state.chip_1w_threshold_val = 0.00
            st.rerun()

    st.caption(
        f"📌 基準 `>= {st.session_state.chip_1w_threshold_val:.2f}`（最多取前 10 檔；若 `{SIGNAL_CSV_PATH}` 為「無資料」，會自動改抓快取或 Excel 總表計算）"
    )

    if run_btn:
        is_golden = "黃金交叉" in cross_type
        th_val = float(st.session_state.chip_1w_threshold_val)
        st.session_state.screened_results = _filter_chip_candidates(
            is_golden, th_val
        )
        if not st.session_state.screened_results:
            st.warning(
                f"目前 `近1週大戶變動 >= {th_val:.2f}` 無符合標的（若 `{SIGNAL_CSV_PATH}` 顯示「無資料」，請先執行集保抓取腳本更新 CSV 或快取）。"
            )

    if st.session_state.screened_results:
        df_chip_res = pd.DataFrame(st.session_state.screened_results)
        st.success(
            f"共選出前 {len(df_chip_res)} 檔（點股票列看「個股籌碼圖表」，或點右側「神秘金字塔」看趨勢圖）："
        )
        chip_event = st.dataframe(
            df_chip_res,
            column_config={
                "神秘金字塔": st.column_config.LinkColumn(
                    "🔗 神秘金字塔", display_text="📈 神秘金字塔"
                )
            },
            use_container_width=True,
            hide_index=True,
            on_select="rerun",
            selection_mode="single-row",
            key="df_chip_screen_table",
        )
        chip_selected_rows = (
            chip_event.selection.rows if hasattr(chip_event, "selection") else []
        )
        if chip_selected_rows:
            c_idx = chip_selected_rows[0]
            _jump_to_chart_with_code(
                str(df_chip_res.iloc[c_idx]["代碼"]).strip(),
                str(df_chip_res.iloc[c_idx]["名稱"]).strip()
                if "名稱" in df_chip_res.columns
                else "",
            )

    st.markdown("---")

    if os.path.exists(EXCEL_FILENAME):
        try:
            df_meta = pd.read_excel(
                EXCEL_FILENAME, sheet_name="大戶增幅前15名", nrows=1, header=None
            )
            week_info = (
                str(df_meta.iloc[0, 0])
                if not pd.isna(df_meta.iloc[0, 0])
                else "最新單週"
            )
            date_info = (
                str(df_meta.iloc[0, 4])
                if df_meta.shape[1] > 4 and not pd.isna(df_meta.iloc[0, 4])
                else ""
            )

            df_top15 = pd.read_excel(
                EXCEL_FILENAME, sheet_name="大戶增幅前15名", header=1
            )
            df_display = pd.DataFrame()
            df_display["代碼"] = df_top15["代碼"].apply(
                lambda x: str(x).strip().zfill(4)
            )
            df_display["名稱"] = df_top15["名稱"].astype(str).str.strip()
            if "大戶持有率_差異(%)" in df_top15.columns:
                df_display["大戶增幅(%)"] = df_top15["大戶持有率_差異(%)"].apply(
                    lambda x: f"+{float(x):.2f}%" if pd.notna(x) else ""
                )
            df_display["趨勢圖連結"] = df_top15["代碼"].apply(
                lambda x: _pyramid_link(str(x).strip().zfill(4))
            )

            c_title, c_btn = st.columns([3, 1])
            with c_title:
                st.markdown(
                    f'<p class="sub-header-14">📋 籌碼增幅榜 ｜ {week_info} ｜ {date_info}</p>',
                    unsafe_allow_html=True,
                )
            with c_btn:
                with open(EXCEL_FILENAME, "rb") as file:
                    st.download_button(
                        "📥 下載 Excel",
                        data=file,
                        file_name=EXCEL_FILENAME,
                        use_container_width=True,
                    )

            col_l, col_r = st.columns(2)
            link_cfg = {
                "趨勢圖連結": st.column_config.LinkColumn(
                    "🔗 連結", display_text="📈 金字塔"
                )
            }
            with col_l:
                st.dataframe(
                    df_display.iloc[:8],
                    column_config=link_cfg,
                    use_container_width=True,
                    hide_index=True,
                )
            with col_r:
                st.dataframe(
                    df_display.iloc[8:],
                    column_config=link_cfg,
                    use_container_width=True,
                    hide_index=True,
                )
        except Exception as e:
            st.error(f"讀取總表格式發生錯誤：{e}")
    else:
        st.warning(
            f"找不到總表檔案 (`{EXCEL_FILENAME}`)，請確認背景自動更新排程已順利執行。"
        )

# =========================================================
# 分頁四：📊 基本面與圖表
# =========================================================
elif app_mode == "📊 基本面與圖表":
    _tab4_fund = fetch_stock_fundamentals(stock_id)

    st.markdown(
        f'<p class="sub-header-14">📋 基本面分析表 ｜ [{stock_id}] {stock_name}</p>',
        unsafe_allow_html=True,
    )
    _m_cols = st.columns(4)
    _m_cols[0].metric("今日本益比", _tab4_fund.get("pe_str", "--"))
    _m_cols[1].metric("單季 EPS", _tab4_fund.get("eps_str", "--"))
    _m_cols[2].metric("近4季 EPS", _tab4_fund.get("eps_4q_str", "--"))
    _m_cols[3].metric("現金殖利率", _tab4_fund.get("yield_str", "--"))

    _latest_cash_div = _tab4_fund.get("latest_cash_div")
    _cash_div_str = (
        f"{float(_latest_cash_div):.2f} 元"
        if _latest_cash_div is not None and pd.notna(_latest_cash_div)
        else "--"
    )
    _fund_table_df = pd.DataFrame([
        {
            "證券代號": stock_id,
            "公司名稱": stock_name,
            "今日本益比": _tab4_fund.get("pe_str", "--"),
            "單季 EPS": _tab4_fund.get("eps_str", "--"),
            "近4季 EPS": _tab4_fund.get("eps_4q_str", "--"),
            "近一年現金股利": _cash_div_str,
            "現金殖利率": _tab4_fund.get("yield_str", "--"),
        }
    ])
    st.dataframe(_fund_table_df, use_container_width=True, hide_index=True)

    st.markdown(
        f'<p class="sub-header-14">📊 基本面趨勢圖表 ｜ [{stock_id}] {stock_name}</p>',
        unsafe_allow_html=True,
    )

    quarters = ["2024Q1", "2024Q2", "2024Q3", "2024Q4", "2025Q1"]
    data_sets = [
        {
            "title": "毛利率與營業利益率",
            "val1": [15.2, 16.5, 18.0, 17.2, 19.1],
            "val2": [8.1, 9.0, 10.5, 9.8, 11.2],
        },
        {
            "title": "單季營業收入與年增率",
            "val1": [12.5, 13.2, 14.1, 13.8, 15.0],
            "val2": [5.2, 6.1, 8.3, 7.0, 9.2],
        },
        {
            "title": "每股盈餘 (EPS)",
            "val1": [0.85, 0.92, 1.15, 1.02, 1.30],
            "val2": [],
        },
    ]

    plt.style.use("dark_background")
    cols = st.columns(2)
    for idx, ds in enumerate(data_sets):
        fig, ax = plt.subplots(figsize=(4.2, 2.0))
        ax.plot(
            quarters,
            ds["val1"],
            marker="o",
            markersize=3,
            color="#00FF66",
            linewidth=1.5,
        )
        if ds["val2"]:
            ax.plot(
                quarters,
                ds["val2"],
                marker="s",
                markersize=3,
                color="#00FFFF",
                linewidth=1.5,
            )
        ax.set_title(
            f"[{stock_id}] {ds['title']}",
            color="white",
            fontsize=9.0,
            fontweight="bold",
        )
        ax.tick_params(axis="both", labelsize=7.0, colors="#FFFFFF")
        ax.grid(True, linestyle=":", color="#555555", alpha=0.5)
        fig.tight_layout(pad=0.3)

        with cols[idx % 2]:
            with st.expander(f"📊 {ds['title']} (放大)", expanded=False):
                st.pyplot(fig, use_container_width=True)
