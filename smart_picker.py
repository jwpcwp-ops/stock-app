from datetime import datetime, timedelta
import os
import pandas as pd
import yfinance as yf

TXT_DIR = "txt_data"
os.makedirs(TXT_DIR, exist_ok=True)

STOCK_IDS_PATH = "StockIDs.xlsx"

print("=== 開始執行：GitHub 雲端自動更新 TXT 與選股作業 ===")

# 1. 讀取 StockIDs.xlsx
if not os.path.exists(STOCK_IDS_PATH):
  print(f"❌ 找不到股票代碼檔: {STOCK_IDS_PATH}")
  exit(1)

df_ids = pd.read_excel(STOCK_IDS_PATH, sheet_name="StockIDs", dtype={"代碼": str})
df_ids["代碼"] = (
    df_ids["代碼"].astype(str).str.strip().str.replace(r"\.0$", "", regex=True)
)

selected_results = []
end_date = datetime.today().strftime("%Y-%m-%d")
start_date = (datetime.today() - timedelta(days=450)).strftime(
    "%Y-%m-%d"
)  # 確保有充足的 300 個交易日

for _, row in df_ids.iterrows():
  code = str(row.iloc[0]).zfill(4)
  name = str(row.iloc[1]) if len(row) > 1 else ""

  yf_ticker = "^TWII" if code == "99991" else f"{code}.TW"

  try:
    # 抓取歷史資料
    df_dl = yf.download(yf_ticker, start=start_date, end=end_date, progress=False)
    if df_dl.empty and code != "99991":
      df_dl = yf.download(
          f"{code}.TWO", start=start_date, end=end_date, progress=False
      )

    if df_dl.empty:
      continue

    if isinstance(df_dl.columns, pd.MultiIndex):
      df_dl.columns = df_dl.columns.get_level_values(0)

    df_dl = df_dl[["Open", "High", "Low", "Close", "Volume"]].dropna()
    df_dl = df_dl.tail(300)  # 嚴格維持 300 個交易日

    # 2. 自動產生並覆寫為你習慣的飛狐 TXT 格式 (日期 開 高 低 收 量)
    txt_path = os.path.join(TXT_DIR, f"TW{code}.txt")
    with open(txt_path, "w", encoding="utf-8") as f:
      for idx, r in df_dl.iterrows():
        date_str = idx.strftime("%Y/%m/%d")
        o, h, l, c, v = (
            float(r["Open"]),
            float(r["High"]),
            float(r["Low"]),
            float(r["Close"]),
            int(r["Volume"]),
        )
        f.write(f"{date_str} {o:.2f} {h:.2f} {l:.2f} {c:.2f} {v}\n")

    # 3. 執行策略選股運算 (範例：收盤價站上 200 日年線且帶量)
    closes = df_dl["Close"].values
    volumes = df_dl["Volume"].values
    s_close = pd.Series(closes)
    s_vol = pd.Series(volumes)

    if len(df_dl) >= 200:
      ma200 = s_close.rolling(window=200).mean().iloc[-1]
      vol_ma20 = s_vol.rolling(window=20).mean().iloc[-1]

      if closes[-1] > ma200 and volumes[-1] > vol_ma20 * 1.5:
        selected_results.append({
            "代碼": code,
            "名稱": name,
            "收盤價": round(float(closes[-1]), 2),
            "年線(200MA)": round(float(ma200), 2),
            "更新日期": datetime.today().strftime("%Y-%m-%d"),
        })

  except Exception as e:
    print(f"處理 {code} 發生錯誤: {e}")

# 4. 輸出選股結果給網頁讀取
output_csv = "smart_selected_output.csv"
if selected_results:
  res_df = pd.DataFrame(selected_results)
  res_df.to_csv(output_csv, index=False, encoding="utf-8-sig")
  print(
      f"\n🎉 雲端選股完成！共篩選出 {len(res_df)} 檔標的，已儲存至"
      f" {output_csv}"
  )
else:
  print("\n今日無符合條件標的。")