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
    page_title="波段指標專屬測試系統",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ---------------------------------------------------------
# 2. 注入自訂 CSS
# ---------------------------------------------------------
st.markdown(
    """
    <style>
        header[data-testid="stHeader"] { display: none !important; }
        footer { display: none !important; }
        .block-container {
            padding-top: 0.05rem !important;
            padding-bottom: 0.0rem !important;
            padding-left: 0.1rem !important;
            padding-right: 0.1rem !important;
            max-width: 100% !important;
        }
        [data-testid="stHorizontalBlock"] {
            display: flex !important;
            flex-direction: row !important;
            gap: 4px !important;
            align-items: center !important;
            margin-bottom: 2px !important;
        }
        [data-testid="stSelectbox"] {
            max-width: 150px !important;
            width: 150px !important;
            margin-bottom: 0px !important;
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
    plt.rcParams["font.sans-serif"] = ["Microsoft JhengHei", "Arial Unicode MS", "sans-serif"]

plt.rcParams["axes.unicode_minus"] = False

def get_bright_effect(stroke_color="#FFFFFF", linewidth=0.5):
    return [path_effects.withStroke(linewidth=linewidth, foreground=stroke_color), path_effects.Normal()]

# ---------------------------------------------------------
# 4. 讀取股票清單 (StockIDs.xlsx)
# ---------------------------------------------------------
@st.cache_data
def load_stock_list():
    try:
        df = pd.read_excel("StockIDs.xlsx", sheet_name="StockIDs", dtype={"代碼": str})
        df["代碼"] = df["代碼"].astype(str).str.strip().str.replace(r'\.0$', '', regex=True)
        options = df["代碼"] + " " + df["名稱"].astype(str)
        return options.tolist(), df
    except Exception as e:
        default_data = pd.DataFrame({
            "代碼": ["99991", "1477", "2428"],
            "名稱": ["加權指數", "聚陽", "興勤"]
        })
        options = default_data["代碼"] + " " + default_data["名稱"]
        return options.tolist(), default_data

stock_options, stock_df = load_stock_list()

# ---------------------------------------------------------
# 5. 資料抓取函數
# ---------------------------------------------------------
def get_stock_data(stock_id, target_days=250):
    df_yf = pd.DataFrame()
    ticker = "^TWII" if stock_id == "99991" else f"{stock_id}.TW"
    
    try:
        t_obj = yf.Ticker(ticker)
        temp_df = t_obj.history(period="2y", interval="1d", auto_adjust=True)
        if not temp_df.empty and "Close" in temp_df.columns:
            temp_df.index = pd.to_datetime(temp_df.index).tz_localize(None)
            df_yf = temp_df
    except:
        try:
            ticker = f"{stock_id}.TWO"
            t_obj = yf.Ticker(ticker)
            temp_df = t_obj.history(period="2y", interval="1d", auto_adjust=True)
            if not temp_df.empty and "Close" in temp_df.columns:
                temp_df.index = pd.to_datetime(temp_df.index).tz_localize(None)
                df_yf = temp_df
        except:
            pass

    if not df_yf.empty:
        df_yf = df_yf.dropna(subset=["Close"])
        df_k = df_yf.tail(target_days).copy()
        
        k_records = []
        for idx, row in df_k.iterrows():
            k_records.append({
                "date": idx.strftime("%Y/%m/%d"),
                "open": float(row["Open"]),
                "high": float(row["High"]),
                "low": float(row["Low"]),
                "close": float(row["Close"]),
                "vol": float(row["Volume"]) / 1000
            })
    else:
        dates = pd.date_range(end=datetime.today(), periods=target_days, freq="B")
        prices = 100 + np.cumsum(np.random.randn(target_days) * 0.8)
        k_records = []
        for i, d in enumerate(dates):
            k_records.append({
                "date": d.strftime("%Y/%m/%d"),
                "open": prices[i] - 0.5,
                "high": prices[i] + 1.0,
                "low": prices[i] - 1.0,
                "close": prices[i],
                "vol": 10000
            })

    return k_records

# ---------------------------------------------------------
# 6. 主介面與波段繪圖邏輯
# ---------------------------------------------------------
if stock_options:
    col1, col2 = st.columns([1.5, 5.0])
    with col1:
        selected_stock = st.selectbox("選擇測試股票", stock_options, label_visibility="collapsed")
        stock_id = selected_stock.split()[0]
        stock_name = selected_stock.split()[1] if len(selected_stock.split()) > 1 else ""

    # 取得資料
    k_records = get_stock_data(stock_id, target_days=250)
    df = pd.DataFrame(k_records)
    s_close = df["close"]

    # 計算均線
    df["ma_60"] = s_close.rolling(window=60).mean()
    df["ma_250"] = s_close.rolling(window=250).mean()

    # 🎯 萃取：波段專用指標計算 (MACD 5,10 + 反向 BIAS + MTM 10,1)
    df["band_macd_dif"] = s_close.ewm(span=5, adjust=False).mean() - s_close.ewm(span=10, adjust=False).mean()
    df["band_macd_dem"] = df["band_macd_dif"].ewm(span=5, adjust=False).mean()
    df["band_macd_osc"] = (df["band_macd_dif"] - df["band_macd_dem"]) * 2
    
    df["band_bias_base"] = s_close.rolling(window=20).mean()
    df["band_bias_val"] = ((s_close - df["band_bias_base"]) / (df["band_bias_base"] + 1e-8)) * 100
    df["band_bias_val_rev"] = -1.0 * df["band_bias_val"]

    df["mtm_val"] = s_close - s_close.shift(10)
    df["mtm_ma1"] = df["mtm_val"].rolling(window=1).mean()

    # 長趨勢判定
    cond3 = ((s_close.ewm(span=15, adjust=False).mean() / s_close.ewm(span=30, adjust=False).mean() - 1) * 100) > 0
    cond4 = s_close.ewm(span=15, adjust=False).mean() > s_close.ewm(span=30, adjust=False).mean()
    df["long_trend"] = cond3 & cond4

    # 顏色與樣式設定
    BG_COLOR, PANEL_BG, GRID_COLOR, SUB_BORDER = "#000000", "#000000", "#333333", "#666666"
    BAR_UP_COLOR, BAR_DOWN_COLOR = "#FF3B30", "#00C853"
    
    prev_closes = df["close"].shift(1).fillna(df["open"])
    body_colors = [BAR_UP_COLOR if c >= o else BAR_DOWN_COLOR for o, c in zip(df["open"], df["close"])]
    band_macd_bar_colors = [BAR_UP_COLOR if osc >= 0 else BAR_DOWN_COLOR for osc in df["band_macd_osc"]]

    plt.style.use("dark_background")

    # 🎯 建立 4 個獨立子圖 (K線主圖 + 波段MACD + 波段BIAS + 波段MTM)
    fig, axes = plt.subplots(
        4, 1, figsize=(10, 5.0), sharex=True,
        gridspec_kw={"height_ratios": [2.8, 0.7, 0.7, 0.7]}
    )
    ax1, ax_sub1, ax_sub2, ax_sub3 = axes

    for ax in [fig] + list(axes):
        ax.set_facecolor(BG_COLOR)
    fig.patch.set_facecolor(BG_COLOR)
    x = list(range(len(df)))

    # ---------------------------------------------------------
    # 層 1：K線主圖
    # ---------------------------------------------------------
    ax1.set_facecolor(PANEL_BG)
    ax1.vlines(x, df["low"], df["high"], color=body_colors, linewidth=0.5, alpha=0.95)
    body_bottom = [min(o, c) for o, c in zip(df["open"], df["close"])]
    body_height = [max(abs(c - o), 0.01) for o, c in zip(df["open"], df["close"])]
    ax1.bar(x, body_height, bottom=body_bottom, width=0.75, color=body_colors, edgecolor="none")

    if not df.empty:
        p_max = float(df["high"].max())
        p_min = float(df["low"].min())
        p_range = p_max - p_min if p_max != p_min else 1.0
        ax1.set_ylim(p_min - p_range * 0.08, p_max + p_range * 0.15)
        ax1.set_xlim(-1, len(x) + max(4, int(len(x) * 0.12)))

    # 繪製均線
    ax1.plot(x, df["ma_60"], linewidth=0.8, color="#FFA500", label="MA60")
    ax1.plot(x, df["ma_250"], linewidth=0.8, color="#FFFFFF", label="MA250")

    ax1.yaxis.tick_right()
    ax1.tick_params(axis="y", labelsize=7.5, colors="#FFFFFF")
    ax1.grid(True, linestyle="--", color=GRID_COLOR, alpha=0.9)

    last_date = df["date"].iloc[-1]
    last_close = float(df["close"].iloc[-1])
    header_str = f"[{stock_id}] {stock_name}   {last_date}   收盤:{last_close:.2f} (【波段專屬測試模式】)"
    t_header = ax1.text(0.01, 0.90, header_str, transform=ax1.transAxes, fontsize=8.0, fontweight="bold", color="#FFFFFF")
    t_header.set_path_effects(get_bright_effect("#FFFFFF", 0.5))

    # ---------------------------------------------------------
    # 層 2：波段 MACD (5, 10)
    # ---------------------------------------------------------
    cur_band_dif = float(df["band_macd_dif"].iloc[-1]) if not df.empty else 0.0
    ax_sub1.set_facecolor(PANEL_BG)
    ax_sub1.bar(x, df["band_macd_osc"], width=0.75, color=band_macd_bar_colors, edgecolor="none", alpha=0.9)
    ax_sub1.plot(x, df["band_macd_dif"], linewidth=0.6, color="#FFFF00", label="DIF")
    ax_sub1.plot(x, df["band_macd_dem"], linewidth=0.6, color="#FF3B30", label="MACD")
    ax_sub1.axhline(0, color="#666666", linestyle=":", linewidth=1)
    ax_sub1.yaxis.tick_right()
    ax_sub1.tick_params(axis="y", labelsize=7.5, colors="#FFFFFF")
    ax_sub1.grid(True, linestyle="--", color=GRID_COLOR, alpha=0.9)
    
    t_s1 = ax_sub1.text(0.015, 0.76, f"波段 MACD(5,10)  DIF:{cur_band_dif:.2f}", transform=ax_sub1.transAxes, fontsize=8.0, fontweight="bold", color="#FFFFFF")
    t_s1.set_path_effects(get_bright_effect("#FFFFFF", 0.5))

    # ---------------------------------------------------------
    # 層 3：波段 BIAS (反向)
    # ---------------------------------------------------------
    cur_band_bias = float(df["band_bias_val"].iloc[-1]) if not df.empty else 0.0
    ax_sub2.set_facecolor(PANEL_BG)
    ax_sub2.plot(x, df["band_bias_val_rev"], linewidth=0.6, color="#FFFF00", label="BIAS(反向)")
    ax_sub2.axhline(0, color="#666666", linestyle=":", linewidth=1)
    ax_sub2.yaxis.tick_right()
    ax_sub2.tick_params(axis="y", labelsize=7.5, colors="#FFFFFF")
    ax_sub2.grid(True, linestyle="--", color=GRID_COLOR, alpha=0.9)
    
    t_s2 = ax_sub2.text(0.015, 0.76, f"波段 BIAS(反向)  {cur_band_bias:.2f}%", transform=ax_sub2.transAxes, fontsize=8.0, fontweight="bold", color="#FFFFFF")
    t_s2.set_path_effects(get_bright_effect("#FFFFFF", 0.5))

    # ---------------------------------------------------------
    # 層 4：波段 MTM (10, 1)
    # ---------------------------------------------------------
    cur_mtm = float(df["mtm_val"].iloc[-1]) if not df.empty else 0.0
    ax_sub3.set_facecolor(PANEL_BG)
    ax_sub3.plot(x, df["mtm_val"], linewidth=0.6, color="#FFFF00", label="MTM")
    ax_sub3.plot(x, df["mtm_ma1"], linewidth=0.6, color="#008080", label="Avg")
    ax_sub3.axhline(0, color="#666666", linestyle=":", linewidth=1)
    ax_sub3.yaxis.tick_right()
    ax_sub3.tick_params(axis="y", labelsize=7.5, colors="#FFFFFF")
    ax_sub3.grid(True, linestyle="--", color=GRID_COLOR, alpha=0.9)
    
    t_s3 = ax_sub3.text(0.015, 0.76, f"波段 MTM(10,1)  MTM:{cur_mtm:.2f}", transform=ax_sub3.transAxes, fontsize=8.0, fontweight="bold", color="#FFFFFF")
    t_s3.set_path_effects(get_bright_effect("#FFFFFF", 0.5))

    for ax in axes:
        for spine in ax.spines.values():
            spine.set_visible(True)
            spine.set_color(SUB_BORDER)
            spine.set_linewidth(1.0)

    plt.subplots_adjust(left=0.01, right=0.98, top=0.98, bottom=0.02, hspace=0.03)
    st.pyplot(fig, use_container_width=True, dpi=150)

else:
    st.warning("請確認 StockIDs.xlsx 檔案已就位。")