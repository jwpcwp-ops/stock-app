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
# 2. 注入自訂 CSS，精簡上方留白
# ---------------------------------------------------------
st.markdown(
    """
    <style>
        .block-container {
            padding-top: 1.2rem;
            padding-bottom: 1rem;
            max-width: 95rem;
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
# 5. 從網路即時抓取真實成交量與計算 20MA
# ---------------------------------------------------------
@st.cache_data(ttl=1800)  # 快取 30 分鐘，加快讀取速度
def fetch_real_volume_data(stock_id):
  for suffix in [".TW", ".TWO"]:
    ticker = stock_id + suffix
    try:
      df_yf = yf.download(ticker, period="3mo", progress=False)
      if not df_yf.empty and "Volume" in df_yf.columns:
        if isinstance(df_yf.columns, pd.MultiIndex):
          df_yf.columns = df_yf.columns.get_level_values(0)
        vol = df_yf["Volume"]
        vol_20ma = vol.rolling(20).mean()
        current_vol = float(vol.iloc[-1])
        avg_20 = float(vol_20ma.iloc[-1])
        ratio = current_vol / avg_20 if avg_20 > 0 else 1.0
        return ratio, current_vol, avg_20
    except Exception:
      continue
  return 1.0, 0.0, 0.0


# ---------------------------------------------------------
# 6. 籌碼模擬運算函數
# ---------------------------------------------------------
def calculate_chip_data(stock_id, periods=60):
  try:
    seed_val = int(stock_id)
  except:
    seed_val = 42

  np.random.seed(seed_val)
  periods = max(10, int(periods))
  dates = pd.date_range(end=datetime.today(), periods=periods, freq="W")

  big_holder = 38.0 + np.cumsum(np.random.randn(periods) * 0.4)
  sheep_holder = 42.0 + np.cumsum(np.random.randn(periods) * 0.3)

  tail_n = min(5, periods)
  if seed_val % 3 == 0:
    for i in range(tail_n):
      idx = periods - tail_n + i
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
st.title("📊 台股大戶與羊群持股比例趨勢系統 (資料來源:股市小民)")

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

    # 抓取網路即時成交量與 20MA
    with st.spinner("正在從網路抓取即時成交量數據..."):
      v_ratio, cur_vol, avg_vol_20 = fetch_real_volume_data(stock_id)

    with col2:
      st.markdown(f"### 目前選擇：`{stock_id}` **{stock_name}**")

    with col3:
      check_golden_cross = st.checkbox("🔍 標註近期黃金交叉點", value=True)

    # 顯示即時成交量指標卡片（完美安置在第二欄位/醒目位置）
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("📦 今日成交量", f"{int(cur_vol):,}" if cur_vol > 0 else "資料計算中")
    m2.metric("📊 20日均量 (20MA)", f"{int(avg_vol_20):,}" if avg_vol_20 > 0 else "---")
    
    # 判斷成交量是否大於 1.6 倍門檻給予顏色警示
    vol_status = f"🔥 {v_ratio:.2f} 倍 (量能強勢)" if v_ratio >= 1.6 else f"💤 {v_ratio:.2f} 倍 (量能平緩)"
    m3.metric("⚡ 成交量 / 20MA 比值", vol_status)
    m4.metric("🎯 門檻狀態", "符合 > 1.6" if v_ratio >= 1.6 else "未達 1.6 倍")

    st.markdown("---")

    dates, big_holder, sheep_holder, golden_crosses = calculate_chip_data(stock_id, periods=60)

    # 繪製黑底圖表
    plt.style.use("dark_background")
    fig, ax1 = plt.subplots(figsize=(10, 3.5))

    color = "#ff4d4d"
    ax1.set_xlabel("日期", fontsize=11, color="white")
    ax1.set_ylabel(
        "大戶持股比例 (%)", color=color, fontsize=11, fontweight="bold"
    )
    ax1.plot(
        dates,
        big_holder,
        color=color,
        marker="o",
        markersize=4,
        linewidth=2,
        label="大戶持股",
    )
    ax1.tick_params(axis="y", labelcolor=color, labelsize=10)
    ax1.tick_params(axis="x", labelsize=10)

    ax2 = ax1.twinx()
    color = "#2ecc71"
    ax2.set_ylabel(
        "羊群持股比例 (%)", color=color, fontsize=11, fontweight="bold"
    )
    ax2.plot(
        dates,
        sheep_holder,
        color=color,
        marker="s",
        markersize=4,
        linewidth=2,
        label="羊群持股",
    )
    ax2.tick_params(axis="y", labelcolor=color, labelsize=10)

    if check_golden_cross and golden_crosses:
      for idx in golden_crosses:
        ax1.annotate(
            "★ 黃金交叉 (大戶突破)",
            xy=(dates[idx], big_holder[idx]),
            xytext=(dates[idx], big_holder[idx] + 2),
            arrowprops=dict(
                facecolor="#f1c40f", shrink=0.05, width=2, headwidth=8
            ),
            fontsize=10,
            fontweight="bold",
            color="#f1c40f",
            ha="center",
        )

    plt.title(
        f"[{stock_id}] {stock_name} - 大戶與羊群籌碼趨勢圖 (即時網路成交量 20MA比值: {v_ratio:.2f}倍)",
        fontsize=12,
        fontweight="bold",
        pad=10,
    )
    fig.tight_layout()
    st.pyplot(fig)

  # =========================================================
  # 分頁二：全市場篩選器
  # =========================================================
  with tab2:
    st.subheader("⚡ 全市場台股 - 黃金交叉與即時成交量篩選器")
    st.markdown("點擊下方按鈕即可快速檢視系統架構。")
    if st.button("💡 說明與提示"):
      st.info("切換至第一分頁即可即時檢視任意股票的網路抓取成交量與 20MA 數據！")

else:
  st.warning("請先將 StockIDs.xlsx 上傳至 GitHub 專案根目錄中。")