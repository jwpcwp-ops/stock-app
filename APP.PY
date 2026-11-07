import streamlit as st
import pandas as pd
import json
import os
import matplotlib.pyplot as plt

st.set_page_config(page_title="羊群籌碼監控系統", layout="wide")

st.title("📊 台股大戶與羊群持股比例趨勢圖 (雙軸對應)")

@st.cache_data
def load_data():
    file_path = '羊群籌碼_fetch_cache.jsonl'
    if not os.path.exists(file_path):
        return pd.DataFrame()

    data = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                try:
                    data.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return pd.DataFrame(data)

df = load_data()

if df.empty:
    st.error("找不到 `羊群籌碼_fetch_cache.jsonl` 檔案或檔案內容為空。")
else:
    id_col = 'stock_id' if 'stock_id' in df.columns else df.columns[0]
    name_col = 'stock_name' if 'stock_name' in df.columns else df.columns[1]
    date_col = 'date' if 'date' in df.columns else '日期'
    big_col = 'big_holder' if 'big_holder' in df.columns else '大戶'
    flock_col = 'flock' if 'flock' in df.columns else '羊群'

    df[date_col] = pd.to_datetime(df[date_col])
    
    stock_list = df[[id_col, name_col]].drop_duplicates().sort_values(id_col)
    stock_options = [f"{row[id_col]} {row[name_col]}" for _, row in stock_list.iterrows()]

    selected_stock_str = st.selectbox("選擇股票", stock_options)
    stock_id = selected_stock_str.split(' ')[0]

    stock_df = df[df[id_col] == stock_id].sort_values(date_col)

    if not stock_df.empty:
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
        title_str = f"大戶 : 大戶持股 : {last_big:.2f}%  羊群持股 : {last_flock:.2f}%"
        ax1.set_title(title_str, color='white', fontsize=12, loc='left', pad=10)
        ax2.set_ylabel("羊群", color='white', rotation=0, labelpad=20, loc='top')

        plt.tight_layout()
        st.pyplot(fig)
    else:
        st.warning("查無資料")