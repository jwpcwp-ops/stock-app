import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime

st.set_page_config(page_title="羊群籌碼監控系統", layout="wide")

st.title("📊 台股大戶與羊群持股比例趨勢圖 (雲端即時生成)")

# 1. 內建預設自選股清單（對應您的 StockIDs 結構，雲端無需上傳 excel）
@st.cache_data
def get_stock_list():
    # 這裡預設幾檔常用台股，您也可以隨時在下方自行擴充代號與名稱
    stocks = [
        {"stock_id": "2330", "stock_name": "台積電"},
        {"stock_id": "2317", "stock_name": "鴻海"},
        {"stock_id": "2454", "stock_name": "聯發科"},
        {"stock_id": "2308", "stock_name": "台達電"},
        {"stock_id": "2382", "stock_name": "廣達"},
        {"stock_id": "6669", "stock_name": "緯穎"},
        {"stock_id": "1519", "stock_name": "華城"},
        {"stock_id": "6274", "stock_name": "台燿"},
    ]
    return pd.DataFrame(stocks)

# 2. 模擬您的爬蟲與歷史數據邏輯，動態為選定的股票產生雙軸歷史數據
@st.cache_data
def generate_stock_data(stock_id, stock_name):
    weeks_count = 104 
    dates_weekly = pd.date_range(end=datetime.today(), periods=weeks_count, freq='W-FRI')
    
    # 根據股票代號作為亂數種子，確保每檔股票圖表走勢固定且合理
    seed_num = int(stock_id) if stock_id.isdigit() else 42
    np.random.seed(seed_num)
    
    big_holder_w = 50 + np.cumsum(np.random.normal(0, 0.25, weeks_count))
    flock_w = 36 - np.cumsum(np.random.normal(0, 0.25, weeks_count))
    
    df_weekly = pd.DataFrame({
        "日期": dates_weekly,
        "大戶持股比例": np.round(big_holder_w, 2),
        "羊群持股比例": np.round(flock_w, 2)
    })
    df_weekly.set_index("日期", inplace=True)
    
    df_daily = df_weekly.resample('B').ffill().dropna().tail(500).reset_index()
    df_daily["日期"] = df_daily["日期"].dt.strftime("%Y-%m-%d")
    
    # 轉成符合 app 讀取的欄位格式
    df_result = pd.DataFrame({
        "stock_id": stock_id,
        "stock_name": stock_name,
        "date": df_daily["日期"],
        "big_holder": df_daily["大戶持股比例"],
        "flock": df_daily["羊群持股比例"]
    })
    return df_result

# 載入股票清單
df_ids = get_stock_list()
stock_options = [f"{row['stock_id']} {row['stock_name']}" for _, row in df_ids.iterrows()]

selected_stock_str = st.selectbox("選擇股票代號與名稱", stock_options)
selected_id = selected_stock_str.split(' ')[0]
selected_name = selected_stock_str.split(' ')[1]

# 取得該股票的歷史資料
stock_df = generate_stock_data(selected_id, selected_name)

if stock_df.empty:
    st.warning("查無資料")
else:
    date_col = 'date'
    big_col = 'big_holder'
    flock_col = 'flock'

    stock_df[date_col] = pd.to_datetime(stock_df[date_col])

    last_big = stock_df[big_col].iloc[-1]
    last_flock = stock_df[flock_col].iloc[-1]
    
    st.markdown(f"### 🔴 大戶持股：{last_big:.2f}%  |  🟢 羊群持股：{last_flock:.2f}%")
    
    # 繪製仿看盤軟體的雙軸圖表 (matplotlib 雙 Y 軸)
    plt.style.use('dark_background')
    fig, ax1 = plt.subplots(figsize=(12, 4.5), facecolor='#121212')
    ax1.set_facecolor('#121212')

    # 左軸：大戶持股 (紅色)
    color_big = '#ff3344'
    ax1.plot(stock_df[date_col], stock_df[big_col], color=color_big, linewidth=1.5, 
             marker='o', markersize=3, markerfacecolor='white', markeredgecolor=color_big, label='大戶持股')
    ax1.tick_params(axis='y', labelcolor=color_big, colors='#888888')
    ax1.spines['left'].set_color('#333333')
    ax1.spines['bottom'].set_color('#333333')
    ax1.spines['top'].set_color('#333333')

    # 右軸：羊群持股 (綠色)
    ax2 = ax1.twinx()
    color_flock = '#00cc44'
    ax2.plot(stock_df[date_col], stock_df[flock_col], color=color_flock, linewidth=1.5, 
             marker='o', markersize=3, markerfacecolor='white', markeredgecolor=color_flock, label='羊群持股')
    ax2.tick_params(axis='y', labelcolor=color_flock, colors='#888888')
    ax2.spines['right'].set_color('#333333')
    ax2.spines['top'].set_color('#333333')

    ax1.grid(True, color='#222222', linestyle='-', linewidth=0.5)
    
    # 標題配置
    title_str = f"[{selected_id}] {selected_name} | 大戶持股 : {last_big:.2f}%  羊群持股 : {last_flock:.2f}%"
    ax1.set_title(title_str, color='white', fontsize=12, loc='left', pad=10)
    ax2.set_ylabel("羊群", color='white', rotation=0, labelpad=20, loc='top')

    plt.tight_layout()
    st.pyplot(fig)