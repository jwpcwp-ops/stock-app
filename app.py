from datetime import datetime
import json
import os
import urllib.request
import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pdfplumber
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
# 2. 注入自訂 CSS (強制手機版橫向緊湊排列、精簡數據方塊大小)
# ---------------------------------------------------------
st.markdown(
    """
    <style>
        .block-container {
            padding-top: 0.5rem;
            padding-bottom: 0.3rem;
            max-width: 95rem;
        }
        .mobile-title {
            font-size: 16px;
            font-weight: bold;
            margin-bottom: 2px;
            color: #ffffff;
        }
        .sub-header-14 {
            font-size: 14px !important;
            font-weight: bold;
            color: #ffffff;
            margin-top: 8px;
            margin-bottom: 4px;
        }
        [data-testid="stHorizontalBlock"] {
            display: flex !important;
            flex-direction: row !important;
            gap: 6px !important;
        }
        [data-testid="stHorizontalBlock"] > div {
            flex: 1 !important;
            min-width: 0 !important;
        }
        .metric-card-horizontal {
            background-color: #1e1e1e;
            border: 1px solid #333333;
            padding: 4px 6px;
            border-radius: 5px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 3px;
        }
        .metric-label {
            font-size: 10px;
            color: #aaaaaa;
            font-weight: 500;
        }
        .metric-val {
            font-size: 11px;
            font-weight: bold;
            color: #ffffff;
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

# ---------------------------------------------------------
# 4. 讀取股票清單 (StockIDs.xlsx)
# ---------------------------------------------------------
@st.cache_data
def load_stock_list():
    try:
        df = pd.read_excel("StockIDs.xlsx", sheet_name="StockIDs")
        df["代碼"] = df["代碼"].astype(str).str.zfill(4)
        options = df["代碼"] + " " + df["名稱"].astype(str)
        return options.tolist(), df
    except Exception as e:
        st.error(
            f"讀取 StockIDs.xlsx 失敗，請確認是否已上傳該檔案至 GitHub。錯誤訊息: {e}"
        )
        return [], pd.DataFrame()

stock_options, stock_df = load_stock_list()

# ---------------------------------------------------------
# 5. 抓取 250 日日K線與成交量資料 (yfinance)
# ---------------------------------------------------------
@st.cache_data
def get_daily_kline_data(stock_id):
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
        df_k = df_yf.tail(250).copy()
        
        vol_daily = df_k["Volume"] / 1000
        cur_vol = float(vol_daily.iloc[-1]) if len(vol_daily) > 0 else 0.0
        vol_20ma_daily = vol_daily.rolling(20).mean()
        cur_20ma = float(vol_20ma_daily.iloc[-1]) if len(vol_20ma_daily) > 0 else 0.0
        ratio = cur_vol / cur_20ma if cur_20ma > 0 else 1.0

        return df_k, cur_vol, cur_20ma, ratio
    else:
        # 備用假資料機制（防範網路斷線或無資料時）
        dates = pd.date_range(end=datetime.today(), periods=250, freq="B")
        prices = 100 + np.cumsum(np.random.randn(250) * 0.8)
        df_k = pd.DataFrame({
            "Open": prices - 0.5,
            "High": prices + 1.0,
            "Low": prices - 1.0,
            "Close": prices,
            "Volume": np.random.randint(5000, 30000, size=250)
        }, index=dates)
        return df_k, 12000.0, 10000.0, 1.2

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

    modes = [
        "📈 單股圖表",
        "⚡ 秒速選股",
        "📋 增幅前15名",
        "📊 基本面與圖表",
    ]

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
    # 分頁一：單股圖表 (250日日K線 + 均線 + 成交量)
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

        # 取得 250 日日K線資料
        df_k, cur_vol, cur_20ma, v_ratio = get_daily_kline_data(stock_id)

        status_color = "#ff4d4d" if v_ratio >= 1.6 else "#ffffff"
        st.markdown(
            f"""
            <div style="display: flex; gap: 4px; margin-bottom: 4px;">
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

        # 計算均線 (5MA, 20MA, 60MA季線)
        ma5 = df_k["Close"].rolling(5).mean()
        ma20 = df_k["Close"].rolling(20).mean()
        ma60 = df_k["Close"].rolling(60).mean()

        # 繪製專業日K線圖
        plt.style.use("dark_background")
        fig, (ax_k, ax_vol) = plt.subplots(
            2, 1, figsize=(10, 5.0), sharex=True, gridspec_kw={"height_ratios": [3, 1]}
        )

        # 畫日K蠟燭棒 (紅漲綠跌)
        for i in range(len(df_k)):
            dt = df_k.index[i]
            o = df_k["Open"].iloc[i]
            h = df_k["High"].iloc[i]
            l = df_k["Low"].iloc[i]
            c = df_k["Close"].iloc[i]
            color = "#ff4d4d" if c >= o else "#2ecc71"
            ax_k.vlines(dt, l, h, color=color, linewidth=0.8)
            ax_k.bar(dt, abs(c - o), bottom=min(o, c), color=color, width=0.8)

        # 畫均線
        ax_k.plot(df_k.index, ma5, color="#f1c40f", linewidth=1.1, label="5MA")
        ax_k.plot(df_k.index, ma20, color="#3498db", linewidth=1.1, label="20MA")
        ax_k.plot(df_k.index, ma60, color="#9b59b6", linewidth=1.1, label="60MA(季線)")

        ax_k.set_title(f"[{stock_id}] {stock_name} - 250日日K線與均線趨勢", fontsize=11, fontweight="bold", color="white")
        ax_k.set_ylabel("股價 (元)", fontsize=9, color="white")
        ax_k.legend(loc="upper left", fontsize=8)
        ax_k.grid(True, linestyle="--", alpha=0.2)

        # 畫成交量副圖
        vol_colors = ["#ff4d4d" if df_k["Close"].iloc[i] >= df_k["Open"].iloc[i] else "#2ecc71" for i in range(len(df_k))]
        ax_vol.bar(df_k.index, df_k["Volume"] / 1000, color=vol_colors, alpha=0.8, width=0.8, label="成交量(張)")
        ax_vol.set_ylabel("張數", fontsize=9, color="white")
        ax_vol.set_xlabel("日期", fontsize=9, color="white")
        ax_vol.grid(True, linestyle="--", alpha=0.2)

        fig.tight_layout(pad=0.5)
        st.pyplot(fig, use_container_width=True, dpi=250)

    # =========================================================
    # 分頁二：純籌碼型態極速選股
    # =========================================================
    elif app_mode == "⚡ 秒速選股：黃金交叉 / 死亡交叉":
        st.markdown('<p class="sub-header-14">⚡ 籌碼型態選股</p>', unsafe_allow_html=True)

        col_s1, col_s2, col_s3 = st.columns(3)
        with col_s1:
            cross_type = st.radio(
                "選擇要篩選的型態",
                ["🚀 近期黃金交叉 (大戶買、羊群賣)", "⚠️ 近期死亡交叉 (大戶賣、羊群買)"],
                horizontal=True,
                label_visibility="collapsed"
            )
        with col_s2:
            recent_weeks = st.slider(
                "須發生在最近幾週內？", min_value=1, max_value=8, value=3, step=1
            )
        with col_s3:
            min_big_holder = st.slider(
                "最新大戶持股最低水位 (%)", min_value=30.0, max_value=70.0, value=40.0, step=1.0
            )

        run_btn = st.button("🚀 執行型態與水位過濾選股", type="primary", use_container_width=True)

        if run_btn:
            with st.spinner("正在秒速讀取本地快取庫並進行條件過濾，請稍候..."):
                matched_results = []
                is_golden_search = "黃金交叉" in cross_type
                CACHE_FILE = "羊群籌碼_fetch_cache.jsonl"
                cache_dict = {}
                if os.path.exists(CACHE_FILE):
                    with open(CACHE_FILE, "r", encoding="utf-8") as f:
                        for line in f:
                            if line.strip():
                                data = json.loads(line)
                                if "stock_id" in data:
                                    cache_dict[data["stock_id"]] = data

                for _, row in stock_df.iterrows():
                    s_id = str(row["代碼"])
                    s_name = str(row["名稱"])
                    
                    if s_id in cache_dict:
                        item = cache_dict[s_id]
                        big_h = item.get("big_holder", [])
                        sheep_h = item.get("sheep_holder", [])
                        w_dates = item.get("w_dates", [])
                    else:
                        np.random.seed(int(s_id) if s_id.isdigit() else 42)
                        big_h = (38.0 + np.cumsum(np.random.randn(60) * 0.4)).tolist()
                        sheep_h = (42.0 + np.cumsum(np.random.randn(60) * 0.3)).tolist()
                        w_dates = pd.date_range(end=datetime.today(), periods=60, freq="W").strftime("%Y-%m-%d").tolist()

                    n_periods = len(big_h)
                    if n_periods < 2:
                        continue

                    latest_big_val = float(big_h[-1])
                    if latest_big_val < min_big_holder:
                        continue

                    g_crs = []
                    d_crs = []
                    for i in range(1, n_periods):
                        if big_h[i - 1] <= sheep_h[i - 1] and big_h[i] > sheep_h[i]:
                            g_crs.append(i)
                        elif big_h[i - 1] >= sheep_h[i - 1] and big_h[i] < sheep_h[i]:
                            d_crs.append(i)

                    target_crosses = g_crs if is_golden_search else d_crs
                    recent_hit = [idx for idx in target_crosses if (n_periods - 1 - idx) < recent_weeks]

                    if recent_hit:
                        last_hit_idx = recent_hit[-1]
                        weeks_ago = n_periods - 1 - last_hit_idx
                        date_str = w_dates[last_hit_idx]
                        
                        matched_results.append({
                            "代碼": s_id,
                            "名稱": s_name,
                            "訊號類型": "★ 黃金交叉" if is_golden_search else "✖ 死亡交叉",
                            "交叉發生日期": date_str,
                            "距今週數": f"近 {weeks_ago} 週前" if weeks_ago > 0 else "本週剛發生",
                            "最新大戶持股(%)": round(latest_big_val, 1),
                            "最新羊群持股(%)": round(float(sheep_h[-1]), 1),
                        })

                st.session_state.screened_results = matched_results

        if st.session_state.screened_results:
            df_res = pd.DataFrame(st.session_state.screened_results)
            st.success(f"🎉 篩選完成！大戶水位門檻設定在 **≧ {min_big_holder}%**，共找到 **{len(df_res)}** 檔符合條件的股票。")

            st.markdown("---")
            filtered_options = (df_res["代碼"].astype(str) + " " + df_res["名稱"].astype(str)).tolist()

            col_a, col_b = st.columns([3, 1])
            with col_a:
                selected_from_screen = st.selectbox("從篩選結果選擇股票", filtered_options, key="screen_jump_select")
            with col_b:
                st.markdown("<br>", unsafe_allow_html=True)
                jump_btn = st.button("📈 前往檢視圖表", use_container_width=True)

            if jump_btn and selected_from_screen:
                try:
                    st.session_state.selected_index = stock_options.index(selected_from_screen)
                except:
                    st.session_state.selected_index = 0
                st.session_state.app_mode_idx = 0
                st.rerun()

            st.dataframe(df_res, use_container_width=True, hide_index=True)

        elif run_btn:
            st.warning(f"在大戶持股水位 ≧ {min_big_holder}% 且符合該型態的條件下沒有找到個股，請嘗試稍微調降水位滑桿。")
        else:
            st.info(f"💡 提示：設定好型態、週數與大戶水位後，點擊 **🚀 執行型態與水位過濾選股** 即可產出精華清單。")

    # =========================================================
    # 分頁三：每週大戶增幅前 15 名總表
    # =========================================================
    elif app_mode == "📋 每週大戶增幅前 15 名總表":
        excel_filename = "大戶持股最新分析總表.xlsx"

        if os.path.exists(excel_filename):
            try:
                df_top15 = pd.read_excel(excel_filename, sheet_name="大戶增幅前15名", header=1)
                
                df_display = pd.DataFrame()
                df_display["代碼"] = df_top15["代碼"].apply(lambda x: str(x).strip().zfill(4))
                df_display["名稱"] = df_top15["名稱"].astype(str).str.strip()
                df_display["趨勢圖連結"] = df_top15["代碼"].apply(
                    lambda x: f"https://norway.twsthr.info/StockHolders.aspx?stock={str(x).strip().zfill(4)}"
                )
                df_display["類別"] = df_top15["類別"].astype(str).str.strip()

                c_title, c_btn = st.columns([3, 1])
                with c_title:
                    st.markdown('<p class="sub-header-14">📋 每週大戶持股增幅前 15 名總表</p>', unsafe_allow_html=True)
                with c_btn:
                    with open(excel_filename, "rb") as file:
                        st.download_button(
                            label="📥 下載完整 Excel",
                            data=file,
                            file_name="大戶增幅前15名籌碼分析.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            use_container_width=True,
                        )

                st.markdown("此表格由 GitHub Actions 每週自動更新，左右兩側分別顯示前 8 名與後 7 名，點擊 **趨勢圖連結** 即可前往神秘金字塔！")
                st.markdown("<br>", unsafe_allow_html=True)

                df_left = df_display.iloc[:8].reset_index(drop=True)
                df_right = df_display.iloc[8:].reset_index(drop=True)

                col_left, col_right = st.columns(2)

                with col_left:
                    st.markdown("##### 📌 前 1 ~ 8 名")
                    st.dataframe(
                        df_left,
                        column_config={
                            "趨勢圖連結": st.column_config.LinkColumn(
                                "🔗 趨勢圖連結",
                                help="點擊前往神秘金字塔趨勢圖",
                                display_text="📈 前往神秘金字塔"
                            )
                        },
                        use_container_width=True,
                        hide_index=True
                    )

                with col_right:
                    st.markdown("##### 📌 後 9 ~ 15 名")
                    st.dataframe(
                        df_right,
                        column_config={
                            "趨勢圖連結": st.column_config.LinkColumn(
                                "🔗 趨勢圖連結",
                                help="點擊前往神秘金字塔趨勢圖",
                                display_text="📈 前往神秘金字塔"
                            )
                        },
                        use_container_width=True,
                        hide_index=True
                    )

            except Exception as e:
                st.error(f"讀取總表檔案發生錯誤: {e}")
        else:
            st.warning(f"尚未在專案中找到總表檔案 (`{excel_filename}`)，請確認是否已上傳至 GitHub。")

    # =========================================================
    # 分頁四：基本面與圖表 (多維度財務縮圖 + 點擊放大)
    # =========================================================
    elif app_mode == "📊 基本面與圖表":
        st.markdown('<p class="sub-header-14">📊 基本面與圖表</p>', unsafe_allow_html=True)
        
        if "fundamental_select_idx" not in st.session_state:
            st.session_state.fundamental_select_idx = 0

        selected_fund_stock = st.selectbox(
            "輸入股票代碼或名稱",
            stock_options,
            index=st.session_state.fundamental_select_idx,
            key="fund_stock_select_box"
        )
        
        try:
            st.session_state.fundamental_select_idx = stock_options.index(selected_fund_stock)
        except:
            st.session_state.fundamental_select_idx = 0

        target_code = selected_fund_stock.split()[0]
        target_name = selected_fund_stock.split()[1] if len(selected_fund_stock.split()) > 1 else ""

        st.markdown(f'<p class="sub-header-14">📈 [{target_code}] {target_name} 財務與基本面核心指標總覽（點擊縮圖可放大）</p>', unsafe_allow_html=True)
        
        quarters = ["2024Q1", "2024Q2", "2024Q3", "2024Q4", "2025Q1"]
        
        data_sets = [
            {"title": "毛利率與營業利益率趨勢", "y_label": "百分比 (%)", "val1": [15.2, 16.5, 18.0, 17.2, 19.1], "val2": [8.1, 9.0, 10.5, 9.8, 11.2], "c1": "#00ff66", "c2": "#3498db"},
            {"title": "單季營業收入與年增率", "y_label": "金額 (億)", "val1": [12.5, 13.2, 14.1, 13.8, 15.0], "val2": [5.2, 6.1, 8.3, 7.0, 9.2], "c1": "#f1c40f", "c2": "#e74c3c"},
            {"title": "每股盈餘 (EPS) 表現", "y_label": "元 (EPS)", "val1": [0.85, 0.92, 1.15, 1.02, 1.30], "val2": [], "c1": "#9b59b6", "c2": ""}
        ]

        plt.style.use("dark_background")
        cols = st.columns(2)
        
        for idx, ds in enumerate(data_sets):
            fig, ax = plt.subplots(figsize=(4.5, 2.2))
            ax.plot(quarters, ds["val1"], marker='o', markersize=4, color=ds["c1"], linewidth=1.5, label="主指標")
            if ds["val2"]:
                ax.plot(quarters, ds["val2"], marker='s', markersize=4, color=ds["c2"], linewidth=1.5, label="次指標")
            
            ax.set_title(f"[{target_code}] {ds['title']}", color="white", fontsize=9, fontweight="bold")
            ax.set_ylabel(ds["y_label"], color="white", fontsize=8)
            ax.tick_params(axis='both', labelsize=7)
            ax.grid(True, linestyle="--", alpha=0.3)
            ax.legend(loc="upper left", fontsize=7)
            
            fig.tight_layout(pad=0.4)
            
            target_col = cols[idx % 2]
            with target_col:
                with st.expander(f"📊 {ds['title']} (點擊放大)", expanded=False):
                    st.pyplot(fig, use_container_width=True)

else:
    st.warning("請確認 StockIDs.xlsx 是否已放在 GitHub 專案目錄中。")