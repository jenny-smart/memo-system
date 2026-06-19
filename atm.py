# atm.py
# -*- coding: utf-8 -*-
"""
ATM 對帳自動化模組

流程：
1. 從台北/台中 ATM Google Sheet（分頁名稱固定為「ATM」）讀取要處理的列號，取得 J 欄（訂單編號）
2. 用訂單編號去 https://backend.lemonclean.com.tw/purchase 搜尋，
   從頁面內嵌的 Vue purchaseList JSON 拿到該筆訂單的 purchase_id / 付款狀態等資訊
3. 依序執行：
   - 按「已付款」：GET /purchase/set_success/{purchase_id}
   - 按「開立發票」：GET /purchase/make_invoice/{purchase_id}
   - 按「發確認信」：GET /purchase/mail_success/{order_no}
4. 動作後重新查詢一次該筆訂單，把最新的「付款時間」「發票號碼」寫回 ATM Sheet 的 P/Q 欄，
   並把 R 欄填上「已發送」

⚠️ 這三個後台動作都是「點了就送出」，沒有像 shift 那樣的 dry-run 預覽機制
（因為它們本身就是簡單的 GET 觸發，沒有複雜的合併邏輯）。
所以這支模組會在處理「每一列」之前都先記錄完整 log，方便事後追查，
但無法在送出前讓你逐筆確認——這點麻煩你知悉。
"""
import json
import re
from typing import Dict, List, Optional, Callable

import gspread
from google.oauth2.service_account import Credentials

import memo


# -----------------------------------------------------------------------------
# Config
# -----------------------------------------------------------------------------
ATM_SHEET_IDS = {
    "台北": "1bNcJuFuP--jdpNo2zJKOpvuq-5rSHW3LgGE8HEepf44",
    "台中": "1AlsgBL7uAooiU8hb0v-02J2MdBgDVJtGHgvD3U84hCM",
}

# 兩份 ATM Sheet 實際要處理的分頁名稱都是「ATM」
ATM_WORKSHEET_TITLE = "ATM"

# 欄位位置（1-based）：J=10, P=16, Q=17, R=18
COL_ORDER_NO = 10
COL_PAID_AT = 16
COL_INVOICE_NO = 17
COL_MAIL_STATUS = 18


def make_logger(ui_logger: Optional[Callable[[str], None]] = None):
    def _log(msg: str):
        msg = str(msg)
        print(msg, flush=True)
        if ui_logger:
            ui_logger(msg)
    return _log


# -----------------------------------------------------------------------------
# Google Sheet
# -----------------------------------------------------------------------------
def get_atm_spreadsheet(sheet_id: str):
    """
    跟 memo.get_spreadsheet() 邏輯一樣，但這裡是給「另一份」ATM Sheet 用，
    不是 memo.py 主程式自己的 SHEET_ID。
    """
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    try:
        creds = Credentials.from_service_account_info(
            dict(memo.st.secrets["GOOGLE_SERVICE_ACCOUNT"]),
            scopes=scopes,
        )
        gc = gspread.authorize(creds)
        return gc.open_by_key(sheet_id)
    except Exception:
        pass

    creds = Credentials.from_service_account_file(
        memo.GOOGLE_SERVICE_ACCOUNT_FILE,
        scopes=scopes,
    )
    gc = gspread.authorize(creds)
    return gc.open_by_key(sheet_id)


def get_atm_worksheet(region: str):
    """
    region: "台北" 或 "台中"
    固定抓分頁名稱「ATM」（台北、台中兩份 Sheet 的分頁名稱都一樣）。
    """
    if region not in ATM_SHEET_IDS:
        raise ValueError(f"未知地區「{region}」，目前支援：{list(ATM_SHEET_IDS.keys())}")

    sh = get_atm_spreadsheet(ATM_SHEET_IDS[region])
    return sh.worksheet(ATM_WORKSHEET_TITLE)


# -----------------------------------------------------------------------------
# 解析 /purchase 頁面內嵌的 Vue purchaseList JSON
# -----------------------------------------------------------------------------
def extract_purchase_list_json(html: str) -> Optional[Dict]:
    """
    從 /purchase 頁面原始碼裡，挖出 Vue data() 裡的 purchaseList JSON 物件
    （比硬解 HTML 表格準確、也比較不容易因排版改版而壞掉）。
    """
    idx = html.find("purchaseList:")
    if idx == -1:
        return None

    start = html.find("{", idx)
    if start == -1:
        return None

    depth = 0
    in_str = False
    esc = False
    i = start

    while i < len(html):
        c = html[i]
        if in_str:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = False
        else:
            if c == '"':
                in_str = True
            elif c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    raw = html[start:i + 1]
                    try:
                        return json.loads(raw)
                    except Exception:
                        return None
        i += 1

    return None


def find_purchase_by_order_no(session, order_no: str) -> Optional[Dict]:
    """
    用訂單編號搜尋 /purchase，回傳該筆訂單的完整資料 dict
    （含 purchase_id, order_no, paid_at, invoice_no, purchase_status 等）。
    找不到回傳 None。
    """
    url = f"{memo.BASE_URL}/purchase"
    r = memo.session_get(session, url, params={"orderNo": order_no})
    r.raise_for_status()

    data = extract_purchase_list_json(r.text)
    if not data:
        return None

    for item in data.get("data", []):
        if str(item.get("order_no", "")).strip() == str(order_no).strip():
            return item

    # 找不到完全相符的，退而求其次回傳第一筆（萬一訂單編號格式有些微差異）
    items = data.get("data", [])
    return items[0] if items else None


# -----------------------------------------------------------------------------
# 三個後台動作
# -----------------------------------------------------------------------------
def mark_paid(session, purchase_id) -> bool:
    url = f"{memo.BASE_URL}/purchase/set_success/{purchase_id}"
    r = memo.session_get(session, url)
    r.raise_for_status()
    return True


def issue_invoice(session, purchase_id) -> bool:
    url = f"{memo.BASE_URL}/purchase/make_invoice/{purchase_id}"
    r = memo.session_get(session, url)
    r.raise_for_status()
    return True


def send_confirmation_mail(session, order_no: str) -> Dict:
    """
    回傳後端回應的 JSON：{"orderNo":..., "dateClean":..., "period":...}
    """
    url = f"{memo.BASE_URL}/purchase/mail_success/{order_no}"
    r = memo.session_get(session, url)
    r.raise_for_status()
    try:
        return r.json()
    except Exception:
        return {}


# -----------------------------------------------------------------------------
# 主流程
# -----------------------------------------------------------------------------
def process_atm_rows(
    region: str,
    row_spec: str,
    do_mark_paid: bool = True,
    do_issue_invoice: bool = True,
    do_send_mail: bool = True,
    ui_logger=None,
) -> Dict:
    """
    region: "台北" 或 "台中"
    row_spec: 跟 memo.parse_row_spec 一樣的格式，例如 "241,243,246-248"
    do_mark_paid / do_issue_invoice / do_send_mail: 各自開關，方便你只想做某幾步
    """
    log = make_logger(ui_logger)
    result = {
        "processed": 0,
        "success": 0,
        "failed": 0,
        "skipped": 0,
        "errors": [],
    }

    row_nums = memo.parse_row_spec(row_spec)
    log(f"===== 開始處理 ATM 對帳（{region}）=====")
    log(f"列號：{row_nums}")

    ws = get_atm_worksheet(region)
    rows = memo.with_retry(ws.get_all_values)

    session = memo.login(ui_logger=ui_logger)

    for r in row_nums:
        try:
            if r - 1 >= len(rows):
                log(f"❌ 第{r}列：超出資料範圍")
                result["failed"] += 1
                result["errors"].append(f"第{r}列：超出資料範圍")
                continue

            row = rows[r - 1]
            order_no = memo.safe_cell(row, COL_ORDER_NO)

            if not order_no:
                log(f"⏭ 第{r}列：J欄沒有訂單編號，略過")
                result["skipped"] += 1
                continue

            log(f"\n----- 第{r}列：訂單 {order_no} -----")

            purchase = find_purchase_by_order_no(session, order_no)
            if not purchase:
                msg = f"❌ 第{r}列（{order_no}）：在後台找不到這筆訂單"
                log(msg)
                result["failed"] += 1
                result["errors"].append(msg)
                continue

            purchase_id = purchase.get("purchase_id")
            log(f"找到 purchase_id={purchase_id}")

            updates = []  # [(col, value), ...]

            if do_mark_paid:
                if purchase.get("purchase_status") == 1:
                    log("（已經是已付款狀態，略過按已付款）")
                else:
                    mark_paid(session, purchase_id)
                    log("✅ 已按下「已付款」")

            if do_issue_invoice:
                if purchase.get("invoice_no"):
                    log(f"（已有發票號碼 {purchase['invoice_no']}，略過開立發票）")
                else:
                    issue_invoice(session, purchase_id)
                    log("✅ 已按下「開立發票」")

            if do_send_mail:
                mail_resp = send_confirmation_mail(session, order_no)
                log(f"✅ 已發確認信，回應：{mail_resp}")

            # 動作後重新查一次最新狀態，把付款時間/發票號碼寫回表
            if do_mark_paid or do_issue_invoice:
                purchase = find_purchase_by_order_no(session, order_no) or purchase

            paid_at = purchase.get("paid_at") or ""
            invoice_no = purchase.get("invoice_no") or ""

            if do_mark_paid and paid_at:
                updates.append((COL_PAID_AT, paid_at))
            if do_issue_invoice and invoice_no:
                updates.append((COL_INVOICE_NO, invoice_no))
            if do_send_mail:
                updates.append((COL_MAIL_STATUS, "已發送"))

            for col, value in updates:
                memo.with_retry(ws.update_cell, r, col, value)
                log(f"已寫回第{r}列 第{col}欄 = {value}")

            result["processed"] += 1
            result["success"] += 1

        except Exception as e:
            msg = f"❌ 第{r}列 失敗：{e}"
            log(msg)
            result["processed"] += 1
            result["failed"] += 1
            result["errors"].append(msg)

    log("\n===== ATM 對帳處理完成 =====")
    return result
