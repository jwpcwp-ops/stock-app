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

# 飛狐上下方向鍵 K 線根數跳動序列：6, 11, 18, 29, 45, 69, 105, 159, 240...
FEIHU_BAR_STEPS = [6, 11, 18, 29, 45, 69, 105, 159, 240, 361, 543, 816]

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
            min-height: 26px !important;
            height: 26px !important;
            font-size: 10.5px !important;
            padding-left: 4px !important;
            padding-right: 4px !important;
        }

        div[data-testid="stPills"] button {
            font-size: 9.0px !important;
            padding: 2px 5px !important;
            margin: 0px 1px !important;
            min-height: 22px !important;
            height: 22px !important;
            border-radius: 4px !important;
            line-height: 1.1 !important;
            font-weight: bold !important;
        }
        div[data-testid="stPills"] {
            gap: 2px !important;
            flex-wrap: nowrap !important;
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

        /* 鎖定包含 gold-row-anchor 的控制列，強制整排所有元件高度統一為 30px 並完全水平置中對齊 */
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


def find_stock_index_by_code(code_str):
  clean_code = str(code_str).strip().replace(".0", "")
  candidates = [clean_code, clean_code.zfill(4)]
  for i, opt in enumerate(stock_options):
    opt_code = opt.split()[0].strip() if opt.split() else ""
    if opt_code in candidates:
      return i
  return -1


# ---------------------------------------------------------
# 5. 本地快取支援、資料抓取與基本面查詢
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
            s_id = str(data.get("stock_id", "")).strip()
            if s_id:
              cache_dict[s_id] = data
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
  elif period_type in ["週線", "周"]:
    yf_interval = "1wk"
    yf_period = "max"
  elif period_type == "月線":
    yf_interval = "1mo"
    yf_period = "max"
  elif period_type in ["日線", "日"]:
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

  if period_type in ["日線", "日"] and not df_yf.empty:
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


@st.cache_data(ttl=1800)
def fetch_stock_fundamentals(stock_id):
  """抓取個股基本面數據：今日本益比、單季 EPS、近 4 季 EPS 合計、殖利率。"""
  result = {
      "pe_str": "--",
      "eps_str": "--",
      "eps_4q_str": "--",
      "yield_str": "--",
  }
  clean_id = str(stock_id).strip()
  if not clean_id or clean_id == "99991":
    return result

  tickers = [f"{clean_id}.TW", f"{clean_id}.TWO"]
  info = {}
  last_price = None
  q_inc = None

  for tk in tickers:
    try:
      t = yf.Ticker(tk)
      tmp_info = t.info or {}
      if tmp_info and (
          tmp_info.get("regularMarketPrice")
          or tmp_info.get("currentPrice")
          or tmp_info.get("trailingPE")
          or tmp_info.get("trailingEps")
          or tmp_info.get("dividendYield")
      ):
        info = tmp_info
        last_price = (
            info.get("regularMarketPrice")
            or info.get("currentPrice")
            or info.get("previousClose")
        )
        try:
          q_inc = t.quarterly_income_stmt
        except Exception:
          q_inc = None
        break
    except Exception:
      continue

  if not info:
    return result

  single_eps = None
  eps_4q = None

  if q_inc is not None and not q_inc.empty:
    for r_name in ["Basic EPS", "Diluted EPS", "EPS"]:
      if r_name in q_inc.index:
        vals = (
            pd.to_numeric(q_inc.loc[r_name], errors="coerce").dropna().tolist()
        )
        if len(vals) >= 1:
          single_eps = float(vals[0])
        if len(vals) >= 4:
          eps_4q = float(sum(vals[:4]))
        elif len(vals) > 0:
          eps_4q = float(sum(vals))
        break

  if single_eps is None:
    q_eps_info = info.get("epsCurrentQuarter") or info.get(
        "epsTrailingTwelveMonths"
    )
    if q_eps_info is not None:
      try:
        single_eps = float(q_eps_info)
      except Exception:
        pass

  if eps_4q is None:
    ttm_eps = info.get("trailingEps")
    if ttm_eps is not None:
      try:
        eps_4q = float(ttm_eps)
      except Exception:
        pass

  pe_val = None
  if last_price is not None and eps_4q is not None and eps_4q > 0:
    try:
      pe_val = float(last_price) / float(eps_4q)
    except Exception:
      pe_val = None
  if pe_val is None:
    raw_pe = info.get("trailingPE") or info.get("forwardPE")
    if raw_pe is not None:
      try:
        v = float(raw_pe)
        if v > 0:
          pe_val = v
      except Exception:
        pass

  yield_pct = None
  raw_yield = info.get("dividendYield")
  if raw_yield is not None:
    try:
      y_f = float(raw_yield)
      yield_pct = y_f * 100.0 if y_f <= 0.5 else y_f
    except Exception:
      yield_pct = None

  if yield_pct is None:
    div_rate = info.get("dividendRate") or info.get("trailingAnnualDividendRate")
    if div_rate is not None and last_price is not None and float(last_price) > 0:
      try:
        yield_pct = (float(div_rate) / float(last_price)) * 100.0
      except Exception:
        yield_pct = None

  if pe_val is not None:
    result["pe_str"] = f"{pe_val:.2f}倍"
  if single_eps is not None:
    result["eps_str"] = f"{single_eps:.2f}元"
  if eps_4q is not None:
    result["eps_4q_str"] = f"{eps_4q:.2f}元"
  if yield_pct is not None:
    result["yield_str"] = f"{yield_pct:.2f}%"

  return result


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
  if stock_id in cache_dict:
    b_arr, s_arr, _ = extract_tdcc_arrays(cache_dict[stock_id])
    if len(b_arr) > 0 and len(s_arr) > 0:
      n_p = len(df_show)
      if len(b_arr) >= n_p:
        big_holder = np.array(b_arr[-n_p:])
        sheep_holder = np.array(s_arr[-n_p:])
      else:
        pad_len = n_p - len(b_arr)
        big_holder = np.concatenate([np.full(pad_len, b_arr[0]), b_arr])
        sheep_holder = np.concatenate([np.full(pad_len, s_arr[0]), s_arr])
    else:
      big_holder = np.full(len(df_show), 40.0)
      sheep_holder = np.full(len(df_show), 42.0)
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
    df,
    big_holder,
    sheep_holder,
    idx_r,
    selected_indicator,
    period_label,
    stock_id="",
):
  r = df.iloc[idx_r]
  df_slice = df.iloc[: idx_r + 1]

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
    dif_arr = "▲" if dif_v >= prev_dif else "▼"
    dem_arr = "▲" if dem_v >= prev_dem else "▼"
    osc_arr = "▲" if osc_v >= prev_osc else "▼"
    osc_col = "#FF3333" if osc_v >= 0 else "#00E64D"
    ind_tokens = [
        {"text": "MACD(長)", "color": "#FFFFFF"},
        {"text": "DIF::", "color": "#FF00FF"},
        {"text": f"{dif_v:.2f}{dif_arr}", "color": "#FF00FF"},
        {"text": "DEA::", "color": "#00FFFF"},
        {"text": f"{dem_v:.2f}{dem_arr}", "color": "#00FFFF"},
        {"text": "MACD::", "color": osc_col},
        {"text": f"{osc_v:.2f}{osc_arr}", "color": osc_col},
    ]
  elif selected_indicator == "BIAS":
    bias_v = float(r["bias_val"])
    prev_bias = float(df["bias_val"].iloc[idx_r - 1]) if idx_r > 0 else bias_v
    b_arr = "▲" if bias_v >= prev_bias else "▼"
    ind_tokens = [
        {"text": "BIAS(60)::", "color": "#FFFFFF"},
        {
            "text": f"{bias_v:.2f}%{b_arr}",
            "color": "#FF3333" if bias_v >= 0 else "#00E64D",
        },
    ]
  elif selected_indicator == "KDJ":
    k_diff = float(r["kdj_diff"])
    kd_arr = "▲" if k_diff >= 0 else "▼"
    ind_tokens = [
        {"text": "KD(9,3,3)", "color": "#FFFFFF"},
        {"text": "K::", "color": "#FF00FF"},
        {"text": f"{k_v:.2f}", "color": "#FF00FF"},
        {"text": "D::", "color": "#00FFFF"},
        {"text": f"{d_v:.2f}", "color": "#00FFFF"},
        {"text": "J::", "color": "#FFFFFF"},
        {"text": f"{j_v:.2f}", "color": "#FFFFFF"},
        {"text": "乖離::", "color": "#FFFF00"},
        {"text": f"{k_diff:.2f}{kd_arr}", "color": "#FFFF00"},
    ]
  elif selected_indicator == "RSI":
    r6_v = float(r["rsi_6"])
    r12_v = float(r["rsi_12"])
    rdiff_v = float(r["rsi_diff"])
    rd_arr = "▲" if rdiff_v >= 0 else "▼"
    ind_tokens = [
        {"text": "RSI(6,12)", "color": "#FFFFFF"},
        {"text": "RSI6::", "color": "#FF00FF"},
        {"text": f"{r6_v:.2f}", "color": "#FF00FF"},
        {"text": "RSI12::", "color": "#00FFFF"},
        {"text": f"{r12_v:.2f}", "color": "#00FF00"},
        {"text": "差值::", "color": "#FFFF00"},
        {"text": f"{rdiff_v:.2f}{rd_arr}", "color": "#FFFF00"},
    ]
  elif selected_indicator == "W%":
    wr_v = float(r["w_r"])
    prev_wr = float(df["w_r"].iloc[idx_r - 1]) if idx_r > 0 else wr_v
    w_arr = "▲" if wr_v >= prev_wr else "▼"
    ind_tokens = [
        {"text": "W%::", "color": "#FFFFFF"},
        {
            "text": f"{wr_v:.2f}%{w_arr}",
            "color": "#FF3333" if wr_v >= prev_wr else "#00E64D",
        },
    ]
  elif selected_indicator == "QT":
    qt_v = float(r["qt"])
    prev_qt = float(df["qt"].iloc[idx_r - 1]) if idx_r > 0 else qt_v
    q_arr = "▲" if qt_v >= prev_qt else "▼"
    ind_tokens = [
        {"text": "QT::", "color": "#FFFFFF"},
        {
            "text": f"{qt_v:.2f}{q_arr}",
            "color": "#FF3333" if qt_v >= prev_qt else "#00E64D",
        },
    ]
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
        {"text": "大戶::", "color": "#FFFFFF"},
        {"text": f"{b_val:.1f}%", "color": "#FF3333"},
        {"text": "散戶::", "color": "#FFFFFF"},
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
        {
            "text": f"{bosc_v:.2f}",
            "color": "#FF3333" if bosc_v >= 0 else "#00E64D",
        },
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

  prev_vol = float(df["vol"].iloc[idx_r - 1]) if idx_r > 0 else c_vol
  prev_v5 = float(df["vol_ma5"].iloc[idx_r - 1]) if idx_r > 0 else vol_ma5_v
  prev_v20 = float(df["vol_ma20"].iloc[idx_r - 1]) if idx_r > 0 else vol_ma20_v
  prev_vr5 = (
      prev_vol / prev_v5 if (idx_r > 0 and prev_v5 > 0) else v_ratio_5
  )
  prev_vr20 = (
      prev_vol / prev_v20 if (idx_r > 0 and prev_v20 > 0) else v_ratio_20
  )

  v_is_up = c_vol >= prev_vol
  v5_is_up = vol_ma5_v >= prev_v5
  vr5_is_up = v_ratio_5 >= prev_vr5
  v20_is_up = vol_ma20_v >= prev_v20
  vr20_is_up = v_ratio_20 >= prev_vr20

  vol_tokens = [
      {"text": "成交量::", "color": "#FFFFFF"},
      {
          "text": f"{int(c_vol)}{'▲' if v_is_up else '▼'}",
          "color": "#FF3333" if v_is_up else "#00E64D",
      },
      {"text": "5日::", "color": "#FFFF00"},
      {
          "text": f"{int(vol_ma5_v)}{'▲' if v5_is_up else '▼'}",
          "color": "#FF3333" if v5_is_up else "#00E64D",
      },
      {"text": "值5::", "color": "#FFFF00"},
      {
          "text": f"{v_ratio_5:.2f}{'▲' if vr5_is_up else '▼'}",
          "color": "#FF3333" if vr5_is_up else "#00E64D",
      },
      {"text": "20日::", "color": "#FF9900"},
      {
          "text": f"{int(vol_ma20_v)}{'▲' if v20_is_up else '▼'}",
          "color": "#FF3333" if v20_is_up else "#00E64D",
      },
      {"text": "20日值::", "color": "#FF9900"},
      {
          "text": f"{v_ratio_20:.2f}{'▲' if vr20_is_up else '▼'}",
          "color": "#FF3333" if vr20_is_up else "#00E64D",
      },
  ]

  o_up = c_open >= p_open
  h_up = c_high >= p_high
  l_up = c_low >= p_low
  c_up = c_close >= p_close
  vol_up = c_vol >= p_vol

  chg_pts = c_close - p_close
  chg_pct = (chg_pts / p_close * 100) if p_close > 0 else 0.0
  amp_pct = ((c_high - c_low) / p_close * 100) if p_close > 0 else 0.0
  chg_is_up = chg_pts >= 0
  chg_color = "#FF3333" if chg_is_up else "#00E64D"
  chg_label = "漲" if chg_is_up else "跌"

  header_tokens = [
      {"text": f"{c_date}", "color": "#FFFFFF"},
      {"text": "開:", "color": "#FFFFFF"},
      {
          "text": f"{c_open:.2f}{'▲' if o_up else '▼'}",
          "color": "#FF3333" if o_up else "#00E64D",
      },
      {"text": "高:", "color": "#FFFFFF"},
      {
          "text": f"{c_high:.2f}{'▲' if h_up else '▼'}",
          "color": "#FF3333" if h_up else "#00E64D",
      },
      {"text": "低:", "color": "#FFFFFF"},
      {
          "text": f"{c_low:.2f}{'▲' if l_up else '▼'}",
          "color": "#FF3333" if l_up else "#00E64D",
      },
      {"text": "收:", "color": "#FFFFFF"},
      {
          "text": f"{c_close:.2f}{'▲' if c_up else '▼'}",
          "color": "#FF3333" if c_up else "#00E64D",
      },
      {"text": "量:", "color": "#FFFFFF"},
      {
          "text": (
              f"{int(c_vol):,}{'張' if stock_id != '99991' else ''}"
              f"{'▲' if vol_up else '▼'}"
          ),
          "color": "#FF3333" if vol_up else "#00E64D",
      },
  ]

  if stock_id == "99991":
    header_tokens.extend([
        {"text": f"振:{amp_pct:.2f}%", "color": "#FFFF00"},
        {
            "text": (
                f"{chg_label}({abs(chg_pts):.2f}){chg_pct:.2f}%"
                f"{'▲' if chg_is_up else '▼'}"
            ),
            "color": chg_color,
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


# ---------------------------------------------------------
# 6. Session State 初始化
# ---------------------------------------------------------
if "selected_index" not in st.session_state:
  st.session_state.selected_index = 0
if "stock_select_version" not in st.session_state:
  st.session_state.stock_select_version = 0
if "selected_synth_strat" not in st.session_state:
  st.session_state.selected_synth_strat = "主力底部吃貨"
if "app_mode_state" not in st.session_state:
  st.session_state.app_mode_state = "📈 個股籌碼圖表"
if "k_bars_count" not in st.session_state:
  st.session_state.k_bars_count = 250
if "screened_results" not in st.session_state:
  st.session_state.screened_results = []
if "default_indicator_override" not in st.session_state:
  st.session_state.default_indicator_override = None

if "ma_active_map" not in st.session_state:
  st.session_state.ma_active_map = {
      "5": False,
      "10": False,
      "20": False,
      "35": False,
      "60": True,
      "120": False,
      "200": False,
      "分割": False,
  }

all_strategies = [
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


def step_feihu_bars(current_bars, direction):
  seq = FEIHU_BAR_STEPS
  if direction < 0:
    smaller = [v for v in seq if v < current_bars]
    return smaller[-1] if smaller else seq[0]
  else:
    larger = [v for v in seq if v > current_bars]
    return larger[0] if larger else seq[-1]


# ---------------------------------------------------------
# 7. 網頁主介面佈局
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
  stock_id = selected_stock.split()[0]
  stock_name = (
      selected_stock.split()[1] if len(selected_stock.split()) > 1 else ""
  )

with top_cols[1]:
  chart_period = st.selectbox(
      "週期",
      ["日線", "60分", "週線", "月線"],
      index=0,
      label_visibility="collapsed",
      key="select_period_dropdown_top",
  )
  actual_chart_period = chart_period

with top_cols[2]:
  if st.button("📈 個股籌碼圖表", use_container_width=True, key="top_go_chart"):
    st.session_state.app_mode_state = "📈 個股籌碼圖表"
    st.rerun()

with top_cols[3]:
  if st.button("⚡ 9大策略選股", use_container_width=True, key="top_go_strat"):
    st.session_state.app_mode_state = "⚡ 9大策略選股"
    st.rerun()

with top_cols[4]:
  if st.button("📋 大戶總表", use_container_width=True, key="top_go_table"):
    st.session_state.app_mode_state = "📋 大戶總表"
    st.rerun()

with top_cols[5]:
  if st.button("📊 基本面與圖表", use_container_width=True, key="top_go_fund"):
    st.session_state.app_mode_state = "📊 基本面與圖表"
    st.rerun()

app_mode = st.session_state.app_mode_state

# =========================================================
# 分頁一：📈 個股籌碼圖表
# =========================================================
if app_mode == "📈 個股籌碼圖表":
  third_row_cols = st.columns([1.25, 0.90, 1.05])

  with third_row_cols[0]:
    ma_items = ["5", "10", "20", "35", "60", "120", "200", "分割"]
    ma_btn_cols = st.columns(len(ma_items))
    for idx_m, m_key in enumerate(ma_items):
      is_on = st.session_state.ma_active_map.get(m_key, False)
      with ma_btn_cols[idx_m]:
        lbl = f"●{m_key}" if is_on else f"○{m_key}"
        if st.button(lbl, key=f"ma_toggle_{m_key}", use_container_width=True):
          st.session_state.ma_active_map[m_key] = not is_on
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
                        box-shadow: 0 0 5px {line_col} !important;
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
                    }}
                """
        )
    st.markdown(
        f"<style>{''.join(active_css_rules)}</style>", unsafe_allow_html=True
    )

  with third_row_cols[1]:
    default_ind_val = (
        st.session_state.default_indicator_override
        if st.session_state.default_indicator_override
        else "MACD"
    )
    if st.session_state.default_indicator_override:
      st.session_state["pills_ind"] = st.session_state.default_indicator_override
      st.session_state.default_indicator_override = None

    selected_indicator = st.pills(
        "指標",
        ["波段", "MACD", "BIAS", "KDJ", "RSI", "W%", "QT", "大戶羊群"],
        default=default_ind_val,
        selection_mode="single",
        label_visibility="collapsed",
        key="pills_ind",
    )
    if not selected_indicator:
      selected_indicator = "MACD"

  with third_row_cols[2]:
    row_bar_cols = st.columns([0.55, 0.55, 0.55, 0.55, 0.55, 0.65])
    preset_vals = [120, 250, 500]
    for p_idx, p_val in enumerate(preset_vals):
      with row_bar_cols[p_idx]:
        is_cur = st.session_state.k_bars_count == p_val
        if st.button(
            str(p_val),
            key=f"btn_preset_{p_val}",
            use_container_width=True,
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
      st.markdown(
          f"<div style='color:#00FFFF; font-size:10px; font-weight:bold;"
          f" text-align:right; line-height:22px; white-space:nowrap;'>K:{st.session_state.k_bars_count}</div>",
          unsafe_allow_html=True,
      )

  k_days_choice = int(st.session_state.k_bars_count)

  ma_map = st.session_state.ma_active_map
  show_ma5 = ma_map.get("5", False)
  show_ma10 = ma_map.get("10", False)
  show_ma20 = ma_map.get("20", False)
  show_ma35 = ma_map.get("35", False)
  show_ma60 = ma_map.get("60", True)
  show_ma120 = ma_map.get("120", False)
  show_ma200 = ma_map.get("200", False)
  show_fib = ma_map.get("分割", False)

  df, big_holder, sheep_holder, cur_vol, cur_20ma, v_ratio = (
      get_continuous_stock_df(
          stock_id, target_days=k_days_choice, period_type=actual_chart_period
      )
  )

  ma_config = {
      "5": (5, show_ma5, MA_COLOR_MAP["5"]),
      "10": (10, show_ma10, MA_COLOR_MAP["10"]),
      "20": (20, show_ma20, MA_COLOR_MAP["20"]),
      "35": (35, show_ma35, MA_COLOR_MAP["35"]),
      "60": (60, show_ma60, MA_COLOR_MAP["60"]),
      "120": (120, show_ma120, MA_COLOR_MAP["120"]),
      "200": (200, show_ma200, MA_COLOR_MAP["200"]),
  }

  deduct_periods = [5, 35, 65, 120, 200]
  deduct_indices = {}
  n_len = len(df)
  for p in deduct_periods:
    idx_pos = n_len - p
    deduct_indices[p] = idx_pos if 0 <= idx_pos < n_len else 0

  BG_COLOR, PANEL_BG, GRID_COLOR = "#000000", "#000000", "#333333"
  BAR_UP_COLOR, BAR_DOWN_COLOR = "#FF3333", "#00E64D"

  prev_closes = df["close"].shift(1).fillna(df["open"])
  body_colors = [
      BAR_UP_COLOR if c >= o else BAR_DOWN_COLOR
      for o, c, pc in zip(df["open"], df["close"], prev_closes)
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
  fig = plt.figure(figsize=(10.0, 4.65))

  if is_wave_mode:
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
  body_height = np.maximum(np.abs(df["close"].values - df["open"].values), 0.01)
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
    ax1.set_ylim(p_min - p_range * 0.08, p_max + p_range * 0.15)
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

  for count_days in [5, 35, 65, 120, 200]:
    if count_days in deduct_indices:
      idx_pos = deduct_indices[count_days]
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

  for ma_name, (period, is_show, color) in ma_config.items():
    if is_show:
      ma_series = df[f"ma_{period}"].ffill().bfill()
      ax1.plot(
          x,
          ma_series.values,
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
          price_val, color="#00FFFF", linestyle=":", linewidth=1.1, alpha=0.95
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
  band_height = (ymax_lim - ymin_lim) * 0.035
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

  ax1.yaxis.tick_right()
  ax1.tick_params(axis="y", labelsize=6.5, pad=1.0, colors="#FFFFFF")
  plt.setp(ax1.get_xticklabels(), visible=False)
  ax1.grid(True, which="both", linestyle="--", color=GRID_COLOR, alpha=0.5)

  if is_wave_mode:
    ax_sub1.set_facecolor(PANEL_BG)
    ax_sub1.bar(
        x,
        df["band_macd_osc"],
        width=0.75,
        color=band_macd_bar_colors,
        edgecolor="none",
        linewidth=0,
        alpha=1.0,
        zorder=2,
    )
    ax_sub1.plot(
        x,
        df["band_macd_dif"],
        linewidth=0.6,
        color="#FFFF00",
        label="DIF",
        zorder=3,
    )
    ax_sub1.plot(
        x,
        df["band_macd_dem"],
        linewidth=0.6,
        color="#FF3333",
        label="MACD",
        zorder=3,
    )
    ax_sub1.axhline(0, color="#777777", linestyle=":", linewidth=1.0)
    ax_sub1.yaxis.tick_right()
    ax_sub1.tick_params(axis="y", labelsize=6.5, pad=1.0, colors="#FFFFFF")
    plt.setp(ax_sub1.get_xticklabels(), visible=False)
    ax_sub1.grid(
        True, which="both", linestyle="--", color=GRID_COLOR, alpha=0.5
    )

    ax_sub2.set_facecolor(PANEL_BG)
    ax_sub2.plot(
        x,
        df["band_bias_val_rev"],
        linewidth=0.65,
        color="#00FFFF",
        label="BIAS(反向)",
        zorder=3,
    )
    ax_sub2.axhline(0, color="#777777", linestyle=":", linewidth=1.0)
    ax_sub2.yaxis.tick_right()
    ax_sub2.tick_params(axis="y", labelsize=6.5, pad=1.0, colors="#FFFFFF")
    plt.setp(ax_sub2.get_xticklabels(), visible=False)
    ax_sub2.grid(
        True, which="both", linestyle="--", color=GRID_COLOR, alpha=0.5
    )

    ax_sub3.set_facecolor(PANEL_BG)
    ax_sub3.plot(
        x, df["mtm_val"], linewidth=0.65, color="#FFFF00", label="MTM", zorder=3
    )
    ax_sub3.plot(
        x, df["mtm_ma1"], linewidth=0.65, color="#00FF66", label="Avg", zorder=3
    )
    ax_sub3.axhline(0, color="#777777", linestyle=":", linewidth=1.0)
    ax_sub3.yaxis.tick_right()
    ax_sub3.tick_params(axis="y", labelsize=6.5, pad=1.0, colors="#FFFFFF")
    ax_sub3.tick_params(axis="x", labelsize=7.5, colors="#FFFFFF")
    plt.setp(ax_sub3.get_xticklabels(), visible=True)
    for label in ax_sub3.get_xticklabels():
      label.set_color("#FFFFFF")
      label.set_fontsize(7.5)
    ax_sub3.grid(
        True, which="both", linestyle="--", color=GRID_COLOR, alpha=0.5
    )
  else:
    ax_sub1.set_facecolor(PANEL_BG)
    if selected_indicator == "MACD":
      ax_sub1.bar(
          x,
          df["macd_osc"],
          width=0.75,
          color=macd_bar_colors,
          edgecolor="none",
          linewidth=0,
          alpha=1.0,
          zorder=2,
      )
      ax_sub1.plot(
          x,
          df["macd_dif"],
          linewidth=0.6,
          color="#FF00FF",
          label="DIF",
          zorder=3,
      )
      ax_sub1.plot(
          x,
          df["macd_dem"],
          linewidth=0.6,
          color="#00FFFF",
          label="DEA",
          zorder=3,
      )
    elif selected_indicator == "BIAS":
      ax_sub1.plot(
          x,
          df["bias_val"],
          linewidth=0.6,
          color="#FFFF00",
          label="BIAS(60)",
          zorder=3,
      )
    elif selected_indicator == "KDJ":
      ax_sub1.plot(
          x, df["kdj_k"], linewidth=0.6, color="#FF00FF", label="K", zorder=3
      )
      ax_sub1.plot(
          x, df["kdj_d"], linewidth=0.6, color="#00FFFF", label="D", zorder=3
      )
      ax_sub1.plot(
          x, df["kdj_j"], linewidth=0.6, color="#FFFFFF", label="J", zorder=3
      )
    elif selected_indicator == "RSI":
      ax_sub1.plot(
          x, df["rsi_6"], linewidth=0.6, color="#FF00FF", label="RSI6", zorder=3
      )
      ax_sub1.plot(
          x,
          df["rsi_12"],
          linewidth=0.6,
          color="#00FFFF",
          label="RSI12",
          zorder=3,
      )
    elif selected_indicator == "W%":
      ax_sub1.plot(
          x, df["w_r"], linewidth=0.6, color="#FFFF00", label="W%", zorder=3
      )
    elif selected_indicator == "QT":
      ax_sub1.bar(
          x,
          df["qt"],
          width=0.75,
          color=qt_bar_colors,
          edgecolor="none",
          linewidth=0,
          alpha=1.0,
          zorder=2,
      )
    elif selected_indicator == "大戶羊群":
      if len(big_holder) > 0 and len(sheep_holder) > 0:
        b_plot = np.asarray(big_holder[-len(df) :], dtype=float)
        s_plot = np.asarray(sheep_holder[-len(df) :], dtype=float)
        ax_sub1.plot(
            x,
            b_plot,
            color="#FF3333",
            linewidth=1.15,
            linestyle="-",
            label="大戶(%)",
            zorder=4,
        )
        ax_sub1.plot(
            x,
            s_plot,
            color="#00E64D",
            linewidth=1.15,
            linestyle="-",
            label="羊群(%)",
            zorder=4,
        )

        comb = np.concatenate([b_plot, s_plot])
        comb = comb[np.isfinite(comb)]
        if len(comb) > 0:
          y_lo = float(np.min(comb))
          y_hi = float(np.max(comb))
          span = max(y_hi - y_lo, 4.0)
          pad = span * 0.18
          ax_sub1.set_ylim(max(0.0, y_lo - pad), min(100.0, y_hi + pad))

          mid_ref = float(np.mean(comb))
          ax_sub1.axhline(
              mid_ref, color="#666666", linestyle=":", linewidth=0.9, zorder=2
          )

    if selected_indicator != "大戶羊群":
      ax_sub1.axhline(0, color="#777777", linestyle=":", linewidth=1.0)
    ax_sub1.yaxis.tick_right()
    ax_sub1.tick_params(axis="y", labelsize=6.5, pad=1.0, colors="#FFFFFF")
    plt.setp(ax_sub1.get_xticklabels(), visible=False)
    ax_sub1.grid(
        True, which="both", linestyle="--", color=GRID_COLOR, alpha=0.5
    )

    ax_sub2.set_facecolor(PANEL_BG)
    ax_sub2.bar(
        x,
        df["vol"],
        width=0.75,
        color=body_colors,
        edgecolor="none",
        linewidth=0,
        alpha=1.0,
        zorder=2,
    )
    ax_sub2.plot(
        x,
        df["vol_ma5"],
        linewidth=0.6,
        color="#FFFF00",
        label="Vol MA5",
        alpha=0.95,
        zorder=3,
    )
    ax_sub2.plot(
        x,
        df["vol_ma20"],
        linewidth=0.6,
        color="#FF9900",
        label="Vol MA20",
        alpha=0.95,
        zorder=3,
    )
    ax_sub2.yaxis.tick_right()
    ax_sub2.tick_params(axis="y", labelsize=6.5, pad=1.0, colors="#FFFFFF")
    ax_sub2.tick_params(axis="x", labelsize=7.5, colors="#FFFFFF")
    plt.setp(ax_sub2.get_xticklabels(), visible=True)
    for label in ax_sub2.get_xticklabels():
      label.set_color("#FFFFFF")
      label.set_fontsize(7.5)
    ax_sub2.grid(
        True, which="both", linestyle="--", color=GRID_COLOR, alpha=0.5
    )

  for ax in axes:
    for spine in ax.spines.values():
      spine.set_visible(True)
      spine.set_color("#777777")
      spine.set_linewidth(1.2)

  bottom_margin = 0.08
  plt.subplots_adjust(
      left=0.008, right=0.965, top=0.98, bottom=bottom_margin, hspace=0.10
  )

  fig.canvas.draw()
  ax1_bbox = ax1.get_position()
  ax_sub1_bbox = ax_sub1.get_position()
  ax_sub2_bbox = ax_sub2.get_position()
  ax_sub3_bbox = ax_sub3.get_position() if ax_sub3 is not None else None

  ax_x0 = float(ax1_bbox.x0)
  ax_x1 = float(ax1_bbox.x1)

  ax1_top_frac = float(1.0 - ax1_bbox.y1)
  sub1_top_frac = float(1.0 - ax_sub1_bbox.y1)
  sub2_top_frac = float(1.0 - ax_sub2_bbox.y1)
  sub3_top_frac = (
      float(1.0 - ax_sub3_bbox.y1) if ax_sub3_bbox is not None else 0.0
  )

  buf = BytesIO()
  fig.savefig(
      buf, format="png", dpi=150, facecolor=BG_COLOR, edgecolor="none"
  )
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
        v_prev = (
            float(df[f"ma_{period}"].iloc[idx_r - 1])
            if idx_r > 0
            else v_now
        )
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
    snap.update(fund_data)
    feihu_rev_no = total_bars_cnt - idx_r

    payload_rows.append({
        "rev_no": feihu_rev_no,
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
  plot_height = 675
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
    .t-row {{
      font-size: 11px;
      line-height: 1.3;
      margin-bottom: 1px;
      display: flex;
      justify-content: space-between;
    }}
    .t-label {{ color: #ffff00; font-weight: bold; }}
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
        <div class="terminal-title">【均線解盤】</div>
        <div class="t-row"><span class="t-label">狀態:</span><span id="p-ma-status" class="{init_snap.get("ma_cls", "t-val-white")}">{init_snap.get("ma_status", "")}</span></div>
        <div class="t-row"><span class="t-label">MA5:</span><span id="p-ma5" class="t-val-cyan">{init_snap.get("ma5", "")}</span></div>
        <div class="t-row"><span class="t-label">MA20:</span><span id="p-ma20" class="t-val-cyan">{init_snap.get("ma20", "")}</span></div>
        <div class="t-row"><span class="t-label">季60:</span><span id="p-ma60" class="t-val-cyan">{init_snap.get("ma60", "")}</span></div>
      </div>

      <div class="terminal-panel">
        <div class="terminal-title">【區間漲跌幅】</div>
        <div class="t-row"><span class="t-label">近30高:</span><span id="p-high30" class="t-val-cyan">{init_snap.get("high30", "")}</span></div>
        <div class="t-row"><span class="t-label">近30低:</span><span id="p-low30" class="t-val-cyan">{init_snap.get("low30", "")}</span></div>
        <div class="t-row"><span class="t-label">回檔幅:</span><span id="p-drop" class="t-val-green">{init_snap.get("drop_pct", "")}</span></div>
        <div class="t-row"><span class="t-label">彈升幅:</span><span id="p-rise" class="t-val-red">{init_snap.get("rise_pct", "")}</span></div>
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
        <div class="t-row"><span class="t-label">紅天數:</span><span id="p-red" class="t-val-red">{init_snap.get("red_days", "")}</span></div>
        <div class="t-row"><span class="t-label">綠天數:</span><span id="p-green" class="t-val-green">{init_snap.get("green_days", "")}</span></div>
      </div>

      <div class="terminal-panel">
        <div class="terminal-title">【基本面快訊】</div>
        <div class="t-row"><span class="t-label">今日本益比:</span><span id="p-pe" class="t-val-cyan">{init_snap.get("pe_str", "--")}</span></div>
        <div class="t-row"><span class="t-label">EPS:</span><span id="p-eps" class="t-val-white">{init_snap.get("eps_str", "--")}</span></div>
        <div class="t-row"><span class="t-label">近4季EPS:</span><span id="p-eps4q" class="t-val-red">{init_snap.get("eps_4q_str", "--")}</span></div>
        <div class="t-row"><span class="t-label">殖利率:</span><span id="p-yield" class="t-val-green">{init_snap.get("yield_str", "--")}</span></div>
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
    const isWaveMode = {str(is_wave_mode).lower()};
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
    let lastHoverPos = null;

    function setEl(id, text, cls) {{
      const el = document.getElementById(id);
      if (!el) return;
      el.textContent = text;
      if (cls) el.className = cls;
    }}

    function syncAnalysisPanel(r) {{
      if (!r || !r.snap) return;
      const s = r.snap;
      setEl("p-ma-status", s.ma_status, s.ma_cls);
      setEl("p-ma5", s.ma5);
      setEl("p-ma20", s.ma20);
      setEl("p-ma60", s.ma60);

      setEl("p-high30", s.high30);
      setEl("p-low30", s.low30);
      setEl("p-drop", s.drop_pct);
      setEl("p-rise", s.rise_pct);

      setEl("p-kdj-sig", s.kdj_sig, s.kdj_cls);
      setEl("p-kd", s.kd_str);
      setEl("p-j", s.j_str);
      setEl("p-kddiff", s.kd_diff);

      setEl("p-vratio", s.vol_ratio, s.vol_cls);
      setEl("p-vstatus", s.vol_status);
      setEl("p-vval", s.vol_str);

      setEl("p-trend", s.trend_txt, s.trend_cls);
      setEl("p-wave", s.wave_txt, s.wave_cls);
      setEl("p-red", s.red_days);
      setEl("p-green", s.green_days);

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

    function drawTokensRow(tokens, startX, yPos, fontStr, baseGap) {{
      let curX = startX;
      (tokens || []).forEach((tk) => {{
        drawOutlinedText(tk.text, curX, yPos, tk.color, fontStr, 1.3);
        const w = ctx.measureText(tk.text).width;
        const isLabel = tk.text.endsWith("::") || tk.text.endsWith(":");
        const extra = isLabel ? 5.5 : (baseGap || 13.0);
        curX += w + extra;
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
        ctx.stroke();

        ctx.beginPath();
        ctx.moveTo(plotLeft, lineY);
        ctx.lineTo(plotRight, lineY);
        ctx.stroke();
        ctx.restore();
      }}

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

      const badgeX = plotLeft + b.width * 0.72;
      drawOutlinedText(s.trend_badge || "", badgeX, headerY, s.trend_badge_color || "#FF3333", fontHeader, 1.3);

      const revX = plotLeft + b.width * 0.815;
      drawOutlinedText(`逆序:${{r.rev_no}}`, revX, headerY, "#00FFFF", fontHeader, 1.3);

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
      if (isWaveMode) {{
        const s1Y = b.top + b.height * (sub1TopFrac + 0.014);
        drawTokensRow(s.ind_tokens, headerX, s1Y, fontSub, 14.0);

        const s2Y = b.top + b.height * (sub2TopFrac + 0.014);
        drawTokensRow(s.sub2_tokens, headerX, s2Y, fontSub, 14.0);

        const s3Y = b.top + b.height * (sub3TopFrac + 0.014);
        drawTokensRow(s.sub3_tokens, headerX, s3Y, fontSub, 14.0);
      }} else {{
        const sub1Y = b.top + b.height * (sub1TopFrac + 0.016);
        drawTokensRow(s.ind_tokens, headerX, sub1Y, fontSub, 14.0);

        const sub2Y = b.top + b.height * (sub2TopFrac + 0.016);
        drawTokensRow(s.vol_tokens, headerX, sub2Y, fontSub, 15.0);
      }}
    }}

    function onHover(clientX, clientY) {{
      const b = getImgBounds();
      if (b.width <= 0 || b.height <= 0 || totalBars <= 0) return;

      const plotLeft = b.left + b.width * axX0;
      const plotRight = b.left + b.width * axX1;
      const plotW = Math.max(10, plotRight - plotLeft);
      const wRect = wrap.getBoundingClientRect();

      const relX = clientX - wRect.left;
      const frac = (relX - plotLeft) / plotW;
      const barPos = xMinBar + frac * (xMaxBar - xMinBar);
      let idx = Math.round(barPos);
      if (idx < 0) idx = 0;
      if (idx >= totalBars) idx = totalBars - 1;

      const r = rows[idx];
      const fracIdx = (idx - xMinBar) / (xMaxBar - xMinBar);
      const lineX = plotLeft + fracIdx * plotW;
      const lineY = clientY ? (clientY - wRect.top) : (b.top + b.height * 0.35);

      lastHoverPos = {{ r, lineX, lineY, b }};
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
      if (e.button === 0) {{
        wrap.focus();
        crosshairEnabled = !crosshairEnabled;
        onHover(e.clientX, e.clientY);
      }}
    }});

    canvas.addEventListener("mousemove", function(e) {{
      onHover(e.clientX, e.clientY);
    }});

    canvas.addEventListener("mouseleave", function() {{
      lastHoverPos = null;
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
          if (matchBtn) {{
            matchBtn.click();
          }}
        }}
      }} catch (err) {{
        console.log("跳動觸發:", err);
      }}
    }}

    wrap.addEventListener("keydown", function(e) {{
      if (e.key === "ArrowUp") {{
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
  components.html(unified_interactive_html, height=plot_height, scrolling=False)

# =========================================================
# 分頁二：⚡ 9大策略選股 (偏重技術分析)
# =========================================================
elif app_mode == "⚡ 9大策略選股":
  strat_cols = st.columns(len(all_strategies))
  for idx, strat_name in enumerate(all_strategies):
    with strat_cols[idx]:
      is_active = st.session_state.selected_synth_strat == strat_name
      btn_label = f"🔥 {strat_name}" if is_active else strat_name
      if st.button(
          btn_label, key=f"strat_btn_{idx}", use_container_width=True
      ):
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

  output_csv = "smart_selected_output.csv"
  if os.path.exists(output_csv):
    try:
      df_res = pd.read_csv(output_csv, dtype={"代碼": str})
    except Exception:
      df_res = pd.DataFrame(columns=["策略名稱", "代碼"])
  else:
    df_res = pd.DataFrame(columns=["策略名稱", "代碼"])

  if not df_res.empty and "策略名稱" in df_res.columns:
    raw_strat_df = df_res[df_res["策略名稱"] == selected_strat].copy()
  else:
    raw_strat_df = pd.DataFrame(columns=["策略名稱", "代碼"])

  has_raw_candidates = not (
      raw_strat_df.empty
      or (
          len(raw_strat_df) == 1
          and raw_strat_df.iloc[0]["代碼"] in ["無", "無符合股票"]
      )
  )

  if not has_raw_candidates:
    filtered_df = pd.DataFrame(columns=["策略名稱", "代碼"])
    status_msg = f"【{selected_strat}】尚無符合"
  else:
    id_to_name = dict(
        zip(
            stock_df["代碼"].astype(str).str.zfill(4),
            stock_df["名稱"].astype(str),
        )
    )
    filtered_df = raw_strat_df.copy()
    if "代碼" in filtered_df.columns:
      filtered_df["名稱"] = filtered_df["代碼"].map(id_to_name).fillna("")

    period_arg = "週線" if dw_choice_cur == "周" else "日線"
    col_v_name = f"最新{dw_choice_cur}量(張)"
    col_val_name = f"{dw_choice_cur}量比"

    metrics_rows = []
    if "代碼" in filtered_df.columns:
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
      df_m = pd.DataFrame(metrics_rows)
      filtered_df = pd.concat(
          [filtered_df.reset_index(drop=True), df_m.reset_index(drop=True)],
          axis=1,
      )
      keep_mask = pd.Series([True] * len(filtered_df))
      if col_v_name in filtered_df.columns:
        keep_mask = keep_mask & (
            filtered_df[col_v_name].fillna(0) > min_dw_vol_cur
        )
      if col_val_name in filtered_df.columns:
        keep_mask = keep_mask & (
            filtered_df[col_val_name].fillna(0.0) > float(min_dw_val_cur)
        )
      filtered_df = filtered_df[keep_mask].reset_index(drop=True)

    if filtered_df.empty:
      status_msg = f"【{selected_strat}｜{dw_choice_cur}】0檔"
    else:
      status_msg = f"【{selected_strat}｜{dw_choice_cur}】{len(filtered_df)}檔"

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
      if matched_idx != -1 and st.session_state.selected_index != matched_idx:
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
      '<p class="sub-header-14">⚡ 大戶與羊群秒速籌碼選股（點擊個股列直接跳轉圖表）</p>',
      unsafe_allow_html=True,
  )

  col_s1, col_s2, col_s3, col_s4 = st.columns([1.3, 1.3, 1.3, 1.1])
  with col_s1:
    cross_type = st.radio(
        "選擇型態",
        ["🚀 黃金交叉", "⚠️ 死亡交叉"],
        horizontal=True,
        label_visibility="collapsed",
        key="chip_cross_type",
    )
  with col_s2:
    recent_weeks = st.slider(
        "最近幾週內", 1, 8, 3, 1, key="chip_recent_weeks"
    )
  with col_s3:
    min_big_holder = st.slider(
        "大戶持股最低 (%)", 30.0, 70.0, 40.0, 1.0, key="chip_min_big"
    )
  with col_s4:
    run_btn = st.button(
        "🚀 執行籌碼過濾",
        type="primary",
        use_container_width=True,
        key="btn_run_chip_screen",
    )

  if run_btn:
    with st.spinner("正在掃描 219 檔大戶與羊群集保籌碼..."):
      matched_results = []
      is_golden_search = "黃金交叉" in cross_type
      cache_dict = load_local_cache_cached()

      for _, row in stock_df.iterrows():
        s_id = str(row["代碼"]).strip()
        s_name = str(row["名稱"]).strip()
        if s_id == "99991":
          continue

        if s_id in cache_dict:
          big_h, sheep_h, w_dates = extract_tdcc_arrays(cache_dict[s_id])
        else:
          np.random.seed(int(s_id) if s_id.isdigit() else 42)
          big_h = (38.0 + np.cumsum(np.random.randn(60) * 0.4)).tolist()
          sheep_h = (42.0 + np.cumsum(np.random.randn(60) * 0.3)).tolist()
          w_dates = (
              pd.date_range(end=datetime.today(), periods=60, freq="W")
              .strftime("%Y-%m-%d")
              .tolist()
          )

        n_periods = len(big_h)
        if n_periods < 2 or float(big_h[-1]) < min_big_holder:
          continue

        g_crs, d_crs = [], []
        for i in range(1, n_periods):
          if big_h[i - 1] <= sheep_h[i - 1] and big_h[i] > sheep_h[i]:
            g_crs.append(i)
          elif big_h[i - 1] >= sheep_h[i - 1] and big_h[i] < sheep_h[i]:
            d_crs.append(i)

        target_crosses = g_crs if is_golden_search else d_crs
        recent_hit = [
            idx for idx in target_crosses if (n_periods - 1 - idx) < recent_weeks
        ]

        if recent_hit:
          last_hit_idx = recent_hit[-1]
          hit_date = (
              w_dates[last_hit_idx] if last_hit_idx < len(w_dates) else ""
          )
          matched_results.append({
              "代碼": s_id,
              "名稱": s_name,
              "訊號": "★ 黃金交叉" if is_golden_search else "✖ 死亡交叉",
              "訊號日期": hit_date,
              "最新大戶(%)": round(float(big_h[-1]), 1),
              "最新散戶(%)": round(float(sheep_h[-1]), 1),
          })
      st.session_state.screened_results = matched_results

  if st.session_state.screened_results:
    df_chip_res = pd.DataFrame(st.session_state.screened_results)
    st.success(
        f"籌碼篩選完成！共找到 {len(df_chip_res)} 檔符合條件個股（直接點擊下方任一股票列，立即開啟該股籌碼圖表）："
    )

    chip_event = st.dataframe(
        df_chip_res,
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
      picked_code = str(df_chip_res.iloc[c_idx]["代碼"]).strip()
      matched_idx = find_stock_index_by_code(picked_code)
      if matched_idx != -1:
        st.session_state.selected_index = matched_idx
        st.session_state.stock_select_version += 1
        st.session_state.default_indicator_override = "大戶羊群"
        st.session_state.app_mode_state = "📈 個股籌碼圖表"
        st.rerun()

  st.markdown("---")

  excel_filename = "大戶持股最新分析總表.xlsx"
  if os.path.exists(excel_filename):
    try:
      df_meta = pd.read_excel(
          excel_filename, sheet_name="大戶增幅前15名", nrows=1, header=None
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
          excel_filename, sheet_name="大戶增幅前15名", header=1
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
          lambda x: (
              "https://norway.twsthr.info/StockHolders.aspx?stock="
              f"{str(x).strip().zfill(4)}"
          )
      )

      c_title, c_btn = st.columns([3, 1])
      with c_title:
        st.markdown(
            f'<p class="sub-header-14">📋 籌碼增幅榜 ｜ {week_info} ｜'
            f" {date_info}</p>",
            unsafe_allow_html=True,
        )
      with c_btn:
        with open(excel_filename, "rb") as file:
          st.download_button(
              "📥 下載 Excel",
              data=file,
              file_name="大戶持股最新分析總表.xlsx",
              use_container_width=True,
          )

      col_l, col_r = st.columns(2)
      with col_l:
        st.dataframe(
            df_display.iloc[:8],
            column_config={
                "趨勢圖連結": st.column_config.LinkColumn(
                    "🔗 連結", display_text="📈 金字塔"
                )
            },
            use_container_width=True,
            hide_index=True,
        )
      with col_r:
        st.dataframe(
            df_display.iloc[8:],
            column_config={
                "趨勢圖連結": st.column_config.LinkColumn(
                    "🔗 連結", display_text="📈 金字塔"
                )
            },
            use_container_width=True,
            hide_index=True,
        )
    except Exception as e:
      st.error(f"讀取總表格式發生錯誤：{e}")
  else:
    st.warning(
        "找不到總表檔案 (`大戶持股最新分析總表.xlsx`)，請確認背景自動更新排程已順利執行。"
    )

# =========================================================
# 分頁四：📊 基本面與圖表
# =========================================================
elif app_mode == "📊 基本面與圖表":
  st.markdown(
      f'<p class="sub-header-14">📊 基本面與圖表 ｜ [{stock_id}] {stock_name}</p>',
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
    grid_color = "#555555"
    ax.grid(True, linestyle=":", color=grid_color, alpha=0.5)
    fig.tight_layout(pad=0.3)

    with cols[idx % 2]:
      with st.expander(f"📊 {ds['title']} (放大)", expanded=False):
        st.pyplot(fig, use_container_width=True)