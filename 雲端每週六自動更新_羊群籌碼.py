from datetime import datetime
import json
import os
from pathlib import Path
import re
import pandas as pd
from playwright.sync_api import sync_playwright

目前資料夾 = Path(__file__).resolve().parent
集保查詢網址 = "https://www.tdcc.com.tw/portal/zh/smWeb/qryStock"

候選快取清單 = [
    目前資料夾 / "羊群籌碼_219檔.jsonl",
    目前資料夾 / "資料" / "羊群籌碼_219檔.jsonl",
    目前資料夾 / "data" / "羊群籌碼_219檔.jsonl",
]
輸出快取檔 = 目前資料夾 / "羊群籌碼_219檔.jsonl"
輸出訊號檔 = 目前資料夾 / "自選股_羊群籌碼_最新訊號.csv"
最多保留週數 = 104


def 現在時間() -> str:
    return datetime.now().strftime("%H:%M:%S")


def 是否有效比例(大戶值, 散戶值) -> bool:
    """持股比例必須在 0~100% 之間，且兩者合計不超過 100.5%；超過即視為異常/改過數值"""
    if 大戶值 is None or 散戶值 is None:
        return False
    if not (0.0 <= 大戶值 <= 100.0) or not (0.0 <= 散戶值 <= 100.0):
        return False
    if (大戶值 + 散戶值) > 100.5:
        return False
    return True


def 判斷持股級距張數(級距文字: str):
    """集保表格以「股」為單位，除以 1000 換算成「張」"""
    文字 = 級距文字.replace(",", "").replace(" ", "").strip()
    if "合計" in 文字 or "總計" in 文字 or "差異數" in 文字:
        return True, 0.0, 0.0

    數字清單 = [float(x) for x in re.findall(r"\d+(?:\.\d+)?", 文字)]
    if not 數字清單:
        return False, 0.0, 0.0

    if len(數字清單) >= 2:
        return False, 數字清單[0] / 1000.0, 數字清單[1] / 1000.0

    單一數值張 = 數字清單[0] / 1000.0
    if "以上" in 文字:
        return False, 單一數值張, 999999.0
    return False, 0.0, 單一數值張


def 抓取單一期別(網頁, 股票代號: str, 期別代碼: str):
    網頁.locator("select").first.select_option(期別代碼, timeout=15000)
    網頁.locator("input[type='text']").first.fill(股票代號, timeout=15000)
    網頁.locator(
        "button:has-text('查詢'), input[type='submit'][value*='查詢']"
    ).first.click(no_wait_after=True, timeout=15000)
    網頁.wait_for_timeout(800)

    大戶比例合計 = 0.0
    散戶比例合計 = 0.0
    有抓到資料 = False

    表格列 = 網頁.locator("table tr")
    for i in range(表格列.count()):
        欄位文字 = [
            c.strip() for c in 表格列.nth(i).locator("th, td").all_inner_texts()
        ]
        if len(欄位文字) < 4:
            continue

        級距欄 = ""
        for 欄 in 欄位文字[:3]:
            if any(k in 欄 for k in ["-", "~", "以上", "合計", "總計", "差異數"]) or (
                re.search(r"\d{3,}", 欄.replace(",", ""))
            ):
                級距欄 = 欄
                break
        if not 級距欄:
            continue

        是否合計, 最小張, 最大張 = 判斷持股級距張數(級距欄)
        if 是否合計:
            continue

        比例數值 = None
        for 欄 in reversed(欄位文字):
            比對 = re.search(r"(-?\d+(?:\.\d+)?)\s*%?", 欄.replace(",", ""))
            if 比對:
                候選值 = float(比對.group(1))
                if 0.0 <= 候選值 <= 100.0:
                    比例數值 = 候選值
                    break
        if 比例數值 is None:
            continue

        if 最小張 >= 400.0:
            大戶比例合計 += 比例數值
            有抓到資料 = True
        elif 最大張 <= 100.0:
            散戶比例合計 += 比例數值
            有抓到資料 = True

    大戶四捨五入 = round(大戶比例合計, 2)
    散戶四捨五入 = round(散戶比例合計, 2)
    日期解析 = pd.to_datetime(
        re.sub(r"[^\d]", "", str(期別代碼)), format="%Y%m%d", errors="coerce"
    )

    if (
        有抓到資料
        and pd.notna(日期解析)
        and (大戶四捨五入 > 0.0 or 散戶四捨五入 > 0.0)
        and 是否有效比例(大戶四捨五入, 散戶四捨五入)
    ):
        return {
            "date": 日期解析.strftime("%Y/%m/%d"),
            "big": 大戶四捨五入,
            "retail": 散戶四捨五入,
        }
    return None


def 取得週資料清單(股票紀錄: dict) -> list[dict]:
    for 欄位名 in ["tdcc_series", "weeks", "data", "history"]:
        值 = 股票紀錄.get(欄位名)
        if isinstance(值, list) and len(值) > 0:
            return 值
    return []


def 計算交叉與變動(週資料清單: list[dict]):
    if not 週資料清單:
        return "無資料", None, None, None, None, ""

    日期欄位 = next(
        (
            k
            for k in ["date", "日期", "週別", "week"]
            if isinstance(週資料清單[0], dict) and k in 週資料清單[0]
        ),
        None,
    )
    已排序週資料 = (
        sorted(週資料清單, key=lambda x: str(x.get(日期欄位, "")))
        if 日期欄位
        else list(週資料清單)
    )

    def 取數值(單週資料: dict, 候選鍵: list[str]):
        for 鍵 in 候選鍵:
            if (
                鍵 in 單週資料
                and 單週資料[鍵] is not None
                and str(單週資料[鍵]).strip() != ""
            ):
                try:
                    return float(單週資料[鍵])
                except (ValueError, TypeError):
                    pass
        return None

    合法紀錄 = []
    for 單週 in 已排序週資料:
        if not isinstance(單週, dict):
            continue
        m_val = 取數值(單週, ["big", "大戶%", "major_pct", "big_pct"])
        r_val = 取數值(單週, ["retail", "散戶%", "retail_pct", "small_pct", "羊群%"])
        if 是否有效比例(m_val, r_val):
            dt_str = str(單週.get(日期欄位, "")) if 日期欄位 else ""
            合法紀錄.append((dt_str, round(float(m_val), 2), round(float(r_val), 2)))

    if not 合法紀錄:
        return "無資料", None, None, None, None, ""

    最新日期 = 合法紀錄[-1][0]
    大戶序列 = [x[1] for x in 合法紀錄]
    散戶序列 = [x[2] for x in 合法紀錄]

    最新大戶 = 大戶序列[-1]
    最新散戶 = 散戶序列[-1]
    近1週變動 = round(最新大戶 - 大戶序列[-2], 2) if len(大戶序列) >= 2 else None
    近4週變動 = round(最新大戶 - 大戶序列[-5], 2) if len(大戶序列) >= 5 else None

    訊號 = "大戶領先" if 最新大戶 > 最新散戶 else "散戶領先"
    if len(大戶序列) >= 2 and len(散戶序列) >= 2:
        前週大戶 = 大戶序列[-2]
        前週散戶 = 散戶序列[-2]
        if 前週大戶 <= 前週散戶 and 最新大戶 > 最新散戶:
            訊號 = "黃金交叉"
        elif 前週大戶 >= 前週散戶 and 最新大戶 < 最新散戶:
            訊號 = "死亡交叉"

    return 訊號, 最新大戶, 最新散戶, 近1週變動, 近4週變動, 最新日期


def 執行雲端更新():
    來源快取檔 = next((p for p in 候選快取清單 if p.exists()), None)
    if 來源快取檔 is None:
        raise FileNotFoundError(
            "雲端找不到「羊群籌碼_219檔.jsonl」，請確認檔案已上傳到雲端專案資料夾。"
        )

    所有股票紀錄: list[dict] = []
    with 來源快取檔.open("r", encoding="utf-8") as f:
        for 行內容 in f:
            文字 = 行內容.strip()
            if 文字:
                所有股票紀錄.append(json.loads(文字))

    print(
        f"[{現在時間()}] 已載入 {len(所有股票紀錄)} 檔紀錄（來源：{來源快取檔.name}）"
    )

    try:
        with sync_playwright() as p:
            瀏覽器 = p.chromium.launch(headless=True)
            網頁 = 瀏覽器.new_page()
            網頁.set_default_timeout(20000)
            網頁.goto(集保查詢網址, wait_until="domcontentloaded", timeout=60000)
            網頁.wait_for_timeout(1200)

            期別選項 = 網頁.eval_on_selector_all(
                "select option",
                "opts => opts.map(o => o.value).filter(v => v && v.trim() !== '')",
            )
            最新兩期 = 期別選項[:2] if 期別選項 else []

            已更新檔數 = 0
            for 序號, 紀錄 in enumerate(所有股票紀錄, start=1):
                代號 = str(紀錄.get("stock_id") or 紀錄.get("代號") or "").strip()
                if not 代號:
                    continue

                既有週資料 = 取得週資料清單(紀錄)
                日期對應表 = {
                    str(項目.get("date")): 項目
                    for 項目 in 既有週資料
                    if isinstance(項目, dict) and 項目.get("date")
                }

                有新增期別 = False
                for 期別代碼 in 最新兩期:
                    日期解析 = pd.to_datetime(
                        re.sub(r"[^\d]", "", str(期別代碼)),
                        format="%Y%m%d",
                        errors="coerce",
                    )
                    if pd.isna(日期解析):
                        continue
                    日期字串 = 日期解析.strftime("%Y/%m/%d")
                    if 日期字串 not in 日期對應表:
                        新資料 = 抓取單一期別(網頁, 代號, 期別代碼)
                        if 新資料:
                            日期對應表[新資料["date"]] = 新資料
                            有新增期別 = True

                if 有新增期別:
                    已排序日期鍵 = sorted(日期對應表.keys())[-最多保留週數:]
                    紀錄["tdcc_series"] = [日期對應表[k] for k in 已排序日期鍵]
                    紀錄["update_date"] = datetime.today().strftime("%Y-%m-%d")
                    已更新檔數 += 1

                if 序號 % 25 == 0:
                    瀏覽器.close()
                    瀏覽器 = p.chromium.launch(headless=True)
                    網頁 = 瀏覽器.new_page()
                    網頁.set_default_timeout(20000)
                    網頁.goto(
                        集保查詢網址, wait_until="domcontentloaded", timeout=60000
                    )
                    網頁.wait_for_timeout(1000)

            瀏覽器.close()
            print(f"[{現在時間()}] 本次新增更新 {已更新檔數} 檔最新集保期別。")
    except Exception as 錯誤:
        print(
            f"[{現在時間()}] 雲端連線集保略過／發生狀況（將以現有快取產出 CSV）：{錯誤}"
        )

    # 回寫更新後的 219 檔快取：只剔除超過 100% 或小於 0% 的異常週次，保留正常歷史趨勢線
    暫存快取檔 = 輸出快取檔.with_suffix(".jsonl.tmp")
    with 暫存快取檔.open("w", encoding="utf-8") as 寫出檔:
        for 紀錄 in 所有股票紀錄:
            既有週次 = 取得週資料清單(紀錄)
            乾淨週次 = []
            for 單週 in 既有週次:
                if not isinstance(單週, dict):
                    continue
                try:
                    大戶值 = float(單週.get("big"))
                    散戶值 = float(單週.get("retail"))
                except (TypeError, ValueError):
                    continue
                if 是否有效比例(大戶值, 散戶值):
                    新單週 = dict(單週)
                    新單週["big"] = round(大戶值, 2)
                    新單週["retail"] = round(散戶值, 2)
                    乾淨週次.append(新單週)

            if 乾淨週次:
                乾淨週次 = sorted(乾淨週次, key=lambda x: str(x.get("date", "")))[-最多保留週數:]
                紀錄["tdcc_series"] = 乾淨週次

            寫出檔.write(json.dumps(紀錄, ensure_ascii=False) + "\n")
    os.replace(暫存快取檔, 輸出快取檔)

    彙整列清單 = []
    已剔除異常檔數 = 0
    for 紀錄 in 所有股票紀錄:
        代號 = str(紀錄.get("stock_id") or 紀錄.get("代號") or "").strip()
        名稱 = str(紀錄.get("name") or 紀錄.get("名稱") or "").strip()
        週資料 = 取得週資料清單(紀錄)
        訊號, 最新大戶, 最新散戶, 近1週變動, 近4週變動, 最新日期 = (
            計算交叉與變動(週資料)
        )
        if 訊號 == "無資料" and 週資料:
            已剔除異常檔數 += 1
        彙整列清單.append({
            "代號": 代號,
            "名稱": 名稱,
            "最新日期": 最新日期,
            "訊號": 訊號,
            "最新大戶%": 最新大戶,
            "最新散戶%": 最新散戶,
            "近1週大戶變動": 近1週變動,
            "近4週大戶變動": 近4週變動,
        })

    訊號表格 = pd.DataFrame(彙整列清單)
    訊號表格.to_csv(輸出訊號檔, index=False, encoding="utf-8-sig")
    print(
        f"[{現在時間()}] 已產生「{輸出訊號檔.name}」，共 {len(訊號表格)} 檔資料（含異常數值剔除 {已剔除異常檔數} 檔）。"
    )


if __name__ == "__main__":
    執行雲端更新()