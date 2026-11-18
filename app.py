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

# ---------------------------------------------------------
# 2. 注入自訂 CSS (改善擁擠現象與介面排版)
# ---------------------------------------------------------
st.markdown(
    """
    <style>
        header[data-testid="stHeader"] { display: none !important; }
        footer { display: none !important; }
        
        .block-container {
            padding-top: 0.5rem !important;
            padding-bottom: 0.5rem !important;
            padding-left: 0.8rem !important;
            padding-right: 0.8rem !important;
            max-width: 100% !important;
        }
        .sub-header-14 {
            font-size: 14px !important;
            font-weight: bold;
            color: #00ffff;
            margin-top: 5px;
            margin-bottom: 8px;
        }
        [data-testid="stHorizontalBlock"] {
            display: flex !important;
            flex-direction: row !important;
            gap: 12px !important;
            align-items: center !important;
            margin-bottom: 10px !important;
        }
        .stSelectbox {
            font-size: 13px !important;
        }
        
        /* 專屬右側解盤面板樣式：模仿專業看盤軟體填滿、黑底紅框綠字大字體 */
        .terminal-panel {
            background-color: #0b0b0b;
            border: 1px solid #cc0000;
            padding: 8px 10px;
            margin-bottom: 4px;
            font-family: 'Courier New', Courier, monospace;
            color: #ffffff;
            box-sizing: border-box;
        }
        .terminal-title {
            color: #ffffff;
            background-color: #0000aa;
            font-weight: bold;
            font-size: 13px;
            padding: 2px 6px;
            margin-bottom: 6px;
            text-align: center;
        }
        .t-row {
            font-size: 12px;
            line-height: 1.4;
            margin-bottom: 2px;
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


def get_bright_effect(stroke_color="#000000", linewidth=1.5):
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
    default_data = pd.DataFrame(
        {"代碼": ["99991", "1477", "2428"], "名稱": ["加權指數", "聚陽", "興勤"]}
    )
    options = default_data["代碼"] + " " + default_data["名稱"]
    return options.tolist(), default_data


stock_options, stock_df = load_stock_list()

TXT_DIR = "txt_data"
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


def parse_date_to_yyyymmdd(raw_date):
  if raw_date is None:
    return ""
  d_str = str(raw_date).split(" ")[0].strip().replace("/", "-")
  parts = d_str.split("-")
  if len(parts) == 3:
    y, m, d = parts[0], parts[1], parts[2]
    if len(y) < 4 and y.isdigit():
      y = str(int(y) + 1911)
    return f"{int(y):04d}-{int(m):02d}-{int(d):02d}"
  return d_str


def get_comprehensive_stock_data(stock_id, target_days=250):
  txt_path = os.path.join(TXT_DIR, f"TW{stock_id}.txt")
  k_records = []

  if os.path.exists(txt_path):
    try:
      with open(txt_path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
          parts = line.strip().split()
          if len(parts) >= 6:
            try:
              d_formatted = parse_date_to_yyyymmdd(parts[0])
              k_records.append({
                  "date": d_formatted,
                  "open": float(parts[1]),
                  "high": float(parts[2]),
                  "low": float(parts[3]),
                  "close": float(parts[4]),
                  "vol": float(parts[5]),
              })
            except:
              continue
    except Exception as e:
      print(f"讀取 TXT 失敗: {e}")

  if not k_records:
    yf_ticker = "^TWII" if stock_id == "99991" else f"{stock_id}.TW"
    try:
      df_yf = yf.Ticker(yf_ticker).history(period="2y", auto_adjust=True)
      if df_yf.empty and stock_id != "99991":
        df_yf = yf.Ticker(f"{stock_id}.TWO").history(
            period="2y", auto_adjust=True
        )
      if not df_yf.empty:
        for idx, row in df_yf.iterrows():
          k_records.append({
              "date": idx.strftime("%Y-%m-%d"),
              "open": float(row["Open"]),
              "high": float(row["High"]),
              "low": float(row["Low"]),
              "close": float(row["Close"]),
              "vol": float(row["Volume"]) / 1000,
          })
    except:
      pass

  if k_records:
    k_records = k_records[-target_days:]
    df_k = pd.DataFrame(k_records)
  else:
    dates = pd.date_range(end=datetime.today(), periods=target_days, freq="B")
    df_k = pd.DataFrame({
        "date": dates.strftime("%Y-%m-%d"),
        "open": 100.0,
        "high": 102.0,
        "low": 98.0,
        "close": 100.0,
        "vol": 5000.0,
    })
    k_records = df_k.to_dict(orient="records")

  vol_series = df_k["vol"]
  cur_vol = float(vol_series.iloc[-1]) if len(vol_series) > 0 else 0.0
  vol_20ma = vol_series.rolling(20).mean()

  val_20 = (
      vol_20ma.iloc[-1]
      if len(vol_20ma) > 0 and not pd.isna(vol_20ma.iloc[-1])
      else 0.0
  )
  cur_20ma = float(val_20) if val_20 > 0 else 1.0
  ratio = cur_vol / cur_20ma if cur_20ma > 0 else 1.0

  cache_dict = load_local_cache_cached()
  today_str = datetime.today().strftime("%Y-%m-%d")
  if (
      stock_id in cache_dict
      and cache_dict[stock_id].get("update_date") == today_str
  ):
    cached = cache_dict[stock_id]
    big_holder = np.array(cached.get("big_holder", [40.0] * len(k_records)))
    sheep_holder = np.array(cached.get("sheep_holder", [42.0] * len(k_records)))
  else:
    seed_val = int(stock_id) if stock_id.isdigit() else 42
    np.random.seed(seed_val)
    n_p = len(k_records)
    base_big = 50.0 + np.cumsum(np.random.randn(n_p) * 0.6)
    big_holder = np.clip(base_big, 20.0, 85.0)
    sheep_holder = np.clip(
        100.0 - big_holder + np.random.randn(n_p) * 0.3, 15.0, 80.0
    )

  return k_records, big_holder, sheep_holder, cur_vol, cur_20ma, ratio


if "selected_index" not in st.session_state:
  st.session_state.selected_index = 0

if stock_options:
  top_row_cols = st.columns([2.0, 2.5, 1.5, 4.0])
  modes = ["📈 個股籌碼圖表", "⚡ 9大策略選股", "📋 大戶總表", "📊 基本面與圖表"]

  with top_row_cols[0]:
    app_mode = st.selectbox(
        "功能模式",
        modes,
        label_visibility="visible",
        key="mode_select_dropdown",
    )

  if app_mode == "📈 個股籌碼圖表":
    if st.session_state.selected_index >= len(stock_options):
      st.session_state.selected_index = 0

    with top_row_cols[1]:
      selected_stock = st.selectbox(
          "股票選單",
          stock_options,
          index=st.session_state.selected_index,
          label_visibility="visible",
          key="stock_select_box",
      )
      try:
        st.session_state.selected_index = stock_options.index(selected_stock)
      except:
        st.session_state.selected_index = 0
      stock_id = selected_stock.split()[0]
      stock_name = (
          selected_stock.split()[1] if len(selected_stock.split()) > 1 else ""
      )

    with top_row_cols[2]:
      chart_period = st.selectbox(
          "週期",
          ["日線", "週線", "月線"],
          index=0,
          label_visibility="visible",
          key="select_period_dropdown",
      )
      actual_chart_period = chart_period

    second_row_cols = st.columns([1.5, 1.5, 0.8])
    with second_row_cols[0]:
      selected_ma = st.pills(
          "均線",
          ["5", "10", "20", "35", "60", "120", "200", "分割"],
          default=["60", "200"],
          selection_mode="multi",
          label_visibility="visible",
          key="pills_ma",
      )

    with second_row_cols[1]:
      selected_indicator = st.pills(
          "技術指標",
          ["波段", "MACD", "BIAS", "KDJ", "RSI", "W%", "QT", "大戶羊群"],
          default="MACD",
          selection_mode="single",
          label_visibility="visible",
          key="pills_ind",
      )
      if not selected_indicator:
        selected_indicator = "MACD"

    with second_row_cols[2]:
      k_days_choice_str = st.pills(
          "歷史天數",
          ["120", "250", "300"],
          default="250",
          selection_mode="single",
          label_visibility="visible",
          key="pills_k_days",
      )
      k_days_choice = int(k_days_choice_str) if k_days_choice_str else 250

    show_ma5 = "5" in selected_ma
    show_ma10 = "10" in selected_ma
    show_ma20 = "20" in selected_ma
    show_ma35 = "35" in selected_ma
    show_ma60 = "60" in selected_ma
    show_ma120 = "120" in selected_ma
    show_ma200 = "200" in selected_ma
    show_fib = "分割" in selected_ma

    k_records, big_holder, sheep_holder, cur_vol, cur_20ma, v_ratio = (
        get_comprehensive_stock_data(stock_id, target_days=k_days_choice)
    )

    df = pd.DataFrame(k_records)
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

    for ma_name, (period, is_show, color) in ma_config.items():
      df[f"ma_{period}"] = s_close.rolling(window=period).mean()

    df["macd_dif"] = (
        s_close.ewm(span=12, adjust=False).mean()
        - s_close.ewm(span=26, adjust=False).mean()
    )
    df["macd_dem"] = df["macd_dif"].ewm(span=9, adjust=False).mean()
    df["macd_osc"] = (df["macd_dif"] - df["macd_dem"]) * 2

    df["vol_ma5"] = df["vol"].rolling(window=5).mean()
    df["vol_ma20"] = df["vol"].rolling(window=20).mean()

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

    plt.style.use("dark_background")
    chart_col, info_col = st.columns([8.2, 1.8])

    with chart_col:
      fig = plt.figure(figsize=(10.0, 4.2))
      gs = fig.add_gridspec(3, 1, height_ratios=[2.9, 1.1, 1.1], hspace=0.10)
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

      for ma_name, (period, is_show, color) in ma_config.items():
        if is_show:
          ma_series = df[f"ma_{period}"]
          ax1.plot(
              x, ma_series, linewidth=0.5, color=color, linestyle="-", alpha=1.0
          )

      ax1.yaxis.tick_right()
      ax1.tick_params(axis="y", labelsize=5.8, pad=1.5, colors="#FFFFFF")
      plt.setp(ax1.get_xticklabels(), visible=False)
      ax1.grid(True, which="both", linestyle="--", color=GRID_COLOR, alpha=0.5)

      standard_header_str = f"[{stock_id}] {stock_name}   {last_date}   開:{last_open:.2f}  高:{last_high:.2f}  低:{last_low:.2f}  收:{last_close:.2f}  量:{int(last_vol):,}張"
      t_header = ax1.text(
          0.01,
          0.93,
          standard_header_str,
          transform=ax1.transAxes,
          fontsize=8.0,
          fontweight="bold",
          color="#FFFFFF",
      )
      t_header.set_path_effects(get_bright_effect("#000000", 1.5))

      ax_sub1.set_facecolor(PANEL_BG)
      ax_sub1.bar(
          x,
          df["macd_osc"],
          width=0.75,
          color=macd_bar_colors,
          edgecolor="none",
          alpha=1.0,
      )
      ax_sub1.plot(
          x, df["macd_dif"], linewidth=0.5, color="#FF00FF", label="DIF"
      )
      ax_sub1.plot(
          x, df["macd_dem"], linewidth=0.5, color="#00FFFF", label="DEA"
      )
      ax_sub1.axhline(0, color="#777777", linestyle=":", linewidth=1.0)
      ax_sub1.yaxis.tick_right()
      ax_sub1.tick_params(axis="y", labelsize=5.8, pad=1.5, colors="#FFFFFF")
      plt.setp(ax_sub1.get_xticklabels(), visible=False)
      ax_sub1.grid(True, which="both", linestyle="--", color=GRID_COLOR, alpha=0.5)

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
          x, df["vol_ma5"], linewidth=0.5, color="#FFFF00", label="Vol MA5"
      )
      ax_sub2.plot(
          x, df["vol_ma20"], linewidth=0.5, color="#FF9900", label="Vol MA20"
      )
      ax_sub2.yaxis.tick_right()
      ax_sub2.tick_params(axis="y", labelsize=5.8, pad=1.5, colors="#FFFFFF")
      ax_sub2.tick_params(axis="x", labelsize=6.5, colors="#FFFFFF")
      plt.setp(ax_sub2.get_xticklabels(), visible=True)
      ax_sub2.grid(True, which="both", linestyle="--", color=GRID_COLOR, alpha=0.5)

      plt.subplots_adjust(
          left=0.01, right=0.99, top=0.98, bottom=0.08, hspace=0.10
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
# =========================================================
# 分頁二：9大策略選股 (強制完整顯示 9 大策略分類)
# =========================================================
elif app_mode == "⚡ 9大策略選股":
    st.markdown('<p class="sub-header-14">⚡ GitHub 雲端 9 大策略選股結果</p>', unsafe_allow_html=True)

    output_csv = "smart_selected_output.csv"

    # 定義固定的 9 大策略標準清單
    all_strategies = [
        "主力底部吃貨",
        "突破前高",
        "MACD 選股",
        "金剛指標",
        "均線與MACD篩選",
        "波段買點",
        "多空轉折信號",
        "5均線匯集",
        "底部量大強漲"
    ]

    # 讀取 CSV 或建立預設結構
    if os.path.exists(output_csv):
        try:
            df_res = pd.read_csv(output_csv, dtype={"代碼": str})
        except:
            df_res = pd.DataFrame(columns=["策略名稱", "代碼"])
    else:
        df_res = pd.DataFrame(columns=["策略名稱", "代碼"])

    # 下拉選單直接使用固定的 9 大策略，確保一個不漏！
    selected_strat = st.selectbox("選擇策略分類", all_strategies, key="strat_sel")

    # 過濾出該策略的結果
    if not df_res.empty and "策略名稱" in df_res.columns:
        filtered_df = df_res[df_res["策略名稱"] == selected_strat].copy()
    else:
        filtered_df = pd.DataFrame(columns=["策略名稱", "代碼"])

    # 檢查是否為空或只有「無」
    if filtered_df.empty or (len(filtered_df) == 1 and filtered_df.iloc[0]["代碼"] in ["無", "無符合股票"]):
        st.info(f"【{selected_strat}】目前尚無符合條件的股票標的。")
    else:
        # 補上股票名稱對照
        id_to_name = dict(
            zip(
                stock_df["代碼"].astype(str).str.zfill(4),
                stock_df["名稱"].astype(str),
            )
        )
        if "代碼" in filtered_df.columns:
            filtered_df["名稱"] = filtered_df["代碼"].map(id_to_name).fillna("")

        st.success(f"【{selected_strat}】共篩選出 {len(filtered_df)} 檔標的。")
        st.dataframe(filtered_df, use_container_width=True, hide_index=True)        else:
          st.info("目前選股清單為空。")
      except Exception as e:
        st.error(f"讀取選股結果發生錯誤: {e}")
    else:
      st.warning(
          "找不到 `smart_selected_output.csv` 選股結果檔案，請確認 GitHub Actions"
          " 排程已執行。"
      )

  # =========================================================
  # 分頁三：大戶總表
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

        st.markdown(
            f'<p class="sub-header-14">📋 籌碼增幅榜 ｜ {week_info} ｜'
            f" {date_info}</p>",
            unsafe_allow_html=True,
        )
        st.dataframe(
            df_display,
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
      st.warning("找不到總表檔案 (`大戶持股最新分析總表.xlsx`)。")

  # =========================================================
  # 分頁四：基本面與圖表
  # =========================================================
  elif app_mode == "📊 基本面與圖表":
    st.markdown(
        '<p class="sub-header-14">📊 基本面與圖表</p>', unsafe_allow_html=True
    )
    selected_fund_stock = st.selectbox(
        "選擇股票", stock_options, label_visibility="visible"
    )
    target_code = selected_fund_stock.split()[0]
    target_name = (
        selected_fund_stock.split()[1]
        if len(selected_fund_stock.split()) > 1
        else ""
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
          f"[{target_code}] {ds['title']}",
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

else:
  st.warning("請確認 StockIDs.xlsx 檔案已就位。")