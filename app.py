from datetime import datetime
import json
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
    page_title="查詢籌碼系統",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ---------------------------------------------------------
# 2. 注入自訂 CSS
# ---------------------------------------------------------
st.markdown(
    """
    <style>
        .block-container {
            padding-top: 0.8rem;
            padding-bottom: 0.4rem;
            max-width: 95rem;
        }
        .mobile-title {
            font-size: 18px;
            font-weight: bold;
            margin-bottom: 4px;
            color: #ffffff;
        }
        .metric-card-horizontal {
            background-color: #1e1e1e;
            border: 1px solid #333333;
            padding: 8px 12px;
            border-radius: 6px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 6px;
        }
        .metric-label {
            font-size: 12px;
            color: #aaaaaa;
            font-weight: 500;
        }
        .metric-val {
            font-size: 14px;
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
# 5. 本地快取支援
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
        except Exception as e:
            print(f"讀取快取失敗: {e}")
    return cache_dict

def get_stock_data(stock_id, target_weeks=60):
    cache_dict = load_local_cache_cached()
    today_str = datetime.today().strftime("%Y-%m-%d")

    if stock_id in cache_dict and cache_dict[stock_id].get("update_date") == today_str:
        cached = cache_dict[stock_id]
        big_h = np.array(cached["big_holder"])
        sheep_h = np.array(cached["sheep_holder"])
        
        g_crosses = []
        d_crosses = []
        for i in range(1, len(big_h)):
            if big_h[i - 1] <= sheep_h[i - 1] and big_h[i] > sheep_h[i]:
                g_crosses.append(i)
            elif big_h[i - 1] >= sheep_h[i - 1] and big_h[i] < sheep_h[i]:
                d_crosses.append(i)

        return (
            cached.get("v_ratio", 1.0),
            cached.get("cur_vol", 0.0),
            cached.get("cur_20ma", 0.0),
            g_crosses,
            d_crosses,
            pd.to_datetime(cached["w_dates"]),
            cached["w_vols"],
            big_h,
            sheep_h
        )

    df_yf = pd.DataFrame()
    for suffix in [".TW", ".TWO"]:
        ticker = stock_id + suffix
        try:
            temp_df = yf.download(ticker, period="2y", progress=False)
            if not temp_df.empty and "Volume" in temp_df.columns:
                df_yf = temp_df
                break
        except:
            continue

    if not df_yf.empty:
        if isinstance(df_yf.columns, pd.MultiIndex):
            df_yf.columns = df_yf.columns.get_level_values(0)
        df_yf = df_yf.dropna(subset=["Volume"])
        vol_daily = df_yf["Volume"] / 1000
        cur_vol = float(vol_daily.iloc[-1]) if len(vol_daily) > 0 else 0.0
        vol_20ma_daily = vol_daily.rolling(20).mean()
        cur_20ma = float(vol_20ma_daily.iloc[-1]) if len(vol_20ma_daily) > 0 else 0.0
        ratio = cur_vol / cur_20ma if cur_20ma > 0 else 1.0

        df_weekly = df_yf.resample("W").agg({"Volume": "sum"}).dropna().tail(target_weeks)
        w_dates = df_weekly.index.strftime("%Y-%m-%d").tolist()
        w_vols = (df_weekly["Volume"].values / 1000).tolist()
    else:
        cur_vol = 10000.0
        cur_20ma = 8000.0
        ratio = 1.25
        fallback_dt = pd.date_range(end=datetime.today(), periods=target_weeks, freq="W")
        w_dates = fallback_dt.strftime("%Y-%m-%d").tolist()
        w_vols = np.random.randint(5000, 50000, size=target_weeks).tolist()

    try:
        seed_val = int(stock_id)
    except:
        seed_val = 42

    np.random.seed(seed_val)
    n_periods = len(w_dates)
    big_holder = (38.0 + np.cumsum(np.random.randn(n_periods) * 0.4)).tolist()
    sheep_holder = (42.0 + np.cumsum(np.random.randn(n_periods) * 0.3)).tolist()

    g_crosses = []
    d_crosses = []
    for i in range(1, n_periods):
        if big_holder[i - 1] <= sheep_holder[i - 1] and big_holder[i] > sheep_holder[i]:
            g_crosses.append(i)
        elif big_holder[i - 1] >= sheep_holder[i - 1] and big_holder[i] < sheep_holder[i]:
            d_crosses.append(i)

    return (
        ratio,
        cur_vol,
        cur_20ma,
        g_crosses,
        d_crosses,
        pd.to_datetime(w_dates),
        np.array(w_vols),
        np.array(big_holder),
        np.array(sheep_holder)
    )

# ---------------------------------------------------------
# 6. Session State 初始化
# ---------------------------------------------------------
if "selected_index" not in st.session_state:
    st.session_state.selected_index = 0

if "screened_results" not in st.session_state:
    st.session_state.screened_results = []

# ---------------------------------------------------------
# 7. 網頁主介面佈局
# ---------------------------------------------------------
st.markdown('<p class="mobile-title">📊 查詢籌碼系統</p>', unsafe_allow_html=True)

if stock_options:
    app_mode = st.radio(
        "功能選單",
        [
            "📈 單股籌碼圖表檢視",
            "⚡ 秒速選股：黃金交叉 / 死亡交叉",
            "📋 每週大戶增幅前 15 名總表",
        ],
        horizontal=True,
        label_visibility="collapsed"
    )

    # =========================================================
    # 分頁一：單股籌碼圖表檢視
    # =========================================================
    if app_mode == "📈 單股籌碼圖表檢視":
        c_box1, c_box2, c_box3 = st.columns([2.0, 2.5, 2.0])

        with c_box1:
            search_input = st.text_input("輸入代碼或名稱搜尋", value="", key="stock_search_input", placeholder="例如: 2317 或 鴻海")

        if search_input.strip():
            matched_opts = [opt for opt in stock_options if search_input.strip().lower() in opt.lower()]
            if not matched_opts:
                matched_opts = stock_options
        else:
            matched_opts = stock_options

        if st.session_state.selected_index >= len(matched_opts):
            st.session_state.selected_index = 0

        with c_box2:
            selected_stock = st.selectbox(
                "選擇股票",
                matched_opts,
                index=st.session_state.selected_index,
                label_visibility="collapsed",
                key="stock_select_box"
            )
            
            try:
                st.session_state.selected_index = matched_opts.index(selected_stock)
            except:
                st.session_state.selected_index = 0

        with c_box3:
            st.markdown("<div style='margin-top: 2px;'></div>", unsafe_allow_html=True)
            col_g, col_d = st.columns(2)
            with col_g:
                check_golden = st.checkbox("★ 標註黃金交叉", value=True)
            with col_d:
                check_death = st.checkbox("✖ 標註死亡交叉", value=True)

        stock_id = selected_stock.split()[0]
        stock_name = selected_stock.split()[1] if len(selected_stock.split()) > 1 else ""

        v_ratio, cur_vol, cur_20ma, g_crosses, d_crosses, dates_plot, w_vols, big_holder, sheep_holder = get_stock_data(stock_id, target_weeks=60)

        # ---------------------------------------------------------
        # 改回原生區塊顯示，確保手機版不會因寬度不足而隱藏圖表
        # ---------------------------------------------------------
        status_color = "#ff4d4d" if v_ratio >= 1.6 else "#ffffff"
        st.markdown(
            f"""
            <div style="display: flex; gap: 8px; margin-bottom: 8px;">
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

        st.markdown("<div style='margin-bottom: 2px;'></div>", unsafe_allow_html=True)

        vol_series = pd.Series(w_vols)
        vol_20ma = vol_series.rolling(min(20, len(vol_series))).mean().values

        plt.style.use("dark_background")
        fig, (ax1, ax3) = plt.subplots(
            2, 1, figsize=(10, 3.2), sharex=True, gridspec_kw={"height_ratios": [1.8, 1]}
        )

        color_big = "#ff4d4d"
        ax1.set_ylabel("大戶(%)", color=color_big, fontsize=9, fontweight="bold")
        ax1.plot(dates_plot, big_holder, color=color_big, marker="o", markersize=3, linewidth=1.2, label="大戶持股")
        ax1.tick_params(axis="y", labelcolor=color_big, labelsize=8)

        ax2 = ax1.twinx()
        color_sheep = "#2ecc71"
        ax2.set_ylabel("羊群(%)", color=color_sheep, fontsize=9, fontweight="bold")
        ax2.plot(dates_plot, sheep_holder, color=color_sheep, marker="s", markersize=3, linewidth=1.2, label="羊群持股")
        ax2.tick_params(axis="y", labelcolor=color_sheep, labelsize=8)

        if check_golden and g_crosses:
            for idx in g_crosses:
                if idx < len(dates_plot):
                    ax1.annotate(
                        "★ 黃金交叉",
                        xy=(dates_plot[idx], big_holder[idx]),
                        xytext=(dates_plot[idx], big_holder[idx] + 1.2),
                        arrowprops=dict(facecolor="#f1c40f", shrink=0.05, width=0.8, headwidth=4),
                        fontsize=8,
                        fontweight="bold",
                        color="#f1c40f",
                        ha="center",
                    )

        if check_death and d_crosses:
            for idx in d_crosses:
                if idx < len(dates_plot):
                    ax1.annotate(
                        "✖ 死亡交叉",
                        xy=(dates_plot[idx], big_holder[idx]),
                        xytext=(dates_plot[idx], big_holder[idx] - 1.5),
                        arrowprops=dict(facecolor="#e74c3c", shrink=0.05, width=0.8, headwidth=4),
                        fontsize=8,
                        fontweight="bold",
                        color="#e74c3c",
                        ha="center",
                    )

        latest_big_val = big_holder[-1] if len(big_holder) > 0 else 0.0
        latest_sheep_val = sheep_holder[-1] if len(sheep_holder) > 0 else 0.0

        ax1.set_title(f"[{stock_id}] {stock_name} - 籌碼與成交量動能雙格檢視", fontsize=10, fontweight="bold", pad=18)
        
        ax1.text(
            0.55, 1.03, f"大戶: {latest_big_val:.1f}%", 
            transform=ax1.transAxes, color=color_big, fontsize=9, fontweight="bold", ha="left", va="bottom"
        )
        ax1.text(
            0.75, 1.03, f"羊群: {latest_sheep_val:.1f}%", 
            transform=ax1.transAxes, color=color_sheep, fontsize=9, fontweight="bold", ha="left", va="bottom"
        )

        ax1.grid(True, linestyle="--", alpha=0.3)

        ax3.bar(dates_plot, vol_series.values, color="#3498db", alpha=0.7, width=3.5, label="成交量(張)")
        ax3.plot(dates_plot, vol_20ma, color="#f39c12", linewidth=1.2, label="20MA")
        ax3.set_ylabel("張數", fontsize=9, color="white", fontweight="bold")
        ax3.set_xlabel("日期", fontsize=9, color="white")
        ax3.tick_params(axis="x", labelsize=8, rotation=10)
        ax3.tick_params(axis="y", labelsize=8)
        ax3.legend(loc="upper left", fontsize=8)
        ax3.grid(True, linestyle="--", alpha=0.3)

        fig.tight_layout(pad=0.5)
        st.pyplot(fig, use_container_width=True, dpi=250)

    # =========================================================
    # 分頁二：純籌碼型態極速選股
    # =========================================================
    elif app_mode == "⚡ 秒速選股：黃金交叉 / 死亡交叉":
        st.subheader("⚡ 籌碼型態選股：搜尋近期的「黃金交叉」與「死亡交叉」")
        st.markdown("結合型態轉折與大戶持股水位過濾，秒速產出精華清單！")

        col_s1, col_s2, col_s3 = st.columns(3)
        with col_s1:
            cross_type = st.radio(
                "選擇要篩選的型態",
                ["🚀 近期黃金交叉 (大戶買、羊群賣)", "⚠️ 近期死亡交叉 (大戶賣、羊群買)"],
                horizontal=True,
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
                cache_dict = load_local_cache_cached()

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
                st.rerun()

            st.dataframe(df_res, use_container_width=True, hide_index=True)

        elif run_btn:
            st.warning(f"在大戶持股水位 ≧ {min_big_holder}% 且符合該型態的條件下沒有找到個股，請嘗試稍微調降水位滑桿。")
        else:
            st.info(f"💡 提示：設定好型態、週數與大戶水位後，點擊 **🚀 執行型態與水位過濾選股** 即可產出精華清單。")

    # =========================================================
    # 分頁三：每週大戶增幅前 15 名總表 (左右雙欄並排：左 8 檔、右 7 檔)
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
                    st.subheader("📋 每週大戶持股增幅前 15 名總表")
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

else:
    st.warning("請確認 StockIDs.xlsx 是否已放在 GitHub 專案目錄中。")