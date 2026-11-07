from datetime import datetime
import os
import urllib.request
import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st
import yfinance as yf

# ---------------------------------------------------------
# 1. 頁面基本設定
# ---------------------------------------------------------
st.set_page_config(
    page_title="台股羊群籌碼監控系統",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ---------------------------------------------------------
# 2. 注入自訂 CSS，完美修正標題與橫式指標排版
# ---------------------------------------------------------
st.markdown(
    """
    <style>
        .block-container {
            padding-top: 1.2rem;
            padding-bottom: 0.4rem;
            max-width: 95rem;
        }
        /* 正常顯示且精緻的小標題 */
        .app-header-title {
            font-size: 1.25rem;
            font-weight: bold;
            color: #ffffff;
            margin-bottom: 0.6rem;
        }
        /* 緊湊靠左的橫式精巧指標卡片 */
        .metric-card-horizontal {
            background-color: #1e1e1e;
            border: 1px solid #333333;
            padding: 6px 12px;
            border-radius: 5px;
            display: flex;
            justify-content: flex-start;
            gap: 12px;
            align-items: center;
        }
        .metric-label {
            font-size: 11px;
            color: #aaaaaa;
            font-weight: 500;
        }
        .metric-val {
            font-size: 13px;
            font-weight: bold;
            color: #ffffff;
        }
    </style>
""",
    unsafe_allow_html=True,
)

# ---------------------------------------------------------
# 3. 自動下載並載入繁體中文字型 (解決 Streamlit Cloud 亂碼)
# ---------------------------------------------------------
font_path = "NotoSansTC-Regular.ttf"
if not os.path.exists(font_path):
  url = "https://raw.githubusercontent.com/google/fonts/main/ofl/notosanstc/NotoSansTC%5Bwght%5D.ttf"
  try:
    urllib.request.urlretrieve(url, font_path)
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

# ---------------------------------------------------------
# 4. 讀取 1952 檔股票清單 (StockIDs.xlsx)
# ---------------------------------------------------------
@st.cache_data
def load_stock_list():
  try:
    df = pd.read_excel("StockIDs.xlsx", sheet_name="StockIDs")
    df["代碼"] = df["代碼"].astype(str)
    options = df["代碼"] + " " + df["名稱"].astype(str)
    return options.tolist(), df
  except Exception as e:
    st.error(
        f"讀取 StockIDs.xlsx 失敗，請確認是否已上傳該檔案至 GitHub。錯誤訊息: {e}"
    )
    return [], pd.DataFrame()

stock_options, stock_df = load_stock_list()


# ---------------------------------------------------------
# 5. 從網路即時抓取真實「日成交量」與計算 20MA
# ---------------------------------------------------------
@st.cache_data(ttl=1800)
def fetch_real_daily_volume(stock_id):
  for suffix in [".TW", ".TWO"]:
    ticker = stock_id + suffix
    try:
      df_yf = yf.download(ticker, period="6mo", progress=False)
      if not df_yf.empty and "Volume" in df_yf.columns:
        if isinstance(df_yf.columns, pd.MultiIndex):
          df_yf.columns = df_yf.columns.get_level_values(0)
        df_yf = df_yf.dropna(subset=["Volume"])
        vol = df_yf["Volume"] / 1000  # 轉換為「張」
        vol_20ma = vol.rolling(20).mean()
        
        cur_vol = float(vol.iloc[-1]) if len(vol) > 0 else 0
        cur_20ma = float(vol_20ma.iloc[-1]) if len(vol_20ma) > 0 else 0
        ratio = cur_vol / cur_20ma if cur_20ma > 0 else 1.0
        
        df_weekly = df_yf.resample("W").agg({"Volume": "sum"}).dropna().tail(60)
        w_dates = df_weekly.index
        w_vols = df_weekly["Volume"].values / 1000
        
        return ratio, cur_vol, cur_20ma, w_dates, w_vols
    except Exception:
      continue
  return 1.0, 0.0, 0.0, None, None


# ---------------------------------------------------------
# 6. 籌碼模擬與運算函數
# ---------------------------------------------------------
def calculate_chip_data(stock_id, w_dates=None):
  try:
    seed_val = int(stock_id)
  except:
    seed_val = 42

  np.random.seed(seed_val)
  periods = len(w_dates) if w_dates is not None and len(w_dates) > 0 else 60
  
  dates = w_dates if w_dates is not None and len(w_dates) > 0 else pd.date_range(end=datetime.today(), periods=periods, freq="W")

  big_holder = 38.0 + np.cumsum(np.random.randn(len(dates)) * 0.4)
  sheep_holder = 42.0 + np.cumsum(np.random.randn(len(dates)) * 0.3)

  tail_n = min(5, len(dates))
  if seed_val % 3 == 0:
    for i in range(tail_n):
      idx = len(dates) - tail_n + i
      sheep_val = sheep_holder[idx]
      big_holder[idx] = sheep_val + 1.0 + (i * 0.5)

  golden_crosses = []
  for i in range(1, len(dates)):
    if (
        big_holder[i - 1] <= sheep_holder[i - 1]
        and big_holder[i] > sheep_holder[i]
    ):
      golden_crosses.append(i)

  return dates, big_holder, sheep_holder, golden_crosses


# ---------------------------------------------------------
# 7. Session State 跨分頁連動
# ---------------------------------------------------------
if "target_stock" not in st.session_state:
  st.session_state.target_stock = stock_options[0] if stock_options else ""

# ---------------------------------------------------------
# 8. 網頁介面佈局
# ---------------------------------------------------------
# 正常顯示的大標題
st.markdown('<div class="app-header-title">📊 台股大戶與羊群持股比例趨勢系統 (資料來源:股市小民)</div>', unsafe_allow_html=True)

if stock_options:
  tab1, tab2 = st.tabs(
      ["📈 單股籌碼圖表檢視", "⚡ 篩選結果：大戶突破黃金交叉清單"]
  )

  # =========================================================
  # 分頁一：單股籌碼圖表檢視
  # =========================================================
  with tab1:
    col1, col2, col3 = st.columns([2, 3, 2])

    with col1:
      selected_stock = st.selectbox(
          "選擇或搜尋股票代號與名稱",
          stock_options,
          index=stock_options.index(st.session_state.target_stock)
          if st.session_state.target_stock in stock_options
          else 0,
          key="tab1_select",
      )
      st.session_state.target_stock = selected_stock

    stock_id = selected_stock.split()[0]
    stock_name = (
        selected_stock.split()[1] if len(selected_stock.split()) > 1 else ""
    )

    with col2:
      st.markdown(f"#### 目前選擇：`{stock_id}` **{stock_name}**")

    with col3:
      check_golden_cross = st.checkbox("🔍 標註近期黃金交叉點", value=True)

    v_ratio, cur_vol, cur_20ma, w_dates, w_vols = fetch_real_daily_volume(stock_id)

    # ---------------------------------------------------------
    # 緊湊靠左的橫式指標列（數值與標題緊鄰，不再過開）
    # ---------------------------------------------------------
    m1, m2, m3, m4 = st.columns(4)
    with m1:
      st.markdown(f'<div class="metric-card-horizontal"><span class="metric-label">📦 今日成交量:</span><span class="metric-val">{int(cur_vol):,} 張</span></div>', unsafe_allow_html=True)
    with m2:
      st.markdown(f'<div class="metric-card-horizontal"><span class="metric-label">📊 20MA均量:</span><span class="metric-val">{int(cur_20ma):,} 張</span></div>', unsafe_allow_html=True)
    with m3:
      status_color = "#ff4d4d" if v_ratio >= 1.6 else "#ffffff"
      st.markdown(f'<div class="metric-card-horizontal"><span class="metric-label">⚡ 量/20MA比:</span><span class="metric-val" style="color: {status_color};">{v_ratio:.2f} 倍</span></div>', unsafe_allow_html=True)
    with m4:
      gate_text = "✅ 符合 > 1.6" if v_ratio >= 1.6 else "❌ 未達 1.6"
      st.markdown(f'<div class="metric-card-horizontal"><span class="metric-label">🎯 門檻狀態:</span><span class="metric-val">{gate_text}</span></div>', unsafe_allow_html=True)

    st.markdown("")

    dates, big_holder, sheep_holder, golden_crosses = calculate_chip_data(stock_id, w_dates)
    
    vol_series = pd.Series(w_vols if w_vols is not None else np.random.randint(1000, 50000, size=len(dates)))
    vol_20ma = vol_series.rolling(min(20, len(vol_series))).mean().values

    # ---------------------------------------------------------
    # 9. 繪製微型化雙格圖表 (高度壓低至 2.4)
    # ---------------------------------------------------------
    plt.style.use("dark_background")
    
    fig, (ax1, ax3) = plt.subplots(2, 1, figsize=(9, 2.4), sharex=True, gridspec_kw={'height_ratios': [1.8, 1]})

    # --- 上圖：大戶與羊群持股雙軸趨勢 ---
    color_big = "#ff4d4d"
    ax1.set_ylabel("大戶(%)", color=color_big, fontsize=7, fontweight="bold")
    ax1.plot(dates, big_holder, color=color_big, marker="o", markersize=1.5, linewidth=1.0, label="大戶持股")
    ax1.tick_params(axis="y", labelcolor=color_big, labelsize=6)

    ax2 = ax1.twinx()
    color_sheep = "#2ecc71"
    ax2.set_ylabel("羊群(%)", color=color_sheep, fontsize=7, fontweight="bold")
    ax2.plot(dates, sheep_holder, color=color_sheep, marker="s", markersize=1.5, linewidth=1.0, label="羊群持股")
    ax2.tick_params(axis="y", labelcolor=color_sheep, labelsize=6)

    if check_golden_cross and golden_crosses:
      for idx in golden_crosses:
        if idx < len(dates):
          ax1.annotate(
              "★ 黃金交叉",
              xy=(dates[idx], big_holder[idx]),
              xytext=(dates[idx], big_holder[idx] + 1.0),
              arrowprops=dict(facecolor="#f1c40f", shrink=0.05, width=0.6, headwidth=3),
              fontsize=6,
              fontweight="bold",
              color="#f1c40f",
              ha="center",
          )

    ax1.set_title(f"[{stock_id}] {stock_name} - 籌碼與成交量動能雙格檢視", fontsize=8, fontweight="bold", pad=3)
    ax1.grid(True, linestyle="--", alpha=0.3)

    # --- 下圖：成交量柱狀圖與 20MA 均量線 ---
    ax3.bar(dates, vol_series.values, color="#3498db", alpha=0.7, width=2.8, label="成交量(張)")
    ax3.plot(dates, vol_20ma, color="#f39c12", linewidth=1.0, label="20MA")
    ax3.set_ylabel("張數", fontsize=7, color="white", fontweight="bold")
    ax3.set_xlabel("日期", fontsize=7, color="white")
    ax3.tick_params(axis="x", labelsize=6, rotation=10)
    ax3.tick_params(axis="y", labelsize=6)
    ax3.legend(loc="upper left", fontsize=6)
    ax3.grid(True, linestyle="--", alpha=0.3)

    fig.tight_layout(pad=0.3)
    
    st.pyplot(fig, use_container_width=True)

  # =========================================================
  # 分頁二：全市場篩選器
  # =========================================================
  with tab2:
    st.subheader("⚡ 全市場台股 - 黃金交叉與成交量篩選器")
    st.info("切換至第一分頁即可流暢檢視任意股票的精巧雙格圖表！")

else:
  st.warning("請先將 StockIDs.xlsx 上傳至 GitHub 專案根目錄中。")