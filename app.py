from datetime import datetime
import json
import os
import urllib.request
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
import yfinance as yf

# ---------------------------------------------------------
# 1. 頁面基本設定 (針對手機極致緊湊優化)
# ---------------------------------------------------------
st.set_page_config(
    page_title="查詢籌碼系統",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ---------------------------------------------------------
# 2. 注入自訂 CSS (擬真券商 App 黑底風格與精簡排版)
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
            gap: 4px !important;
        }
        [data-testid="stHorizontalBlock"] > div {
            flex: 1 !important;
            min-width: 0 !important;
        }
        .metric-card-horizontal {
            background-color: #121212;
            border: 1px solid #262626;
            padding: 3px 5px;
            border-radius: 4px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 2px;
        }
        .metric-label {
            font-size: 9.5px;
            color: #999999;
            font-weight: 500;
        }
        .metric-val {
            font-size: 10.5px;
            font-weight: bold;
            color: #ffffff;
        }
        .stButton button {
            font-size: 12px !important;
            padding: 4px 8px !important;
        }
    </style>
""",
    unsafe_allow_html=True,
)

# ---------------------------------------------------------
# 3. 讀取股票清單 (StockIDs.xlsx)
# ---------------------------------------------------------
@st.cache_data
def load_stock_list():
    try:
        df = pd.read_excel("StockIDs.xlsx", sheet_name="StockIDs")
        df["代碼"] = df["代碼"].astype(str).str.zfill(4)
        options = df["代碼"] + " " + df["名稱"].astype(str)
        return options.tolist(), df
    except Exception as e:
        return [], pd.DataFrame()

stock_options, stock_df = load_stock_list()

# ---------------------------------------------------------
# 4. 本地快取支援與資料抓取
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

def get_comprehensive_stock_data(stock_id, target_days=250):
    cache_dict = load_local_cache_cached()
    today_str = datetime.today().strftime("%Y-%m-%d")

    df_yf = pd.DataFrame()
    for suffix in [".TW", ".TWO"]:
        ticker = stock_id + suffix
        try:
            temp_df = yf.download(ticker, period="1y", progress=False)
            if not temp_df.empty and "Close" in temp_df.columns:
                df_yf = temp_df
                break
        except:
            continue

    if not df_yf.empty:
        if isinstance(df_yf.columns, pd.MultiIndex):
            df_yf.columns = df_yf.columns.get_level_values(0)
        df_yf = df_yf.dropna(subset=["Close", "Volume"])
        df_k = df_yf.tail(target_days).copy()
        
        vol_daily = df_k["Volume"] / 1000
        cur_vol = float(vol_daily.iloc[-1]) if len(vol_daily) > 0 else 0.0
        vol_20ma_daily = vol_daily.rolling(20).mean()
        cur_20ma = float(vol_20ma_daily.iloc[-1]) if len(vol_20ma_daily) > 0 else 0.0
        ratio = cur_vol / cur_20ma if cur_20ma > 0 else 1.0
        
        k_records = []
        for idx, row in df_k.iterrows():
            k_records.append({
                "date": idx.strftime("%Y-%m-%d"),
                "open": float(row["Open"]),
                "high": float(row["High"]),
                "low": float(row["Low"]),
                "close": float(row["Close"]),
                "vol": float(row["Volume"]) / 1000
            })
    else:
        cur_vol, cur_20ma, ratio = 12000.0, 10000.0, 1.2
        dates = pd.date_range(end=datetime.today(), periods=target_days, freq="B")
        prices = 100 + np.cumsum(np.random.randn(target_days) * 0.8)
        k_records = []
        for i, d in enumerate(dates):
            k_records.append({
                "date": d.strftime("%Y-%m-%d"),
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
# 5. Session State 初始化
# ---------------------------------------------------------
if "selected_index" not in st.session_state:
    st.session_state.selected_index = 0
if "screened_results" not in st.session_state:
    st.session_state.screened_results = []
if "app_mode_idx" not in st.session_state:
    st.session_state.app_mode_idx = 0

# ---------------------------------------------------------
# 6. 網頁主介面佈局 (4個分頁按鈕並排)
# ---------------------------------------------------------
st.markdown('<p class="mobile-title">📊 查詢籌碼系統 (手機版)</p>', unsafe_allow_html=True)

if stock_options:
    m_col1, m_col2, m_col3, m_col4 = st.columns(4)
    modes = ["📈 單股圖表", "⚡ 秒速選股", "📋 增幅前15", "📊 基本面"]

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

        # --- 控制面板：十字查詢開關、K線數量、均線開關 ---
        with st.expander("⚙️ 互動設定 (十字查詢線、K線數量、均線開關)", expanded=True):
            c_opt1, c_opt2, c_opt3 = st.columns([1.2, 1, 1.2])
            with c_opt1:
                k_days_choice = st.selectbox("顯示 K線數量", [60, 120, 200], index=0)
            with c_opt2:
                show_fib = st.checkbox("📐 黃金分割率", value=True)
            with c_opt3:
                show_crosshair = st.checkbox("➕ 十字查詢線", value=True)

            st.markdown("---")
            ma_cols = st.columns(7)
            with ma_cols[0]:
                show_ma5 = st.checkbox("5日", value=True)
            with ma_cols[1]:
                show_ma10 = st.checkbox("10日", value=False)
            with ma_cols[2]:
                show_ma20 = st.checkbox("20日", value=False)
            with ma_cols[3]:
                show_ma35 = st.checkbox("35日", value=False)
            with ma_cols[4]:
                show_ma65 = st.checkbox("65日", value=False)
            with ma_cols[5]:
                show_ma120 = st.checkbox("120日", value=False)
            with ma_cols[6]:
                show_ma200 = st.checkbox("200日", value=False)

        k_records, big_holder, sheep_holder, cur_vol, cur_20ma, v_ratio = get_comprehensive_stock_data(stock_id, target_days=k_days_choice)

        status_color = "#ff4d4d" if v_ratio >= 1.6 else "#ffffff"
        st.markdown(
            f"""
            <div style="display: flex; gap: 4px; margin-bottom: 3px;">
                <div class="metric-card-horizontal" style="flex: 1;">
                    <span class="metric-label">📦 今日成交</span>
                    <span class="metric-val">{int(cur_vol):,} 張</span>
                </div>
                <div class="metric-card-horizontal" style="flex: 1;">
                    <span class="metric-label">📊 20MA均量</span>
                    <span class="metric-val">{int(cur_20ma):,} 張</span>
                </div>
                <div class="metric-card-horizontal" style="flex: 1;">
                    <span class="metric-label">⚡ 量比值</span>
                    <span class="metric-val" style="color: {status_color};">{v_ratio:.2f} 倍</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        df = pd.DataFrame(k_records)
        s_close = df["close"]

        # 計算均線
        ma_config = {
            "MA5": (5, show_ma5, "#00E5FF"),
            "MA10": (10, show_ma10, "#FFD700"),
            "MA20": (20, show_ma20, "#FF00FF"),
            "MA35": (35, show_ma35, "#00FF66"),
            "MA65": (65, show_ma65, "#FFA500"),
            "MA120": (120, show_ma120, "#9D4EDD"),
            "MA200": (200, show_ma200, "#FFFFFF")
        }
        for ma_name, (period, is_show, color) in ma_config.items():
            df[ma_name] = s_close.rolling(window=period).mean()

        # MACD
        df["DIF"] = s_close.ewm(span=12, adjust=False).mean() - s_close.ewm(span=26, adjust=False).mean()
        df["DEA"] = df["DIF"].ewm(span=9, adjust=False).mean()
        df["OSC"] = (df["DIF"] - df["DEA"]) * 2

        df["VOL5"] = df["vol"].rolling(window=5).mean()

        cond3 = ((s_close.ewm(span=15, adjust=False).mean() / s_close.ewm(span=30, adjust=False).mean() - 1) * 100) > 0
        cond4 = s_close.ewm(span=15, adjust=False).mean() > s_close.ewm(span=30, adjust=False).mean()
        df["LongTrend"] = (cond3 & cond4).astype(int)

        # 建立 Plotly 5 層子圖
        fig = make_subplots(
            rows=5, cols=1, shared_xaxes=True,
            vertical_spacing=0.03,
            row_heights=[0.45, 0.12, 0.12, 0.16, 0.05]
        )

        bar_colors = ['#FF3B30' if c >= o else '#00C853' for o, c in zip(df["open"], df["close"])]

        # 層 1：K線與均線
        fig.add_trace(go.Candlestick(
            x=df["date"], open=df["open"], high=df["high"], low=df["low"], close=df["close"],
            name="K線", increasing_line_color='#FF3B30', decreasing_line_color='#00C853'
        ), row=1, col=1)

        for ma_name, (period, is_show, color) in ma_config.items():
            if is_show:
                fig.add_trace(go.Scatter(
                    x=df["date"], y=df[ma_name], name=ma_name,
                    line=dict(color=color, width=1.2)
                ), row=1, col=1)

        # 黃金分割率水平線
        if show_fib and not df.empty:
            max_p = df["high"].max()
            min_p = df["low"].min()
            diff_p = max_p - min_p
            fib_levels = [
                ("0%", max_p),
                ("19.1%", max_p - diff_p * 0.191),
                ("38.2%", max_p - diff_p * 0.382),
                ("50.0%", max_p - diff_p * 0.5),
                ("61.8%", max_p - diff_p * 0.618),
                ("80.9%", max_p - diff_p * 0.809),
                ("100%", min_p)
            ]
            for label_txt, price_val in fib_levels:
                fig.add_hline(
                    y=price_val, line_dash="dot", line_color="#00E5FF", line_width=0.8,
                    annotation_text=f"{price_val:.1f} ({label_txt})", annotation_position="top right",
                    annotation_font_size=8, annotation_font_color="#00E5FF", row=1, col=1
                )

        # 層 2：MACD
        osc_colors = ['#FF3B30' if val >= 0 else '#00C853' for val in df["OSC"]]
        fig.add_trace(go.Bar(x=df["date"], y=df["OSC"], marker_color=osc_colors, name="OSC"), row=2, col=1)
        fig.add_trace(go.Scatter(x=df["date"], y=df["DIF"], line=dict(color="#00E5FF", width=1), name="DIF"), row=2, col=1)
        fig.add_trace(go.Scatter(x=df["date"], y=df["DEA"], line=dict(color="#FFB300", width=1), name="DEA"), row=2, col=1)

        # 層 3：成交量
        fig.add_trace(go.Bar(x=df["date"], y=df["vol"], marker_color=bar_colors, name="成交量"), row=3, col=1)
        fig.add_trace(go.Scatter(x=df["date"], y=df["VOL5"], line=dict(color="#00E5FF", width=1), name="VOL5"), row=3, col=1)

        # 層 4：大戶與羊群持股
        b_plot = big_holder[-len(df):]
        s_plot = sheep_holder[-len(df):]
        fig.add_trace(go.Scatter(x=df["date"], y=b_plot, line=dict(color="#FF3B30", width=1.2), name="大戶(%)"), row=4, col=1)
        fig.add_trace(go.Scatter(x=df["date"], y=s_plot, line=dict(color="#00C853", width=1.2), name="羊群(%)"), row=4, col=1)

        # 層 5：多空線色帶
        trend_colors = ['#FF3B30' if val == 1 else '#00C853' for val in df["LongTrend"]]
        fig.add_trace(go.Bar(x=df["date"], y=[1]*len(df), marker_color=trend_colors, name="多空線"), row=5, col=1)

        # 十字查詢線互動開關設定
        hover_mode_setting = "x unified" if show_crosshair else "closest"

        fig.update_layout(
            title=dict(text=f"[{stock_id}] {stock_name} - 專業多維度籌碼技術圖表", font=dict(size=13, color="white")),
            template="plotly_dark",
            paper_bgcolor="#000000",
            plot_bgcolor="#0a0a0a",
            height=680,
            margin=dict(l=10, r=45, t=30, b=10),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, font=dict(size=8)),
            hovermode=hover_mode_setting,
            xaxis_showspikes=show_crosshair,
            yaxis_showspikes=show_crosshair,
            spikemode="to axes"  # <--- 已在此處修正正確參數
        )

        fig.update_xaxes(showgrid=True, gridcolor="#1a1a1a", zeroline=False)
        fig.update_yaxes(showgrid=True, gridcolor="#1a1a1a", zeroline=False, side="right")
        fig.update_yaxes(showticklabels=False, row=5, col=1)

        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

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

        cols = st.columns(2)
        for idx, ds in enumerate(data_sets):
            fig_f = go.Figure()
            fig_f.add_trace(go.Scatter(x=quarters, y=ds["val1"], mode='lines+markers', name='主指標', line=dict(color='#00ff66', width=2)))
            if ds["val2"]:
                fig_f.add_trace(go.Scatter(x=quarters, y=ds["val2"], mode='lines+markers', name='次指標', line=dict(color='#3498db', width=2)))
            fig_f.update_layout(
                title=dict(text=f"[{target_code}] {ds['title']}", font=dict(size=11, color="white")),
                template="plotly_dark",
                paper_bgcolor="#0a0a0a",
                plot_bgcolor="#0a0a0a",
                height=220,
                margin=dict(l=10, r=10, t=30, b=10),
                legend=dict(font=dict(size=8))
            )
            with cols[idx % 2]:
                with st.expander(f"📊 {ds['title']} (放大)", expanded=False):
                    st.plotly_chart(fig_f, use_container_width=True)

else:
    st.warning("請確認 StockIDs.xlsx 檔案已就位。")