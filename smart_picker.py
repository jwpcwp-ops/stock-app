from datetime import datetime, timedelta
import os
import pandas as pd
import yfinance as yf

# ===========================================================
# 9 大策略參數設定區
# ===========================================================
LOOKBACK_DAYS = 250
LOW_PRICE_RATIO = 1.10
VOL_MA_PERIOD = 20

MIN_VOLUME = 500
VOL_MULTIPLIER = 2.0

MIN_BREAKOUT_VOLUME = 10000
VOLUME_FACTOR = 2.0

MIN_MACD_VOLUME = 500
MACD_VOL_MULTIPLIER = 1.5

MIN_KINGKONG_VOLUME = 10000
KINGKONG_VOL_MULTIPLIER = 3.0

MIN_MA_MACD_VOLUME = 5000
MA_MACD_VOL_MULTIPLIER = 2.0

MIN_SWING_VOLUME = 5000
SWING_VOL_MULTIPLIER = 2.0

MIN_TREND_REV_VOLUME = 5000
TREND_REV_VOL_MULTIPLIER = 2.0

MIN_MA_CONV_VOLUME = 500
MA_CONV_VOL_MULTIPLIER = 1.5
MA_CONV_THRESHOLD = 0.025

MIN_BOTTOM_SURGE_VOLUME = 1000
BOTTOM_VOL_MA_PERIOD = 20
BOTTOM_SURGE_MULTIPLIER_MIN = 1.4
BOTTOM_SURGE_MULTIPLIER_MAX = 2.0
BOTTOM_RANGE_PCT = 0.20

TXT_DIR = "txt_data"
os.makedirs(TXT_DIR, exist_ok=True)
STOCK_IDS_PATH = "StockIDs.xlsx"

print("=== 開始執行：GitHub 雲端 300日資料維護與 9 大策略選股 ===")

if not os.path.exists(STOCK_IDS_PATH):
  print(f"❌ 找不到股票代碼檔: {STOCK_IDS_PATH}")
  exit(1)

df_ids = pd.read_excel(STOCK_IDS_PATH, sheet_name="StockIDs", dtype={"代碼": str})
df_ids["代碼"] = (
    df_ids["代碼"].astype(str).str.strip().str.replace(r"\.0$", "", regex=True)
)

end_date = datetime.today().strftime("%Y-%m-%d")
start_date = (datetime.today() - timedelta(days=450)).strftime("%Y-%m-%d")

# 定義固定的 9 大策略名稱清單
all_strategies = [
    "主力底部吃貨",
    "突破前高",
    "MACD 選股",
    "金剛指標",
    "均線與MACD篩選",
    "波段買點",
    "多空轉折信號",
    "5均線匯集",
    "底部量大強漲",
]

strategy_results = {name: [] for name in all_strategies}


# ==========================================
# 9 大策略判斷函數
# ==========================================
def check_accumulation_signal(k_records):
  if len(k_records) < LOOKBACK_DAYS:
    return False
  closes = [item["close"] for item in k_records]
  volumes = [item["vol"] for item in k_records]
  idx = len(k_records) - 1
  lowest_val = min(closes[max(0, idx - (LOOKBACK_DAYS - 1)) : idx + 1])
  vol_ma = sum(volumes[max(0, idx - 19) : idx + 1]) / 20
  return (
      closes[idx] <= lowest_val * LOW_PRICE_RATIO
      and volumes[idx] >= vol_ma * VOL_MULTIPLIER
      and volumes[idx] >= MIN_VOLUME
  )


def check_breakout_signal(k_records):
  if len(k_records) < 60:
    return False
  highs = [item["high"] for item in k_records]
  vols = [item["vol"] for item in k_records]
  idx = len(k_records) - 1
  ch60 = highs[idx] >= max(highs[max(0, idx - 59) : idx])
  vol_ma = sum(vols[max(0, idx - 19) : idx + 1]) / 20
  return (
      ch60
      and vols[idx] > vol_ma * VOLUME_FACTOR
      and vols[idx] >= MIN_BREAKOUT_VOLUME
  )


def check_macd_signal(k_records):
  if len(k_records) < 50:
    return False
  closes = [i["close"] for i in k_records]
  volumes = [i["vol"] for i in k_records]
  s_close = pd.Series(closes)
  s_vol = pd.Series(volumes)
  dif = (
      s_close.ewm(span=12, adjust=False).mean()
      - s_close.ewm(span=26, adjust=False).mean()
  )
  dem = dif.ewm(span=9, adjust=False).mean()
  vol_ma = s_vol.rolling(window=20).mean().iloc[-1]
  idx = len(k_records) - 1
  return (
      dif.iloc[idx - 1] <= dem.iloc[idx - 1]
      and dif.iloc[idx] > dem.iloc[idx]
      and dif.iloc[idx] > 0
      and volumes[idx] > (vol_ma * MACD_VOL_MULTIPLIER)
      and volumes[idx] >= MIN_MACD_VOLUME
  )


def check_kingkong_signal(k_records):
  if len(k_records) < 200:
    return False
  closes = [i["close"] for i in k_records]
  volumes = [i["vol"] for i in k_records]
  s_close, s_vol = pd.Series(closes), pd.Series(volumes)
  idx = len(k_records) - 1
  ma200 = s_close.rolling(window=200).mean().iloc[idx]
  ma20_vol = s_vol.rolling(window=20).mean().iloc[idx]
  is_成立 = (
      s_close.ewm(span=3, adjust=False).mean().iloc[idx]
      > s_close.ewm(span=15, adjust=False).mean().iloc[idx]
  )
  return (
      is_成立
      and closes[idx] > ma200
      and closes[idx] >= max(closes[idx - 2 : idx])
      and volumes[idx] > ma20_vol * KINGKONG_VOL_MULTIPLIER
      and volumes[idx] >= MIN_KINGKONG_VOLUME
  )


def check_ma_macd_signal(k_records):
  if len(k_records) < 40:
    return False
  closes = [i["close"] for i in k_records]
  volumes = [i["vol"] for i in k_records]
  s_close = pd.Series(closes)
  s_vol = pd.Series(volumes)
  ma3 = s_close.rolling(window=3).mean()
  ma7 = s_close.rolling(window=7).mean()
  dif = (
      s_close.ewm(span=12, adjust=False).mean()
      - s_close.ewm(span=26, adjust=False).mean()
  )
  dem = dif.ewm(span=9, adjust=False).mean()
  vol_ma20 = s_vol.rolling(window=20).mean()
  idx = len(k_records) - 1
  return (
      (ma3.iloc[idx - 1] <= ma7.iloc[idx - 1])
      and (ma3.iloc[idx] > ma7.iloc[idx])
      and (dif.iloc[idx - 1] <= dem.iloc[idx - 1])
      and (dif.iloc[idx] > dem.iloc[idx])
      and (dif.iloc[idx] > 0)
      and (volumes[idx] > vol_ma20.iloc[idx] * MA_MACD_VOL_MULTIPLIER)
      and (volumes[idx] >= MIN_MA_MACD_VOLUME)
  )


def check_swing_signal(k_records):
  if len(k_records) < 35:
    return False
  closes = [i["close"] for i in k_records]
  volumes = [i["vol"] for i in k_records]
  s_close = pd.Series(closes)
  s_vol = pd.Series(volumes)
  ema3 = s_close.ewm(span=3, adjust=False).mean()
  ema15 = s_close.ewm(span=15, adjust=False).mean()
  ema30 = s_close.ewm(span=35, adjust=False).mean()
  seishin = (ema3 > ema15) & (s_close > ema15) & (ema15 > ema30)
  idx = len(k_records) - 1
  if idx < 1:
    return False
  is_new = seishin.iloc[idx] and not seishin.iloc[idx - 1]
  is_cont = (
      seishin.iloc[idx] and seishin.iloc[idx - 1] and not seishin.iloc[idx - 2]
      if idx >= 2
      else False
  )
  vol_ma5 = s_vol.rolling(window=5).mean().iloc[idx]
  return (
      (is_new or is_cont)
      and volumes[idx] > vol_ma5 * SWING_VOL_MULTIPLIER
      and volumes[idx] >= MIN_SWING_VOLUME
  )


def check_trend_reversal_signal(k_records):
  if len(k_records) < 30:
    return False
  closes = [i["close"] for i in k_records]
  volumes = [i["vol"] for i in k_records]
  s_close = pd.Series(closes)
  s_vol = pd.Series(volumes)
  ema3 = s_close.ewm(span=3, adjust=False).mean()
  ma5 = s_close.rolling(window=5).mean()
  vol_ma20 = s_vol.rolling(window=20).mean()
  idx = len(k_records) - 1
  if idx < 1:
    return False
  return (
      (ema3.iloc[idx - 1] <= ma5.iloc[idx - 1])
      and (ema3.iloc[idx] > ma5.iloc[idx])
      and (volumes[idx] > vol_ma20.iloc[idx] * TREND_REV_VOL_MULTIPLIER)
      and (volumes[idx] >= MIN_TREND_REV_VOLUME)
  )


def check_ma_convergence_signal(k_records):
  if len(k_records) < 130:
    return False
  closes = [i["close"] for i in k_records]
  volumes = [i["vol"] for i in k_records]
  s_close = pd.Series(closes)
  s_vol = pd.Series(volumes)
  ema3 = s_close.ewm(span=3, adjust=False).mean()
  ema7 = s_close.ewm(span=7, adjust=False).mean()
  ema35 = s_close.ewm(span=35, adjust=False).mean()
  ema60 = s_close.ewm(span=60, adjust=False).mean()
  ema120 = s_close.ewm(span=120, adjust=False).mean()
  idx = len(k_records) - 1
  vals = [
      ema3.iloc[idx],
      ema7.iloc[idx],
      ema35.iloc[idx],
      ema60.iloc[idx],
      ema120.iloc[idx],
  ]
  is_conv = (max(vals) - min(vals)) / min(vals) <= MA_CONV_THRESHOLD
  dif = (
      s_close.ewm(span=12, adjust=False).mean()
      - s_close.ewm(span=26, adjust=False).mean()
  )
  dem = dif.ewm(span=9, adjust=False).mean()
  macd_bar = (dif - dem) * 2
  is_macd = (macd_bar.iloc[idx] > macd_bar.iloc[idx - 1]) and (
      dif.iloc[idx] > dem.iloc[idx] or macd_bar.iloc[idx] > 0
  )
  ma5 = s_close.rolling(window=5).mean()
  vol_ma20 = s_vol.rolling(window=20).mean().iloc[idx]
  return (
      is_conv
      and is_macd
      and (ema3.iloc[idx] > ma5.iloc[idx])
      and (volumes[idx] > vol_ma20 * MA_CONV_VOL_MULTIPLIER)
      and (volumes[idx] >= MIN_MA_CONV_VOLUME)
  )


def check_bottom_surge_signal(k_records):
  if len(k_records) < 60:
    return False
  highs = [i["high"] for i in k_records]
  lows = [i["low"] for i in k_records]
  closes = [i["close"] for i in k_records]
  opens = [i["open"] for i in k_records]
  volumes = [i["vol"] for i in k_records]
  idx = len(k_records) - 1
  period_high = max(highs[max(0, idx - 59) : idx])
  period_low = min(lows[max(0, idx - 59) : idx])
  if period_low == 0:
    return False
  price_range_ratio = (period_high - period_low) / period_low
  vol_ma = (
      sum(volumes[max(0, idx - BOTTOM_VOL_MA_PERIOD) : idx])
      / BOTTOM_VOL_MA_PERIOD
  )
  return (
      price_range_ratio < BOTTOM_RANGE_PCT
      and volumes[idx] >= MIN_BOTTOM_SURGE_VOLUME
      and volumes[idx] >= vol_ma * BOTTOM_SURGE_MULTIPLIER_MIN
      and volumes[idx] <= vol_ma * BOTTOM_SURGE_MULTIPLIER_MAX
      and closes[idx] > opens[idx]
      and (highs[idx] - closes[idx]) / (highs[idx] - lows[idx] + 1e-6) < 0.15
  )


# ==========================================
# 主迴圈
# ==========================================
for _, row in df_ids.iterrows():
  code = str(row.iloc[0]).zfill(4)
  yf_ticker = "^TWII" if code == "99991" else f"{code}.TW"

  try:
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
    df_dl = df_dl.tail(300)

    txt_path = os.path.join(TXT_DIR, f"TW{code}.txt")
    k_records = []
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
        k_records.append(
            {"date": date_str, "open": o, "high": h, "low": l, "close": c, "vol": v}
        )

    if check_accumulation_signal(k_records):
      strategy_results["主力底部吃貨"].append(code)
    if check_breakout_signal(k_records):
      strategy_results["突破前高"].append(code)
    if check_macd_signal(k_records):
      strategy_results["MACD 選股"].append(code)
    if check_kingkong_signal(k_records):
      strategy_results["金剛指標"].append(code)
    if check_ma_macd_signal(k_records):
      strategy_results["均線與MACD篩選"].append(code)
    if check_swing_signal(k_records):
      strategy_results["波段買點"].append(code)
    if check_trend_reversal_signal(k_records):
      strategy_results["多空轉折信號"].append(code)
    if check_ma_convergence_signal(k_records):
      strategy_results["5均線匯集"].append(code)
    if check_bottom_surge_signal(k_records):
      strategy_results["底部量大強漲"].append(code)

  except Exception as e:
    print(f"處理代號 {code} 發生錯誤: {e}")

# ==========================================
# 3. 強制寫入全部 9 大策略至 CSV
# ==========================================
output_data = []
for strat_name in all_strategies:
  codes = strategy_results[strat_name]
  if codes:
    for c in codes:
      output_data.append({"策略名稱": strat_name, "代碼": c})
  else:
    # 確保每個策略名稱都存在於 CSV 中，無股票時代碼填「無」
    output_data.append({"策略名稱": strat_name, "代碼": "無"})

res_df = pd.DataFrame(output_data)
res_df.to_csv("smart_selected_output.csv", index=False, encoding="utf-8-sig")
print("🎉 9 大策略資料已完整寫入 smart_selected_output.csv")