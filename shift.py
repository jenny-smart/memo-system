# shift.py
# -*- coding: utf-8 -*-
"""
自動勾班模組

對應後台頁面 cleaner1/{id}/shift?month=YYYY-MM 的實際結構：
- 每天有四組「各自獨立」的 radio button group：
    shift_{date}_all  (value: "6" 或 "8")
    shift_{date}_1    (上午，value: "0830-1230" / "0900-1200" / "0900-1100")
    shift_{date}_2    (下午，value: "1400-1800" / "1400-1700" / "1400-1600")
    shift_{date}_3    (晚上，value: "1900-2100")
  同一天的這四組可以同時被勾選（業務上通常不會，但程式層面沒有互斥）。
- 「清」不是一個會送出的欄位，而是前端 JS 把當天四組 radio 全部取消勾選。
  匯入檔遇到「清」時，代表要把該日期當天既有的四組勾選全部移除，
  而不是新增什麼資料。
- 判斷「目前已勾選」要看 radio 的 checked 屬性，不是看 value 是否存在
  （因為每個選項本來就都有固定的 value，只是沒被勾選的話沒有 checked）。

⚠️ 尚待確認：
1. find_cleaner_id_by_name()：居家專員搜尋頁的 URL／參數名稱還沒拿到，
   目前用猜測的 `?search=` 寫，需要你確認後修正（見檔案下方 TODO）。
"""
import re
from typing import Dict, List, Optional, Callable

import requests
from bs4 import BeautifulSoup

import memo  # 重用 memo.py 的 BASE_URL / login() / session_get / session_post 等


# -----------------------------------------------------------------------------
# 類型 -> (slot 代碼, value) 對照表
# -----------------------------------------------------------------------------
TYPE_MAP = {
    "全6": ("all", "6"),
    "全8": ("all", "8"),
    "上2": ("1", "0900-1100"),
    "上3": ("1", "0900-1200"),
    "上4": ("1", "0830-1230"),
    "下2": ("2", "1400-1600"),
    "下3": ("2", "1400-1700"),
    "下4": ("2", "1400-1800"),
    "晚2": ("3", "1900-2100"),
}

# 「清」不是欄位，是「把當天這四個 slot 全部清空」的動作
CLEAR_TYPE = "清"
ALL_SLOTS = ["all", "1", "2", "3"]

# -----------------------------------------------------------------------------
# Slot 衝突規則
# -----------------------------------------------------------------------------
# 業務規則：
# - 全6 / 全8（slot="all"）跟 上午（slot="1"）、下午（slot="2"）互斥：
#   勾了全天班就不能再勾上午或下午；反過來勾了上午或下午，就不能再勾全天班。
# - 上午（slot="1"）跟 下午（slot="2"）彼此「不」衝突，可以同時勾（例如上2 +下午）。
# - 晚上（slot="3"）目前沒有業務規則說會跟誰衝突，視為獨立 slot。
CONFLICT_MAP = {
    "all": {"1", "2"},
    "1": {"all"},
    "2": {"all"},
    "3": set(),
}


def get_conflicting_slot_keys(existing: Dict[str, str], date_val: str, slot: str) -> Dict[str, str]:
    """
    檢查 existing（某人某月已勾選的 dict）裡，在 date_val 這天，
    有沒有跟 slot 互相衝突、且「已經被勾選」的項目。
    回傳 {衝突的 slot_key: 已勾選的值}，沒有衝突就回傳空 dict。
    """
    conflicts = {}
    for conflicting_slot in CONFLICT_MAP.get(slot, set()):
        key = f"{date_val}_{conflicting_slot}"
        if key in existing:
            conflicts[key] = existing[key]
    return conflicts


def make_logger(ui_logger: Optional[Callable[[str], None]] = None):
    def _log(msg: str):
        msg = str(msg)
        print(msg, flush=True)
        if ui_logger:
            ui_logger(msg)
    return _log


# -----------------------------------------------------------------------------
# 匯入檔解析：地區 / 日期 / 類型 / 時段 / 名稱
# -----------------------------------------------------------------------------
def parse_import_file(file_obj, filename: str) -> List[Dict]:
    """
    讀取 Excel / CSV，回傳 list of dict：
    [{"area": "台北", "date": "2026-06-03", "type": "全8", "name": "蔡立娟"}, ...]

    欄位「時段」目前看起來在範例資料裡都是空的（類型已經涵蓋上/下/晚/全），
    先不使用，若實際上「時段」欄位有額外用途，麻煩再說明。
    """
    import pandas as pd

    if filename.lower().endswith(".csv"):
        df = pd.read_csv(file_obj, dtype=str)
    else:
        df = pd.read_excel(file_obj, dtype=str)

    df = df.rename(columns={
        "地區": "area",
        "日期": "date",
        "類型": "type",
        "時段": "period",
        "名稱": "name",
    })

    required = {"date", "type", "name"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"匯入檔缺少欄位：{missing}")

    rows = []
    for _, r in df.iterrows():
        date_val = str(r.get("date", "")).strip()
        type_val = str(r.get("type", "")).strip()
        name_val = str(r.get("name", "")).strip()

        if not date_val or not type_val or not name_val:
            continue

        # 日期正規化成 YYYY-MM-DD
        date_val = re.sub(r"[./]", "-", date_val)
        date_val = date_val[:10]

        rows.append({
            "area": str(r.get("area", "")).strip(),
            "date": date_val,
            "type": type_val,
            "name": name_val,
        })

    return rows


def group_rows_by_name_and_month(rows: List[Dict]) -> Dict[str, Dict[str, List[Dict]]]:
    """
    回傳 {姓名: {月份(YYYY-MM): [row, ...]}}
    """
    grouped: Dict[str, Dict[str, List[Dict]]] = {}
    for row in rows:
        name = row["name"]
        month = row["date"][:7]
        grouped.setdefault(name, {}).setdefault(month, []).append(row)
    return grouped


# -----------------------------------------------------------------------------
# 依姓名搜尋專員 ID
# -----------------------------------------------------------------------------
# 「居家專員」列表頁有分頁（目前 29 頁，會持續增加），逐頁搜尋不可靠。
# /schedule 頁面裡剛好有一份 <select id="cleaner_id"> 下拉選單，
# 一次列出「全部」專員（含所有檸檬人）的姓名→ID 對照，改用這個一次抓全部最穩。
_CLEANER_NAME_TO_ID_CACHE: Dict[str, str] = {}


def build_cleaner_directory(session: requests.Session, force_refresh: bool = False) -> Dict[str, str]:
    """
    回傳 {姓名: 專員ID} 的完整對照表，來源是 /schedule 頁面的 cleaner_id 下拉選單。
    結果會快取在模組層級變數，同一次 process 內不用重複打。
    """
    global _CLEANER_NAME_TO_ID_CACHE

    if _CLEANER_NAME_TO_ID_CACHE and not force_refresh:
        return _CLEANER_NAME_TO_ID_CACHE

    url = f"{memo.BASE_URL}/schedule"
    r = memo.session_get(session, url)
    r.raise_for_status()

    soup = BeautifulSoup(r.text, "html.parser")
    select_el = soup.select_one("select#cleaner_id")

    directory = {}
    if select_el:
        for opt in select_el.select("option"):
            value = (opt.get("value") or "").strip()
            name = opt.get_text(strip=True)
            if value and value != "0" and name:
                directory[name] = value

    _CLEANER_NAME_TO_ID_CACHE = directory
    return directory


def find_cleaner_id_by_name(session: requests.Session, name: str) -> Optional[str]:
    directory = build_cleaner_directory(session)
    return directory.get(name)


# -----------------------------------------------------------------------------
# 取得目前班表的 _token 與已勾選狀態
# -----------------------------------------------------------------------------
def get_shift_page_state(session: requests.Session, cleaner_id: str, month: str):
    """
    回傳 (token, existing_shift_dict)
    existing_shift_dict 格式跟 POST payload 一致（key 已去掉 "shift_" 前綴）：
    {"2026-07-01_all": "8", "2026-07-04_2": "1400-1700", ...}

    只收集「目前已勾選（checked）」的 radio，未勾選的選項雖然也有 value
    但不會被收進來。
    """
    url = f"{memo.BASE_URL}/cleaner1/{cleaner_id}/shift"
    r = memo.session_get(session, url, params={"month": month})
    r.raise_for_status()

    soup = BeautifulSoup(r.text, "html.parser")

    token_el = soup.select_one('input[name="_token"]')
    token = token_el.get("value", "") if token_el else ""

    existing = {}
    for el in soup.select('input[name^="shift_"][checked]'):
        name = el.get("name", "")
        value = el.get("value", "")
        key = name[len("shift_"):]  # 去掉前綴 "shift_"
        if value:
            existing[key] = value

    return token, existing


# -----------------------------------------------------------------------------
# 把匯入檔的資料轉成 payload key
# -----------------------------------------------------------------------------
def build_new_shift_entries(rows: List[Dict], log=None):
    """
    rows: 同一人、同一月份的匯入列
    回傳 (entries, clear_dates)
      entries: {"2026-07-01_all": "8", ...} 要新增/覆蓋的勾選
      clear_dates: {"2026-07-05", ...} 要整天清空的日期（對應「清」）
    """
    entries: Dict[str, str] = {}
    clear_dates = set()

    for row in rows:
        type_val = row["type"]
        date_val = row["date"]

        if type_val == CLEAR_TYPE:
            clear_dates.add(date_val)
            continue

        if type_val not in TYPE_MAP:
            msg = f"⚠️ 未知類型「{type_val}」（{row.get('name', '')} {date_val}），先略過，需要補對照表"
            if log:
                log(msg)
            continue

        slot, value = TYPE_MAP[type_val]
        key = f"{date_val}_{slot}"
        entries[key] = value

    return entries, clear_dates


def merge_shift_entries(existing: Dict[str, str], new_entries: Dict[str, str], clear_dates=None) -> Dict[str, str]:
    """
    合併規則：
    1. 先以既有勾選為底。
    2. clear_dates 裡的日期：把該日 all/1/2/3 四個 slot 全部移除（對應「清」）。
    3. 再套用 new_entries：同一個 key（同一天同 slot）以新匯入的為準。
       （清空跟新增同時出現在同一天時，新增會保留，因為後套用。）
    """
    merged = dict(existing)

    for date_val in (clear_dates or []):
        for slot in ALL_SLOTS:
            merged.pop(f"{date_val}_{slot}", None)

    merged.update(new_entries)
    return merged


# -----------------------------------------------------------------------------
# 送出整月班表
# -----------------------------------------------------------------------------
def submit_shift_payload(session: requests.Session, cleaner_id: str, token: str, merged: Dict[str, str]):
    url = f"{memo.BASE_URL}/cleaner1/{cleaner_id}/shift"

    payload = {f"shift_{k}": v for k, v in merged.items()}
    payload["_token"] = token

    resp = memo.session_post(
        session,
        url,
        data=payload,
        headers={
            "Referer": url,
            "User-Agent": "Mozilla/5.0",
        },
    )
    resp.raise_for_status()
    return resp


# -----------------------------------------------------------------------------
# 找「檸檬人」空檔並勾選
# -----------------------------------------------------------------------------
# 業務情境：排班時某個時段約不到真人，就用「檸檬人1」~「檸檬人N」這種佔位帳號
# 頂上去。但檸檬人帳號可能在同一天同時段已經被別張訂單用掉了（代表那個號碼
# 「目前有訂單在用」），這時就要往下一個檸檬人找，直到找到「該日期該 slot
# 沒有被勾選」的檸檬人為止，才能勾這個號碼。
LEMON_REN_PREFIX = "檸檬人"
LEMON_REN_DEFAULT_COUNT = 10


def find_available_lemon_ren(
    session: requests.Session,
    date_val: str,
    type_val: str,
    max_count: int = LEMON_REN_DEFAULT_COUNT,
    log=None,
):
    """
    依序檢查 檸檬人1 ~ 檸檬人{max_count}，找出「該日期、該類型對應的 slot」
    目前沒有被勾選的第一個檸檬人。

    回傳 dict：
    {
        "found": True/False,
        "name": "檸檬人3",
        "cleaner_id": "31",
        "month": "2026-07",
        "slot_key": "2026-07-05_2",
        "value": "1400-1700",
        "token": "...",
        "existing": {...},          # 該檸檬人當月既有勾選（尚未合併新的）
        "checked_candidates": [...] # 已經檢查過、但被佔用而跳過的名單
    }
    找不到任何空檔則 found=False。

    注意：這個函式只負責「找」，不會真的送出勾選；
    要實際勾選，請呼叫 confirm_lemon_ren_assignment()。
    """
    if type_val == CLEAR_TYPE:
        raise ValueError("「清」不是可勾選的類型，不適用於找空檔勾選")
    if type_val not in TYPE_MAP:
        raise ValueError(f"未知類型「{type_val}」，無法判斷對應的 slot")

    slot, value = TYPE_MAP[type_val]
    month = date_val[:7]
    slot_key = f"{date_val}_{slot}"

    checked_candidates = []

    for i in range(1, max_count + 1):
        lemon_name = f"{LEMON_REN_PREFIX}{i}"

        cleaner_id = find_cleaner_id_by_name(session, lemon_name)
        if not cleaner_id:
            if log:
                log(f"⚠️ 找不到「{lemon_name}」的後台帳號，略過")
            continue

        token, existing = get_shift_page_state(session, cleaner_id, month)

        occupied_reason = None

        if slot_key in existing:
            occupied_reason = f"{date_val} 的「{type_val}」時段本身已被勾選（{existing[slot_key]}）"
        else:
            conflicts = get_conflicting_slot_keys(existing, date_val, slot)
            if conflicts:
                conflict_desc = "、".join(f"{k}={v}" for k, v in conflicts.items())
                occupied_reason = f"{date_val} 已有跟「{type_val}」互斥的勾選（{conflict_desc}），不能再勾"

        if occupied_reason:
            if log:
                log(f"⏭ {lemon_name}（id={cleaner_id}）{occupied_reason}，往下一位找")
            checked_candidates.append({
                "name": lemon_name,
                "cleaner_id": cleaner_id,
                "occupied_value": existing.get(slot_key, occupied_reason),
            })
            continue

        if log:
            log(f"✅ 找到空檔：{lemon_name}（id={cleaner_id}），{date_val} 的「{type_val}」目前是空的且無衝突")

        return {
            "found": True,
            "name": lemon_name,
            "cleaner_id": cleaner_id,
            "month": month,
            "slot_key": slot_key,
            "value": value,
            "token": token,
            "existing": existing,
            "checked_candidates": checked_candidates,
        }

    if log:
        log(f"❌ 檸檬人1~{max_count} 在 {date_val}「{type_val}」這個時段全部被佔用或找不到帳號")

    return {
        "found": False,
        "name": None,
        "cleaner_id": None,
        "month": month,
        "slot_key": slot_key,
        "value": value,
        "token": None,
        "existing": {},
        "checked_candidates": checked_candidates,
    }


def confirm_lemon_ren_assignment(session: requests.Session, candidate: Dict, log=None):
    """
    拿 find_available_lemon_ren() 回傳的 candidate，實際送出勾選。
    會重新合併 existing + 新的 slot_key/value，再 submit。

    （不重新整頁 GET 一次最新狀態，是因為通常找到空檔後會緊接著呼叫這個函式，
    時間差很短；如果中間隔了很久，建議呼叫前重新跑一次 find_available_lemon_ren
    確認還是空的，避免兩個人同時搶同一個檸檬人時段。）
    """
    if not candidate.get("found"):
        raise RuntimeError("沒有找到可用的檸檬人，無法勾選")

    merged = dict(candidate["existing"])
    merged[candidate["slot_key"]] = candidate["value"]

    submit_shift_payload(
        session,
        candidate["cleaner_id"],
        candidate["token"],
        merged,
    )

    if log:
        log(f"✅ 已將「{candidate['name']}」於 {candidate['slot_key']} 勾選為 {candidate['value']} 並儲存")

    return merged


def check_merged_conflicts(merged: Dict[str, str]) -> List[str]:
    """
    檢查合併後的結果裡，有沒有同一天「全天」跟「上午/下午」同時被勾選的情況。

    ⚠️ 注意：這個檢查目前「沒有」在一般匯入流程（process_import_file）裡被呼叫。
    因為一般專員是真人，可以彈性支援（例如全8 可以涵蓋上4、全6 可以涵蓋下3），
    全天 + 半天同時勾選對一般專員來說是合理、允許的排班方式，不是錯誤。

    這個函式只保留給「檸檬人」這種佔位帳號使用（見 find_available_lemon_ren），
    因為檸檬人是用來代表「這個時段有沒有被佔用」的系統佔位機制，
    全天跟半天同時勾對檸檬人來說才真的代表衝突。
    """
    warnings = []

    # 整理出每個日期目前有哪些 slot 被勾
    by_date: Dict[str, Dict[str, str]] = {}
    for key, value in merged.items():
        date_val, slot = key.rsplit("_", 1)
        by_date.setdefault(date_val, {})[slot] = value

    for date_val, slots in by_date.items():
        for slot, value in slots.items():
            for conflicting_slot in CONFLICT_MAP.get(slot, set()):
                if conflicting_slot in slots:
                    pair = tuple(sorted([slot, conflicting_slot]))
                    msg = f"⚠️ {date_val} 同時勾選了 {pair[0]}={slots[pair[0]]} 跟 {pair[1]}={slots[pair[1]]}，這兩個互斥，請確認"
                    if msg not in warnings:
                        warnings.append(msg)

    return warnings


# -----------------------------------------------------------------------------
# 主流程：處理整份匯入檔
# -----------------------------------------------------------------------------
LEMON_REN_NAME_PATTERN = re.compile(r"^檸檬人")


def process_import_file(rows: List[Dict], dry_run: bool = True, ui_logger=None) -> Dict:
    """
    dry_run=True：只做到「組好 payload」為止，不會真的送出，
                  並把每個人/每個月份合併後的 payload 印到 log 讓你核對。
    dry_run=False：實際送出儲存。

    合併規則（預設）：「以匯入檔為準」——只要某個日期有出現在這次匯入檔裡
    （不管是新增還是「清」），就把該日期既有的四個 slot 全部重設，
    再套用匯入檔裡這個日期的內容。完全沒出現在匯入檔裡的日期則維持原樣不動。
    👉 所以做局部微調時，請確保要調整的那個日期，在匯入檔裡是「完整」的當天
    資料，而不是只放你想改的那一筆，否則同一天其他沒列出的時段會被視為清空。

    「檸檬人」相關列會被自動略過，不會透過這個一般匯入流程處理
    （檸檬人請改用「檸檬人空檔勾選」功能，那邊有衝突檢查機制）。
    """
    log = make_logger(ui_logger)
    result = {
        "processed_people": 0,
        "processed_months": 0,
        "saved": 0,
        "skipped": [],
        "errors": [],
        "dry_run_payloads": [],  # [(name, month, merged_dict), ...]
    }

    lemon_rows = [r for r in rows if LEMON_REN_NAME_PATTERN.match(r.get("name", ""))]
    rows = [r for r in rows if not LEMON_REN_NAME_PATTERN.match(r.get("name", ""))]

    if lemon_rows:
        log(f"⏭ 已略過 {len(lemon_rows)} 筆檸檬人資料（請改用「檸檬人空檔勾選」功能處理）")

    grouped = group_rows_by_name_and_month(rows)
    session = memo.login(ui_logger=ui_logger)
    build_cleaner_directory(session, force_refresh=True)  # 強制重新抓最新的姓名→ID對照

    for name, months in grouped.items():
        log(f"\n===== 處理專員：{name} =====")

        cleaner_id = find_cleaner_id_by_name(session, name)
        if not cleaner_id:
            msg = f"❌ 找不到專員「{name}」的後台 ID，略過"
            log(msg)
            result["skipped"].append(name)
            result["errors"].append(msg)
            continue

        result["processed_people"] += 1

        for month, month_rows in months.items():
            log(f"[{name}] 月份 {month}，共 {len(month_rows)} 筆匯入資料")

            try:
                token, existing = get_shift_page_state(session, cleaner_id, month)
                new_entries, clear_dates = build_new_shift_entries(month_rows, log=log)

                # 「以匯入檔為準」：把這次匯入檔裡有提到的日期（不管新增或清空）
                # 整天重設，再套用新內容，避免同一天舊資料殘留跟新檔打架。
                mentioned_dates = clear_dates | {k.rsplit("_", 1)[0] for k in new_entries}
                merged = merge_shift_entries(existing, new_entries, mentioned_dates)

                result["processed_months"] += 1

                if clear_dates:
                    log(f"[{name} {month}] 將清空日期：{sorted(clear_dates)}")

                if dry_run:
                    log(f"[{name} {month}] DRY RUN，合併後共 {len(merged)} 筆，不會送出")
                    result["dry_run_payloads"].append((name, month, merged))
                else:
                    submit_shift_payload(session, cleaner_id, token, merged)
                    log(f"✅ [{name} {month}] 已儲存，共 {len(merged)} 筆")
                    result["saved"] += 1

            except Exception as e:
                msg = f"❌ [{name} {month}] 失敗：{e}"
                log(msg)
                result["errors"].append(msg)

    return result
