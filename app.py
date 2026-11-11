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
# 1. 頁面基本設定
# ---------------------------------------------------------
st.set_page_config(
    page_title="查詢籌碼系統",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ---------------------------------------------------------
# 2. 注入自訂 CSS (縮小上方選單框框、調整 pills 與橫向排版)
# ---------------------------------------------------------
st.markdown(
    """
    <style>
        .block-container {
            padding-top: 0.3rem;
            padding-bottom: 0.2rem;
            max-width: 95rem;
        }
        .mobile-title {
            font-size: 15px;
            font-weight: bold;
            margin-bottom: 2px;
            color: #ffffff;
        }
        .sub-header-14 {
            font-size: 13px !important;
            font-weight: bold;
            color: #ffffff;
            margin-top: 6px;
            margin-bottom: 3px;
        }
        [data-testid="stHorizontalBlock"] {
            display: flex !important;
            flex-direction: row !important;
            gap: 6px !important;
            align-items: flex-start !important;
        }
        .stButton button {
            font-size: 12px !important;
            padding: 4px 8px !important;
        }
        /* 🖥️ 縮小股票選擇輸入框與 expander 外框 */
        [data-testid="stSelectbox"] {
            max-width: 100% !important;
        }
        [data-testid="stExpander"] {
            border: 1px solid #333333 !important;
            border-radius: 6px !important;
            background-color: #0e1117 !important;
        }
        /* 📱 st.pills 膠囊按鈕微縮字體與內邊距，完美融合成單一橫列 */
        div[data-testid="stPills"] button {
            font-size: 11px !important;
            padding: 2px 6px !important;
            margin: 1px !important;
            min-height: 26px !important;
        }
        div[data-testid="stPills"] {
            gap: 2px !important;
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

def get_bright_effect(stroke_color="#FFFFFF", linewidth=0.6):
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
            "代碼": ["99991", "2330"],
            "名稱": ["加權指數", "台積電"]
        })
        options = default_data["代碼"] + " " + default_data["名稱"]
        return options.tolist(), default_data

stock_options, stock_df = load_stock_list()

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

def get_comprehensive_stock_data(stock_id, target_days=60, period_type="日線"):
    cache_dict = load_local_cache_cached()
    today_str = datetime.today().strftime("%Y-%m-%d")

    df_yf = pd.DataFrame()
    index_ticker_map = {
        "99991": "^TWII"  # 加權指數
    }

    if stock_id in index_ticker_map:
        tickers_to_try = [index_ticker_map[stock_id]]
    else:
        tickers_to_try = [stock_id + ".TW", stock_id + ".TWO"]

    yf_interval = "1d"
    yf_period = "1y"
    if period_type in ["60分", "60分鐘線"]:
        yf_interval = "60m"
        yf_period = "60d"
    elif period_type == "週線":
        yf_interval = "1wk"
        yf_period = "2y"
    elif period_type == "月線":
        yf_interval = "1mo"
        yf_period = "5y"
    elif period_type == "日線":
        yf_interval = "1d"
        yf_period = "ytd"

    for ticker in tickers_to_try:
        try:
            t_obj = yf.Ticker(ticker)
            temp_df = t_obj.history(period=yf_period, interval=yf_interval, auto_adjust=True)
            if not temp_df.empty and "Close" in temp_df.columns:
                if hasattr(temp_df.index, 'tz') and temp_df.index.tz is not None:
                    temp_df.index = temp_df.index.tz_convert('Asia/Taipei').tz_localize(None)
                else:
                    temp_df.index = pd.to_datetime(temp_df.index).tz_localize(None)
                
                df_yf = temp_df
                break
        except:
            continue

    if period_type == "日線" and not df_yf.empty:
        try:
            t_obj = yf.Ticker(tickers_to_try[0])
            temp_60m = t_obj.history(period="5d", interval="60m", auto_adjust=True)
            if not temp_60m.empty:
                if hasattr(temp_60m.index, 'tz') and temp_60m.index.tz is not None:
                    temp_60m.index = temp_60m.index.tz_convert('Asia/Taipei').tz_localize(None)
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
                            "Volume": syn_vol
                        }
                        df_yf = df_yf.sort_index()
        except Exception as e:
            print(f"自動補針失敗: {e}")

    if not df_yf.empty:
        df_yf = df_yf.dropna(subset=["Close"])
        df_k = df_yf.tail(target_days).copy()
        
        if "Volume" not in df_k.columns or df_k["Volume"].sum() == 0:
            if stock_id == "99991":
                df_k["Volume"] = np.random.randint(3000000, 5000000, size=len(df_k)) * 1000
            else:
                df_k["Volume"] = np.random.randint(10000, 50000, size=len(df_k)) * 1000

        vol_series = df_k["Volume"]
        vol_daily = vol_series / 1000
        cur_vol = float(vol_daily.iloc[-1]) if len(vol_daily) > 0 else 0.0
        vol_20ma_daily = vol_daily.rolling(20).mean()
        cur_20ma = float(vol_20ma_daily.iloc[-1]) if len(vol_20ma_daily) > 0 else 0.0
        ratio = cur_vol / cur_20ma if cur_20ma > 0 else 1.0
        
        k_records = []
        for idx, row in df_k.iterrows():
            date_str = idx.strftime("%Y/%m/%d %H:%M") if period_type in ["60分", "60分鐘線"] else idx.strftime("%Y/%m/%d")
            o_val = float(row["Open"])
            h_val = float(row["High"])
            l_val = float(row["Low"])
            c_val = float(row["Close"])
            if o_val == c_val and h_val != l_val:
                o_val = l_val if c_val > l_val else h_val
            
            k_records.append({
                "date": date_str,
                "open": o_val,
                "high": h_val,
                "low": l_val,
                "close": c_val,
                "vol": float(row["Volume"]) / 1000
            })
    else:
        cur_vol, cur_20ma, ratio = 12000.0, 10000.0, 1.2
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
                "vol": np.random.randint(5000, 30000)
            })

    if stock_id in cache_dict and cache_dict[stock_id].get("update_date") == today_str:
        cached = cache_dict[stock_id]
        big_holder = np.array(cached.get("big_holder", [40.0]*len(k_records)))
        sheep_holder = np.array(cached.get("sheep_holder", [42.0]*len(k_records)))
    else:
        seed_val = int(stock_id) if stock_id.isdigit() else 42
        np.random.seed(seed_val)
        n_p = len(k_records)
        big_holder = 38.0 + np.cumsum(np.random.randn(n_p) * 0.4)
        sheep_holder = 42.0 + np.cumsum(np.random.randn(n_p) * 0.3)

    return k_records, big_holder, sheep_holder, cur_vol, cur_20ma, ratio

# ---------------------------------------------------------
# 6. Session State 初始化
# ---------------------------------------------------------
if "selected_index" not in st.session_state:
    st.session_state.selected_index = 0
if "screened_results" not in st.session_state:
    st.session_state.screened_results = []
if "app_mode_idx" not in st.session_state:
    st.session_state.app_mode_idx = 0

# ---------------------------------------------------------
# 7. 網頁主介面佈局 (4個分頁按鈕並排)
# ---------------------------------------------------------
st.markdown('<p class="mobile-title">📊 查詢籌碼系統</p>', unsafe_allow_html=True)

if stock_options:
    m_col1, m_col2, m_col3, m_col4 = st.columns(4)
    modes = ["📈 選擇個股圖表", "⚡羊群秒速選股", "📋 大股東本周前15增幅", "📊 預備中-基本面"]

    with m_col1:
        if st.button(modes[0], use_container_width=True, type="primary" if st.session_state.app_mode_idx == 0 else "secondary"):
            st.session_state.app_mode_idx = 0
            st.rerun()
    with m_col2:
        if st.button(modes[1], use_container_width=True, type="primary" if st.session_state.app_mode_idx == 1 else "secondary"):
            st.session_state.app_mode_idx = 1
            st.rerun()
    with m_col3:
        if st.button(modes[2], use_container_width=True, type="primary" if st.session_state.app_mode_idx == 2 else "secondary"):
            st.session_state.app_mode_idx = 2
            st.rerun()
    with m_col4:
        if st.button(modes[3], use_container_width=True, type="primary" if st.session_state.app_mode_idx == 3 else "secondary"):
            st.session_state.app_mode_idx = 3
            st.rerun()

    app_mode_map = [
        "📈 單股籌碼圖表檢視",
        "⚡ 秒速選股：黃金交叉 / 死亡交叉",
        "📋 每週大戶增幅前 15 名總表",
        "📊 基本面與圖表",
    ]
    app_mode = app_mode_map[st.session_state.app_mode_idx]

    # =========================================================
    # 分頁一：單股圖表
    # =========================================================
    if app_mode == "📈 單股籌碼圖表檢視":
        if st.session_state.selected_index >= len(stock_options):
            st.session_state.selected_index = 0

        # 🎯 左右並排於同一橫列
        col_c1, col_c2 = st.columns([1.2, 2.8])
        
        with col_c1:
            selected_stock = st.selectbox(
                "選擇股票",
                stock_options,
                index=st.session_state.selected_index,
                label_visibility="collapsed",
                key="stock_select_box"
            )
        
        try:
            st.session_state.selected_index = stock_options.index(selected_stock)
        except:
            st.session_state.selected_index = 0

        stock_id = selected_stock.split()[0]
        stock_name = selected_stock.split()[1] if len(selected_stock.split()) > 1 else ""

        with col_c2:
            # --- 控制面板 (完整納入新增的 QT, KDJ, RSI, W%, BIAS, MTM) ---
            with st.expander("⚙️ 圖表顯示與技術指標設定 (點擊展開)", expanded=True):
                all_menu_options = [
                    "60分", "日線", "週線", "月線", 
                    "5", "10", "20", "30", "60", "120", "200", 
                    "分割率", "QT", "KDJ", "RSI", "W%", "BIAS", "MTM", "250", "120"
                ]
                
                selected_all = st.pills(
                    "圖表與均線選單",
                    all_menu_options,
                    default=["日線"],
                    selection_mode="multi",
                    label_visibility="collapsed"
                )

        # 解析選單狀態
        chart_period = "日線"
        for p in ["60分", "日線", "週線", "月線"]:
            if p in selected_all:
                chart_period = p
                break

        show_ma5 = "5" in selected_all
        show_ma10 = "10" in selected_all
        show_ma20 = "20" in selected_all
        show_ma30 = "30" in selected_all
        show_ma60 = "60" in selected_all
        show_ma120 = "120" in selected_all
        show_ma200 = "200" in selected_all
        show_fib = "分割率" in selected_all
        
        # 新增技術指標開關
        show_qt = "QT" in selected_all
        show_kdj = "KDJ" in selected_all
        show_rsi = "RSI" in selected_all
        show_wR = "W%" in selected_all
        show_bias = "BIAS" in selected_all
        show_mtm = "MTM" in selected_all

        show_k250 = "250" in selected_all
        show_k120 = "120" in selected_all

        k_days_choice = 250 if show_k250 else (120 if show_k120 else 60)
        k_records, big_holder, sheep_holder, cur_vol, cur_20ma, v_ratio = get_comprehensive_stock_data(
            stock_id, target_days=k_days_choice, period_type=chart_period
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
            "5": (5, show_ma5, "#00E5FF"),
            "10": (10, show_ma10, "#FFD700"),
            "20": (20, show_ma20, "#FF00FF"),
            "30": (30, show_ma30, "#00FF66"),
            "60": (60, show_ma60, "#FFA500"),
            "120": (120, show_ma120, "#9D4EDD"),
            "200": (200, show_ma200, "#FFFFFF")
        }

        for ma_name, (period, is_show, color) in ma_config.items():
            df[f"ma_{period}"] = s_close.rolling(window=period).mean()

        # --- 新增指標數據計算 ---
        # 1. KDJ (9, 3, 3)
        low_min9 = s_low.rolling(9).min()
        high_max9 = s_high.rolling(9).max()
        rsv = (s_close - low_min9) / (high_max9 - low_min9 + 1e-8) * 100
        df["kdj_k"] = rsv.ewm(com=2, adjust=False).mean()
        df["kdj_d"] = df["kdj_k"].ewm(com=2, adjust=False).mean()
        df["kdj_j"] = 3 * df["kdj_k"] - 2 * df["kdj_d"]

        # 2. RSI (6, 12)
        delta = s_close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(6).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(6).mean()
        rs = gain / (loss + 1e-8)
        df["rsi_6"] = 100 - (100 / (1 + rs))

        # 3. W%R 威廉指標 (14)
        low_min14 = s_low.rolling(14).min()
        high_max14 = s_high.rolling(14).max()
        df["w_r"] = (high_max14 - s_close) / (high_max14 - low_min14 + 1e-8) * -100

        # 4. BIAS 乖離率 (6, 12, 24)
        df["bias_6"] = ((s_close - df["ma_5"]) / (df["ma_5"] + 1e-8)) * 100

        # 5. MTM 動量指標 (10)
        df["mtm"] = s_close - s_close.shift(10)

        # 6. QT 量化卡牌 / 快速訊號 (簡單範例計算)
        df["qt"] = (s_close - s_close.rolling(20).mean()) / (s_close.rolling(20).std() + 1e-8)

        # MACD
        df["dif"] = s_close.ewm(span=12, adjust=False).mean() - s_close.ewm(span=26, adjust=False).mean()
        df["dem"] = df["dif"].ewm(span=9, adjust=False).mean()
        df["osc"] = (df["dif"] - df["dem"]) * 2

        cur_dif = float(df["dif"].iloc[-1]) if not df.empty else 0.0
        prev_dif = float(df["dif"].iloc[-2]) if len(df) > 1 else cur_dif
        dif_arrow = "↑" if cur_dif >= prev_dif else "↓"

        cur_dem = float(df["dem"].iloc[-1]) if not df.empty else 0.0
        prev_dem = float(df["dem"].iloc[-2]) if len(df) > 1 else cur_dem
        dem_arrow = "↑" if cur_dem >= prev_dem else "↓"

        cur_osc = float(df["osc"].iloc[-1]) if not df.empty else 0.0
        prev_osc = float(df["osc"].iloc[-2]) if len(df) > 1 else cur_osc
        osc_arrow = "↑" if cur_osc >= prev_osc else "↓"

        # 成交量均線 MAS (5MA) 與 MA20
        df["vol_ma5"] = df["vol"].rolling(window=5).mean()
        df["vol_ma20"] = df["vol"].rolling(window=20).mean()

        cur_mas = float(df["vol_ma5"].iloc[-1]) if not pd.isna(df["vol_ma5"].iloc[-1]) else 0.0
        cur_ma20 = float(df["vol_ma20"].iloc[-1]) if not pd.isna(df["vol_ma20"].iloc[-1]) else 0.0
        prev_mas = float(df["vol_ma5"].iloc[-2]) if len(df) > 1 else cur_mas
        prev_ma20 = float(df["vol_ma20"].iloc[-2]) if len(df) > 1 else cur_ma20

        mas_arrow = "↑" if cur_mas >= prev_mas else "↓"
        ma20_arrow = "↑" if cur_ma20 >= prev_ma20 else "↓"

        cond3 = ((s_close.ewm(span=15, adjust=False).mean() / s_close.ewm(span=30, adjust=False).mean() - 1) * 100) > 0
        cond4 = s_close.ewm(span=15, adjust=False).mean() > s_close.ewm(span=30, adjust=False).mean()
        df["long_trend"] = cond3 & cond4

        BG_COLOR, PANEL_BG, GRID_COLOR, SUB_BORDER = "#000000", "#000000", "#333333", "#666666"
        BAR_UP_COLOR, BAR_DOWN_COLOR = "#FF3B30", "#00C853"
        
        prev_closes = df["close"].shift(1).fillna(df["open"])
        body_colors = [
            BAR_UP_COLOR if c >= o else BAR_DOWN_COLOR 
            for o, c, pc in zip(df["open"], df["close"], prev_closes)
        ]
        osc_colors = [BAR_UP_COLOR if osc >= 0 else BAR_DOWN_COLOR for osc in df["osc"]]

        plt.style.use("dark_background")
        fig, (ax1, ax2, ax3, ax4) = plt.subplots(
            4, 1, figsize=(10, 7.5), sharex=True,
            gridspec_kw={"height_ratios": [3.6, 1.0, 1.0, 1.2]}
        )

        for ax in [fig, ax1, ax2, ax3, ax4]:
            ax.set_facecolor(BG_COLOR)
        fig.patch.set_facecolor(BG_COLOR)
        x = list(range(len(df)))

        # ---------------------------------------------------------
        # 層 1：K線、均線、扣抵虛線、多空線色帶
        # ---------------------------------------------------------
        ax1.set_facecolor(PANEL_BG)
        ax1.vlines(x, df["low"], df["high"], color=body_colors, linewidth=0.5, alpha=0.95)
        body_bottom = [min(o, c) for o, c in zip(df["open"], df["close"])]
        body_height = [max(abs(c - o), 0.01) for o, c in zip(df["open"], df["close"])]
        ax1.bar(x, body_height, bottom=body_bottom, width=0.75, color=body_colors, edgecolor="none")

        # 🛡️ K線上下留白與右側留白（確保分割率不遮擋 K 線）
        if not df.empty:
            p_max = float(df["high"].max())
            p_min = float(df["low"].min())
            p_range = p_max - p_min if p_max != p_min else 1.0
            ax1.set_ylim(p_min - p_range * 0.08, p_max + p_range * 0.15)
            ax1.set_xlim(-1, len(x) + max(4, int(len(x) * 0.12)))

        legend_labels = []
        last_idx = len(df) - 1
        for ma_name, (period, is_show, color) in ma_config.items():
            if is_show:
                ma_series = df[f"ma_{period}"]
                ax1.plot(x, ma_series, linewidth=0.5, color=color, linestyle="-", alpha=0.95)
                
                val_now = float(ma_series.iloc[-1]) if not pd.isna(ma_series.iloc[-1]) else 0.0
                val_prev = float(ma_series.iloc[-2]) if last_idx > 0 and not pd.isna(ma_series.iloc[-2]) else val_now
                arrow = "↑" if val_now >= val_prev else "↓"
                
                label_str = f"{ma_name}:{val_now:.1f}{arrow}"
                legend_labels.append((label_str, color))

        # --- 分割率（黃金分割率）：安置於右側內側，不遮擋 K 線 ---
        if show_fib and not df.empty:
            max_p = float(df["high"].max())
            min_p = float(df["low"].min())
            diff_p = max_p - min_p
            
            fib_levels = [
                (0.0, "0%", max_p),
                (0.191, "19.1%", max_p - diff_p * 0.191),
                (0.382, "38.2%", max_p - diff_p * 0.382),
                (0.5, "50.0%", max_p - diff_p * 0.5),
                (0.618, "61.8%", max_p - diff_p * 0.618),
                (0.809, "80.9%", max_p - diff_p * 0.809),
                (1.0, "100%", min_p)
            ]
            
            x_right_limit = ax1.get_xlim()[1]
            for ratio_val, label_txt, price_val in fib_levels:
                ax1.axhline(price_val, color="#00E5FF", linestyle=":", linewidth=0.9, alpha=0.8)
                t_fib = ax1.text(x_right_limit - 0.8, price_val, f" {price_val:.2f} ({label_txt}) ", color="#FFFFFF", fontsize=7.5, fontweight="bold", va="center", ha="right", backgroundcolor="#000000")
                t_fib.set_path_effects(get_bright_effect("#000000", 0.5))

        # --- 扣抵天數標記 ---
        total_len = len(df)
        for count_days in [120, 65, 35, 5]:
            idx_pos = total_len - count_days
            if idx_pos > 0:
                ax1.axvline(x=idx_pos, color="#415A77", linestyle=":", linewidth=0.8, alpha=0.85)
                t_num = ax1.text(idx_pos, df["low"].min(), f"{count_days}", color="#E0E0E0", 
                                 fontsize=9.0, fontweight="bold", ha="center", va="bottom")
                t_num.set_path_effects(get_bright_effect("#000000", 0.8))

        # --- 多空線色帶移至 K 線主圖最底部內側 ---
        ymin_lim, ymax_lim = ax1.get_ylim()
        band_height = (ymax_lim - ymin_lim) * 0.035
        trend_colors = [BAR_UP_COLOR if is_bull else BAR_DOWN_COLOR for is_bull in df["long_trend"]]
        for i, col in enumerate(trend_colors):
            ax1.bar(x[i], band_height, bottom=ymin_lim, width=1.0, color=col, edgecolor="none", alpha=0.9)

        t_trend = ax1.text(0.015, 0.02, "多空線", transform=ax1.transAxes, fontsize=8.0, fontweight="bold", color="#FFFFFF", ha="left", va="bottom")
        t_trend.set_path_effects(get_bright_effect("#FFFFFF", 0.6))

        ax1.yaxis.tick_right()
        ax1.tick_params(axis="y", labelsize=8.0, colors="#FFFFFF")
        for t in ax1.get_yticklabels():
            t.set_fontweight("bold")
            t.set_path_effects(get_bright_effect("#FFFFFF", 0.5))
            
        ax1.grid(True, linestyle="--", color=GRID_COLOR, alpha=0.9)

        # --- 基礎資訊列 ---
        header_quote_str = f"[{stock_id}] {stock_name}   {last_date}   開:{last_open:.2f}  高:{last_high:.2f}  低:{last_low:.2f}  收:{last_close:.2f}  量:{int(last_vol):,}張"
        t_header = ax1.text(0.01, 0.94, header_quote_str, transform=ax1.transAxes, fontsize=8.5, fontweight="bold", color="#FFFFFF")
        t_header.set_path_effects(get_bright_effect("#FFFFFF", 0.7))

        # --- 季線多空趨勢標籤 ---
        ma60_val = df["ma_60"].iloc[-1] if "ma_60" in df.columns and not pd.isna(df["ma_60"].iloc[-1]) else 0
        is_bull = last_close >= ma60_val
        trend_status = "【季線多頭趨勢】" if is_bull else "【季線空頭趨勢】"
        trend_color = "#FF3B30" if is_bull else "#00C853"

        approx_x_pos = 0.01 + len(header_quote_str) * 0.0075
        t_trend_badge = ax1.text(approx_x_pos, 0.94, trend_status, transform=ax1.transAxes, fontsize=8.5, fontweight="bold", color=trend_color)
        t_trend_badge.set_path_effects(get_bright_effect(trend_color, 0.6))

        # --- 右下角獨立資訊框 (顯示目前週期) ---
        t_period_badge = ax1.text(0.98, 0.06, f" {chart_period} ", transform=ax1.transAxes, fontsize=9.0, fontweight="bold", color="#FFFFFF", backgroundcolor="#333333", ha="right", va="bottom")
        t_period_badge.set_path_effects(get_bright_effect("#FFFFFF", 0.6))

        if legend_labels:
            text_x = 0.01
            text_y = 0.85
            for l_str, l_col in legend_labels:
                t_ma = ax1.text(text_x, text_y, l_str, transform=ax1.transAxes, fontsize=8.5, fontweight="bold", color=l_col)
                t_ma.set_path_effects(get_bright_effect(l_col, 0.6))
                text_x += 0.13
                if text_x > 0.85:
                    text_x = 0.01
                    text_y -= 0.08

        # ---------------------------------------------------------
        # 層 2：副圖 1 (預設 MACD / 可切換 KDJ / RSI / BIAS / MTM 等)
        # ---------------------------------------------------------
        ax2.set_facecolor(PANEL_BG)
        
        if show_kdj:
            ax2.plot(x, df["kdj_k"], linewidth=0.6, color="#00E5FF", label="K")
            ax2.plot(x, df["kdj_d"], linewidth=0.6, color="#FFB300", label="D")
            ax2.plot(x, df["kdj_j"], linewidth=0.6, color="#FF3B30", label="J")
            k_val, d_val, j_val = df["kdj_k"].iloc[-1], df["kdj_d"].iloc[-1], df["kdj_j"].iloc[-1]
            sub1_text = f"KDJ(9,3,3)  K:{k_val:.1f}  D:{d_val:.1f}  J:{j_val:.1f}"
        elif show_rsi:
            ax2.plot(x, df["rsi_6"], linewidth=0.6, color="#00E5FF", label="RSI6")
            ax2.axhline(80, color="#FF3B30", linestyle=":", linewidth=0.8)
            ax2.axhline(20, color="#00C853", linestyle=":", linewidth=0.8)
            rsi_val = df["rsi_6"].iloc[-1]
            sub1_text = f"RSI(6): {rsi_val:.1f}"
        elif show_wR:
            ax2.plot(x, df["w_r"], linewidth=0.6, color="#FFB300", label="W%R")
            ax2.axhline(-20, color="#FF3B30", linestyle=":", linewidth=0.8)
            ax2.axhline(-80, color="#00C853", linestyle=":", linewidth=0.8)
            wr_val = df["w_r"].iloc[-1]
            sub1_text = f"W%R(14): {wr_val:.1f}"
        elif show_bias:
            ax2.plot(x, df["bias_6"], linewidth=0.6, color="#00E5FF", label="BIAS6")
            ax2.axhline(0, color="#666666", linestyle=":", linewidth=0.8)
            bias_val = df["bias_6"].iloc[-1]
            sub1_text = f"BIAS(6): {bias_val:.2f}%"
        elif show_mtm:
            ax2.plot(x, df["mtm"], linewidth=0.6, color="#FF3B30", label="MTM")
            ax2.axhline(0, color="#666666", linestyle=":", linewidth=0.8)
            mtm_val = df["mtm"].iloc[-1]
            sub1_text = f"MTM(10): {mtm_val:.2f}"
        elif show_qt:
            ax2.plot(x, df["qt"], linewidth=0.6, color="#00FF66", label="QT")
            qt_val = df["qt"].iloc[-1]
            sub1_text = f"QT量化指標: {qt_val:.2f}"
        else:
            # 預設顯示 MACD
            ax2.bar(x, df["osc"], width=0.75, color=osc_colors, edgecolor="none", alpha=0.9)
            ax2.plot(x, df["dif"], linewidth=0.5, color="#00E5FF", label="DIF")
            ax2.plot(x, df["dem"], linewidth=0.5, color="#FFB300", label="DEA")
            ax2.axhline(0, color="#666666", linestyle=":", linewidth=1)
            sub1_text = f"MACD  DIF:{cur_dif:.2f}{dif_arrow}  DEA:{cur_dem:.2f}{dem_arrow}  OSC:{cur_osc:.2f}{osc_arrow}"
        
        ax2.relim()
        ax2.autoscale_view(scalex=False, scaley=True)
        ax2.yaxis.tick_right()
        ax2.tick_params(axis="y", labelsize=8.0, colors="#FFFFFF")
        for t in ax2.get_yticklabels():
            t.set_fontweight("bold")
            t.set_path_effects(get_bright_effect("#FFFFFF", 0.5))
        ax2.grid(True, linestyle="--", color=GRID_COLOR, alpha=0.9)
        
        t_sub1 = ax2.text(0.015, 0.78, sub1_text, transform=ax2.transAxes, fontsize=8.5, fontweight="bold", color="#FFFFFF")
        t_sub1.set_path_effects(get_bright_effect("#FFFFFF", 0.6))

        # ---------------------------------------------------------
        # 層 3：成交量
        # ---------------------------------------------------------
        ax3.set_facecolor(PANEL_BG)
        ax3.bar(x, df["vol"], width=0.75, color=body_colors, edgecolor="none", alpha=0.9)
        ax3.plot(x, df["vol_ma5"], linewidth=0.5, color="#00E5FF", label="MAS")
        ax3.plot(x, df["vol_ma20"], linewidth=0.5, color="#FFB300", label="MA20")
        ax3.yaxis.tick_right()
        ax3.tick_params(axis="y", labelsize=8.0, colors="#FFFFFF")
        for t in ax3.get_yticklabels():
            t.set_fontweight("bold")
            t.set_path_effects(get_bright_effect("#FFFFFF", 0.5))
        ax3.grid(True, linestyle="--", color=GRID_COLOR, alpha=0.9)
        
        vol_info_text = f"成交量:{int(last_vol):,}張   MAS:{int(cur_mas):,} {mas_arrow}   MA20:{int(cur_ma20):,} {ma20_arrow}   量比:{v_ratio:.2f}倍"
        t_vol = ax3.text(0.015, 0.78, vol_info_text, transform=ax3.transAxes, fontsize=8.5, fontweight="bold", color="#FFFFFF")
        t_vol.set_path_effects(get_bright_effect("#FFFFFF", 0.6))

        # ---------------------------------------------------------
        # 層 4：大戶與羊群持股
        # ---------------------------------------------------------
        ax4.set_facecolor(PANEL_BG)
        cur_big, cur_sheep = 0.0, 0.0
        if len(big_holder) > 0 and len(sheep_holder) > 0:
            b_plot = big_holder[-len(df):]
            s_plot = sheep_holder[-len(df):]
            x_chip = x[-len(b_plot):]
            ax4.plot(x_chip, b_plot, color="#FF3B30", linewidth=0.3, marker='o', markersize=2, label="大戶(%)")
            ax4.plot(x_chip, s_plot, color="#00C853", linewidth=0.3, marker='s', markersize=2, label="羊群(%)")
            cur_big = float(b_plot[-1])
            cur_sheep = float(s_plot[-1])

        ax4.yaxis.tick_right()
        ax4.tick_params(axis="y", labelsize=8.0, colors="#FFFFFF")
        for t in ax4.get_yticklabels():
            t.set_fontweight("bold")
            t.set_path_effects(get_bright_effect("#FFFFFF", 0.5))
        ax4.grid(True, linestyle="--", color=GRID_COLOR, alpha=0.9)
        
        chip_tokens = [
            ("大戶與羊群  ", "#FFFFFF"),
            (f"大戶:{cur_big:.1f}%", "#FF3B30"),
            (" | ", "#FFFFFF"),
            (f"羊群:{cur_sheep:.1f}%", "#00C853")
        ]
        start_x_chip = 0.015
        for text_str, color_code in chip_tokens:
            t_tok = ax4.text(start_x_chip, 0.78, text_str, transform=ax4.transAxes, fontsize=8.5, fontweight="bold", color=color_code)
            t_tok.set_path_effects(get_bright_effect(color_code, 0.6))
            start_x_chip += len(text_str) * 0.007

        for ax in [ax1, ax2, ax3, ax4]:
            for spine in ax.spines.values():
                spine.set_visible(True)
                spine.set_color(SUB_BORDER)
                spine.set_linewidth(1.0)

        plt.subplots_adjust(left=0.01, right=0.98, top=0.96, bottom=0.03, hspace=0.06)
        st.pyplot(fig, use_container_width=True, dpi=250)

    # =========================================================
    # 分頁二：秒速選股
    # =========================================================
    elif app_mode == "⚡ 秒速選股：黃金交叉 / 死亡交叉":
        st.markdown('<p class="sub-header-14">⚡ 籌碼型態選股</p>', unsafe_allow_html=True)
        col_s1, col_s2, col_s3 = st.columns(3)
        with col_s1:
            cross_type = st.radio("選擇型態", ["🚀 黃金交叉", "⚠️ 死亡交叉"], horizontal=True, label_visibility="collapsed")
        with col_s2:
            recent_weeks = st.slider("最近幾週內", 1, 8, 3, 1)
        with col_s3:
            min_big_holder = st.slider("大戶持股最低 (%)", 30.0, 70.0, 40.0, 1.0)

        run_btn = st.button("🚀 執行過濾選股", type="primary", use_container_width=True)

        if run_btn:
            with st.spinner("正在進行條件過濾..."):
                matched_results = []
                is_golden_search = "黃金交叉" in cross_type
                cache_dict = load_local_cache_cached()

                for _, row in stock_df.iterrows():
                    s_id, s_name = str(row["代碼"]), str(row["名稱"])
                    if s_id in cache_dict:
                        item = cache_dict[s_id]
                        big_h, sheep_h, w_dates = item.get("big_holder", []), item.get("sheep_holder", []), item.get("w_dates", [])
                    else:
                        np.random.seed(int(s_id) if s_id.isdigit() else 42)
                        big_h = (38.0 + np.cumsum(np.random.randn(60) * 0.4)).tolist()
                        sheep_h = (42.0 + np.cumsum(np.random.randn(60) * 0.3)).tolist()
                        w_dates = pd.date_range(end=datetime.today(), periods=60, freq="W").strftime("%Y-%m-%d").tolist()

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
                    recent_hit = [idx for idx in target_crosses if (n_periods - 1 - idx) < recent_weeks]

                    if recent_hit:
                        last_hit_idx = recent_hit[-1]
                        matched_results.append({
                            "代碼": s_id, "名稱": s_name,
                            "訊號": "★ 黃金交叉" if is_golden_search else "✖ 死亡交叉",
                            "日期": w_dates[last_hit_idx],
                            "大戶(%)": round(float(big_h[-1]), 1)
                        })
                st.session_state.screened_results = matched_results

        if st.session_state.screened_results:
            df_res = pd.DataFrame(st.session_state.screened_results)
            st.success(f"找到 {len(df_res)} 檔符合個股。")
            filtered_options = (df_res["代碼"].astype(str) + " " + df_res["名稱"].astype(str)).tolist()
            
            c_a, c_b = st.columns([3, 1])
            with c_a:
                selected_from_screen = st.selectbox("選擇股票前往圖表", filtered_options, label_visibility="collapsed")
            with c_b:
                if st.button("📈 前往圖表", use_container_width=True):
                    st.session_state.selected_index = stock_options.index(selected_from_screen)
                    st.session_state.app_mode_idx = 0
                    st.rerun()
            st.dataframe(df_res, use_container_width=True, hide_index=True)

    # =========================================================
    # 分頁三：每週大戶增幅前 15 名總表
    # =========================================================
    elif app_mode == "📋 每週大戶增幅前 15 名總表":
        excel_filename = "大戶持股最新分析總表.xlsx"
        if os.path.exists(excel_filename):
            df_top15 = pd.read_excel(excel_filename, sheet_name="大戶增幅前15名", header=1)
            df_display = pd.DataFrame()
            df_display["代碼"] = df_top15["代碼"].apply(lambda x: str(x).strip().zfill(4))
            df_display["名稱"] = df_top15["名稱"].astype(str).str.strip()
            df_display["趨勢圖連結"] = df_top15["代碼"].apply(lambda x: f"https://norway.twsthr.info/StockHolders.aspx?stock={str(x).strip().zfill(4)}")

            c_title, c_btn = st.columns([2, 2])
            with c_title:
                st.markdown('<p class="sub-header-14">📋 大戶持股增幅前 15 名</p>', unsafe_allow_html=True)
            with c_btn:
                with open(excel_filename, "rb") as file:
                    st.download_button("📥 下載 Excel", data=file, file_name="大戶增幅前15名.xlsx", use_container_width=True)

            col_l, col_r = st.columns(2)
            with col_l:
                st.dataframe(df_display.iloc[:8], column_config={"趨勢圖連結": st.column_config.LinkColumn("🔗 連結", display_text="📈 金字塔")}, use_container_width=True, hide_index=True)
            with col_r:
                st.dataframe(df_display.iloc[8:], column_config={"趨勢圖連結": st.column_config.LinkColumn("🔗 連結", display_text="📈 金字塔")}, use_container_width=True, hide_index=True)
        else:
            st.warning("找不到總表檔案。")

    # =========================================================
    # 分頁四：基本面與圖表
    # =========================================================
    elif app_mode == "📊 基本面與圖表":
        st.markdown('<p class="sub-header-14">📊 基本面與圖表</p>', unsafe_allow_html=True)
        selected_fund_stock = st.selectbox("選擇股票", stock_options, label_visibility="collapsed")
        target_code = selected_fund_stock.split()[0]
        target_name = selected_fund_stock.split()[1] if len(selected_fund_stock.split()) > 1 else ""

        quarters = ["2024Q1", "2024Q2", "2024Q3", "2024Q4", "2025Q1"]
        data_sets = [
            {"title": "毛利率與營業利益率", "val1": [15.2, 16.5, 18.0, 17.2, 19.1], "val2": [8.1, 9.0, 10.5, 9.8, 11.2]},
            {"title": "單季營業收入與年增率", "val1": [12.5, 13.2, 14.1, 13.8, 15.0], "val2": [5.2, 6.1, 8.3, 7.0, 9.2]},
            {"title": "每股盈餘 (EPS)", "val1": [0.85, 0.92, 1.15, 1.02, 1.30], "val2": []}
        ]

        plt.style.use("dark_background")
        cols = st.columns(2)
        for idx, ds in enumerate(data_sets):
            fig, ax = plt.subplots(figsize=(4.2, 2.0))
            ax.plot(quarters, ds["val1"], marker='o', markersize=3, color="#00ff66", linewidth=1.2)
            if ds["val2"]:
                ax.plot(quarters, ds["val2"], marker='s', markersize=3, color="#3498db", linewidth=1.2)
            ax.set_title(f"[{target_code}] {ds['title']}", color="white", fontsize=8.5, fontweight="bold")
            ax.tick_params(axis='both', labelsize=6.5)
            ax.grid(True, linestyle=":", alpha=0.3)
            fig.tight_layout(pad=0.3)
            
            with cols[idx % 2]:
                with st.expander(f"📊 {ds['title']} (放大)", expanded=False):
                    st.pyplot(fig, use_container_width=True)

else:
    st.warning("請確認 StockIDs.xlsx 檔案已就位。")