from datetime import datetime, timedelta
import os
import pandas as pd
import yfinance as yf

print("=== 開始執行：300日歷史資料累積與智慧選股 ===")

# 1. 讀取你的股票清單 (從 StockIDs.xlsx 或現有大戶總表)
stock_list_file = "StockIDs.xlsx"
if os.path.exists(stock_list_file):
  df_stocks = pd.read_excel(
      stock_list_file, sheet_name="StockIDs", dtype={"代碼": str}
  )
  df_stocks["代碼"] = (
      df_stocks["代碼"].astype(str).str.strip().str.replace(r"\.0$", "", regex=True)
  )
  tickers = df_stocks["代碼"].tolist()
  names = df_stocks["名稱"].tolist()
else:
  # 備用預設清單
  tickers = ["2330", "2317", "2454"]
  names = ["台積電", "鴻海", "聯發科"]

DATA_DIR = "stock_data_300days"
os.makedirs(DATA_DIR, exist_ok=True)

selected_results = []

# 2. 迴圈抓取每一檔股票的 300 日資料
for ticker, name in zip(tickers, names):
  # 略過加權指數等特殊代號或處理台股后缀
  if ticker == "99991":
    yf_ticker = "^TWII"
  else:
    yf_ticker = f"{ticker}.TW"  # 如果有上櫃需求可自行擴充判斷 .TWO

  file_path = os.path.join(DATA_DIR, f"{ticker}.csv")

  try:
    # 抓取最近 450 天（確保扣除例假日後，穩穩擁有 300 個交易日）
    end_date = datetime.today().strftime("%Y-%m-%d")
    start_date = (datetime.today() - timedelta(days=450)).strftime("%Y-%m-%d")

    df = yf.download(yf_ticker, start=start_date, end=end_date, progress=False)

    if df.empty:
      continue

    # 處理 MultiIndex 欄位
    if isinstance(df.columns, pd.MultiIndex):
      df.columns = df.columns.get_level_values(0)

    df = df[["Open", "High", "Low", "Close", "Volume"]].dropna()

    # 嚴格保留最後 300 個交易日（滾動視窗機制）
    df = df.tail(300)

    # 儲存至倉庫內的資料夾
    df.to_csv(file_path)

    # 3. 執行智慧選股策略運算（例如：長線多頭 + 均線黃金交叉 + 籌碼濾網）
    if len(df) >= 200:
      df["MA50"] = df["Close"].rolling(window=50).mean()
      df["MA200"] = df["Close"].rolling(window=200).mean()

      latest = df.iloc[-1]
      prev = df.iloc[-2]

      # 範例智慧選股條件：
      # 條件一：收盤價站上 200 日年線
      # 條件二：50日均線向上穿越 200日年線 (黃金交叉) 或者 50日線持續向上
      is_long_term_bull = latest["Close"] > latest["MA200"]
      is_ma_golden = (prev["MA50"] <= prev["MA200"]) and (
          latest["MA50"] > latest["MA200"]
      )

      if is_long_term_bull and (is_ma_golden or latest["MA50"] > latest["MA200"]):
        selected_results.append({
            "代碼": ticker,
            "名稱": name,
            "收盤價": round(float(latest["Close"]), 2),
            "MA200": round(float(latest["MA200"]), 2),
            "更新日期": datetime.today().strftime("%Y-%m-%d"),
        })

  except Exception as e:
    print(f"處理 {ticker} 發生錯誤: {e}")

# 4. 輸出選股結果總表
output_csv = "smart_selected_output.csv"
if selected_results:
  result_df = pd.DataFrame(selected_results)
  result_df.to_csv(output_csv, index=False, encoding="utf-8-sig")
  print(f"\n🎉 選股完成！共篩選出 {len(result_df)} 檔標的，已儲存至 {output_csv}")
else:
  print("\n今日無符合條件標的。")