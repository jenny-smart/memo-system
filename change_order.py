# change_order.py
# -*- coding: utf-8 -*-
"""
清潔異動模組：車馬費 / 異動服務收款 / 異動服務退款

整體分兩個階段，互相獨立執行：
  階段 A：fetch_and_calc()  → 查訂單 + 試算金額 → 寫入「清潔異動工作表」
  階段 B：sync_pending_rows() → 讀「清潔異動工作表」待處理列 → 回填後台 purchase/edit → 更新 Sheet 狀態

本檔案只負責「清潔異動」這條業務邏輯，網路登入 session、CSRF 處理沿用
memo.py / shift.py / atm.py 既有的共用函式。Google Sheet 連線方式比照
memo.py 用 gspread + Service Account。
"""

import re
import math
from datetime import datetime, date, timedelta

import requests
from bs4 import BeautifulSoup
import gspread
from google.oauth2.service_account import Credentials

try:
    import streamlit as st
except Exception:
    st = None

BASE_URL = "https://backend.lemonclean.com.tw"


# ============================================================
# Google Sheet 連線（比照 memo.py 用 service account）
# ============================================================

# 兩個地區各自的清潔異動工作表（Sheet ID 取自您提供的網址）
SHEET_IDS = {
    "台北": "1bNcJuFuP--jdpNo2zJKOpvuq-5rSHW3LgGE8HEepf44",
    "台中": "1AlsgBL7uAooiU8hb0v-02J2MdBgDVJtGHgvD3U84hCM",
}

# 對應網址列上的 gid，用來精準定位分頁（比用分頁名稱比對更穩，不怕改名）
SHEET_GIDS = {
    "台北": 759897417,
    "台中": 0,
}

_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

_gspread_client = None


def _secret_value(key, default=""):
    if st is None:
        return default
    try:
        return st.secrets.get(key, default)
    except Exception:
        return default


def _get_gspread_client():
    """
    建立（並快取）gspread client。
    服務帳號設定比照 memo.py：優先讀 st.secrets["gcp_service_account"]（TOML 區塊），
    沒有的話再試 st.secrets["GOOGLE_SERVICE_ACCOUNT"]（整包 JSON 字串）。
    若您 memo.py 用的 key 名稱不同，請把下面兩個 _secret_value(...) 的 key 改成一致即可。
    """
    global _gspread_client
    if _gspread_client is not None:
        return _gspread_client

    if st is None:
        raise RuntimeError("找不到 streamlit，無法讀取 st.secrets 取得 Google 憑證")

    sa_info = None

    # 依序嘗試這幾個 key（實際命名以 memo.py 為準：GOOGLE_SERVICE_ACCOUNT 是 TOML 區塊）
    for key in ("GOOGLE_SERVICE_ACCOUNT", "gcp_service_account"):
        try:
            block = st.secrets.get(key, None)
        except Exception:
            block = None

        if not block:
            continue

        if isinstance(block, str):
            # 萬一是整包 JSON 字串
            import json
            sa_info = json.loads(block)
        else:
            # TOML 區塊讀出來是 AttrDict / Mapping，直接轉成一般 dict
            sa_info = dict(block)
        break

    if not sa_info:
        raise RuntimeError(
            "找不到 Google 服務帳號憑證，請確認 secrets.toml 裡有 [GOOGLE_SERVICE_ACCOUNT] "
            "區塊或 GOOGLE_SERVICE_ACCOUNT（JSON 字串），命名請跟 memo.py 現有設定一致"
        )

    creds = Credentials.from_service_account_info(sa_info, scopes=_SCOPES)
    _gspread_client = gspread.authorize(creds)
    return _gspread_client


def get_worksheet(region: str, tab_name: str = "清潔異動"):
    """
    依地區回傳對應的 gspread worksheet 物件。
    優先用 gid（SHEET_GIDS）精準定位分頁；若該地區沒有設定 gid，
    退而用 tab_name 嘗試找同名分頁，最後 fallback 用該試算表第一個分頁。
    """
    if region not in SHEET_IDS:
        raise ValueError(f"不支援的地區：{region}（目前支援：{list(SHEET_IDS.keys())}）")

    client = _get_gspread_client()
    sh = client.open_by_key(SHEET_IDS[region])

    gid = SHEET_GIDS.get(region)
    if gid is not None:
        for ws in sh.worksheets():
            if ws.id == gid:
                return ws

    try:
        return sh.worksheet(tab_name)
    except gspread.exceptions.WorksheetNotFound:
        return sh.get_worksheet(0)


# ============================================================
# 共用：欄位常數（對照清潔異動工作表）
# ============================================================

COL = {
    "A_類別": "A",
    "B_狀態": "B",
    "C_細項": "C",
    "E_登記日期": "E",
    "F_客戶類別": "F",
    "G_訂單編號": "G",
    "H_客人姓名": "H",
    "I_原服務時間": "I",
    "J_備註": "J",
    "M_收款時間": "M",
    "N_收款金額": "N",
    "O_收款發票號碼": "O",
    "P_退款銀行名稱": "P",
    "Q_銀行帳號": "Q",
    "R_付款方式": "R",
    "S_退款金額": "S",
    "T_匯款金額": "T",
    "X_退款訂單發票號碼": "X",
    "Y_二聯三聯": "Y",
    "AA_發票折讓處理時間": "AA",
    "AB_折讓單號碼": "AB",
    "AC_退款時間": "AC",
}

STATUS_PENDING_CHARGE = "待收款"
STATUS_PENDING_REFUND = "待退款"
STATUS_DONE_CHARGE = "已收款"
STATUS_DONE_REFUND = "已退款"

TYPE_FARE = "車馬費發票"
TYPE_CHARGE = "異動服務收款"
TYPE_REFUND = "異動服務退款"


# ============================================================
# 工具函式
# ============================================================

def _parse_period_hours(period_text: str) -> float:
    """ '14:00 - 18:00' -> 4.0 """
    m = re.search(r"(\d{1,2}):(\d{2})\s*-\s*(\d{1,2}):(\d{2})", period_text or "")
    if not m:
        return 0.0
    h1, m1, h2, m2 = map(int, m.groups())
    return round(((h2 * 60 + m2) - (h1 * 60 + m1)) / 60, 2)


def _count_workdays_before(service_date: date, today: date = None) -> int:
    """
    計算「服務日」與「今天」之間相隔的工作天數（不含週六日）。
    當天/已過去 -> 0
    """
    today = today or date.today()
    if service_date <= today:
        return 0
    days = 0
    d = today
    while d < service_date:
        d += timedelta(days=1)
        if d.weekday() < 5:  # 0=Mon ... 4=Fri
            days += 1
    return days


# ============================================================
# 階段 A-1：查訂單基本資料
# ============================================================

def fetch_order_basic(keyword: str, session: requests.Session, ui_logger=None, by="orderNo"):
    """
    依電話或訂單編號查詢 /purchase，回傳該訂單基本資料 dict。
    by: "orderNo" 或 "phone"
    """
    def log(msg):
        if ui_logger:
            ui_logger(msg)

    params = {by: keyword}
    log(f"查詢訂單：{by}={keyword}")

    resp = session.get(f"{BASE_URL}/purchase", params=params, timeout=20)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    row = soup.select_one("table tbody tr")
    if not row:
        log("⚠️ 查無資料")
        return None

    # 訂單編號 + purchase_id
    checkbox = row.select_one('input[name="purchase_id[]"]')
    purchase_id = checkbox["value"] if checkbox else None
    order_no_label = row.select_one("td label")
    order_no = order_no_label.get_text(strip=True).split()[-1] if order_no_label else keyword

    # 客戶姓名
    name_tag = row.select_one('a[href*="/member?keyword"]')
    customer_name = name_tag.get_text(strip=True) if name_tag else ""

    # 服務日期欄（含時段、專員）
    date_cell = row.select("td")[2] if len(row.select("td")) > 2 else None
    date_cell_text = date_cell.get_text("\n", strip=True) if date_cell else ""

    period_match = re.search(r"\d{2}:\d{2}\s*-\s*\d{2}:\d{2}", date_cell_text)
    period_text = period_match.group(0) if period_match else ""

    cleaner_count = len(date_cell.select('a[href*="schedule/edit"]')) if date_cell else 0

    # 付款資訊欄
    pay_cell = row.select("td")[3] if len(row.select("td")) > 3 else None
    pay_cell_text = pay_cell.get_text("\n", strip=True) if pay_cell else ""

    total_match = re.search(r"總金額[：:]\s*([\d,]+)", pay_cell_text)
    total = int(total_match.group(1).replace(",", "")) if total_match else 0

    payway = "儲值金" if "儲值金" in pay_cell_text else "非儲值金"

    invoice_match = re.search(r"發票[：:]\s*([A-Z0-9]+)", pay_cell_text)
    invoice_no = invoice_match.group(1) if invoice_match else ""

    carrier_type = "三聯式" if "統編" in pay_cell_text or "三聯" in pay_cell_text else "二聯式"

    result = {
        "purchase_id": purchase_id,
        "order_no": order_no,
        "customer_name": customer_name,
        "period_text": period_text,
        "service_hours": _parse_period_hours(period_text),
        "cleaner_count": cleaner_count,
        "total": total,
        "payway": payway,           # 儲值金 / 非儲值金
        "invoice_no": invoice_no,
        "carrier_type": carrier_type,  # 二聯式 / 三聯式
        "raw_date_cell": date_cell_text,
    }
    log(f"✅ 查到訂單 {order_no}，總金額 {total}，{cleaner_count} 人，{period_text}")
    return result


# ============================================================
# 階段 A-2：試算金額
# ============================================================

def calc_fare(order: dict) -> int:
    """車馬費 = 專員人數 × $100"""
    return order.get("cleaner_count", 0) * 100


def calc_change_fee(order: dict, service_date: date, change_person: int = None,
                     today: date = None) -> dict:
    """
    依「服務日距今工作天數」+「客戶類別（儲值金/一般）」計算異動費。
    change_person / change_hours：若是儲值金客，異動的人數與時數（若未提供，預設用原訂單人數與時數）
    回傳 dict: {workdays, tier, change_fee, calc_note}
    """
    workdays = _count_workdays_before(service_date, today=today)
    tier = "near" if workdays <= 1 else "far"   # near=服務前1工作天/當天, far=服務前2-3工作天

    if order.get("payway") == "儲值金":
        hours = order.get("service_hours", 0)
        person = change_person or order.get("cleaner_count", 0)
        unit = (hours * person) / 2
        rate = 300 if tier == "near" else 200
        change_fee = round(unit * rate)
        calc_note = f"儲值金客：{hours}小時×{person}人÷2={unit}單位 × ${rate} = ${change_fee}"
    else:
        rate = 0.5 if tier == "near" else 0.3
        change_fee = round(order.get("total", 0) * rate)
        calc_note = f"一般客：總金額{order.get('total', 0)} × {int(rate*100)}% = ${change_fee}"

    return {
        "workdays": workdays,
        "tier": tier,
        "change_fee": change_fee,
        "calc_note": calc_note,
    }


def calc_refund_amount(order: dict, change_fee: int) -> int:
    """應退款 = 原服務總金額 − 異動費"""
    return max(order.get("total", 0) - change_fee, 0)


# ============================================================
# 階段 A-3：組合一筆要寫入 Sheet 的列（三種情境）
# ============================================================

def build_fare_row(order: dict, today: date = None) -> dict:
    """車馬費發票"""
    fare = calc_fare(order)
    return {
        "A": "清潔", "B": "待處理發票", "C": TYPE_FARE,
        "E": (today or date.today()).strftime("%Y/%m/%d"),
        "F": "", "G": order["order_no"], "H": order["customer_name"],
        "I": order.get("period_text", ""), "J": f"車馬費 ${fare}",
        "_calc_amount": fare,
    }


def build_charge_row(order: dict, change_fee_info: dict, service_note: str,
                      customer_type: str = "一般", today: date = None) -> dict:
    """不退服務 → 異動服務收款（待收款）"""
    return {
        "A": "清潔", "B": STATUS_PENDING_CHARGE, "C": TYPE_CHARGE,
        "E": (today or date.today()).strftime("%Y/%m/%d"),
        "F": customer_type, "G": order["order_no"], "H": order["customer_name"],
        "I": order.get("period_text", ""), "J": service_note,
        "M": "", "N": change_fee_info["change_fee"], "O": "",
        "_calc_amount": change_fee_info["change_fee"],
        "_calc_note": change_fee_info["calc_note"],
    }


def build_refund_row(order: dict, change_fee_info: dict, service_note: str,
                      customer_type: str = "一般", today: date = None) -> dict:
    """退服務 → 異動服務退款（待退款），餘額退還"""
    refund_amount = calc_refund_amount(order, change_fee_info["change_fee"])
    return {
        "A": "清潔", "B": STATUS_PENDING_REFUND, "C": TYPE_REFUND,
        "E": (today or date.today()).strftime("%Y/%m/%d"),
        "F": customer_type, "G": order["order_no"], "H": order["customer_name"],
        "I": order.get("period_text", ""),
        "J": f"{service_note}，收異動費 ${change_fee_info['change_fee']} / 退費 ${refund_amount}",
        "R": "信用卡" if order.get("payway") != "儲值金" else "儲值金",
        "S": refund_amount,
        "X": order.get("invoice_no", ""),
        "Y": "三聯" if order.get("carrier_type") == "三聯式" else "二聯",
        "_calc_amount": refund_amount,
        "_calc_note": change_fee_info["calc_note"],
    }


# ============================================================
# 階段 A-4：寫入 Google Sheet
# ============================================================

def append_rows_to_sheet(region: str, rows: list, ui_logger=None):
    """
    把試算好的列（list of dict，欄位用 A/B/C/...）寫入清潔異動工作表最後一列之後。
    呼叫前請先用 ask/dry-run 讓使用者確認過。
    """
    def log(msg):
        if ui_logger:
            ui_logger(msg)

    ws = get_worksheet(region)

    # 不能用 get_all_values() 的列數判斷起始列：
    # 工作表很多空白列掛了資料驗證下拉選單，即使沒選值，
    # Google Sheets 仍可能把那些列算進「有內容」，導致抓到的列數是整個格線上限（例如 922），
    # 而不是實際資料的最後一列。改成只看 B 欄（狀態）實際有值的最後一列。
    b_values = ws.col_values(2)  # B 欄
    last_data_row = len(b_values)
    while last_data_row > 0 and not b_values[last_data_row - 1].strip():
        last_data_row -= 1
    start_row = last_data_row + 1

    col_letters = sorted(set(
        k for row in rows for k in row.keys() if not k.startswith("_")
    ))

    needed_rows = start_row + len(rows) - 1
    if needed_rows > ws.row_count:
        ws.add_rows(needed_rows - ws.row_count)

    written = 0
    errors = []
    for i, row in enumerate(rows):
        target_row = start_row + i
        try:
            for col in col_letters:
                if col in row and row[col] != "":
                    ws.update_acell(f"{col}{target_row}", row[col])
            written += 1
            log(f"✅ 已寫入第 {target_row} 列：{row.get('G', '')}")
        except Exception as e:
            errors.append(f"第 {target_row} 列（{row.get('G','')}）寫入失敗：{e}")

    return {"written": written, "errors": errors, "start_row": start_row}


# ============================================================
# 階段 B：讀取 Sheet 待處理列 → 回填後台
# ============================================================

def get_pending_rows(region: str, ui_logger=None):
    """
    讀取清潔異動工作表，篩出狀態為「待收款」或「待退款」、且金額欄已填的列。
    回傳 list of dict，含 sheet_row（原始列號，回寫用）。
    """
    def log(msg):
        if ui_logger:
            ui_logger(msg)

    ws = get_worksheet(region)
    all_values = ws.get_all_values()
    header = all_values[0]
    col_idx = {h: i for i, h in enumerate(header)}  # 若 header 文字跟欄位對不上，改用固定欄位字母比較保險

    pending = []
    for row_no, row in enumerate(all_values[1:], start=2):
        if len(row) < 2:
            continue
        status = row[1]  # B 欄
        order_no = row[6] if len(row) > 6 else ""  # G 欄
        if not order_no:
            continue

        if status == STATUS_PENDING_CHARGE:
            amount = row[13] if len(row) > 13 else ""  # N 欄
            if amount:
                pending.append({"sheet_row": row_no, "kind": "charge",
                                 "order_no": order_no, "raw": row})
        elif status == STATUS_PENDING_REFUND:
            amount = row[18] if len(row) > 18 else ""  # S 欄
            if amount:
                pending.append({"sheet_row": row_no, "kind": "refund",
                                 "order_no": order_no, "raw": row})

    log(f"掃描到 {len(pending)} 筆待處理（待收款/待退款）資料")
    return pending


def build_purchase_edit_payload(item: dict) -> dict:
    """
    依清潔異動工作表的一列，組成要 POST 到 purchase/edit/{id} 的欄位。
    item["raw"] 是 Sheet 整列原始值（list, index 從 0 對應 A,B,C,...）
    """
    raw = item["raw"]

    def cell(letter):
        idx = ord(letter) - ord("A")
        return raw[idx] if len(raw) > idx else ""

    if item["kind"] == "charge":
        return {
            "isCharge": "1",
            "chargeDate": cell("M") or datetime.now().strftime("%Y-%m-%d"),
            "chargeAmount": cell("N"),
            "chargeInvoice": cell("O"),
            "chargeNote": cell("J"),
        }
    else:  # refund
        return {
            "isRefund": "1",
            "refundDate": cell("AC") or datetime.now().strftime("%Y-%m-%d"),
            "refundAmount": cell("S"),
            "refundNumber": cell("AB"),
            "refundNote": cell("J"),
        }


def sync_one_to_purchase_edit(order_no: str, payload: dict, session: requests.Session,
                               ui_logger=None):
    """
    把 isCharge/isRefund 等欄位 POST 回 purchase/edit/{purchase_id}。
    需要先用訂單編號找到 purchase_id（用 fetch_order_basic 取得）。
    """
    def log(msg):
        if ui_logger:
            ui_logger(msg)

    order = fetch_order_basic(order_no, session=session, ui_logger=ui_logger, by="orderNo")
    if not order or not order.get("purchase_id"):
        raise RuntimeError(f"找不到訂單 {order_no} 對應的 purchase_id")

    purchase_id = order["purchase_id"]
    edit_url = f"{BASE_URL}/purchase/edit/{purchase_id}"

    # 取得編輯頁，拿出原本所有欄位值 + CSRF token，原樣帶回去（避免覆蓋掉沒提到的欄位）
    resp = session.get(edit_url, timeout=20)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    token_input = soup.select_one('input[name="_token"]')
    token = token_input["value"] if token_input else ""

    form_data = {}
    for inp in soup.select("form input[name]"):
        name = inp.get("name")
        if name in ("_token",):
            continue
        form_data[name] = inp.get("value", "")
    for ta in soup.select("form textarea[name]"):
        form_data[ta.get("name")] = ta.get_text()
    for sel in soup.select("form select[name]"):
        chosen = sel.select_one("option[selected]")
        form_data[sel.get("name")] = chosen["value"] if chosen else ""

    form_data.update(payload)
    form_data["_token"] = token

    log(f"回填 {order_no}（purchase_id={purchase_id}）：{payload}")
    post_resp = session.post(edit_url, data=form_data, timeout=20)
    post_resp.raise_for_status()
    log(f"✅ {order_no} 回填完成")
    return True


def mark_sheet_row_done(region: str, sheet_row: int, kind: str, ui_logger=None):
    """回填成功後，把 Sheet 該列狀態改為「已收款」/「已退款」，並標記處理時間，避免重複處理"""
    def log(msg):
        if ui_logger:
            ui_logger(msg)

    ws = get_worksheet(region)
    new_status = STATUS_DONE_CHARGE if kind == "charge" else STATUS_DONE_REFUND
    ws.update_acell(f"B{sheet_row}", new_status)
    # 用 K 欄或額外一欄記錄系統回填時間，避免重複跑到同一筆
    ws.update_acell(f"AD{sheet_row}", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    log(f"✅ Sheet 第 {sheet_row} 列已標記為「{new_status}」")


# ============================================================
# 階段 B 主流程
# ============================================================

def sync_pending_rows(region: str, selected_rows: list, session: requests.Session,
                       ui_logger=None):
    """
    selected_rows: get_pending_rows() 回傳結果中，使用者勾選要執行的項目
    """
    def log(msg):
        if ui_logger:
            ui_logger(msg)

    result = {"processed": 0, "success": 0, "failed": 0, "errors": []}

    for item in selected_rows:
        result["processed"] += 1
        try:
            payload = build_purchase_edit_payload(item)
            sync_one_to_purchase_edit(item["order_no"], payload, session=session, ui_logger=ui_logger)
            mark_sheet_row_done(region, item["sheet_row"], item["kind"], ui_logger=ui_logger)
            result["success"] += 1
        except Exception as e:
            result["failed"] += 1
            result["errors"].append(f"{item['order_no']}：{e}")
            log(f"❌ {item['order_no']} 失敗：{e}")

    return result
