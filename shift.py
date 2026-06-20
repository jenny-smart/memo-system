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
"""
import re
from datetime import date, timedelta
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

# 每個類型對應的「單一數字代碼」（清潔班表頁面上 "44檸檬人10" 這種顯示用的編碼）
TYPE_DIGIT_MAP = {
    "上4": "4",
    "上3": "3",
    "上2": "2",
    "全6": "6",
    "全8": "8",
    "下2": "2",
    "下3": "3",
    "下4": "4",
    "晚2": "2",
}

# 「清」不是欄位，是「把當天這四個 slot 全部清空」的動作
CLEAR_TYPE = "清"
ALL_SLOTS = ["all", "1", "2", "3"]

# -----------------------------------------------------------------------------
# Slot 衝突規則
# -----------------------------------------------------------------------------
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
    """回傳 {姓名: {月份(YYYY-MM): [row, ...]}}"""
    grouped: Dict[str, Dict[str, List[Dict]]] = {}
    for row in rows:
        name = row["name"]
        month = row["date"][:7]
        grouped.setdefault(name, {}).setdefault(month, []).append(row)
    return grouped


# -----------------------------------------------------------------------------
# 依姓名搜尋專員 ID
# -----------------------------------------------------------------------------
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


def search_cleaner1_by_keyword(session: requests.Session, keyword: str) -> Dict[str, str]:
    """
    用 /cleaner1?keyword=... 的搜尋表單查詢，回傳這次搜尋結果裡的 {姓名: 專員ID}。
    ID 是從每筆資料「排班」按鈕的連結 .../cleaner1/{id}/shift 取出來的。
    """
    url = f"{memo.BASE_URL}/cleaner1"
    r = memo.session_get(session, url, params={"keyword": keyword})
    r.raise_for_status()

    soup = BeautifulSoup(r.text, "html.parser")
    results = {}

    for tr in soup.select("table tbody tr"):
        tds = tr.find_all("td", recursive=False)
        if len(tds) < 2:
            continue

        name_td = tds[1]
        lines = name_td.get_text(separator="\n", strip=True).split("\n")
        name = lines[0].strip() if lines else ""

        shift_link = tr.select_one('a[href*="/shift"]')
        if not name or not shift_link:
            continue

        m = re.search(r"/cleaner1/(\d+)/shift", shift_link.get("href", ""))
        if not m:
            continue

        results[name] = m.group(1)

    return results


def find_cleaner_id_by_name(session: requests.Session, name: str) -> Optional[str]:
    """
    先查 /schedule 下拉選單的快取（涵蓋大部分人，速度快）；
    沒找到的話，改用 /cleaner1?keyword=姓名 搜尋當 fallback。
    """
    global _CLEANER_NAME_TO_ID_CACHE

    directory = build_cleaner_directory(session)
    if name in directory:
        return directory[name]

    try:
        found = search_cleaner1_by_keyword(session, name)
    except Exception:
        found = {}

    if found:
        _CLEANER_NAME_TO_ID_CACHE.update(found)

    return _CLEANER_NAME_TO_ID_CACHE.get(name)


# -----------------------------------------------------------------------------
# 取得目前班表的 _token 與已勾選狀態
# -----------------------------------------------------------------------------
def get_shift_page_state(session: requests.Session, cleaner_id: str, month: str):
    """
    回傳 (token, existing_shift_dict)
    existing_shift_dict 格式跟 POST payload 一致（key 已去掉 "shift_" 前綴）：
    {"2026-07-01_all": "8", "2026-07-04_2": "1400-1700", ...}
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
        key = name[len("shift_"):]
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
    3. 再套用 new_entries：同一個 key 以新匯入的為準。
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

    try:
        resp.raise_for_status()
    except requests.HTTPError as e:
        snippet = (resp.text or "")[:500].replace("\n", " ")
        has_token_cookie = any("token" in c.name.lower() or "session" in c.name.lower() for c in session.cookies)
        raise requests.HTTPError(
            f"{e}\n"
            f"[診斷] 送出的 _token 開頭：{token[:10]}…（長度 {len(token)}）"
            f"｜session 是否帶有 session/token 相關 cookie：{has_token_cookie}"
            f"｜回應內容前 500 字：{snippet}"
        ) from e

    return resp


# -----------------------------------------------------------------------------
# 找「檸檬人」空檔並勾選
# -----------------------------------------------------------------------------
LEMON_REN_PREFIX = "檸檬人"
LEMON_REN_DEFAULT_COUNT = 10

LEMON_REN_CHAR_SUFFIXES = "甲乙丙丁戊己"


def parse_lemon_label(text: str) -> Optional[Dict[str, str]]:
    """
    解析「44檸檬人10」這種文字，回傳 {"code": "44", "name": "檸檬人1", "rating": "0"}。
    星等永遠是緊接在名字後面的最後一碼數字（可以是 0），解析時先從尾端拿掉這一碼當星等，
    剩下的才是檸檬人編號／甲乙丙丁戊己。
    """
    m = re.match(r"^(?P<code>\d*)檸檬人(?P<rest>.+)$", text.strip())
    if not m:
        return None

    rest = m.group("rest")
    if not rest:
        return None

    rating = rest[-1]
    if not rating.isdigit():
        return None

    number_part = rest[:-1]
    if not number_part:
        return None

    if number_part.isdigit() or number_part in LEMON_REN_CHAR_SUFFIXES:
        return {
            "code": m.group("code"),
            "name": f"檸檬人{number_part}",
            "rating": rating,
        }

    return None


def find_available_lemon_ren(
    session: requests.Session,
    date_val: str,
    type_val: str,
    max_count: int = LEMON_REN_DEFAULT_COUNT,
    log=None,
):
    """
    依序檢查 檸檬人1 ~ 檸檬人{max_count}，找出「該日期、該類型對應的 slot」
    目前沒有被勾選的第一個檸檬人。只負責「找」，不會真的送出勾選。
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
    一定要用「目前這個 session」重新抓一次最新的 _token 跟既有勾選狀態再送出。
    """
    if not candidate.get("found"):
        raise RuntimeError("沒有找到可用的檸檬人，無法勾選")

    cleaner_id = candidate["cleaner_id"]
    month = candidate["month"]
    slot_key = candidate["slot_key"]
    value = candidate["value"]

    token, existing = get_shift_page_state(session, cleaner_id, month)

    if slot_key in existing:
        raise RuntimeError(
            f"「{candidate['name']}」的 {slot_key} 在送出前已經被勾選為 {existing[slot_key]}，"
            f"可能被別人搶先一步，請重新查詢空檔"
        )

    merged = dict(existing)
    merged[slot_key] = value

    submit_shift_payload(session, cleaner_id, token, merged)

    if log:
        log(f"✅ 已將「{candidate['name']}」於 {slot_key} 勾選為 {value} 並儲存")

    return merged


def check_merged_conflicts(merged: Dict[str, str]) -> List[str]:
    """檢查合併後的結果裡，有沒有同一天「全天」跟「上午/下午」同時被勾選的情況（僅供檸檬人使用）。"""
    warnings = []

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


def process_import_file(rows: List[Dict], dry_run: bool = True, ui_logger=None, session=None) -> Dict:
    """
    dry_run=True：只做到「組好 payload」為止，不會真的送出。
    dry_run=False：實際送出儲存。

    session：可選，傳入已登入的 session 就重用，不傳則自己登入一次
    （讓呼叫端可以共用同一個已登入的 session，不用每個功能各自重新登入）。
    """
    log = make_logger(ui_logger)
    result = {
        "processed_people": 0,
        "processed_months": 0,
        "saved": 0,
        "skipped": [],
        "errors": [],
        "dry_run_payloads": [],
    }

    lemon_rows = [r for r in rows if LEMON_REN_NAME_PATTERN.match(r.get("name", ""))]
    rows = [r for r in rows if not LEMON_REN_NAME_PATTERN.match(r.get("name", ""))]

    if lemon_rows:
        log(f"⏭ 已略過 {len(lemon_rows)} 筆檸檬人資料（請改用「檸檬人空檔勾選」功能處理）")

    grouped = group_rows_by_name_and_month(rows)
    session = session or memo.login(ui_logger=ui_logger)
    build_cleaner_directory(session, force_refresh=True)

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


# =============================================================================
# 清空排班：功能1 —— 清空某人（含檸檬人）一段期間的排班
# =============================================================================
def date_range(date_start: str, date_end: str) -> List[str]:
    """產生 [date_start, date_end] 間每一天的 YYYY-MM-DD 字串（含頭尾）。"""
    d1 = date.fromisoformat(date_start)
    d2 = date.fromisoformat(date_end)
    if d2 < d1:
        d1, d2 = d2, d1
    days = []
    cur = d1
    while cur <= d2:
        days.append(cur.isoformat())
        cur += timedelta(days=1)
    return days


def clear_person_shift_dates(
    session: requests.Session,
    name: str,
    dates_to_clear: List[str],
    ui_logger=None,
) -> Dict:
    """
    清空指定人員（含檸檬人）在 dates_to_clear 這些日期的整天排班，並送出儲存。
    """
    log = make_logger(ui_logger)
    result = {
        "name": name,
        "cleaner_id": None,
        "cleared_dates": [],
        "cleared_slot_count": 0,
        "untouched_dates": [],
        "errors": [],
    }

    cleaner_id = find_cleaner_id_by_name(session, name)
    if not cleaner_id:
        msg = f"❌ 找不到「{name}」的後台帳號"
        log(msg)
        result["errors"].append(msg)
        return result

    result["cleaner_id"] = cleaner_id

    by_month: Dict[str, List[str]] = {}
    for d in dates_to_clear:
        by_month.setdefault(d[:7], []).append(d)

    for month, dates in by_month.items():
        try:
            token, existing = get_shift_page_state(session, cleaner_id, month)

            removed_keys = []
            month_cleared_dates = []
            for d in dates:
                day_had_entry = False
                for slot in ALL_SLOTS:
                    key = f"{d}_{slot}"
                    if key in existing:
                        removed_keys.append(key)
                        day_had_entry = True
                if day_had_entry:
                    result["cleared_dates"].append(d)
                    month_cleared_dates.append(d)
                else:
                    result["untouched_dates"].append(d)

            merged = merge_shift_entries(existing, {}, clear_dates=dates)
            submit_shift_payload(session, cleaner_id, token, merged)

            result["cleared_slot_count"] += len(removed_keys)

            if month_cleared_dates:
                log(f"✅ [{name} {month}] 已清空 {sorted(month_cleared_dates)}，移除 {len(removed_keys)} 筆既有勾選：{removed_keys}")
            else:
                log(f"ℹ️ [{name} {month}] 查詢範圍內這個月沒有任何已勾選的排班，無需清空")

        except Exception as e:
            msg = f"❌ [{name} {month}] 清空失敗：{e}"
            log(msg)
            result["errors"].append(msg)

    return result


def clear_person_shift_range(
    session: requests.Session,
    name: str,
    date_start: str,
    date_end: str,
    ui_logger=None,
) -> Dict:
    """功能1 的對外入口：清空某人（含檸檬人）date_start ~ date_end 這段期間的排班。"""
    dates = date_range(date_start, date_end)
    return clear_person_shift_dates(session, name, dates, ui_logger=ui_logger)


# =============================================================================
# 清空排班：功能2 —— 從清潔班表「未配班」清單，反查並清除檸檬人佔用的時段
# =============================================================================
def _parse_schedule_query_date(html: str, fallback: str) -> str:
    """從清潔班表頁面的 <input id="date" value="..."> 取得目前查詢的日期，取不到就用 fallback。"""
    soup = BeautifulSoup(html, "html.parser")
    el = soup.select_one("input#date")
    if el and el.get("value"):
        return el.get("value").strip()
    return fallback


def _row_label_to_date(label: str, query_date: str) -> Optional[str]:
    """把表格列頭的「06-23（二）」轉成完整日期 YYYY-MM-DD。"""
    m = re.match(r"(\d{2})-(\d{2})", label.strip())
    if not m:
        return None
    month, day = m.group(1), m.group(2)

    q = date.fromisoformat(query_date)
    year = q.year
    if q.month == 12 and int(month) == 1:
        year += 1
    elif q.month == 1 and int(month) == 12:
        year -= 1

    return f"{year}-{month}-{day}"


def parse_unassigned_lemon_entries(html: str, query_date: str) -> List[Dict]:
    """
    解析清潔班表頁面（/schedule?date=YYYY-MM-DD）裡每一天「未配班」灰底清單中的檸檬人。
    """
    soup = BeautifulSoup(html, "html.parser")
    seen = set()
    results = []

    for tr in soup.select("table tr"):
        tds = tr.find_all("td", recursive=False)
        if not tds:
            continue
        first_text = tds[0].get_text(strip=True)
        date_val = _row_label_to_date(first_text, query_date)
        if not date_val:
            continue

        for p in tr.select('p[style*="616161"]'):
            for span in p.find_all("span", recursive=True):
                if span.find_parent("a"):
                    continue
                text = span.get_text(strip=True)
                parsed = parse_lemon_label(text)
                if not parsed:
                    continue
                lemon_name = parsed["name"]
                dedup_key = (date_val, lemon_name)
                if dedup_key in seen:
                    continue
                seen.add(dedup_key)
                results.append({
                    "date": date_val,
                    "name": lemon_name,
                    "raw": text,
                })

    return results


def find_unassigned_lemon_bookings(
    session: requests.Session,
    query_date: str,
    ui_logger=None,
) -> List[Dict]:
    """
    抓 /schedule?date=query_date 這一週的清潔班表，回傳「未配班」清單裡出現的
    檸檬人佔用紀錄（已去重，每個 (date, 檸檬人) 只會出現一次）。只負責「找」。
    """
    log = make_logger(ui_logger)
    url = f"{memo.BASE_URL}/schedule"
    r = memo.session_get(session, url, params={"date": query_date})
    r.raise_for_status()

    actual_query_date = _parse_schedule_query_date(r.text, query_date)
    entries = parse_unassigned_lemon_entries(r.text, actual_query_date)

    log(f"在 {query_date} 所在那週的清潔班表裡，找到 {len(entries)} 筆未配班清單中的檸檬人佔用紀錄")
    for e in entries:
        log(f"  - {e['date']}　{e['name']}（原始文字：{e['raw']}）")

    return entries


def clear_unassigned_lemon_bookings(
    session: requests.Session,
    entries: List[Dict],
    ui_logger=None,
) -> List[Dict]:
    """拿 find_unassigned_lemon_bookings() 的結果，依檸檬人分組，清空並儲存。"""
    log = make_logger(ui_logger)

    by_name: Dict[str, List[str]] = {}
    for e in entries:
        by_name.setdefault(e["name"], []).append(e["date"])

    results = []
    for name, dates in by_name.items():
        log(f"\n===== 清空檸檬人：{name}（{sorted(set(dates))}）=====")
        res = clear_person_shift_dates(session, name, sorted(set(dates)), ui_logger=ui_logger)
        results.append(res)

    return results
