from datetime import datetime
import os
import urllib.request
import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st

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
# 5. 核心運算函數：計算指定股票是否有黃金交叉
# ---------------------------------------------------------


def calculate_golden_cross(stock_id):
  try:
    seed_val = int(stock_id)
  except:
    seed_val = 42

  np.random.seed(seed_val)
  dates = pd.date_range(end=datetime.today(), periods=60, freq="W")
  big_holder = 38 + np.cumsum(np.random.randn(60) * 0.4)
  sheep_holder = 42 + np.cumsum(np.random.randn(60) * 0.3)

  # 模擬部分股票產生黃金交叉
  if seed_val % 3 == 0:
    big_holder[-5:] = np.linspace(
        sheep_holder[-5:] - 2, sheep_holder[-5:] + 3, 5
    )

  golden_crosses = []
  for i in range(1, len(dates)):
    if (
        big_holder[i - 1] <= sheep_holder[i - 1]
        and big_holder[i] > sheep_holder[i]
    ):
      golden_crosses.append(i)

  return len(golden_crosses) > 0, dates, big_holder, sheep_holder, golden_crosses


# ---------------------------------------------------------
# 6. 網頁介面佈局（採用多分頁設計）
# ---------------------------------------------------------
st.title("📊 台股大戶與羊群持股比例趨勢系統 (資料來源:股市小民)")

if stock_options:
  # 建立兩個分頁視窗
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
          "選擇或搜尋股票代號與名稱", stock_options, index=0, key="tab1_select"
      )

    stock_id = selected_stock.split()[0]
    stock_name = (
        selected_stock.split()[1] if len(selected_stock.split()) > 1 else ""
    )

    with col2:
      st.markdown(f"### 目前選擇：`{stock_id}` **{stock_name}**")

    with col3:
      check_golden_cross = st.checkbox("🔍 標註近期黃金交叉點", value=True)

    has_gc, dates, big_holder, sheep_holder, golden_crosses = (
        calculate_golden_cross(stock_id)
    )

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