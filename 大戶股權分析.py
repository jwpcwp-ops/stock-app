import os
import re
import time
from io import StringIO
import pandas as pd
import openpyxl
from openpyxl.styles import Font, Alignment, Border, Side, PatternFill
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

target_dir = r"D:\2026Q1\下載網站\富邦網站\股權分析"
if not os.path.exists(target_dir):
    try:
        os.makedirs(target_dir, exist_ok=True)
    except Exception:
        target_dir = "."

url = "https://norway.twsthr.info/StockHoldersTopWeek.aspx?Show=4"

print("=== 開始執行：最新單週大戶籌碼自動更新系統 (穩定版) ===")

latest_date_str = ""
latest_week_name = ""
target_df = None

with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=True,
        args=["--no-sandbox", "--disable-setuid-sandbox"]
    )
    context = browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    page = context.new_page()
    
    print("正在連線至目標網站...")
    page.goto(url, timeout=60000)
    page.wait_for_load_state("domcontentloaded")
    time.sleep(3)
    
    try:
        page_text = page.content()
        date_match = re.search(r"收盤價日期[:：]\s*(\d{4}/\d{1,2}/\d{1,2})", page_text)
        if date_match:
            latest_date_str = date_match.group(1)
            print(f"📅 成功擷取網頁最新收盤日期：{latest_date_str}")
        else:
            latest_date_str = time.strftime("%Y/%m/%d")
    except Exception:
        latest_date_str = time.strftime("%Y/%m/%d")

    select_weeks = page.locator("select").nth(0)
    options_locator = select_weeks.locator("option")
    week_options = options_locator.all_inner_texts()
    week_values = options_locator.evaluate_all("options => options.map(o => o.value)")
    
    if week_values:
        latest_week_name = week_options[0].strip()
        latest_val = week_values[0]
        print(f"正在擷取最新單週別: {latest_week_name} ...", end="")
        
        for retry in range(3):
            try:
                select_weeks.select_option(latest_val)
                time.sleep(6)  # 確保雲端網頁完整渲染
                
                html_content = page.content()
                
                # 💡 使用 html.parser 解析，避免依賴外部 lxml 套件報錯
                soup = BeautifulSoup(html_content, 'html.parser')
                tables = soup.find_all('table')
                
                if tables:
                    largest_table = max(tables, key=lambda t: len(t.find_all('tr')))
                    dfs = pd.read_html(StringIO(str(largest_table)), flavor='bs4')
                    if dfs:
                        target_df = dfs[0]
                
                if target_df is not None and len(target_df) > 0:
                    print(" ➔ 成功！")
                    break
                else:
                    time.sleep(3)
            except Exception as e:
                print(f"重試中... {e}")
                time.sleep(3)
        
    browser.close()

if target_df is None or len(target_df) == 0:
    print("❌ 未能成功擷取最新單週資料。")
    exit(1)

date_digits = re.sub(r'\D', '', latest_date_str)
if not date_digits or len(date_digits) != 8:
    date_digits = time.strftime("%Y%m%d")

output_filename = f"大戶持股最新單週{date_digits}分析總表.xlsx"
output_path = os.path.join(target_dir, output_filename)
fixed_output_path = "大戶持股最新分析總表.xlsx"

if isinstance(target_df.columns, pd.MultiIndex):
    target_df.columns = ['_'.join([str(c) for c in col if 'Unnamed' not in str(c)]).strip() for col in target_df.columns.values]

target_df.insert(0, "週別", latest_week_name)

if target_df.shape[1] > 3:
    header_mask = (target_df.iloc[:, 3].astype(str).str.strip() != "排名") & \
                  (target_df.iloc[:, 3].notna()) & \
                  (target_df.iloc[:, 3].astype(str).str.strip() != "")
    target_df = target_df[header_mask].reset_index(drop=True)

raw_stock_info = target_df.iloc[:, 4] if target_df.shape[1] > 4 else pd.Series([""] * len(target_df))
stock_codes, stock_names = [], []

for item in raw_stock_info:
    item_str = str(item).strip()
    match = re.match(r"^(\d+)\s*(.*)$", item_str)
    if match:
        stock_codes.append(match.group(1))
        stock_names.append(match.group(2))
    else:
        stock_codes.append(item_str)
        stock_names.append("")

data_dict = {
    '週別': target_df.iloc[:, 0],
    '排名': target_df.iloc[:, 3] if target_df.shape[1] > 3 else '',
    '代碼': stock_codes,
    '名稱': stock_names,
    '類別': target_df.iloc[:, 5] if target_df.shape[1] > 5 else '',
    '總集保戶數_上週': target_df.iloc[:, 6] if target_df.shape[1] > 6 else '',
    '總集保戶數_本週': target_df.iloc[:, 7] if target_df.shape[1] > 7 else '',
}

optional_cols = [
    ('大股東人數_上週', 9), ('大股東人數_本週', 10),
    ('大戶持有率_上週(%)', 12), ('大戶持有率_本週(%)', 13), ('大戶持有率_差異(%)', 14),
    ('平均張數_上週', 15), ('平均張數_本週', 16), ('平均張數_差異(%)', 17),
    ('今日收盤價', 18), ('今日漲跌', 19)
]

for col_name, idx in optional_cols:
    if target_df.shape[1] > idx:
        data_dict[col_name] = target_df.iloc[:, idx]

clean_data = pd.DataFrame(data_dict)
clean_data = clean_data[~clean_data['名稱'].astype(str).str.contains('-DR', na=False)].reset_index(drop=True)

if len(clean_data) > 10:
    clean_data = clean_data.iloc[10:].reset_index(drop=True)

top15_df = pd.DataFrame()
if '大戶持有率_差異(%)' in clean_data.columns:
    clean_data['大戶持有率_差異(%)'] = pd.to_numeric(clean_data['大戶持有率_差異(%)'], errors='coerce')
    top15_raw = clean_data.sort_values(by='大戶持有率_差異(%)', ascending=False).head(15).reset_index(drop=True)
    if '週別' in top15_raw.columns:
        top15_raw = top15_raw.drop(columns=['週別'])
    top15_cols = [col for col in top15_raw.columns if col != '排名']
    top15_df = top15_raw[top15_cols].copy()
    top15_df['連結'] = ""

paths_to_save = [output_path, fixed_output_path]
if target_dir == ".":
    paths_to_save = [fixed_output_path]

for path in paths_to_save:
    try:
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    except Exception:
        pass

    with pd.ExcelWriter(path, engine='openpyxl') as writer:
        clean_data.to_excel(writer, sheet_name='資料中心', index=False)
        if not top15_df.empty:
            top15_df.to_excel(writer, sheet_name='大戶增幅前15名', index=False, startrow=1)

    wb = openpyxl.load_workbook(path)
    if "個股查詢" in wb.sheetnames:
        del wb["個股查詢"]

    fill_blue = PatternFill(start_color="3172AD", end_color="3172AD", fill_type="solid")
    fill_red = PatternFill(start_color="FF0000", end_color="FF0000", fill_type="solid")
    fill_yellow = PatternFill(start_color="FFFF00", end_color="FFFF00", fill_type="solid")

    font_header_8 = Font(name='新細明體', size=8, bold=True, color="FFFFFF")
    font_title_8 = Font(name='標楷體', size=10, bold=True)
    font_date_title_8 = Font(name='標楷體', size=10, bold=True)
    font_data_10 = Font(name='新細明體', size=10)
    font_link = Font(name='新細明體', size=10, color="0000FF", underline="single")

    align_header = Alignment(horizontal='center', vertical='center', wrap_text=True)
    align_center = Alignment(horizontal='center', vertical='center')
    align_left = Alignment(horizontal='left', vertical='center')

    thin_border = Border(
        left=Side(style='thin', color='CCCCCC'), right=Side(style='thin', color='CCCCCC'),
        top=Side(style='thin', color='CCCCCC'), bottom=Side(style='thin', color='CCCCCC')
    )

    if '資料中心' in wb.sheetnames:
        ws_data = wb['資料中心']
        ws_data.sheet_view.showGridLines = True
        for col_idx in range(1, ws_data.max_column + 1):
            col_letter = openpyxl.utils.get_column_letter(col_idx)
            ws_data.column_dimensions[col_letter].width = 10
        ws_data.row_dimensions[1].height = 30
        for r in range(1, ws_data.max_row + 1):
            for c in range(1, ws_data.max_column + 1):
                cell = ws_data.cell(row=r, column=c)
                cell.border = thin_border
                if r == 1:
                    cell.font = font_header_8
                    cell.alignment = align_header
                    cell_val_str = str(cell.value) if cell.value else ""
                    if ("差異(%)" in cell_val_str and "持有率" in cell_val_str) or "差異" in cell_val_str:
                        cell.fill = fill_red
                    else:
                        cell.fill = fill_blue
                else:
                    cell.font = font_data_10
                    cell.alignment = align_left if c in [2, 3] else align_center
                    cell.fill = PatternFill(fill_type=None)

    if '大戶增幅前15名' in wb.sheetnames:
        ws_top15 = wb['大戶增幅前15名']
        ws_top15.sheet_view.showGridLines = True
        for col_idx in range(1, ws_top15.max_column + 1):
            col_letter = openpyxl.utils.get_column_letter(col_idx)
            ws_top15.column_dimensions[col_letter].width = 10
        
        ws_top15.merge_cells('A1:D1')
        ws_top15['A1'].value = "大股東(>400張)股權統計"
        ws_top15['A1'].font = font_title_8
        ws_top15['A1'].alignment = align_center
        ws_top15['A1'].border = thin_border
        
        ws_top15.merge_cells('E1:I1')
        ws_top15['E1'].value = f"收盤價日期:{latest_date_str}"
        ws_top15['E1'].font = font_date_title_8
        ws_top15['E1'].alignment = align_center
        for c in range(5, 10):
            cell_top1 = ws_top15.cell(row=1, column=c)
            cell_top1.fill = fill_yellow
            cell_top1.border = thin_border
            
        ws_top15.row_dimensions[1].height = 25
        ws_top15.row_dimensions[2].height = 28

        link_col_idx = 16
        for col in range(1, ws_top15.max_column + 1):
            if ws_top15.cell(row=2, column=col).value == '連結':
                link_col_idx = col
                break
                
        for c in range(1, ws_top15.max_column + 1):
            cell = ws_top15.cell(row=2, column=c)
            cell.font = font_header_8
            cell.alignment = align_header
            cell.border = thin_border
            col_name_str = str(cell.value) if cell.value else ""
            if ("差異(%)" in col_name_str and "持有率" in col_name_str) or col_name_str == "連結" or c == link_col_idx:
                cell.fill = fill_red
            else:
                cell.fill = fill_blue

        for r in range(3, 18):
            for c in range(1, 18):
                cell = ws_top15.cell(row=r, column=c)
                cell.font = font_data_10
                cell.border = thin_border
                cell.alignment = align_left if c in [2, 3] else align_center
                if c == link_col_idx:
                    cell_code = ws_top15.cell(row=r, column=1).value
                    cell_name = ws_top15.cell(row=r, column=2).value
                    if cell_code is not None:
                        cell.value = f'=HYPERLINK("https://norway.twsthr.info/StockHolders.aspx?stock="&A{r}, B{r})'
                        cell.font = font_link

    wb.save(path)

print(f"\n🎉 執行完畢！最新週別：{latest_week_name}，檔案已成功儲存並同步更新！")