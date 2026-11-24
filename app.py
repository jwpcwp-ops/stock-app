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

# QT（每筆均量）預設參數規劃
QT_SMOOTH_WINDOW = 5
QT_SPIKE_RATIO = 1.45  # 超過近5根均量 1.45 倍視為「異常放大」

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

# 指標組合選單：波段、組合、組合1、組合2、組合3
INDICATOR_BUTTONS = ["波段", "組合", "組合1", "組合2", "組合3"]

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

        .qt-guide-box {
            background-color: #0c1017;
            border: 1px solid #00ffff;
            border-radius: 6px;
            padding: 8px 12px;
            margin: 4px 0 6px 0;
            color: #f8fafc;
            font-size: 12px;
            line-height: 1.55;
        }
        .qt-guide-title {
            color: #ffff00;
            font-weight: bold;
            font-size: 13px;
            margin-bottom: 4px;
        }
        .qt-bull-tag {
            color: #ff4444;
            font-weight: bold;
        }
        .qt-bear-tag {
            color: #00e64d;
            font-weight: bold;
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
    st.session_state.default_indicator_override = "組合2"
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
        tx_raw = row.get("tx_count", row.get("trades", None))
        tx_val = float(tx_raw) if tx_raw is not None and pd.notna(tx_raw) and float(tx_raw) > 0 else np.nan
        records.append({
            "date": idx.strftime(date_fmt),
            "open": o_val,
            "high": h_val,
            "low": l_val,
            "close": c_val,
            "vol": float(row["Volume"]) / 1000,
            "tx_count": tx_val,
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
            data = _fetch_json_url(
                url,
                {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
                    "Accept": "application/json, text/plain, */*",
                    "Referer": "https://www.tpex.org.tw/",
                },
            )
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
                        pe_v = _parse_pos_float(r_item[2]) if len(r_item) > 2 else None
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


def _compute_qt_series(df_full):
    """
    規劃計算 Q/T（每筆均量）：
    - 若有真實成交筆數欄位 tx_count (>0)，直接計算每筆均量 = 成交量 / 成交筆數
    - 若無成交筆數，則以「成交量 × (1 + 單根價格波幅權重)」推估每筆均量強度
    - 同時算出均線 qt_ma 與放大倍數 qt_ratio，並判斷高低檔異常放大
    """
    s_close = df_full["close"].astype(float)
    s_high = df_full["high"].astype(float)
    s_low = df_full["low"].astype(float)
    s_vol = df_full["vol"].astype(float).clip(lower=0.0)

    has_tx = (
        "tx_count" in df_full.columns
        and pd.to_numeric(df_full["tx_count"], errors="coerce").dropna().gt(0).any()
    )
    if has_tx:
        tx_s = pd.to_numeric(df_full["tx_count"], errors="coerce").replace(0, np.nan)
        tx_