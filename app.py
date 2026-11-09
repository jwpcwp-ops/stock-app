import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def generate_comprehensive_chart(
    stock_code, stock_name, k_records, big_holder, sheep_holder, dates_chip
):
  """整合 K線 + MACD + 成交量 + 大戶羊群 + 多空線 的 5 層專業圖表繪製函數"""
  if len(k_records) < 60:
    return None

  # 1. 轉換 K 線 Dataframe
  df = pd.DataFrame(k_records).tail(250).reset_index(drop=True)

  # 2. 計算技術指標 (MACD & EMA & 多空線)
  s_close = df['close']
  df['ema3'] = s_close.ewm(span=3, adjust=False).mean()
  df['ema7'] = s_close.ewm(span=7, adjust=False).mean()
  df['ema15'] = s_close.ewm(span=15, adjust=False).mean()
  df['ema30'] = s_close.ewm(span=30, adjust=False).mean()
  df['ema60'] = s_close.ewm(span=60, adjust=False).mean()

  # MACD 計算
  df['dif'] = s_close.ewm(span=12, adjust=False).mean() - s_close.ewm(
      span=26, adjust=False.mean()
  )
  df['dem'] = df['dif'].ewm(span=9, adjust=False).mean()
  df['osc'] = (df['dif'] - df['dem']) * 2

  # 成交量均量
  df['vol_ma5'] = df['vol'].rolling(window=5).mean()
  df['vol_ma20'] = df['vol'].rolling(window=20).mean()

  # 多空線邏輯判定 (依據您提供的 4 組條件)
  cond1 = df['ema3'] > df['ema15']
  cond2 = s_close > df['ema15']
  slope = (df['ema15'] / df['ema30'] - 1) * 100
  cond3 = slope > 0
  cond4 = df['ema15'] > df['ema30']
  df['long_trend'] = cond3 & cond4  # 多頭成立為 True，否則 False

  # 顏色設定 (暗色系專業風格)
  BG_COLOR, PANEL_BG, GRID_COLOR, SUB_BORDER = (
      '#0D1117',
      '#161B22',
      '#21262D',
      '#30363D',
  )
  BAR_UP_COLOR, BAR_DOWN_COLOR = '#FF4D4D', '#00C853'

  body_colors = [
      BAR_UP_COLOR if c >= o else BAR_DOWN_COLOR
      for o, c in zip(df['open'], df['close'])
  ]
  osc_colors = [
      BAR_UP_COLOR if osc >= 0 else BAR_DOWN_COLOR for osc in df['osc']
  ]

  # 3. 建立 5 層垂直堆疊畫布
  fig, (ax1, ax2, ax3, ax4, ax5) = plt.subplots(
      5,
      1,
      figsize=(11.5, 7.5),
      dpi=180,
      gridspec_kw={
          'height_ratios': [3.5, 1.0, 1.0, 1.2, 0.22]
      },  # 分配各子圖高度比例
      sharex=True,
  )

  for ax in [fig, ax1, ax2, ax3, ax4, ax5]:
    ax.set_facecolor(BG_COLOR)
  fig.patch.set_facecolor(BG_COLOR)
  x = list(range(len(df)))

  # --- 層 1：主圖 (K線 + 均線) ---
  ax1.set_facecolor(PANEL_BG)
  ax1.vlines(
      x, df['low'], df['high'], color=body_colors, linewidth=1, alpha=0.9
  )
  body_bottom = [min(o, c) for o, c in zip(df['open'], df['close'])]
  body_height = [
      max(abs(c - o), 0.01) for o, c in zip(df['open'], df['close'])
  ]
  ax1.bar(
      x,
      body_height,
      bottom=body_bottom,
      width=0.75,
      color=body_colors,
      edgecolor='none',
  )
  ax1.plot(
      x, df['ema3'], linewidth=0.8, color='#58A6FF', label='EMA3', alpha=0.9
  )
  ax1.plot(
      x, df['ema60'], linewidth=0.8, color='#FFFFFF', label='EMA60', linestyle='--'
  )
  ax1.set_title(
      f'[{stock_code}] {stock_name} - 專業多維度籌碼技術圖表',
      fontsize=11,
      fontweight='bold',
      color='white',
  )
  ax1.yaxis.tick_right()
  ax1.tick_params(axis='y', labelsize=7.5, colors='#8B949E')
  ax1.grid(axis='y', linestyle=':', color=GRID_COLOR, alpha=0.8)

  # --- 層 2：MACD 副圖 ---
  ax2.set_facecolor(PANEL_BG)
  ax2.bar(
      x, df['osc'], width=0.75, color=osc_colors, edgecolor='none', alpha=0.85
  )
  ax2.plot(x, df['dif'], linewidth=0.7, color='#00E5FF', label='DIF')
  ax2.plot(x, df['dem'], linewidth=0.7, color='#F59E0B', label='DEA')
  ax2.axhline(0, color='#30363D', linestyle=':', linewidth=1)
  ax2.yaxis.tick_right()
  ax2.tick_params(axis='y', labelsize=7.5, colors='#8B949E')
  ax2.grid(axis='y', linestyle=':', color=GRID_COLOR, alpha=0.8)
  ax2.text(
      0.015,
      0.82,
      'MACD',
      transform=ax2.transAxes,
      fontsize=8,
      fontweight='bold',
      color='#8B949E',
  )

  # --- 層 3：成交量副圖 ---
  ax3.set_facecolor(PANEL_BG)
  ax3.bar(
      x,
      df['vol'] / 1000,
      width=0.75,
      color=body_colors,
      edgecolor='none',
      alpha=0.85,
  )
  ax3.plot(x, df['vol_ma5'] / 1000, linewidth=0.7, color='#00E5FF', label='VOL5')
  ax3.yaxis.tick_right()
  ax3.tick_params(axis='y', labelsize=7.5, colors='#8B949E')
  ax3.grid(axis='y', linestyle=':', color=GRID_COLOR, alpha=0.8)
  ax3.text(
      0.015,
      0.82,
      '成交量(張)',
      transform=ax3.transAxes,
      fontsize=8,
      fontweight='bold',
      color='#8B949E',
  )

  # --- 層 4：大戶與羊群持股比例副圖 ---
  ax4.set_facecolor(PANEL_BG)
  if len(big_holder) > 0 and len(sheep_holder) > 0:
    # 確保對齊最後 N 筆資料
    b_plot = big_holder[-len(df) :]
    s_plot = sheep_holder[-len(df) :]
    x_chip = x[-len(b_plot) :]
    ax4.plot(
        x_chip,
        b_plot,
        color='#FF4D4D',
        linewidth=1.2,
        marker='o',
        markersize=2,
        label='大戶持股(%)',
    )
    ax4.plot(
        x_chip,
        s_plot,
        color='#2ECC71',
        linewidth=1.2,
        marker='s',
        markersize=2,
        label='羊群持股(%)',
    )
  ax4.yaxis.tick_right()
  ax4.tick_params(axis='y', labelsize=7.5, colors='#8B949E')
  ax4.grid(axis='y', linestyle=':', color=GRID_COLOR, alpha=0.8)
  ax4.legend(loc='upper left', fontsize=7)
  ax4.text(
      0.015,
      0.82,
      '大戶與羊群',
      transform=ax4.transAxes,
      fontsize=8,
      fontweight='bold',
      color='#8B949E',
  )

  # --- 層 5：最底部的多空線色帶 ---
  ax5.set_facecolor(PANEL_BG)
  trend_colors = [
      BAR_UP_COLOR if is_bull else BAR_DOWN_COLOR for is_bull in df['long_trend']
  ]
  ax5.bar(x, [1] * len(df), width=1.0, color=trend_colors, edgecolor='none')
  ax5.text(
      0.015,
      0.5,
      '多空線',
      transform=ax5.transAxes,
      fontsize=8.0,
      color='#FFFFFF',
      ha='left',
      va='center',
  )
  ax5.set_yticks([])

  # 統一框線與邊距
  for ax in [ax1, ax2, ax3, ax4, ax5]:
    for spine in ax.spines.values():
      spine.set_visible(True)
      spine.set_color(SUB_BORDER)
      spine.set_linewidth(0.8)

  plt.subplots_adjust(
      left=0.015, right=0.98, top=0.96, bottom=0.06, hspace=0.08
  )

  # 儲存暫存圖檔供 Streamlit 或 Excel 調用
  import os

  temp_dir = os.environ.get('TEMP', os.getcwd())
  img_path = os.path.join(temp_dir, f'comprehensive_chart_{stock_code}.png')
  plt.savefig(
      img_path,
      dpi=180,
      facecolor=fig.get_facecolor(),
      edgecolor='none',
      bbox_inches='tight',
      pad_inches=0.03,
  )
  plt.close(fig)

  return img_path if os.path.exists(img_path) else None