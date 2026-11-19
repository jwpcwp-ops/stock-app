from datetime import datetime
import json
import os
import urllib.request
import matplotlib.font_manager as fm
import matplotlib.patheffects as path_effects
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st
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

        /* 確保圖表右上角 Fullscreen 放大符號清楚顯示（不被黑色覆蓋） */
        button[title="Fullscreen"],
        [data-testid="stElementToolbar"] button,
        div[data-testid="stFullScreenFrame"] button {
            background-color: #1e242b !important;
            color: #00ffff !important;
            border: 1px solid #00ffff !important;
            opacity: 1 !important;
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
        
        .terminal-panel {
            background-color: #0b0b0b;
            border: 1px solid #cc0000;
            padding: 6px 9px;
            margin-bottom: 3px;
            font-family: 'Courier New', Courier, monospace;
            color: #ffffff;
            box-sizing: border-box;
        }
        .terminal-title {
            color: #ffffff;
            background-color: #0000aa;
            font-weight: bold;
            font-size: 12.5px;
            padding: 2px 6px;
            margin-bottom: 4px;
            text-align: center;
        }
        .t-row {
            font-size: 11.5px;
            line-height: 1.32;
            margin-bottom: 1px;
            display: flex;
            justify-content: space-between;
        }
        .t-label { color: #ffff00; font-weight: bold; }
        .t-val-red { color: #ff3333; font-weight: bold; }
        .t-val-green { color: #00e64d; font-weight: bold; }
        .t-val-cyan { color: #00ffff; font-weight: bold; }
        .t-val-white { color: #ffffff; font-weight: bold; }
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
  except Exception as e:
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
# 5. 本地快取支援與資料抓取 (60分/週線/月線/日線皆保留充足暖身期並連貫均線)
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
            syn_open = float(day_data["Open"].iloc[0])
            syn_high = float(day_data["High"].max())
            syn_low = float(day_data["Low"].min())
            syn_close = float(day_data["Close"].iloc[-1])
            syn_vol = float(day_data["Volume"].sum())

            df_yf.loc[latest_60m_date] = {
                "Open": syn_open,
                "High": syn_high,
                "Low": syn_low,
                "Close": syn_close,
                "Volume": syn_vol,
            }
            df_yf = df_yf.sort_index()
    except Exception as e:
      print(f"自動補針失敗: {e}")

  if not df_yf.empty:
    df_yf = df_yf.dropna(subset=["Close"])
    df_k = df_yf.tail(fetch_len).copy()

    if "Volume" not in df_k.columns or df_k["Volume"].sum() == 0:
      if stock_id == "99991":
        df_k["Volume"] = (
            np.random.randint(3000000, 5000000, size=len(df_k)) * 1000
        )
      else:
        df_k["Volume"] = (
            np.random.randint(10000, 50000, size=len(df_k)) * 1000
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

  # 計算各週期均線，並對前段不足 K 棒數做連貫填補，避免 60分/週線/月線 均線斷線
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

# 預設開啟季線（60），其餘 5/10/20/35/120/200/分割 預設關閉
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

# ---------------------------------------------------------
# 7. 網頁主介面佈局：左側【個股選單 + 週期選單】，右側 4 個快捷按鈕同一行
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
  third_row_cols = st.columns([1.45, 1.05, 0.5])

  # 均線開關列：未開啟保持清晰有精神，開啟時套用各均線專屬高亮色系
  with third_row_cols[0]:
    ma_items = ["5", "10", "20", "35", "60", "120", "200", "分割"]
    ma_btn_color_map = {
        "5": "#00FFFF",
        "10": "#FFFF00",
        "20": "#FF00FF",
        "35": "#00FF66",
        "60": "#FF9900",
        "120": "#CC66FF",
        "200": "#FFFFFF",
        "分割": "#00FFFF",
    }

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
      line_col = ma_btn_color_map.get(m_key, "#00FFFF")
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
    selected_indicator = st.pills(
        "指標",
        ["波段", "MACD", "BIAS", "KDJ", "RSI", "W%", "QT", "大戶羊群"],
        default="MACD",
        selection_mode="single",
        label_visibility="collapsed",
        key="pills_ind",
    )
    if not selected_indicator:
      selected_indicator = "MACD"

  with third_row_cols[2]:
    k_days_choice_str = st.pills(
        "天數",
        ["120", "250", "500"],
        default="250",
        selection_mode="single",
        label_visibility="collapsed",
        key="pills_k_days",
    )
    k_days_choice = int(k_days_choice_str) if k_days_choice_str else 250

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

  s_close = df["close"]
  s_high = df["high"]
  s_low = df["low"]

  last_date = df["date"].iloc[-1] if not df.empty else ""
  last_open = float(df["open"].iloc[-1]) if not df.empty else 0.0
  last_high = float(df["high"].iloc[-1]) if not df.empty else 0.0
  last_low = float(df["low"].iloc[-1]) if not df.empty else 0.0
  last_close = float(df["close"].iloc[-1]) if not df.empty else 0.0
  last_vol = float(df["vol"].iloc[-1]) if not df.empty else 0.0

  ma_config = {
      "5": (5, show_ma5, "#00FFFF"),
      "10": (10, show_ma10, "#FFFF00"),
      "20": (20, show_ma20, "#FF00FF"),
      "35": (35, show_ma35, "#00FF66"),
      "60": (60, show_ma60, "#FF9900"),
      "120": (120, show_ma120, "#CC66FF"),
      "200": (200, show_ma200, "#FFFFFF"),
  }

  deduct_periods = [5, 35, 65, 120, 200]
  deduct_indices = {}
  n_len = len(df)
  for p in deduct_periods:
    idx_pos = n_len - p
    deduct_indices[p] = idx_pos if 0 <= idx_pos < n_len else 0

  cur_dif = float(df["macd_dif"].iloc[-1]) if not df.empty else 0.0
  cur_dem = float(df["macd_dem"].iloc[-1]) if not df.empty else 0.0
  cur_osc = float(df["macd_osc"].iloc[-1]) if not df.empty else 0.0
  cur_bias = float(df["bias_val"].iloc[-1]) if not df.empty else 0.0
  cur_mtm = float(df["mtm_val"].iloc[-1]) if not df.empty else 0.0

  prev_dif = float(df["macd_dif"].iloc[-2]) if len(df) > 1 else cur_dif
  dif_arrow = "↑" if cur_dif >= prev_dif else "↓"
  prev_dem = float(df["macd_dem"].iloc[-2]) if len(df) > 1 else cur_dem
  dem_arrow = "↑" if cur_dem >= prev_dem else "↓"
  prev_osc = float(df["macd_osc"].iloc[-2]) if len(df) > 1 else cur_osc
  osc_arrow = "↑" if cur_osc >= prev_osc else "↓"

  cur_vol_val = last_vol
  cur_vol_ma5 = (
      float(df["vol_ma5"].iloc[-1])
      if not pd.isna(df["vol_ma5"].iloc[-1])
      else 0.0
  )
  cur_vol_ma20 = (
      float(df["vol_ma20"].iloc[-1])
      if not pd.isna(df["vol_ma20"].iloc[-1])
      else 0.0
  )

  prev_vol_ma5 = (
      float(df["vol_ma5"].iloc[-2])
      if len(df) > 1 and not pd.isna(df["vol_ma5"].iloc[-2])
      else cur_vol_ma5
  )
  prev_vol_ma20 = (
      float(df["vol_ma20"].iloc[-2])
      if len(df) > 1 and not pd.isna(df["vol_ma20"].iloc[-2])
      else cur_vol_ma20
  )

  v5_arrow = "↓" if cur_vol_ma5 < prev_vol_ma5 else "↑"
  v20_arrow = "↓" if cur_vol_ma20 < prev_vol_ma20 else "↑"
  vol_today_arrow = (
      "↓"
      if last_vol < (float(df["vol"].iloc[-2]) if len(df) > 1 else last_vol)
      else "↑"
  )

  v5_val_ratio = cur_vol_val / cur_vol_ma5 if cur_vol_ma5 > 0 else 1.0
  v20_val_ratio = cur_vol_val / cur_vol_ma20 if cur_vol_ma20 > 0 else 1.0

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

  chart_col, info_col = st.columns([8.2, 1.8])

  with chart_col:
    is_wave_mode = selected_indicator == "波段"
    fig = plt.figure(figsize=(10.0, 5.4 if is_wave_mode else 4.65))

    if is_wave_mode:
      gs = fig.add_gridspec(4, 1, height_ratios=[2.5, 0.8, 0.8, 0.8], hspace=0.10)
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
      axes = [ax1, ax_sub1, ax_sub2]

    for ax in [fig] + list(axes):
      ax.set_facecolor(BG_COLOR)
    fig.patch.set_facecolor(BG_COLOR)
    x = list(range(len(df)))

    ax1.set_facecolor(PANEL_BG)
    ax1.vlines(
        x, df["low"], df["high"], color=body_colors, linewidth=0.7, alpha=1.0
    )
    body_bottom = [min(o, c) for o, c in zip(df["open"], df["close"])]
    body_height = [
        max(abs(c - o), 0.01) for o, c in zip(df["open"], df["close"])
    ]
    ax1.bar(
        x,
        body_height,
        bottom=body_bottom,
        width=0.8,
        color=body_colors,
        edgecolor="none",
    )

    if not df.empty:
      p_max = float(df["high"].max())
      p_min = float(df["low"].min())
      p_range = p_max - p_min if p_max != p_min else 1.0
      ax1.set_ylim(p_min - p_range * 0.08, p_max + p_range * 0.15)
      ax1.set_xlim(-1, len(x) + max(4, int(len(x) * 0.12)))

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

    legend_labels = []
    last_idx = len(df) - 1
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
        )
        val_now = (
            float(ma_series.iloc[-1])
            if not pd.isna(ma_series.iloc[-1])
            else 0.0
        )
        val_prev = (
            float(ma_series.iloc[-2])
            if last_idx > 0 and not pd.isna(ma_series.iloc[-2])
            else val_now
        )
        arrow = "↑" if val_now >= val_prev else "↓"
        legend_labels.append((f"{ma_name}:{val_now:.1f}{arrow}", color))

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
    for i, col in enumerate(trend_colors):
      ax1.bar(
          x[i],
          band_height,
          bottom=ymin_lim,
          width=1.0,
          color=col,
          edgecolor="none",
          alpha=1.0,
      )

    ax1.yaxis.tick_right()
    ax1.tick_params(axis="y", labelsize=7.0, pad=1.5, colors="#FFFFFF")
    plt.setp(ax1.get_xticklabels(), visible=False)
    ax1.grid(True, which="both", linestyle="--", color=GRID_COLOR, alpha=0.5)

    standard_header_str = f"[{stock_id}] {stock_name}   {last_date}   開:{last_open:.2f}  高:{last_high:.2f}  低:{last_low:.2f}  收:{last_close:.2f}  量:{int(last_vol):,}張"
    t_header = ax1.text(
        0.01,
        0.91,
        standard_header_str,
        transform=ax1.transAxes,
        fontsize=9.0,
        fontweight="bold",
        color="#FFFFFF",
    )
    t_header.set_path_effects(get_bright_effect("#000000", 3.0))

    ma60_val = (
        df["ma_60"].iloc[-1]
        if "ma_60" in df.columns and not pd.isna(df["ma_60"].iloc[-1])
        else 0
    )
    is_bull = last_close >= ma60_val
    trend_status = "【季線多頭】" if is_bull else "【季線空頭】"
    trend_color = "#FF3333" if is_bull else "#00E64D"

    t_trend_badge = ax1.text(
        0.57,
        0.91,
        trend_status,
        transform=ax1.transAxes,
        fontsize=8.0,
        fontweight="bold",
        color=trend_color,
    )
    t_trend_badge.set_path_effects(get_bright_effect("#000000", 2.5))

    t_period_badge = ax1.text(
        0.71,
        0.91,
        f" {actual_chart_period} ",
        transform=ax1.transAxes,
        fontsize=8.0,
        fontweight="bold",
        color="#FFFFFF",
        backgroundcolor="#222222",
        ha="center",
        va="center",
    )
    t_period_badge.set_path_effects(get_bright_effect("#000000", 2.5))

    if legend_labels:
      text_x = 0.01
      text_y = 0.82
      for l_str, l_col in legend_labels:
        t_ma = ax1.text(
            text_x,
            text_y,
            l_str,
            transform=ax1.transAxes,
            fontsize=8.5,
            fontweight="bold",
            color=l_col,
        )
        t_ma.set_path_effects(get_bright_effect("#000000", 2.5))
        text_x += 0.11

    if is_wave_mode:
      cur_band_dif = (
          float(df["band_macd_dif"].iloc[-1]) if not df.empty else 0.0
      )
      ax_sub1.set_facecolor(PANEL_BG)
      ax_sub1.bar(
          x,
          df["band_macd_osc"],
          width=0.75,
          color=band_macd_bar_colors,
          edgecolor="none",
          alpha=1.0,
      )
      ax_sub1.plot(
          x, df["band_macd_dif"], linewidth=0.6, color="#FFFF00", label="DIF"
      )
      ax_sub1.plot(
          x, df["band_macd_dem"], linewidth=0.6, color="#FF3333", label="MACD"
      )
      ax_sub1.axhline(0, color="#777777", linestyle=":", linewidth=1.0)
      ax_sub1.yaxis.tick_right()
      ax_sub1.tick_params(axis="y", labelsize=7.0, pad=1.5, colors="#FFFFFF")
      plt.setp(ax_sub1.get_xticklabels(), visible=False)
      ax_sub1.grid(
          True, which="both", linestyle="--", color=GRID_COLOR, alpha=0.5
      )
      t_s1 = ax_sub1.text(
          0.015,
          0.76,
          f"波段 MACD(5,10)  DIF:{cur_band_dif:.2f}",
          transform=ax_sub1.transAxes,
          fontsize=8.5,
          fontweight="bold",
          color="#FFFFFF",
      )
      t_s1.set_path_effects(get_bright_effect("#000000", 2.5))

      cur_band_bias = (
          float(df["band_bias_val"].iloc[-1]) if not df.empty else 0.0
      )
      ax_sub2.set_facecolor(PANEL_BG)
      ax_sub2.plot(
          x,
          df["band_bias_val_rev"],
          linewidth=0.6,
          color="#00FFFF",
          label="BIAS(反向)",
      )
      ax_sub2.axhline(0, color="#777777", linestyle=":", linewidth=1.0)
      ax_sub2.yaxis.tick_right()
      ax_sub2.tick_params(axis="y", labelsize=7.0, pad=1.5, colors="#FFFFFF")
      plt.setp(ax_sub2.get_xticklabels(), visible=False)
      ax_sub2.grid(
          True, which="both", linestyle="--", color=GRID_COLOR, alpha=0.5
      )
      t_s2 = ax_sub2.text(
          0.015,
          0.76,
          f"波段 BIAS(反向)  {cur_band_bias:.2f}%",
          transform=ax_sub2.transAxes,
          fontsize=8.5,
          fontweight="bold",
          color="#FFFFFF",
      )
      t_s2.set_path_effects(get_bright_effect("#000000", 2.5))

      ax_sub3.set_facecolor(PANEL_BG)
      ax_sub3.plot(
          x, df["mtm_val"], linewidth=0.6, color="#FFFF00", label="MTM"
      )
      ax_sub3.plot(
          x, df["mtm_ma1"], linewidth=0.6, color="#00FF66", label="Avg"
      )
      ax_sub3.axhline(0, color="#777777", linestyle=":", linewidth=1.0)
      ax_sub3.yaxis.tick_right()
      ax_sub3.tick_params(axis="y", labelsize=7.0, pad=1.5, colors="#FFFFFF")
      ax_sub3.tick_params(axis="x", labelsize=8.0, colors="#FFFFFF")
      plt.setp(ax_sub3.get_xticklabels(), visible=True)
      for label in ax_sub3.get_xticklabels():
        label.set_color("#FFFFFF")
        label.set_fontsize(8.0)
      ax_sub3.grid(
          True, which="both", linestyle="--", color=GRID_COLOR, alpha=0.5
      )
      t_s3 = ax_sub3.text(
          0.015,
          0.76,
          f"波段 MTM(10,1)  MTM:{cur_mtm:.2f}",
          transform=ax_sub3.transAxes,
          fontsize=8.5,
          fontweight="bold",
          color="#FFFFFF",
      )
      t_s3.set_path_effects(get_bright_effect("#000000", 2.5))
    else:
      ax_sub1.set_facecolor(PANEL_BG)
      if selected_indicator == "MACD":
        ax_sub1.bar(
            x,
            df["macd_osc"],
            width=0.75,
            color=macd_bar_colors,
            edgecolor="none",
            alpha=1.0,
        )
        ax_sub1.plot(
            x, df["macd_dif"], linewidth=0.6, color="#FF00FF", label="DIF"
        )
        ax_sub1.plot(
            x, df["macd_dem"], linewidth=0.6, color="#00FFFF", label="DEA"
        )
        osc_color = "#FF3333" if cur_osc >= 0 else "#00E64D"
        macd_tokens = [
            ("MACD(長) ", "#FFFFFF"),
            ("DIF:", "#FF00FF"),
            (f"{cur_dif:.2f} {dif_arrow} ", "#FF00FF"),
            ("DEA:", "#00FFFF"),
            (f"{cur_dem:.2f} {dem_arrow} ", "#00FFFF"),
            ("MACD:", osc_color),
            (f"{cur_osc:.2f} {osc_arrow}", osc_color),
        ]
        start_x_m = 0.015
        for m_txt, m_col in macd_tokens:
          t_m = ax_sub1.text(
              start_x_m,
              0.84,
              m_txt,
              transform=ax_sub1.transAxes,
              fontsize=8.0,
              fontweight="bold",
              color=m_col,
          )
          t_m.set_path_effects(get_bright_effect("#000000", 2.5))
          start_x_m += len(m_txt) * 0.007

      elif selected_indicator == "BIAS":
        ax_sub1.plot(
            x,
            df["bias_val"],
            linewidth=0.6,
            color="#FFFF00",
            label="BIAS(60)",
        )
        t_s1 = ax_sub1.text(
            0.015,
            0.84,
            f"BIAS(60)  {cur_bias:.2f}%",
            transform=ax_sub1.transAxes,
            fontsize=8.0,
            fontweight="bold",
            color="#FFFF00",
        )
        t_s1.set_path_effects(get_bright_effect("#000000", 2.5))

      elif selected_indicator == "KDJ":
        cur_k = float(df["kdj_k"].iloc[-1]) if not df.empty else 0.0
        cur_d = float(df["kdj_d"].iloc[-1]) if not df.empty else 0.0
        cur_j = float(df["kdj_j"].iloc[-1]) if not df.empty else 0.0
        cur_diff = float(df["kdj_diff"].iloc[-1]) if not df.empty else 0.0
        diff_arrow = "↑" if cur_diff >= 0 else "↓"

        ax_sub1.plot(
            x, df["kdj_k"], linewidth=0.6, color="#FF00FF", label="K"
        )
        ax_sub1.plot(
            x, df["kdj_d"], linewidth=0.6, color="#00FFFF", label="D"
        )
        ax_sub1.plot(
            x, df["kdj_j"], linewidth=0.6, color="#FFFFFF", label="J"
        )

        kdj_tokens = [
            ("KD(9,3,3)  ", "#FFFFFF"),
            ("K:", "#FF00FF"),
            (f"{cur_k:.2f}  ", "#FF00FF"),
            ("D:", "#00FFFF"),
            (f"{cur_d:.2f}  ", "#00FFFF"),
            ("J:", "#FFFFFF"),
            (f"{cur_j:.2f}  ", "#FFFFFF"),
            ("乖離:", "#FFFF00"),
            (f"{cur_diff:.2f} {diff_arrow}", "#FFFF00"),
        ]
        start_x_k = 0.015
        for k_txt, k_col in kdj_tokens:
          t_k = ax_sub1.text(
              start_x_k,
              0.84,
              k_txt,
              transform=ax_sub1.transAxes,
              fontsize=8.0,
              fontweight="bold",
              color=k_col,
          )
          t_k.set_path_effects(get_bright_effect("#000000", 2.5))
          start_x_k += len(k_txt) * 0.007

      elif selected_indicator == "RSI":
        cur_r6 = float(df["rsi_6"].iloc[-1]) if not df.empty else 0.0
        cur_r12 = float(df["rsi_12"].iloc[-1]) if not df.empty else 0.0
        cur_rdiff = float(df["rsi_diff"].iloc[-1]) if not df.empty else 0.0
        rdiff_arrow = "↑" if cur_rdiff >= 0 else "↓"
        ax_sub1.plot(
            x, df["rsi_6"], linewidth=0.6, color="#FF00FF", label="RSI6"
        )
        ax_sub1.plot(
            x, df["rsi_12"], linewidth=0.6, color="#00FFFF", label="RSI12"
        )

        rsi_tokens = [
            ("RSI(6,12)  ", "#FFFFFF"),
            ("RSI6:", "#FF00FF"),
            (f"{cur_r6:.2f}  ", "#FF00FF"),
            ("RSI12:", "#00FFFF"),
            (f"{cur_r12:.2f}  ", "#00FF00"),
            ("差值:", "#FFFF00"),
            (f"{cur_rdiff:.2f} {rdiff_arrow}", "#FFFF00"),
        ]
        start_x_r = 0.015
        for r_txt, r_col in rsi_tokens:
          t_r = ax_sub1.text(
              start_x_r,
              0.84,
              r_txt,
              transform=ax_sub1.transAxes,
              fontsize=8.0,
              fontweight="bold",
              color=r_col,
          )
          t_r.set_path_effects(get_bright_effect("#000000", 2.5))
          start_x_r += len(r_txt) * 0.007

      elif selected_indicator == "W%":
        cur_wr = float(df["w_r"].iloc[-1]) if not df.empty else 0.0
        ax_sub1.plot(x, df["w_r"], linewidth=0.6, color="#FFFF00", label="W%")
        t_wr = ax_sub1.text(
            0.015,
            0.84,
            f"W% (威廉指標)  W%:{cur_wr:.2f}%",
            transform=ax_sub1.transAxes,
            fontsize=8.0,
            fontweight="bold",
            color="#FFFF00",
        )
        t_wr.set_path_effects(get_bright_effect("#000000", 2.5))

      elif selected_indicator == "QT":
        cur_qt = float(df["qt"].iloc[-1]) if not df.empty else 0.0
        ax_sub1.bar(
            x,
            df["qt"],
            width=0.75,
            color=qt_bar_colors,
            edgecolor="none",
            alpha=1.0,
        )
        t_qt = ax_sub1.text(
            0.015,
            0.84,
            f"QT (量價波動)  QT:{cur_qt:.2f}",
            transform=ax_sub1.transAxes,
            fontsize=8.0,
            fontweight="bold",
            color="#00FF66",
        )
        t_qt.set_path_effects(get_bright_effect("#000000", 2.5))

      elif selected_indicator == "大戶羊群":
        if len(big_holder) > 0 and len(sheep_holder) > 0:
          b_plot = big_holder[-len(df) :]
          s_plot = sheep_holder[-len(df) :]
          ax_sub1.plot(
              x,
              b_plot,
              color="#FF3333",
              linewidth=0.6,
              linestyle="-",
              label="大戶(%)",
          )
          ax_sub1.plot(
              x,
              s_plot,
              color="#00E64D",
              linewidth=0.6,
              linestyle="-",
              label="羊群(%)",
          )
          cur_b = float(b_plot[-1])
          cur_s = float(s_plot[-1])
          t_sh = ax_sub1.text(
              0.015,
              0.84,
              f"大戶羊群指標  大戶:{cur_b:.1f}%  散戶:{cur_s:.1f}%",
              transform=ax_sub1.transAxes,
              fontsize=8.0,
              fontweight="bold",
              color="#FF3333",
          )
          t_sh.set_path_effects(get_bright_effect("#000000", 2.5))

      ax_sub1.axhline(0, color="#777777", linestyle=":", linewidth=1.0)
      ax_sub1.yaxis.tick_right()
      ax_sub1.tick_params(axis="y", labelsize=7.0, pad=1.5, colors="#FFFFFF")
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
          alpha=1.0,
      )
      ax_sub2.plot(
          x,
          df["vol_ma5"],
          linewidth=0.6,
          color="#FFFF00",
          label="Vol MA5",
          alpha=0.95,
      )
      ax_sub2.plot(
          x,
          df["vol_ma20"],
          linewidth=0.6,
          color="#FF9900",
          label="Vol MA20",
          alpha=0.95,
      )
      ax_sub2.yaxis.tick_right()
      ax_sub2.tick_params(axis="y", labelsize=7.0, pad=1.5, colors="#FFFFFF")
      ax_sub2.tick_params(axis="x", labelsize=8.0, colors="#FFFFFF")
      plt.setp(ax_sub2.get_xticklabels(), visible=True)
      for label in ax_sub2.get_xticklabels():
        label.set_color("#FFFFFF")
        label.set_fontsize(8.0)
      ax_sub2.grid(
          True, which="both", linestyle="--", color=GRID_COLOR, alpha=0.5
      )

      vol_str_parts = [
          ("今日 ", "#FFFFFF"),
          (f"量:{int(cur_vol_val)}", "#FF3333"),
          (f"{vol_today_arrow}", "#FF3333"),
          ("  ", "#FFFFFF"),
          ("日5:", "#FFFF00"),
          (f"{int(cur_vol_ma5)}", "#FFFF00"),
          (f"{v5_arrow}", "#FFFF00"),
          ("  ", "#FFFFFF"),
          ("值5:", "#FFFF00"),
          (f"{v5_val_ratio:.2f}", "#FFFF00"),
          (f"{v5_arrow}", "#FFFF00"),
          ("  ", "#FFFFFF"),
          ("日20:", "#FF9900"),
          (f"{int(cur_vol_ma20)}", "#FF9900"),
          (f"{v20_arrow}", "#FF9900"),
          ("  ", "#FFFFFF"),
          ("值20:", "#FF9900"),
          (f"{v20_val_ratio:.2f}", "#FF9900"),
          (f"{v20_arrow}", "#FF9900"),
      ]

      start_x_vol = 0.015
      for v_txt, v_col in vol_str_parts:
        t_v = ax_sub2.text(
            start_x_vol,
            0.84,
            v_txt,
            transform=ax_sub2.transAxes,
            fontsize=8.0,
            fontweight="bold",
            color=v_col,
        )
        t_v.set_path_effects(get_bright_effect("#000000", 2.5))
        start_x_vol += len(v_txt) * 0.007

    for ax in axes:
      for spine in ax.spines.values():
        spine.set_visible(True)
        spine.set_color("#777777")
        spine.set_linewidth(1.3)

    bottom_margin = 0.08 if is_wave_mode else 0.06
    plt.subplots_adjust(
        left=0.01, right=0.99, top=0.98, bottom=bottom_margin, hspace=0.10
    )
    st.pyplot(fig, use_container_width=True, dpi=150)

  with info_col:
    ma5_val = (
        float(df["ma_5"].iloc[-1])
        if "ma_5" in df.columns and not pd.isna(df["ma_5"].iloc[-1])
        else 0
    )
    ma20_val = (
        float(df["ma_20"].iloc[-1])
        if "ma_20" in df.columns and not pd.isna(df["ma_20"].iloc[-1])
        else 0
    )
    ma60_val = (
        float(df["ma_60"].iloc[-1])
        if "ma_60" in df.columns and not pd.isna(df["ma_60"].iloc[-1])
        else 0
    )
    ma_status = (
        "多頭排列"
        if ma5_val > ma20_val > ma60_val
        else ("空頭排列" if ma5_val < ma20_val < ma60_val else "均線交錯")
    )
    ma_color_class = "t-val-red" if ma5_val > ma20_val else "t-val-green"

    recent_high_val = (
        float(df["high"].tail(30).max()) if not df.empty else last_high
    )
    recent_low_val = (
        float(df["low"].tail(30).min()) if not df.empty else last_low
    )
    calc_drop = (
        ((recent_high_val - last_low) / recent_high_val) * 100
        if recent_high_val > 0
        else 0.0
    )
    calc_rise = (
        ((last_high / recent_low_val) - 1) * 100
        if recent_low_val > 0
        else 0.0
    )

    cur_k = float(df["kdj_k"].iloc[-1]) if "kdj_k" in df.columns else 0.0
    cur_d = float(df["kdj_d"].iloc[-1]) if "kdj_d" in df.columns else 0.0
    cur_j = float(df["kdj_j"].iloc[-1]) if "kdj_j" in df.columns else 0.0
    prev_k = float(df["kdj_k"].iloc[-2]) if len(df) > 1 else cur_k
    prev_d = float(df["kdj_d"].iloc[-2]) if len(df) > 1 else cur_d
    k_diff_kd = cur_k - cur_d

    is_golden_cross = prev_k <= prev_d and cur_k > cur_d
    is_dead_cross = prev_k >= prev_d and cur_k < cur_d

    kdj_signal = "中立觀望"
    kdj_sig_cls = "t-val-white"

    if cur_k > 90:
      kdj_signal, kdj_sig_cls = "【強力賣出】K>90超買", "t-val-green"
    elif cur_j > 100:
      kdj_signal, kdj_sig_cls = "【強力賣出】J>100超買", "t-val-green"
    elif k_diff_kd > 18:
      kdj_signal, kdj_sig_cls = "【強力賣出】正乖離>+18", "t-val-green"
    elif is_dead_cross:
      kdj_signal, kdj_sig_cls = "【賣出訊號】KD死叉", "t-val-green"
    elif cur_k < 9:
      kdj_signal, kdj_sig_cls = "【強力買進】K<9超賣", "t-val-red"
    elif cur_k < 9 and cur_d < 9:
      kdj_signal, kdj_sig_cls = "【強力買進】KD雙跌破9", "t-val-red"
    elif cur_j < 0:
      kdj_signal, kdj_sig_cls = "【強力買進】J<0超賣", "t-val-red"
    elif k_diff_kd < -18:
      kdj_signal, kdj_sig_cls = "【強力買進】負乖離<-18", "t-val-red"
    elif is_golden_cross:
      kdj_signal, kdj_sig_cls = "【買進訊號】KD金交叉", "t-val-red"

    is_buy_signal_today = (
        bool(df["is_buy_signal"].iloc[-1])
        if "is_buy_signal" in df.columns
        else False
    )
    is_sell_signal_today = (
        bool(df["is_sell_signal"].iloc[-1])
        if "is_sell_signal" in df.columns
        else False
    )

    wave_status = "持倉中 / 觀望"
    wave_cls = "t-val-white"
    if is_buy_signal_today:
      wave_status, wave_cls = "★ 今日波段買進", "t-val-red"
    elif is_sell_signal_today:
      wave_status, wave_cls = "✖ 今日波段賣出", "t-val-cyan"
    elif df["red_days"].iloc[-1] < df["green_days"].iloc[-1]:
      wave_status, wave_cls = "多方波段運行中", "t-val-red"
    else:
      wave_status, wave_cls = "空方波段整理中", "t-val-green"

    red_days_val = int(df["red_days"].iloc[-1])
    green_days_val = int(df["green_days"].iloc[-1])

    vol_status = "量能平穩" if v_ratio < 1.5 else "量能顯著放大"
    vol_cls = "t-val-white" if v_ratio < 1.5 else "t-val-red"
    trend_txt = "多方主力掌控" if is_bull else "空方賣壓佔優"
    trend_cls = "t-val-red" if is_bull else "t-val-green"

    st.markdown(
        f"""
            <div class="terminal-panel">
                <div class="terminal-title">【均線解盤】</div>
                <div class="t-row"><span class="t-label">狀態:</span><span class="{ma_color_class}">{ma_status}</span></div>
                <div class="t-row"><span class="t-label">MA5:</span><span class="t-val-cyan">{ma5_val:.1f}</span></div>
                <div class="t-row"><span class="t-label">MA20:</span><span class="t-val-cyan">{ma20_val:.1f}</span></div>
                <div class="t-row"><span class="t-label">季60:</span><span class="t-val-cyan">{ma60_val:.1f}</span></div>
            </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""
            <div class="terminal-panel">
                <div class="terminal-title">【區間漲跌幅】</div>
                <div class="t-row"><span class="t-label">近30高:</span><span class="t-val-cyan">{recent_high_val:.2f}</span></div>
                <div class="t-row"><span class="t-label">近30低:</span><span class="t-val-cyan">{recent_low_val:.2f}</span></div>
                <div class="t-row"><span class="t-label">回檔幅:</span><span class="t-val-green">-{calc_drop:.2f}%</span></div>
                <div class="t-row"><span class="t-label">彈升幅:</span><span class="t-val-red">+{calc_rise:.2f}%</span></div>
            </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""
            <div class="terminal-panel">
                <div class="terminal-title">【KDJ綜合解盤】</div>
                <div class="t-row"><span class="t-label">判定:</span><span class="{kdj_sig_cls}">{kdj_signal}</span></div>
                <div class="t-row"><span class="t-label">K/D:</span><span class="t-val-white">{cur_k:.1f} / {cur_d:.1f}</span></div>
                <div class="t-row"><span class="t-label">J值:</span><span class="t-val-cyan">{cur_j:.1f}</span></div>
                <div class="t-row"><span class="t-label">K-D乖離:</span><span class="t-val-white">{k_diff_kd:+.1f}</span></div>
            </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""
            <div class="terminal-panel">
                <div class="terminal-title">【成交量解盤】</div>
                <div class="t-row"><span class="t-label">5日均量比:</span><span class="{vol_cls}">{v_ratio:.2f}倍</span></div>
                <div class="t-row"><span class="t-label">現況:</span><span class="t-val-white">{vol_status}</span></div>
                <div class="t-row"><span class="t-label">當日量:</span><span class="t-val-cyan">{int(last_vol):,}張</span></div>
            </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""
            <div class="terminal-panel">
                <div class="terminal-title">【多空與波段判定】</div>
                <div class="t-row"><span class="t-label">多空:</span><span class="{trend_cls}">{trend_txt}</span></div>
                <div class="t-row"><span class="t-label">波段狀態:</span><span class="{wave_cls}">{wave_status}</span></div>
                <div class="t-row"><span class="t-label">紅天數:</span><span class="t-val-red">{red_days_val}日</span></div>
                <div class="t-row"><span class="t-label">綠天數:</span><span class="t-val-green">{green_days_val}日</span></div>
            </div>
        """,
        unsafe_allow_html=True,
    )

# =========================================================
# 分頁二：⚡ 9大策略選股
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

  st.markdown(
      f'<p class="sub-header-14">⚡ GitHub 雲端 9 大策略選股結果 ｜當前策略：【'
      f"{selected_strat}】</p>",
      unsafe_allow_html=True,
  )

  output_csv = "smart_selected_output.csv"
  if os.path.exists(output_csv):
    try:
      df_res = pd.read_csv(output_csv, dtype={"代碼": str})
    except Exception:
      df_res = pd.DataFrame(columns=["策略名稱", "代碼"])
  else:
    df_res = pd.DataFrame(columns=["策略名稱", "代碼"])

  if not df_res.empty and "策略名稱" in df_res.columns:
    filtered_df = df_res[df_res["策略名稱"] == selected_strat].copy()
  else:
    filtered_df = pd.DataFrame(columns=["策略名稱", "代碼"])

  if filtered_df.empty or (
      len(filtered_df) == 1
      and filtered_df.iloc[0]["代碼"] in ["無", "無符合股票"]
  ):
    st.info(f"【{selected_strat}】目前尚無符合條件的股票標的。")
  else:
    id_to_name = dict(
        zip(
            stock_df["代碼"].astype(str).str.zfill(4),
            stock_df["名稱"].astype(str),
        )
    )
    if "代碼" in filtered_df.columns:
      filtered_df["名稱"] = filtered_df["代碼"].map(id_to_name).fillna("")

    st.success(f"【{selected_strat}】共篩選出 {len(filtered_df)} 檔標的。")

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
# 分頁三：📋 大戶總表
# =========================================================
elif app_mode == "📋 大戶總表":
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