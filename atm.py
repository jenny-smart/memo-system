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
4. 動作後重新查詢一次該筆訂單，把 P=對帳完成時間、Q=付款時間、R=發票號碼、S=發確認信、T=已更新系統 寫回 ATM Sheet

⚠️ 這三個後台動作都是「點了就送出」，沒有像 shift 那樣的 dry-run 預覽機制
（因為它們本身就是簡單的 GET 觸發，沒有複雜的合併邏輯）。
所以這支模組會在處理「每一列」之前都先記錄完整 log，方便事後追查，
但無法在送出前讓你逐筆確認——這點麻煩你知悉。
"""
import json
import re
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Dict, List, Optional, Callable
from difflib import SequenceMatcher

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

# 欄位位置（1-based）：J=10, P=16, Q=17, R=18, S=19, T=20
COL_ORDER_NO = 10
COL_RECONCILED_AT = 16  # P 對帳完成時間
COL_PAID_AT = 17        # Q 付款時間
COL_INVOICE_NO = 18     # R 發票號碼
COL_MAIL_STATUS = 19    # S 發確認信
COL_RECON_STATUS = 20   # T 對帳狀態


def make_logger(ui_logger: Optional[Callable[[str], None]] = None):
    def _log(msg: str):
        msg = str(msg)
        print(msg, flush=True)
        if ui_logger:
            ui_logger(msg)
    return _log


def _now_text() -> str:
    return datetime.now(ZoneInfo("Asia/Taipei")).strftime("%Y/%m/%d %H:%M:%S")


def _clear_data_validation(ws, row: int, col_start: int, col_end: int):
    """
    清除指定列、指定欄位範圍的資料驗證（下拉選單）。
    col_start / col_end are 1-based and inclusive.
    """
    try:
        sheet_id = ws.id
        body = {
            "requests": [
                {
                    "repeatCell": {
                        "range": {
                            "sheetId": sheet_id,
                            "startRowIndex": row - 1,
                            "endRowIndex": row,
                            "startColumnIndex": col_start - 1,
                            "endColumnIndex": col_end,
                        },
                        "cell": {"dataValidation": None},
                        "fields": "dataValidation",
                    }
                }
            ]
        }
        memo.with_retry(ws.spreadsheet.batch_update, body)
    except Exception:
        # 清除下拉選單失敗時不阻斷主流程，後續 update 若失敗會回報原錯誤。
        pass


def _copy_data_validation(ws, source_row: int, target_row: int, columns: List[int]):
    """
    將指定欄位的資料驗證（下拉選單）從 source_row 複製到 target_row。
    只複製 data validation，不複製值或格式。
    """
    if not source_row or not target_row or source_row == target_row:
        return
    try:
        sheet_id = ws.id
        requests = []
        for col in columns:
            requests.append({
                "copyPaste": {
                    "source": {
                        "sheetId": sheet_id,
                        "startRowIndex": source_row - 1,
                        "endRowIndex": source_row,
                        "startColumnIndex": col - 1,
                        "endColumnIndex": col,
                    },
                    "destination": {
                        "sheetId": sheet_id,
                        "startRowIndex": target_row - 1,
                        "endRowIndex": target_row,
                        "startColumnIndex": col - 1,
                        "endColumnIndex": col,
                    },
                    "pasteType": "PASTE_DATA_VALIDATION",
                    "pasteOrientation": "NORMAL",
                }
            })
        if requests:
            memo.with_retry(ws.spreadsheet.batch_update, {"requests": requests})
    except Exception:
        # 複製下拉選單失敗時不阻斷配對；值仍會正常寫入。
        pass


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
    session=None,
) -> Dict:
    """
    region: "台北" 或 "台中"
    row_spec: 跟 memo.parse_row_spec 一樣的格式，例如 "241,243,246-248"
    do_mark_paid / do_issue_invoice / do_send_mail: 各自開關，方便你只想做某幾步
    session: 可選，傳入已登入的 session 就重用，不傳則自己登入一次
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

    session = session or memo.login(ui_logger=ui_logger)

    for r in row_nums:
        try:
            if r - 1 >= len(rows):
                log(f"❌ 第{r}列：超出資料範圍")
                result["failed"] += 1
                result["errors"].append(f"第{r}列：超出資料範圍")
                continue

            row = rows[r - 1]
            order_no = memo.safe_cell(row, COL_ORDER_NO)
            recon_status = memo.safe_cell(row, COL_RECON_STATUS)

            if not order_no:
                log(f"⏭ 第{r}列：J欄沒有訂單編號，可能是非訂單收入，略過系統更新")
                result["skipped"] += 1
                continue

            if str(recon_status).strip() in ["需確認", "非訂單", "非訂單收入", "疑似拆單"]:
                log(f"⏭ 第{r}列：T欄狀態為「{recon_status}」，不執行系統更新")
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

            updates.append((COL_RECONCILED_AT, _now_text()))
            updates.append((COL_RECONCILED_AT, _now_text()))
            if do_mark_paid and paid_at:
                updates.append((COL_PAID_AT, paid_at))
            if do_issue_invoice and invoice_no:
                updates.append((COL_INVOICE_NO, invoice_no))
            if do_send_mail:
                updates.append((COL_MAIL_STATUS, "已發送"))
            updates.append((COL_RECON_STATUS, "已更新系統"))
            updates.append((COL_RECON_STATUS, "已更新系統"))

            # P:T 會寫入時間、發票號碼、狀態；若原本是下拉選單，先清除資料驗證。
            _clear_data_validation(ws, r, COL_RECONCILED_AT, COL_RECON_STATUS)

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




# -----------------------------------------------------------------------------
# ATM Sheet 自動配對：銀行明細 A-F ↔ 待付款清單 I-M
# -----------------------------------------------------------------------------
def _to_int_amount(value) -> Optional[int]:
    """把 Sheet 金額（可能含逗號、$、空白）轉成整數；不能轉回傳 None。"""
    s = str(value or "").strip()
    if not s:
        return None
    s = re.sub(r"[^0-9\-]", "", s)
    if not s or s == "-":
        return None
    try:
        return int(s)
    except Exception:
        return None


def _digits(value: str) -> str:
    return re.sub(r"\D", "", str(value or ""))


def _norm_code(value: str) -> str:
    """末碼比對用：去掉非數字與前導 0，但保留全 0 的情境。"""
    d = _digits(value)
    return d.lstrip("0") or ("0" if d else "")


def _bank_note_has_code(bank_note: str, customer_code: str) -> bool:
    """
    判斷銀行備註是否可能包含客人回報的後五碼。
    實務上 M 欄常會因前導 0 被 Sheet 吃掉，所以用 suffix/去前導 0 的方式放寬。
    """
    note_digits = _digits(bank_note)
    code_digits = _digits(customer_code)
    if not note_digits or not code_digits:
        return False

    note_norm = _norm_code(note_digits)
    code_norm = _norm_code(code_digits)
    last5_norm = _norm_code(note_digits[-5:])
    last4_norm = _norm_code(note_digits[-4:])

    return (
        note_digits.endswith(code_digits)
        or note_norm.endswith(code_norm)
        or last5_norm == code_norm
        or last4_norm == code_norm
    )


def _note_matches_name(bank_note: str, customer_name: str) -> bool:
    """客人有填匯款備註時，銀行備註通常是姓名或短文字。"""
    note = str(bank_note or "").strip()
    name = str(customer_name or "").strip()
    if not note or not name:
        return False
    note_compact = re.sub(r"\s+", "", note)
    name_compact = re.sub(r"\s+", "", name)
    if not note_compact or not name_compact:
        return False
    return note_compact in name_compact or name_compact in note_compact


def _compact_text(value: str) -> str:
    """模糊比對用：移除空白與常見符號，只保留中英文數字。"""
    return re.sub(r"[^0-9A-Za-z\u4e00-\u9fff]", "", str(value or "")).lower()


def _similar_text(a: str, b: str, threshold: float = 0.72) -> bool:
    """F 欄備註與 K 欄姓名相近時，列為需確認候選。"""
    aa = _compact_text(a)
    bb = _compact_text(b)
    if not aa or not bb:
        return False
    if aa in bb or bb in aa:
        return True
    return SequenceMatcher(None, aa, bb).ratio() >= threshold


def _normalize_datetime_text(value: str) -> str:
    """把日期時間字串正規化成純數字，例如 2026/06/18 12:14:00 -> 20260618121400。"""
    return re.sub(r"\D", "", str(value or ""))


def _datetime_equals(a: str, b: str) -> bool:
    """M 欄若是日期+時間，且等於 B 欄交易時間，列為需確認候選。"""
    aa = _normalize_datetime_text(a)
    bb = _normalize_datetime_text(b)
    if not aa or not bb:
        return False
    # 允許秒數缺漏，因此用較短長度比對，但至少要到分鐘 YYYYMMDDHHMM。
    n = min(len(aa), len(bb))
    if n < 12:
        return False
    return aa[:n] == bb[:n]


def _build_confirm_code(candidate: Dict) -> str:
    """需確認候選寫到 M 欄的提示；若原 M 有值就保留，沒有就標示需確認。"""
    raw = str(candidate.get("last_code") or "").strip()
    return raw if raw else "需確認"


def _is_non_order_candidate(candidate: Dict) -> bool:
    """J 欄空白但有姓名/金額/類別時，視為非訂單收入。"""
    order_no = str(candidate.get("order_no") or "").strip()
    name = str(candidate.get("name") or "").strip()
    amount = candidate.get("amount")
    service_type = str(candidate.get("service_type") or "").strip()
    fee_type = str(candidate.get("fee_type") or "").strip()
    return (not order_no) and bool(name) and amount is not None and bool(service_type or fee_type)


def _is_split_payment_candidate(income: int, candidate: Dict, note: str) -> bool:
    """客人分筆匯款：入帳金額小於候選金額，且姓名或末碼能對上。"""
    amount = candidate.get("amount")
    if amount is None or income is None:
        return False
    try:
        if int(income) >= int(amount):
            return False
    except Exception:
        return False
    if candidate.get("last_code") and _bank_note_has_code(note, candidate.get("last_code")):
        return True
    if _note_matches_name(note, candidate.get("name")) or _similar_text(note, candidate.get("name")):
        return True
    return False


def _format_match_text(year_month: str, service_type: str, fee_type: str, order_no: str, name: str) -> str:
    service_type = service_type or "清潔"
    fee_type = fee_type or "服務費用"
    return f"{year_month}-{service_type}-{fee_type},{order_no},{name}"


def auto_match_bank_rows(
    region: str,
    row_spec: str = "",
    overwrite_existing: bool = False,
    default_service_type: str = "清潔",
    default_fee_type: str = "服務費用",
    allow_review_prefill: bool = True,
    ui_logger=None,
) -> Dict:
    """
    自動配對 ATM Sheet：
    - 銀行明細：A-F，其中 E=收入、F=備註
    - 待付款清單：I-M，其中 I=服務月份、J=訂單編號、K=姓名、L=金額、M=客人告知末碼

    配對規則：
    1. 金額必須相同
    2. 優先用 F 欄數字備註比對 M 欄末碼
    3. 沒有可用末碼時，用 F 欄文字備註比對 K 欄姓名
    4. 不可只靠金額唯一就自動配對；必須有末碼、姓名/備註、或時間相符依據；多筆/找不到只寫 LOG，不改 G 欄

    成功配對會寫回銀行列：
    I=服務月份、J=訂單編號、K=姓名、L=金額、M=末碼、N=服務類別、O=費用類別
    """
    log = make_logger(ui_logger)
    result = {
        "processed": 0,
        "success": 0,
        "failed": 0,
        "skipped": 0,
        "updated_orders": 0,
        "ambiguous": 0,
        "unmatched": 0,
        "confirm_required": 0,
        "non_order": 0,
        "split_payment": 0,
        "errors": [],
    }

    ws = get_atm_worksheet(region)
    rows = memo.with_retry(ws.get_all_values)
    target_row_nums = memo.parse_row_spec(row_spec) if str(row_spec or "").strip() else []
    target_row_set = set(target_row_nums)
    log(f"===== 開始自動配對 ATM 銀行明細（{region}）=====")
    if target_row_nums:
        log(f"指定銀行列號：{target_row_nums}")
    else:
        log("未指定銀行列號，將掃描全部列")

    # 1-based 欄位：E/F/G/I/J/K/L/M/N/O
    COL_BANK_TIME = 2
    COL_INCOME = 5
    COL_NOTE = 6
    COL_SUMMARY = 7
    COL_MONTH = 9
    COL_MATCH_ORDER_NO = 10
    COL_NAME = 11
    COL_AMOUNT = 12
    COL_LAST_CODE = 13
    COL_SERVICE_TYPE = 14
    COL_FEE_TYPE = 15

    candidates = []
    for idx, row in enumerate(rows, start=1):
        order_no = memo.safe_cell(row, COL_MATCH_ORDER_NO)
        name = memo.safe_cell(row, COL_NAME)
        amount = _to_int_amount(memo.safe_cell(row, COL_AMOUNT))
        last_code = memo.safe_cell(row, COL_LAST_CODE)
        service_type = memo.safe_cell(row, COL_SERVICE_TYPE) or default_service_type
        fee_type = memo.safe_cell(row, COL_FEE_TYPE) or default_fee_type

        # 正常訂單：J 有訂單編號
        # 非訂單收入：J 空白，但 K 姓名 + L 金額 + N/O 類別存在
        if amount is None:
            continue
        if not order_no and not (name and (service_type or fee_type)):
            continue

        candidates.append({
            "row": idx,
            "year_month": memo.safe_cell(row, COL_MONTH),
            "order_no": order_no,
            "name": name,
            "amount": amount,
            "last_code": last_code,
            "service_type": service_type,
            "fee_type": fee_type,
        })

    used_order_nos = set()
    matched_names = set()
    # 已經配在銀行列上的訂單，避免同一筆待付款被重複配到多筆入帳。
    # 同時記錄上方已對帳過的姓名，供「需確認候選」判斷。
    for row in rows:
        income = _to_int_amount(memo.safe_cell(row, COL_INCOME))
        order_no = memo.safe_cell(row, COL_MATCH_ORDER_NO)
        name_val = memo.safe_cell(row, COL_NAME)
        if income is not None and order_no:
            used_order_nos.add(order_no)
            if name_val:
                matched_names.add(_compact_text(name_val))

    log(f"可配對候選訂單：{len(candidates)} 筆")

    for idx, row in enumerate(rows, start=1):
        try:
            if target_row_set and idx not in target_row_set:
                continue

            income = _to_int_amount(memo.safe_cell(row, COL_INCOME))
            bank_time = memo.safe_cell(row, COL_BANK_TIME)
            note = memo.safe_cell(row, COL_NOTE)
            current_order_no = memo.safe_cell(row, COL_MATCH_ORDER_NO)

            if income is None:
                continue

            result["processed"] += 1

            if current_order_no and not overwrite_existing:
                result["skipped"] += 1
                log(f"⏭ 第{idx}列：已有訂單 {current_order_no}，略過")
                continue

            amount_candidates = [c for c in candidates if c["amount"] == income]
            if not overwrite_existing:
                amount_candidates = [c for c in amount_candidates if (not c["order_no"]) or c["order_no"] not in used_order_nos or c["order_no"] == current_order_no]

            split_candidates = [c for c in candidates if _is_split_payment_candidate(income, c, note)]
            code_matches = [c for c in amount_candidates if c["last_code"] and _bank_note_has_code(note, c["last_code"])]
            name_matches = [c for c in amount_candidates if _note_matches_name(note, c["name"])]

            match_type = ""
            matches = []
            needs_confirm = False

            if len(code_matches) == 1:
                matches = code_matches
                match_type = "末碼+金額"
            elif len(code_matches) > 1:
                matches = code_matches
                match_type = "末碼+金額"
            elif len(name_matches) == 1:
                matches = name_matches
                match_type = "備註姓名+金額"
            elif len(name_matches) > 1:
                matches = name_matches
                match_type = "備註姓名+金額"
            elif len(split_candidates) == 1:
                matches = [dict(split_candidates[0], split_reason="疑似拆單")]
                match_type = "疑似拆單"
                needs_confirm = True
            elif len(split_candidates) > 1:
                matches = [dict(c, split_reason="疑似拆單") for c in split_candidates]
                match_type = "疑似拆單"
                needs_confirm = True
            else:
                matches = []

            # 需確認候選：
            # 1) 候選列 M 欄是日期+時間，且等於銀行 B 欄
            # 2) 銀行 F 欄與候選 K 欄姓名相近
            # 3) 候選 K 欄姓名已出現在上方已對帳列表
            if not matches and allow_review_prefill:
                review_matches = []
                for c in amount_candidates:
                    reasons = []
                    if _datetime_equals(c.get("last_code", ""), bank_time):
                        reasons.append("M欄日期時間=B欄")
                    if _similar_text(note, c.get("name", "")):
                        reasons.append("F欄與K欄姓名相近")
                    if _compact_text(c.get("name", "")) in matched_names:
                        reasons.append("K欄姓名曾出現在上方已對帳列表")
                    if reasons:
                        cc = dict(c)
                        cc["review_reasons"] = reasons
                        review_matches.append(cc)

                if len(review_matches) == 1:
                    matches = review_matches
                    match_type = "需確認候選：" + "、".join(review_matches[0].get("review_reasons", []))
                    needs_confirm = True
                elif len(review_matches) > 1:
                    matches = review_matches
                    match_type = "需確認候選"

            if len(matches) == 1:
                c = matches[0]
                summary = _format_match_text(
                    c["year_month"], c["service_type"], c["fee_type"], c["order_no"], c["name"]
                )
                is_non_order = _is_non_order_candidate(c)
                is_split = str(match_type).startswith("疑似拆單") or bool(c.get("split_reason"))
                if is_non_order:
                    needs_confirm = True
                    status_text = "非訂單收入"
                    display_last_code = _build_confirm_code(c)
                elif is_split:
                    needs_confirm = True
                    status_text = "疑似拆單"
                    display_last_code = _build_confirm_code(c)
                elif needs_confirm:
                    status_text = "需確認"
                    display_last_code = _build_confirm_code(c)
                else:
                    status_text = "已配對"
                    display_last_code = c["last_code"]

                values = [[
                    c["year_month"],
                    c["order_no"],
                    c["name"],
                    c["amount"],
                    display_last_code,
                    c["service_type"],
                    c["fee_type"],
                ]]
                source_row = int(c.get("row") or 0)

                # I/N/O 欄必須維持下拉選單；若目標列沒有驗證，從原候選列複製過來。
                # I=服務月份、N=服務類別、O=費用類別。
                _copy_data_validation(ws, source_row, idx, [COL_MONTH, COL_SERVICE_TYPE, COL_FEE_TYPE])

                # 寫入 I:O，不覆蓋 G/H 欄；P:S 保留給系統對帳結果；T 欄寫狀態
                memo.with_retry(ws.update, f"I{idx}:O{idx}", values, value_input_option="RAW")
                # P 與 T 可能原本是下拉選單，先清除資料驗證再寫入時間/狀態。
                _clear_data_validation(ws, idx, COL_RECONCILED_AT, COL_RECONCILED_AT)
                _clear_data_validation(ws, idx, COL_RECON_STATUS, COL_RECON_STATUS)
                memo.with_retry(ws.update_cell, idx, COL_RECONCILED_AT, _now_text())
                memo.with_retry(ws.update_cell, idx, COL_RECON_STATUS, status_text)

                # 只要已經移到上方指定對帳列，不論是否需確認/非訂單/疑似拆單，
                # 原下方待配對列表都要清空，避免同一筆留在列表中重複配對。
                if source_row and source_row != idx:
                    # 清空下方待配對列的值，但保留 I/N/O 的下拉選單格式。
                    # 先把目前目標列的 I/N/O 驗證複製回來源列，再清空值。
                    _copy_data_validation(ws, idx, source_row, [COL_MONTH, COL_SERVICE_TYPE, COL_FEE_TYPE])
                    memo.with_retry(ws.update, f"I{source_row}:O{source_row}", [["", "", "", "", "", "", ""]], value_input_option="RAW")
                    _copy_data_validation(ws, idx, source_row, [COL_MONTH, COL_SERVICE_TYPE, COL_FEE_TYPE])
                    _clear_data_validation(ws, source_row, COL_RECON_STATUS, COL_RECON_STATUS)
                    memo.with_retry(ws.update_cell, source_row, COL_RECON_STATUS, "")
                    log(f"↳ 已從下方待配對列表移除原候選列第{source_row}列 I:O 與 T，並保留 I/N/O 下拉選單")

                if needs_confirm:
                    result["confirm_required"] += 1
                    if is_non_order:
                        result["non_order"] += 1
                    if is_split:
                        result["split_payment"] += 1
                    result["errors"].append(f"第{idx}列：已預填需確認 {status_text} {c['order_no'] or '-'} {c['name']}（{match_type}）")
                    log(f"⚠️ 第{idx}列：已預填需使用者確認 → {c['order_no'] or '-'} {c['name']} ${c['amount']}（{status_text}／{match_type}）")
                else:
                    log(f"✅ 第{idx}列：{match_type} → {c['order_no']} {c['name']} ${c['amount']}")

                if c["order_no"]:
                    used_order_nos.add(c["order_no"])
                result["success"] += 1
                result["updated_orders"] += 1

            elif len(matches) > 1:
                text = "多筆候選：" + "、".join(f"{c.get('order_no') or '-'} {c.get('name')}" for c in matches[:5])
                result["ambiguous"] += 1
                result["failed"] += 1
                result["errors"].append(f"第{idx}列：{text}")
                log(f"⚠️ 第{idx}列：{text}")

            else:
                text = "待人工確認"
                if len(amount_candidates) > 1:
                    text = f"待人工確認：同金額候選 {len(amount_candidates)} 筆，但缺少末碼/姓名/時間依據"
                elif len(amount_candidates) == 1:
                    c = amount_candidates[0]
                    text = f"待人工確認：同金額候選 {c.get('order_no') or '-'} {c['name']}，但缺少末碼/姓名/時間依據"
                result["unmatched"] += 1
                result["failed"] += 1
                result["errors"].append(f"第{idx}列：{text}")
                log(f"❌ 第{idx}列：{text}")

        except Exception as e:
            msg = f"❌ 第{idx}列配對失敗：{e}"
            log(msg)
            result["failed"] += 1
            result["errors"].append(msg)

    log("===== 自動配對完成 =====")
    return result

# -----------------------------------------------------------------------------
# /ATM-list：查詢「訂單統計表」勾選 + 待付款 + ATM 付款方式 的訂單清單，
# 整理成 訂單服務年月｜訂單編號｜客戶名稱｜總金額扣車馬費，貼到 ATM 對帳工作表。
# -----------------------------------------------------------------------------
def search_atm_unpaid_orders(session, date_until: str, ui_logger=None) -> List[Dict]:
    """
    對應後台「訂單管理」頁面的搜尋條件：
    訂購日期-迄＝date_until、勾選「訂單統計表」、付款狀態＝待付款、付款方式＝ATM。

    /purchase 頁面底部的 Vue 元件裡有完整的 purchaseList JSON（含 total / fare 等欄位），
    直接解析這份 JSON 比逐筆爬 HTML 表格穩，沿用 extract_purchase_list_json()。

    回傳 list of dict：
    [{"year_month": "2026.07", "order_no": "LC00211493", "name": "謝依純", "net_amount": 5600}, ...]
    （net_amount = total 總金額 - fare 車馬費）
    """
    log = make_logger(ui_logger)

    url = f"{memo.BASE_URL}/purchase"
    params = {
        "keyword": "",
        "name": "",
        "phone": "",
        "orderNo": "",
        "date_s": "",
        "date_e": date_until,
        "clean_date_s": "",
        "clean_date_e": "",
        "paid_at_s": "",
        "paid_at_e": "",
        "refundDateS": "",
        "refundDateE": "",
        "buy": "",
        "buy_item": "",
        "area_id": "",
        "isCharge": "",
        "isRefund": "",
        "payway": "2",            # ATM
        "purchase_status": "0",   # 待付款
        "progress_status": "",
        "invoiceStatus": "",
        "otherFee": "",
        "orderBy": "",
        "p_board": "on",          # 勾選「訂單統計表」
    }

    log(f"===== 查詢 ATM 待付款名單（訂購日期迄：{date_until}）=====")
    r = memo.session_get(session, url, params=params)
    r.raise_for_status()

    data = extract_purchase_list_json(r.text)
    if not data:
        log("⚠️ 找不到訂單統計表的內嵌資料（頁面結構可能改變，或查無資料）")
        return []

    items = data.get("data", [])
    log(f"查到 {len(items)} 筆待付款 ATM 訂單")

    rows = []
    for item in items:
        date_clean = str(item.get("date_clean") or "")
        year_month = date_clean[:7].replace("-", ".") if len(date_clean) >= 7 else ""
        order_no = item.get("order_no", "")
        name = item.get("name", "")
        total = item.get("total") or 0
        fare = item.get("fare") or 0
        net_amount = total - fare

        rows.append({
            "year_month": year_month,
            "order_no": order_no,
            "name": name,
            "total": total,
            "fare": fare,
            "net_amount": net_amount,
        })
        log(f"  - {year_month}　{order_no}　{name}　總金額{total} - 車馬費{fare} = {net_amount}")

    return rows


def paste_atm_unpaid_list(region: str, rows: List[Dict], ui_logger=None) -> Dict:
    """
    把 search_atm_unpaid_orders() 的結果貼到「跟 ATM 對帳相同」的工作表（get_atm_worksheet(region)）。

    規則：
    1. 找 B 欄目前最後一個非空白列（last_b_row）。
    2. 從 last_b_row + 5 列開始，檢查該列 I~L 欄是否已經有資料；
       有的話再往下 5 列，直到找到 I~L 全空的列為止，才開始貼。
    3. 每一筆資料佔一列，依序往下貼：I=年月、J=訂單編號、K=客戶姓名、L=總金額扣車馬費。
    """
    log = make_logger(ui_logger)
    result = {"pasted": 0, "start_row": None, "errors": []}

    if not rows:
        log("沒有資料可以貼")
        return result

    ws = get_atm_worksheet(region)
    all_values = memo.with_retry(ws.get_all_values)

    last_b_row = 0
    for idx, row in enumerate(all_values, start=1):
        b_val = row[1] if len(row) > 1 else ""
        if str(b_val).strip():
            last_b_row = idx

    start_row = last_b_row + 5

    def block_has_data(row_num: int) -> bool:
        if row_num - 1 >= len(all_values):
            return False
        row = all_values[row_num - 1]
        for col_idx in range(8, 12):  # I~L 是 0-based index 8~11
            if len(row) > col_idx and str(row[col_idx]).strip():
                return True
        return False

    while block_has_data(start_row):
        log(f"第 {start_row} 列的 I~L 欄已經有資料，往下移 5 列")
        start_row += 5

    updates = []
    for i, r in enumerate(rows):
        row_num = start_row + i
        updates.append({
            "range": f"I{row_num}:L{row_num}",
            "values": [[r["year_month"], r["order_no"], r["name"], r["net_amount"]]],
        })

    memo.with_retry(ws.batch_update, updates, value_input_option="RAW")

    result["pasted"] = len(rows)
    result["start_row"] = start_row
    log(f"✅ 已從第 {start_row} 列開始，貼上 {len(rows)} 筆資料到 I~L 欄")

    return result
