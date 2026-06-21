# memoapp.py
# -*- coding: utf-8 -*-
import streamlit as st
import re
import importlib
from datetime import date, timedelta
import memo
import shift
import atm
atm = importlib.reload(atm)
import change_order

st.set_page_config(
    page_title="Memo 自動回填系統",
    page_icon="📝",
    layout="wide"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@400;500;700;900&family=Space+Grotesk:wght@500;700&display=swap');

:root {
    --lemon:       #F5C518;
    --lemon-dark:  #D4A017;
    --lemon-soft:  #FFFCF2;
    --lemon-mid:   #FFF3C4;
    --charcoal:    #1C1C1E;
    --ink:         #3A3A3C;
    --muted:       #8E8E93;
    --border:      #E8E8EC;
    --surface:     #FFFFFF;
    --success:     #34C759;
    --danger:      #FF3B30;
    --radius:      16px;
    --shadow:      0 2px 14px rgba(0,0,0,0.05);
}

html, body, [class*="css"] {
    font-family: 'Noto Sans TC', sans-serif;
    color: var(--charcoal);
}

#MainMenu, footer, header {
    visibility: hidden;
}

[data-testid="stAppViewContainer"] {
    background: #FAFAFA;
}

.block-container {
    padding-top: 2.2rem !important;
    padding-bottom: 2.5rem !important;
    max-width: 1180px !important;
}

/* ---------- Hero ---------- */

.hero {
    background: linear-gradient(135deg, #FFFDF5 0%, #FFFBEA 100%);
    border: 1.5px solid var(--lemon-mid);
    border-radius: var(--radius);
    padding: 2.1rem 2.6rem;
    margin-bottom: 2.2rem;
    display: flex;
    align-items: center;
    gap: 1.3rem;
    box-shadow: 0 2px 14px rgba(245,197,24,0.08);
}

.hero-emoji {
    font-size: 3.1rem;
    line-height: 1;
}

.hero-title {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 2rem;
    font-weight: 700;
    color: var(--charcoal);
    margin: 0;
    letter-spacing: -0.5px;
}

.hero-sub {
    color: var(--ink);
    font-size: 0.94rem;
    margin-top: 0.35rem;
    opacity: 0.75;
    line-height: 1.6;
}

/* ---------- Step pill (numbered section header) ---------- */

.step-pill {
    display: inline-flex;
    align-items: center;
    gap: 0.6rem;
    background: var(--surface);
    border: 1.5px solid var(--lemon-mid);
    border-radius: 30px;
    padding: 0.4rem 1.1rem 0.4rem 0.5rem;
    font-size: 0.98rem;
    font-weight: 900;
    color: var(--charcoal);
    margin-bottom: 1.1rem;
    box-shadow: 0 2px 8px rgba(245,197,24,0.10);
}

.step-num {
    background: var(--lemon);
    border-radius: 50%;
    width: 26px;
    height: 26px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    font-size: 0.85rem;
    font-weight: 900;
    box-shadow: 0 1px 4px rgba(212,160,23,0.4);
}

.sec-label {
    font-size: 12px;
    font-weight: 700;
    color: var(--muted);
    letter-spacing: .04em;
    margin-bottom: 8px;
}

.info-strip {
    background: var(--lemon-soft);
    border-left: 4px solid var(--lemon);
    border-radius: 0 10px 10px 0;
    padding: 0.75rem 1.1rem;
    font-size: 0.9rem;
    color: var(--ink);
    margin-bottom: 1rem;
}

.info-strip code {
    background: var(--lemon-mid);
    color: var(--charcoal);
    padding: 1px 6px;
    border-radius: 5px;
    font-weight: 700;
}

.warn-strip {
    background: #FFF4E5;
    border-left: 4px solid #FF9500;
    border-radius: 0 10px 10px 0;
    padding: 0.75rem 1.1rem;
    font-size: 0.9rem;
    color: var(--ink);
    margin-bottom: 1rem;
}

/* ---------- Field labels ---------- */

.stTextInput label,
.stSelectbox label,
.stDateInput label,
.stNumberInput label,
.stRadio label,
.stTextArea label,
.stFileUploader label {
    font-weight: 700 !important;
    font-size: 14.5px !important;
    color: var(--charcoal) !important;
}

/* ---------- Buttons ---------- */

.stButton > button {
    background: var(--lemon) !important;
    color: var(--charcoal) !important;
    border: none !important;
    border-radius: 12px !important;
    font-weight: 700 !important;
    font-family: 'Noto Sans TC', sans-serif !important;
    font-size: 15px !important;
    padding: 0.6rem 1.2rem !important;
    transition: background 0.18s, transform 0.12s, box-shadow 0.18s !important;
    box-shadow: 0 3px 12px rgba(245,197,24,0.30) !important;
}

.stButton > button:hover {
    background: var(--lemon-dark) !important;
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 16px rgba(245,197,24,0.40) !important;
}

.stButton > button[kind="primary"] {
    background: var(--charcoal) !important;
    color: var(--lemon) !important;
    box-shadow: 0 3px 14px rgba(28,28,30,0.25) !important;
}

.stButton > button[kind="primary"]:hover {
    background: #2C2C2E !important;
}

/* secondary / ghost-style small buttons (used for select-all etc.) */
button[kind="secondary"] {
    background: var(--surface) !important;
    color: var(--charcoal) !important;
    border: 1.5px solid var(--border) !important;
    box-shadow: none !important;
}

/* ---------- Inputs ---------- */

.stTextInput input,
.stSelectbox > div > div,
.stDateInput input,
.stNumberInput input,
.stTextArea textarea {
    border-radius: 12px !important;
    border: 1.5px solid var(--border) !important;
    background: white !important;
    font-size: 15px !important;
}

.stTextInput input:focus,
.stNumberInput input:focus,
.stTextArea textarea:focus {
    border-color: var(--lemon) !important;
    box-shadow: 0 0 0 3px rgba(245,197,24,0.18) !important;
}

.stCheckbox label, .stRadio > div {
    font-weight: 600 !important;
}

/* ---------- Tabs / radio as segmented control feel ---------- */

div[role="radiogroup"] {
    gap: 0.4rem;
}

/* ---------- Metrics ---------- */

[data-testid="stMetric"] {
    background: white;
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 16px;
    box-shadow: var(--shadow);
}

[data-testid="stMetricValue"] {
    font-family: 'Space Grotesk', sans-serif;
    font-weight: 700;
}

[data-testid="stMetricLabel"] {
    font-weight: 600;
    color: var(--muted);
}

/* ---------- Cards (preview rows) ---------- */

.preview-card {
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 16px 18px;
    margin-bottom: 12px;
    background: white;
    box-shadow: var(--shadow);
}

.preview-ok {
    border-left: 6px solid var(--success);
}

.preview-ng {
    border-left: 6px solid #d4d4d8;
}

.preview-title {
    font-size: 16px;
    font-weight: 700;
    margin-bottom: 8px;
}

.preview-sub {
    color: #444;
    font-size: 14px;
    line-height: 1.7;
}

/* ---------- Code & Expander ---------- */

[data-testid="stCode"] {
    border-radius: 12px !important;
    font-size: 13px !important;
}

.streamlit-expanderHeader {
    font-weight: 700 !important;
    font-size: 0.95rem !important;
}

.streamlit-expander {
    border-radius: var(--radius) !important;
    border: 1px solid var(--border) !important;
}

hr {
    border-color: #ececec !important;
    margin: 1.6rem 0 !important;
}
</style>
""", unsafe_allow_html=True)

DEFAULT_RESULT = {
    "processed": 0,
    "success": 0,
    "failed": 0,
    "skipped": 0,
    "updated_orders": 0,
    "errors": [],
}

DEFAULT_STATE = {
    "logs": [],
    "result": None,
    "is_running": False,
    "is_logged_in": False,
    "preview_rows": [],
    "last_mode": "",
    "login_identity": "",
    "sheet_summary": None,
    "shift_import_rows": [],
    "shift_dry_run_result": None,
    "lemon_candidate": None,
    "atm_result": None,
    "atm_match_result": None,
    "atm_list_rows": None,
    "atm_list_paste_result": None,
    "clear_person_result": None,
    "lemon_scan_entries": None,
    "lemon_clear_results": None,
    # 清潔異動相關 state
    "co_calc_rows": [],
    "co_pending_rows": [],
    "co_phone_orders": [],
    "co_selected_order_no": "",
    "co_selected_order_detail": None,
    # 已登入的 requests.Session 物件，登入一次後重複使用，
    # 之後每個功能執行時優先重用這個 session，不存在才會去登入。
    "auth_session": None,
    "auth_env": "",
    "credentials_ready": False,
}

for k, v in DEFAULT_STATE.items():
    if k not in st.session_state:
        st.session_state[k] = v

st.session_state.is_running = False


def sec(title):
    st.markdown(f'<p class="sec-label">{title}</p>', unsafe_allow_html=True)


def step(num, title):
    st.markdown(
        f'<div class="step-pill"><span class="step-num">{num}</span>{title}</div>',
        unsafe_allow_html=True
    )


def normalize_result(r):
    base = DEFAULT_RESULT.copy()
    if isinstance(r, dict):
        base.update(r)
    if not isinstance(base.get("errors"), list):
        base["errors"] = []
    return base


def render_result(result):
    r = normalize_result(result)
    with result_container:
        st.markdown("---")
        step("6", "執行結果")

        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("執行筆數", r["processed"])
        c2.metric("成功", r["success"])
        c3.metric("失敗", r["failed"])
        c4.metric("略過", r["skipped"])
        c5.metric("回寫筆數", r["updated_orders"])

        if r["errors"]:
            with st.expander(f"⚠️ 錯誤明細（{len(r['errors'])} 筆）", expanded=True):
                for i, err in enumerate(r["errors"], 1):
                    st.markdown(f"**{i}.** {err}")
        elif r["processed"] > 0:
            st.success(f"✅ 全部完成，共處理 {r['processed']} 筆，成功 {r['success']} 筆。")
        else:
            st.info("執行完成，無資料被處理。")


def render_atm_result(result, container):
    r = normalize_result(result)
    with container:
        st.markdown("---")
        step("4", "執行結果")

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("執行筆數", r["processed"])
        c2.metric("成功", r["success"])
        c3.metric("失敗", r["failed"])
        c4.metric("略過", r["skipped"])

        if r["errors"]:
            with st.expander(f"⚠️ 錯誤明細（{len(r['errors'])} 筆）", expanded=True):
                for i, err in enumerate(r["errors"], 1):
                    st.markdown(f"**{i}.** {err}")
        elif r["processed"] > 0:
            st.success(f"✅ 全部完成，共處理 {r['processed']} 筆，成功 {r['success']} 筆。")
        else:
            st.info("執行完成，無資料被處理。")


def ui_log(msg):
    st.session_state.logs.append(str(msg))
    try:
        log_box.code("\n".join(st.session_state.logs[-3000:]))
    except Exception:
        pass


def safe_get(row, *keys, default=""):
    for k in keys:
        if k in row and row.get(k) is not None:
            return row.get(k)
    return default


def clear_pick_states():
    keys_to_delete = []
    for k in list(st.session_state.keys()):
        if k.startswith("pick_"):
            keys_to_delete.append(k)
    for k in keys_to_delete:
        del st.session_state[k]


def reset_before_action(clear_preview=True, clear_selection=True):
    st.session_state.logs = []
    st.session_state.result = None

    if clear_preview:
        st.session_state.preview_rows = []
        st.session_state.sheet_summary = None

    if clear_selection:
        clear_pick_states()

    try:
        log_box.code("尚未執行")
    except Exception:
        pass


def reset_before_execute_keep_preview():
    st.session_state.logs = []
    st.session_state.result = None

    try:
        log_box.code("尚未執行")
    except Exception:
        pass


def reset_mode_state_if_changed(current_mode):
    if st.session_state.last_mode != current_mode:
        st.session_state.preview_rows = []
        st.session_state.sheet_summary = None
        clear_pick_states()
        st.session_state.last_mode = current_mode


def get_session(ui_logger=None):
    """
    取得目前可用的已登入 session：
    - 如果之前已經登入過（st.session_state.auth_session 存在），直接重用，不會再登入一次。
    - 沒有的話才呼叫 memo.login() 登入一次，並把結果存起來給之後的功能繼續共用。
    這樣「找空檔」「確認勾選」這類前後兩個步驟才會是同一個 session，
    不會因為各自重新登入產生兩個互不相干的 session 導致 CSRF token 對不上（419）。
    不需要先手動按 Login——只要 Step 1 帳密欄位有填，這裡會自動登入一次。
    """
    if st.session_state.auth_session is not None:
        return st.session_state.auth_session

    if not st.session_state.get("credentials_ready"):
        raise RuntimeError("請先在「登入」區塊輸入帳號密碼")

    session = memo.login(ui_logger=ui_logger)
    st.session_state.auth_session = session
    st.session_state.is_logged_in = True
    st.session_state.login_identity = st.session_state.get("login_email", "")
    st.session_state.auth_env = st.session_state.get("login_env", "prod")
    return session


def render_preview_blocks(rows):
    step("4", "查詢結果預覽")

    if not rows:
        st.info("查無資料")
        return []

    can_rows = [r for r in rows if r.get("can_autofill")]
    no_rows = [r for r in rows if not r.get("can_autofill")]

    m1, m2, m3 = st.columns(3)
    m1.metric("查詢總筆數", len(rows))
    m2.metric("可自動回填", len(can_rows))
    m3.metric("無可參照來源", len(no_rows))

    st.markdown(
        '<div class="info-strip">每一列是「目標訂單」；若有來源訂單，代表已找到最近一筆同地址＋已付款＋已處理＋有備註的來源。若該地址完全沒有歷史訂單，會視為新成單並自動帶入固定提醒文字。</div>',
        unsafe_allow_html=True
    )

    selected_ids = []

    def render_section(title, items, section_key, default_checked):
        st.markdown(f"### {title}")

        if not items:
            st.caption("沒有資料")
            return

        c1, c2, c3 = st.columns([1, 1, 4])

        with c1:
            if st.button("本區全選", key=f"sel_{section_key}", use_container_width=True):
                for row in items:
                    oid = str(row.get("order_id", "")).strip()
                    if oid:
                        st.session_state[f"pick_{oid}"] = True

        with c2:
            if st.button("本區全不選", key=f"unsel_{section_key}", use_container_width=True):
                for row in items:
                    oid = str(row.get("order_id", "")).strip()
                    if oid:
                        st.session_state[f"pick_{oid}"] = False

        with c3:
            st.caption(f"本區共 {len(items)} 筆")

        for row in items:
            order_id = str(row.get("order_id", "")).strip()

            checked = st.checkbox(
                f"選取 {order_id}",
                key=f"pick_{order_id}",
                value=st.session_state.get(f"pick_{order_id}", default_checked),
                label_visibility="collapsed"
            )

            card_cls = "preview-card preview-ok" if row.get("can_autofill") else "preview-card preview-ng"

            target_name = row.get("customer_name", "")
            phone = row.get("phone", "")
            address = row.get("address", "")
            service_date = row.get("service_date", "")
            purchase_status_name = row.get("purchase_status_name", "")
            source_order_id = row.get("source_order_id", "")
            source_service_date = row.get("source_service_date", "")
            source_purchase_status_name = row.get("source_purchase_status_name", "")
            source_status_name = row.get("source_status_name", "")
            source_notice_preview = row.get("source_notice_preview", "")
            is_new_order = row.get("is_new_order", False)

            if is_new_order:
                source_notice_display_html = "（請於下方欄位編輯要寫入後台的提醒文字）"
            else:
                source_notice_display_html = source_notice_preview.replace("\n", "<br>") if source_notice_preview else ""

            can_autofill = row.get("can_autofill", False)

            if is_new_order:
                suggestion_text = "新成單，將帶入下方可編輯的提醒文字"
            elif can_autofill:
                suggestion_text = "建議執行"
            else:
                suggestion_text = "無可參照來源，請人工確認"

            st.markdown(f"""
            <div class="{card_cls}">
                <div class="preview-title">目前訂單：{order_id}</div>
                <div class="preview-sub">
                    <b>客戶 / 電話：</b>{target_name} / {phone}<br>
                    <b>地址：</b>{address}<br>
                    <b>目前服務日期：</b>{service_date}　
                    <b>目前付款狀態：</b>{purchase_status_name or "-"}
                </div>
                <hr style="margin:10px 0;">
                <div class="preview-sub">
                    <b>來源訂單：</b>{source_order_id or "無"}<br>
                    <b>來源服務日期：</b>{source_service_date or "-"}　
                    <b>來源付款狀態：</b>{source_purchase_status_name or "-"}　
                    <b>來源服務狀態：</b>{source_status_name or "-"}<br>
                    <b>來源備註：</b>{source_notice_display_html or "無"}
                </div>
                <div class="preview-sub" style="margin-top:8px;">
                    <b>建議：</b>{suggestion_text}
                </div>
            </div>
            """, unsafe_allow_html=True)

            if is_new_order:
                st.text_area(
                    f"✏️ 新成單提醒文字（{order_id}，可自行編輯，將寫入後台備註）",
                    value=st.session_state.get(f"new_notice_{order_id}", memo.DEFAULT_NEW_ORDER_NOTICE),
                    key=f"new_notice_{order_id}",
                    height=130,
                )

            if checked and order_id:
                selected_ids.append(order_id)

    render_section("可自動回填", can_rows, "can_autofill", True)
    render_section("無可參照來源", no_rows, "no_source", False)

    st.markdown("---")
    step("5", "執行確認")

    st.metric("目前勾選", len(selected_ids))
    st.caption("執行後會把來源客服備註（或新成單固定提醒文字）寫入目標訂單，並把目標訂單服務狀態改為已處理。")

    return selected_ids


# ============================================================
# Hero
# ============================================================

st.markdown("""
<div class="hero">
  <div class="hero-emoji">📝</div>
  <div>
    <div class="hero-title">檸檬營運自動化工具</div>
    <div class="hero-sub">訂單備註・排班功能・ATM 對帳・服務異動 整合工具</div>
  </div>
</div>
""", unsafe_allow_html=True)

# ============================================================
# Step 1：登入與環境設定（所有功能共用同一組登入狀態）
# 已登入後改成摺疊狀態，畫面比較乾淨；要換帳號再展開即可。
# 不強制先按 Login——只要帳密有填，下面任何功能執行時會自動登入。
# ============================================================

step("1", "登入與環境設定")

login_expanded = not st.session_state.is_logged_in

with st.expander(
    f"✅ 已登入：{st.session_state.login_identity}" if st.session_state.is_logged_in else "🔐 尚未登入，請輸入帳密",
    expanded=login_expanded,
):
    col_e, col_p, col_env = st.columns([2.4, 2.4, 1.2])

    with col_e:
        email = st.text_input("後台帳號", placeholder="jenny@lemonclean.com.tw", key="login_email")

    with col_p:
        password = st.text_input("後台密碼", type="password", key="login_password")

    with col_env:
        env_option = st.selectbox("環境", ["prod", "dev"], index=0, key="login_env")

    # 不論有沒有手動操作，只要帳密欄位有值就先同步給 memo 模組，
    # 這樣等一下任何功能按鈕觸發 get_session() 時，能直接拿這組帳密自動登入，
    # 不需要額外的「Login」按鈕。
    memo.set_env(env_option)
    memo.set_runtime_credentials(email, password)
    st.session_state.credentials_ready = bool(email.strip()) and bool(password.strip())

    unlock_clicked = st.button("解除鎖定 / 重新登入", use_container_width=True)

    if unlock_clicked:
        st.session_state.is_running = False
        st.session_state.logs = []
        st.session_state.auth_session = None
        st.session_state.is_logged_in = False
        st.success("已解除鎖定，下次執行任何功能時會自動重新登入。")
        st.rerun()

    # 切換 prod/dev 環境時，舊的 session 是綁在舊環境的網域上，不能繼續用，
    # 偵測到環境跟上次登入時不一樣就自動失效，下次執行任何功能時會自動重新登入。
    if (
        st.session_state.is_logged_in
        and st.session_state.auth_env
        and st.session_state.auth_env != env_option
    ):
        st.session_state.auth_session = None
        st.session_state.is_logged_in = False
        st.warning("環境已切換，下次執行功能時會自動重新登入。")

if not st.session_state.credentials_ready:
    st.markdown(
        '<div class="info-strip">⚠️ 請先在上方輸入帳號密碼，才能使用下方功能（執行功能時會自動登入，不用先按 Login）。</div>',
        unsafe_allow_html=True
    )
elif not st.session_state.is_logged_in:
    st.markdown(
        '<div class="info-strip">ℹ️ 帳密已就緒，第一次執行下方任何功能時會自動登入一次。</div>',
        unsafe_allow_html=True
    )

st.markdown("---")

# ============================================================
# Step 2：選擇功能
# ============================================================

step("2", "選擇功能")

main_section = st.selectbox(
    "功能",
    [
        "📝 訂單客服備註",
        "📅 排班功能",
        "💳 ATM 對帳",
        "🔄 服務異動",
    ],
    label_visibility="collapsed",
    key="main_section",
)

MAIN_SECTION_HELP = {
    "📝 訂單客服備註": """
    <div class="info-strip">
        <b>功能說明：</b>自動尋找同地址的歷史訂單客服備註，回填到目前未處理訂單。<br>
        <b>適用情境：</b>舊客回購、定期客戶、新成單客服整理。<br>
        <b>建議流程：</b>選擇查詢方式 → 查詢 / 預覽 → 勾選要處理的訂單 → 執行回填。
    </div>
    """,
    "📅 排班功能": """
    <div class="info-strip">
        <b>功能說明：</b>排班相關作業整合入口，包含排班匯入、檸檬人空檔查詢、清空排班。<br>
        <b>適用情境：</b>月排班、臨時派工、補人力、取消案件、班表重整。<br>
        <b>下一步：</b>請在下方選擇要使用的排班子功能。
    </div>
    """,
    "💳 ATM 對帳": """
    <div class="info-strip">
        <b>功能說明：</b>處理 ATM 待付款清單、銀行明細配對、付款狀態更新、開立發票與發送確認信。<br>
        <b>適用情境：</b>每日財務對帳、補款確認。<br>
        <b>建議流程：</b>待付款清單查詢 → 配對銀行明細 → 更新系統對帳。
    </div>
    """,
    "🔄 服務異動": """
    <div class="info-strip">
        <b>功能說明：</b>處理改期、取消、異動費、車馬費、退款、客訴退款與物損退款。<br>
        <b>適用情境：</b>客服異動處理、財務收退款同步。<br>
        <b>建議流程：</b>階段 A 查詢試算並寫入工作表 → 階段 B 讀取待處理資料並回填後台。
    </div>
    """,
}

st.markdown(MAIN_SECTION_HELP.get(main_section, ""), unsafe_allow_html=True)

shift_sub_section = None

if main_section == "📅 排班功能":
    step("3", "選擇排班子功能")

    shift_sub_section = st.radio(
        "排班子功能",
        [
            "排班匯入",
            "檸檬人空檔查詢",
            "清空排班",
        ],
        horizontal=True,
        label_visibility="collapsed",
        key="shift_sub_section",
    )

    SHIFT_SUB_HELP = {
        "排班匯入": """
        <div class="info-strip">
            <b>排班匯入：</b>上傳 Excel / CSV 批次更新專員班表。<br>
            <b>下一步：</b>上傳檔案 → Dry Run 預覽 → 確認合併結果 → 正式儲存。<br>
            <b>提醒：</b>正式儲存會直接改動後台排班資料。
        </div>
        """,
        "檸檬人空檔查詢": """
        <div class="info-strip">
            <b>檸檬人空檔查詢：</b>依指定日期與班別，自動檢查檸檬人 1～N 是否有空檔。<br>
            <b>下一步：</b>選擇日期與類型 → 尋找空檔 → 確認候選檸檬人 → 送出勾班。
        </div>
        """,
        "清空排班": """
        <div class="warn-strip">
            <b>清空排班：</b>批次移除指定人員、日期區間內的既有班表。<br>
            <b>下一步：</b>選擇清空模式 → 輸入人員與期間 / 來源清單 → 確認後執行。<br>
            <b>提醒：</b>此功能會直接更新後台排班，請確認人員與日期後再執行。
        </div>
        """,
    }

    st.markdown(SHIFT_SUB_HELP.get(shift_sub_section, ""), unsafe_allow_html=True)

st.markdown("---")


# ============================================================
# 功能一：Memo 自動回填
# ============================================================

def render_memo_section():
    step("3", "設定查詢條件")

    st.markdown(
        '<div class="info-strip"><b>下一步：</b>請選擇要用 Google Sheet、電話或搜尋條件來找訂單。查詢後會先顯示預覽，確認勾選後才會回填客服備註。</div>',
        unsafe_allow_html=True
    )

    mode = st.radio(
        "",
        ["By Google Sheet", "By 電話", "By 搜尋條件"],
        horizontal=True,
        label_visibility="collapsed",
        key="memo_mode",
    )

    reset_mode_state_if_changed(mode)

    row_spec = ""
    force = False
    sheet_run_mode = "指定列號"
    sheet_limit = 5

    phone_text = ""
    date_mode = "服務日期"
    purchase_status_name = "全部"
    start_date = None
    end_date = None

    sheet_summary_btn = False
    search_btn = False
    execute_btn = False

    MEMO_MODE_HELP = {
        "By Google Sheet": '<div class="info-strip"><b>By Google Sheet：</b>依 Sheet 列號處理，適合每日批次回填。可指定列號，也可依剩餘未處理筆數執行。</div>',
        "By 電話": '<div class="info-strip"><b>By 電話：</b>輸入一支或多支電話，系統會找出該客戶目前未處理訂單，並比對最近可參照來源訂單。</div>',
        "By 搜尋條件": '<div class="info-strip"><b>By 搜尋條件：</b>依服務日期 / 購買日期與付款狀態批次搜尋未處理訂單，適合每日整理。</div>',
    }
    st.markdown(MEMO_MODE_HELP.get(mode, ""), unsafe_allow_html=True)

    if mode == "By Google Sheet":
        sheet_run_mode = st.radio(
            "處理方式",
            ["指定列號", "依剩餘筆數處理"],
            horizontal=True
        )

        if sheet_run_mode == "指定列號":
            st.markdown(
                '<div class="info-strip">列號支援：單列 <code>2</code>、逗號分隔 <code>2,3,5</code>、區間 <code>2,3,5-7</code></div>',
                unsafe_allow_html=True
            )

            c1, c2 = st.columns([5, 1])

            with c1:
                row_spec = st.text_input("列號")

            with c2:
                st.markdown("<div style='height:26px'></div>", unsafe_allow_html=True)
                force = st.checkbox("強制重跑")

            execute_btn = st.button(
                "🚀 執行",
                use_container_width=True,
                disabled=not st.session_state.credentials_ready
            )

        else:
            c1, c2 = st.columns(2)

            with c1:
                sheet_summary_btn = st.button(
                    "🔍 查詢目前筆數",
                    use_container_width=True,
                    disabled=not st.session_state.credentials_ready
                )

            with c2:
                sheet_limit = st.number_input(
                    "本次處理筆數",
                    min_value=1,
                    value=5
                )

            if st.session_state.sheet_summary:
                s = st.session_state.sheet_summary
                m1, m2, m3 = st.columns(3)
                m1.metric("總筆數", s.get("total_rows", 0))
                m2.metric("未處理筆數", s.get("pending_rows", 0))
                m3.metric("已處理筆數", s.get("done_rows", 0))

            execute_btn = st.button(
                "🚀 執行前 N 筆未處理資料",
                use_container_width=True,
                disabled=not st.session_state.credentials_ready
            )

    elif mode == "By 電話":
        phone_text = st.text_area(
            "電話號碼",
            placeholder="可輸入多支，以逗號或換行分隔，例：0912345678,0922345678"
        )

        st.caption("會先找出「目標訂單」，再比對最近一筆可參照的來源訂單。")

        c1, c2 = st.columns(2)

        with c1:
            search_btn = st.button(
                "🔍 查詢列表",
                use_container_width=True,
                disabled=not st.session_state.credentials_ready
            )

        with c2:
            execute_btn = st.button(
                "🚀 執行勾選項目",
                use_container_width=True,
                disabled=not st.session_state.credentials_ready
            )

    else:
        c1, c2 = st.columns(2)

        with c1:
            date_mode = st.selectbox("日期條件", ["服務日期", "購買日期"])

        with c2:
            purchase_status_name = st.selectbox(
                "付款狀態",
                ["全部", "已付款", "未付款"],
                index=0
            )

        c3, c4 = st.columns(2)

        with c3:
            start_date = st.date_input("開始日期", value=None)

        with c4:
            end_date = st.date_input("結束日期", value=None)

        st.caption("搜尋條件固定只撈服務狀態＝未處理的目標訂單，再比對最近的可參照來源。")

        c5, c6 = st.columns(2)

        with c5:
            search_btn = st.button(
                "🔍 查詢列表",
                use_container_width=True,
                disabled=not st.session_state.credentials_ready
            )

        with c6:
            execute_btn = st.button(
                "🚀 執行勾選項目",
                use_container_width=True,
                disabled=not st.session_state.credentials_ready
            )

    global log_box, result_container

    with st.expander("執行 LOG", expanded=True):
        log_box = st.empty()
        log_box.code(
            "\n".join(st.session_state.logs[-3000:])
            if st.session_state.logs
            else "尚未執行"
        )

    result_container = st.container()

    if st.session_state.result is not None:
        render_result(st.session_state.result)

    if sheet_summary_btn:
        try:
            st.session_state.is_running = True
            reset_before_action(clear_preview=True, clear_selection=True)
            ui_log("===== 查詢目前筆數 =====")

            with st.spinner("查詢中，請稍候…"):
                st.session_state.sheet_summary = memo.get_sheet_summary(ui_logger=ui_log)

            ui_log("✅ 查詢完成")

        except Exception as e:
            ui_log(f"❌ 查詢失敗：{e}")
            st.error(str(e))

        finally:
            st.session_state.is_running = False

    if search_btn:
        try:
            st.session_state.is_running = True
            reset_before_action(clear_preview=True, clear_selection=True)
            ui_log("===== 開始查詢 =====")

            with st.spinner("查詢中，請稍候…"):
                session = get_session(ui_logger=ui_log)

                if mode == "By 電話":
                    if not phone_text.strip():
                        raise ValueError("請輸入至少一支電話")

                    preview_rows = memo.preview_by_phone_multi(
                        phone_text=phone_text.strip(),
                        ui_logger=ui_log,
                        session=session,
                    )

                else:
                    start_text = start_date.strftime("%Y/%m/%d") if start_date else ""
                    end_text = end_date.strftime("%Y/%m/%d") if end_date else ""

                    preview_rows = memo.preview_by_conditions(
                        date_mode=date_mode,
                        date_start=start_text,
                        date_end=end_text,
                        purchase_status_name=purchase_status_name,
                        ui_logger=ui_log,
                        session=session,
                    )

            st.session_state.preview_rows = preview_rows or []
            ui_log(f"✅ 查詢完成，共 {len(st.session_state.preview_rows)} 筆")
            st.rerun()

        except Exception as e:
            ui_log(f"❌ 查詢錯誤：{e}")
            st.error(str(e))

        finally:
            st.session_state.is_running = False

    if mode in ["By 電話", "By 搜尋條件"] and st.session_state.preview_rows:
        st.markdown("---")
        render_preview_blocks(st.session_state.preview_rows)

    if execute_btn:
        try:
            st.session_state.is_running = True
            reset_before_execute_keep_preview()

            if mode == "By Google Sheet":
                ui_log("===== 開始執行 =====")

                with st.spinner("執行中，請稍候…"):
                    session = get_session(ui_logger=ui_log)

                    if sheet_run_mode == "指定列號":
                        result = memo.main(
                            row_spec=row_spec,
                            force=force,
                            ui_logger=ui_log,
                            session=session,
                        )
                    else:
                        result = memo.main_first_n_pending(
                            limit=int(sheet_limit),
                            ui_logger=ui_log,
                            session=session,
                        )

            else:
                if not st.session_state.preview_rows:
                    raise RuntimeError("請先查詢列表")

                current_selected_ids = []
                custom_notices = {}

                for row in st.session_state.preview_rows:
                    oid = str(safe_get(row, "order_id", default="")).strip()

                    if oid and st.session_state.get(f"pick_{oid}", False):
                        current_selected_ids.append(oid)

                        if row.get("is_new_order"):
                            custom_notices[oid] = st.session_state.get(
                                f"new_notice_{oid}", memo.DEFAULT_NEW_ORDER_NOTICE
                            )

                if not current_selected_ids:
                    raise RuntimeError("請先勾選要執行的資料")

                ui_log("===== 開始執行勾選項目 =====")
                ui_log(f"勾選筆數：{len(current_selected_ids)}")

                with st.spinner("執行中，請稍候…"):
                    session = get_session(ui_logger=ui_log)
                    result = memo.main_by_selected_order_ids(
                        order_ids=current_selected_ids,
                        ui_logger=ui_log,
                        session=session,
                        custom_notices=custom_notices,
                    )

            ui_log("===== 執行完成 =====")
            st.session_state.result = result
            render_result(result)

        except Exception as e:
            ui_log(f"❌ 執行錯誤：{e}")
            st.session_state.result = {
                **DEFAULT_RESULT,
                "failed": 1,
                "errors": [str(e)]
            }
            render_result(st.session_state.result)

        finally:
            st.session_state.is_running = False


# ============================================================
# 功能二：排班勾選（匯入檔）
# ============================================================

def render_shift_import_section():
    step("3", "上傳排班匯入檔")

    st.markdown(
        '<div class="info-strip">欄位需求：<code>地區</code> / <code>日期</code> / <code>類型</code> / <code>時段</code> / <code>名稱</code>。'
        '「類型」支援：全6、全8、上4、上3、上2、下4、下3、下2、晚2、清。</div>',
        unsafe_allow_html=True
    )
    st.markdown(
        '<div class="warn-strip">⚠️ 這個功能會直接改動後台真實排班資料，請務必先用「Dry Run 預覽」確認合併結果正確，再按「正式儲存」。</div>',
        unsafe_allow_html=True
    )

    uploaded_file = st.file_uploader("選擇 Excel / CSV 檔案", type=["xlsx", "xls", "csv"])

    c1, c2 = st.columns(2)
    with c1:
        dry_run_btn = st.button(
            "🔍 Dry Run 預覽（不會寫入）",
            use_container_width=True,
            disabled=not (st.session_state.credentials_ready and uploaded_file is not None),
        )
    with c2:
        execute_btn = st.button(
            "🚀 正式儲存",
            use_container_width=True,
            disabled=not (
                st.session_state.credentials_ready
                and st.session_state.shift_dry_run_result is not None
            ),
        )

    with st.expander("執行 LOG", expanded=True):
        log_box_local = st.empty()
        log_box_local.code(
            "\n".join(st.session_state.logs[-3000:])
            if st.session_state.logs
            else "尚未執行"
        )

    def shift_ui_log(msg):
        st.session_state.logs.append(str(msg))
        try:
            log_box_local.code("\n".join(st.session_state.logs[-3000:]))
        except Exception:
            pass

    if dry_run_btn and uploaded_file is not None:
        try:
            st.session_state.logs = []
            st.session_state.shift_dry_run_result = None
            shift_ui_log("===== 開始解析匯入檔 =====")

            rows = shift.parse_import_file(uploaded_file, uploaded_file.name)
            shift_ui_log(f"解析完成，共 {len(rows)} 筆有效資料")
            st.session_state.shift_import_rows = rows

            with st.spinner("Dry Run 中，請稍候…"):
                session = get_session(ui_logger=shift_ui_log)
                result = shift.process_import_file(rows, dry_run=True, ui_logger=shift_ui_log, session=session)

            st.session_state.shift_dry_run_result = result
            shift_ui_log("===== Dry Run 完成 =====")

        except Exception as e:
            shift_ui_log(f"❌ Dry Run 失敗：{e}")
            st.error(str(e))

    if st.session_state.shift_dry_run_result:
        result = st.session_state.shift_dry_run_result

        st.markdown("---")
        step("4", "Dry Run 結果預覽")

        m1, m2, m3 = st.columns(3)
        m1.metric("處理人數", result.get("processed_people", 0))
        m2.metric("處理月份數", result.get("processed_months", 0))
        m3.metric("略過人數", len(result.get("skipped", [])))

        if result.get("errors"):
            with st.expander(f"⚠️ 訊息（{len(result['errors'])} 筆）", expanded=True):
                for i, err in enumerate(result["errors"], 1):
                    st.markdown(f"**{i}.** {err}")

        for name, month, merged in result.get("dry_run_payloads", []):
            with st.expander(f"{name} — {month}（合併後共 {len(merged)} 筆勾選）", expanded=False):
                if merged:
                    sorted_items = sorted(merged.items())
                    st.code("\n".join(f"{k} = {v}" for k, v in sorted_items))
                else:
                    st.caption("這個月份合併後沒有任何勾選（可能是被「清」全部清空了）")

        st.caption("確認上面合併後的結果沒有問題，再按「正式儲存」送出。")

    if execute_btn:
        try:
            st.session_state.logs = []
            ui_log("===== 開始正式儲存 =====")

            rows = st.session_state.shift_import_rows
            with st.spinner("儲存中，請稍候…"):
                session = get_session(ui_logger=ui_log)
                result = shift.process_import_file(rows, dry_run=False, ui_logger=ui_log, session=session)

            ui_log("===== 儲存完成 =====")
            st.success(f"✅ 完成，共儲存 {result.get('saved', 0)} 個人/月份")

            if result.get("errors"):
                st.error("\n".join(result["errors"][:20]))

            st.session_state.shift_dry_run_result = None

        except Exception as e:
            ui_log(f"❌ 儲存失敗：{e}")
            st.error(str(e))


# ============================================================
# 功能三：檸檬人空檔勾選
# ============================================================

def render_lemon_ren_section():
    step("3", "設定要找空檔的日期與類型")

    st.markdown(
        '<div class="info-strip">會依序檢查 檸檬人1 ~ 檸檬人N，找出「該日期、該類型對應的時段」目前沒有被勾選的第一位，'
        '當作可用的佔位帳號。找到後可以直接送出勾選，或是只查詢不勾選。</div>',
        unsafe_allow_html=True
    )

    c1, c2, c3 = st.columns([1.3, 1.3, 1])

    with c1:
        target_date = st.date_input("日期")

    with c2:
        type_options = list(shift.TYPE_MAP.keys())
        type_val = st.selectbox("類型", type_options)

    with c3:
        max_count = st.number_input("檸檬人最大數量", min_value=1, max_value=50, value=shift.LEMON_REN_DEFAULT_COUNT)

    find_btn = st.button(
        "🔍 尋找空檔檸檬人",
        use_container_width=True,
        disabled=not st.session_state.credentials_ready,
    )

    with st.expander("執行 LOG", expanded=True):
        log_box_local = st.empty()
        log_box_local.code(
            "\n".join(st.session_state.logs[-3000:])
            if st.session_state.logs
            else "尚未執行"
        )

    def lemon_ui_log(msg):
        st.session_state.logs.append(str(msg))
        try:
            log_box_local.code("\n".join(st.session_state.logs[-3000:]))
        except Exception:
            pass

    if find_btn:
        try:
            st.session_state.logs = []
            st.session_state.lemon_candidate = None
            lemon_ui_log("===== 開始尋找空檔檸檬人 =====")

            date_str = target_date.strftime("%Y-%m-%d")

            with st.spinner("查詢中，請稍候…"):
                session = get_session(ui_logger=lemon_ui_log)
                candidate = shift.find_available_lemon_ren(
                    session=session,
                    date_val=date_str,
                    type_val=type_val,
                    max_count=int(max_count),
                    log=lemon_ui_log,
                )

            st.session_state.lemon_candidate = candidate
            lemon_ui_log("===== 查詢完成 =====")

        except Exception as e:
            lemon_ui_log(f"❌ 查詢失敗：{e}")
            st.error(str(e))

    candidate = st.session_state.lemon_candidate

    if candidate:
        st.markdown("---")
        step("4", "查詢結果")

        if candidate.get("found"):
            checked_names = ", ".join(c["name"] for c in candidate.get("checked_candidates", [])) or "無，第一位就是空的"
            date_part = candidate["slot_key"].rsplit("_", 1)[0]

            st.markdown(f"""
            <div class="preview-card preview-ok">
                <div class="preview-title">✅ 找到空檔：{candidate['name']}</div>
                <div class="preview-sub">
                    <b>日期：</b>{date_part}<br>
                    <b>類型：</b>{type_val}（slot 值：{candidate['value']}）<br>
                    <b>已檢查並跳過：</b>{checked_names}
                </div>
            </div>
            """, unsafe_allow_html=True)

            confirm_btn = st.button(
                f"🚀 確認勾選「{candidate['name']}」並儲存",
                type="primary",
                use_container_width=True,
            )

            if confirm_btn:
                try:
                    ui_log(f"===== 確認勾選 {candidate['name']} =====")
                    with st.spinner("儲存中，請稍候…"):
                        session = get_session(ui_logger=ui_log)
                        shift.confirm_lemon_ren_assignment(session, candidate, log=ui_log)

                    st.success(f"✅ 已將「{candidate['name']}」勾選並儲存")
                    st.session_state.lemon_candidate = None

                except Exception as e:
                    ui_log(f"❌ 勾選失敗：{e}")
                    st.error(str(e))

        else:
            checked_names = ", ".join(c["name"] for c in candidate.get("checked_candidates", [])) or "無"

            st.markdown(f"""
            <div class="preview-card preview-ng">
                <div class="preview-title">❌ 沒有找到空檔</div>
                <div class="preview-sub">
                    檸檬人1 ~ 檸檬人{max_count} 在這個日期＋類型的時段全部被佔用，或是找不到對應帳號。<br>
                    <b>已檢查：</b>{checked_names}
                </div>
            </div>
            """, unsafe_allow_html=True)


# ============================================================
# 功能四：ATM 對帳
# ============================================================

def render_atm_section():
    step("3", "選擇 ATM 對帳步驟")

    atm_mode = st.radio(
        "",
        ["待付款清單查詢（/ATM-list）", "配對銀行明細", "更新系統對帳"],
        horizontal=True,
        label_visibility="collapsed",
        key="atm_mode",
    )

    ATM_MODE_HELP = {
        "待付款清單查詢（/ATM-list）": '<div class="info-strip"><b>步驟 1：</b>從後台查詢 ATM 待付款訂單，整理後貼到 ATM 工作表 I～L 欄。</div>',
        "配對銀行明細": '<div class="info-strip"><b>步驟 2：</b>用金額、末碼、姓名 / 備註或時間自動配對銀行明細與待付款訂單。</div>',
        "更新系統對帳": '<div class="warn-strip"><b>步驟 3：</b>確認配對結果後，更新後台付款狀態、開立發票、發送確認信，並回寫 Sheet。此步驟會直接更新系統。</div>',
    }
    st.markdown(ATM_MODE_HELP.get(atm_mode, ""), unsafe_allow_html=True)

    if atm_mode.startswith("待付款清單查詢"):
        render_atm_list_mode()
    elif atm_mode.startswith("配對銀行明細"):
        render_atm_auto_match_mode()
    else:
        render_atm_reconcile_mode()


def render_atm_reconcile_mode():
    step("5", "更新系統對帳")

    st.markdown(
        '<div class="info-strip">完成「待付款清單查詢」與「配對銀行明細」後，再用這裡依序處理已確認的對帳列：搜尋訂單 → 按已付款 → 開立發票 → 發確認信，'
        '完成後回填 P=對帳完成時間（台北時間）、Q=付款時間、R=發票號碼、S=發確認信，並在 T 欄標示已更新系統。</div>',
        unsafe_allow_html=True
    )
    st.markdown(
        '<div class="warn-strip">⚠️ 這是最後一步系統更新；三個動作（尤其是發確認信）都是「點了就送出」，沒有預覽機制，輸入列號後按執行就會直接全部跑，請務必先確認列號正確再送出。</div>',
        unsafe_allow_html=True
    )

    c1, c2 = st.columns([1, 3])

    with c1:
        region = st.selectbox("地區", ["台北", "台中"], key="atm_reconcile_region")

    with c2:
        row_spec = st.text_input(
            "列號",
            placeholder="支援：單列 2、逗號分隔 2,3,5、區間 2,3,5-7，例：241,243,246-248"
        )

    st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

    c3, c4, c5 = st.columns(3)

    with c3:
        do_mark_paid = st.checkbox("按已付款", value=True)

    with c4:
        do_issue_invoice = st.checkbox("開立發票", value=True)

    with c5:
        do_send_mail = st.checkbox("發確認信", value=True)

    execute_btn = st.button(
        "🚀 執行",
        use_container_width=True,
        disabled=not (st.session_state.credentials_ready and bool(row_spec.strip())),
    )

    with st.expander("執行 LOG", expanded=True):
        log_box_local = st.empty()
        log_box_local.code(
            "\n".join(st.session_state.logs[-3000:])
            if st.session_state.logs
            else "尚未執行"
        )

    def atm_ui_log(msg):
        st.session_state.logs.append(str(msg))
        try:
            log_box_local.code("\n".join(st.session_state.logs[-3000:]))
        except Exception:
            pass

    atm_result_container = st.container()

    if st.session_state.get("atm_result") is not None:
        render_atm_result(st.session_state.atm_result, atm_result_container)

    if execute_btn:
        try:
            st.session_state.logs = []
            st.session_state.atm_result = None
            atm_ui_log(f"===== 開始更新系統對帳（{region}）=====")

            if not (do_mark_paid or do_issue_invoice or do_send_mail):
                raise ValueError("請至少勾選一項要執行的動作")

            with st.spinner("執行中，請稍候…"):
                session = get_session(ui_logger=atm_ui_log)
                result = atm.process_atm_rows(
                    region=region,
                    row_spec=row_spec,
                    do_mark_paid=do_mark_paid,
                    do_issue_invoice=do_issue_invoice,
                    do_send_mail=do_send_mail,
                    ui_logger=atm_ui_log,
                    session=session,
                )

            atm_ui_log("===== 執行完成 =====")
            st.session_state.atm_result = result
            render_atm_result(result, atm_result_container)

        except Exception as e:
            atm_ui_log(f"❌ 執行錯誤：{e}")
            st.session_state.atm_result = {
                **DEFAULT_RESULT,
                "failed": 1,
                "errors": [str(e)],
            }
            render_atm_result(st.session_state.atm_result, atm_result_container)


def render_atm_auto_match_mode():
    step("4", "配對銀行明細")

    st.markdown(
        '<div class="info-strip">先完成「待付款清單查詢」產生 I-L 欄，再貼上 A-F 銀行明細；M 欄可等客人告知末碼後填入。'
        '按下方按鈕會自動用「金額＋末碼」優先配對；若客人有寫匯款備註、沒有末碼，則改用「金額＋姓名/備註」配對。'
        '成功配對會寫回 I~O 欄、P 欄台北時間與 T 欄狀態；I/N/O 會維持下拉選單；下方待配對列被清空後也會保留 I/N/O 下拉選單，P/T 若原為下拉選單會先清除該格驗證，不會覆蓋 G 欄；Q~S 保留給系統對帳結果。</div>',
        unsafe_allow_html=True
    )
    st.markdown(
        '<div class="warn-strip">⚠️ 不可只靠金額唯一自動配對；必須有末碼、姓名/備註或時間相符依據；若符合需確認、非訂單收入或疑似拆單規則，會先預填 I~O、P 欄台北時間，並在 T 欄標示狀態；多筆或找不到時只顯示 LOG，不會修改 G 欄。</div>',
        unsafe_allow_html=True
    )

    row_spec = st.text_input("指定銀行列號", placeholder="例如：762-764,767-771")

    c1, c2, c3, c4 = st.columns([1, 1, 1, 1])

    with c1:
        region = st.selectbox("地區", ["台北", "台中"], key="atm_match_region")

    with c2:
        default_service_type = st.text_input("預設服務類別", value="清潔", key="atm_match_service_type")

    with c3:
        default_fee_type = st.text_input("預設費用類別", value="服務費用", key="atm_match_fee_type")

    with c4:
        st.markdown("<div style='height:26px'></div>", unsafe_allow_html=True)
        overwrite_existing = st.checkbox("覆蓋已配對列", value=False, key="atm_match_overwrite")

    allow_review_prefill = st.checkbox(
        "允許需確認候選預填",
        value=True,
        key="atm_match_allow_review_prefill",
        help="符合 M欄日期時間=B欄、F欄與K欄姓名相近、或K欄姓名已在上方對帳列表出現時，會先預填 I~O 並在 LOG 標示需確認。"
    )

    execute_btn = st.button(
        "🚀 配對銀行明細",
        use_container_width=True,
        disabled=not st.session_state.credentials_ready,
    )

    with st.expander("執行 LOG", expanded=True):
        log_box_local = st.empty()
        log_box_local.code(
            "\n".join(st.session_state.logs[-3000:])
            if st.session_state.logs
            else "尚未執行"
        )

    def atm_match_ui_log(msg):
        st.session_state.logs.append(str(msg))
        try:
            log_box_local.code("\n".join(st.session_state.logs[-3000:]))
        except Exception:
            pass

    result_container_local = st.container()
    if st.session_state.get("atm_match_result") is not None:
        render_atm_result(st.session_state.atm_match_result, result_container_local)

    if execute_btn:
        try:
            st.session_state.logs = []
            st.session_state.atm_match_result = None
            atm_match_ui_log(f"===== 開始配對銀行明細（{region}）=====")

            with st.spinner("配對中，請稍候…"):
                result = atm.auto_match_bank_rows(
                    region=region,
                    row_spec=row_spec.strip(),
                    overwrite_existing=overwrite_existing,
                    default_service_type=default_service_type.strip() or "清潔",
                    default_fee_type=default_fee_type.strip() or "服務費用",
                    allow_review_prefill=allow_review_prefill,
                    ui_logger=atm_match_ui_log,
                )

            atm_match_ui_log("===== 配對銀行明細完成 =====")
            st.session_state.atm_match_result = result
            render_atm_result(result, result_container_local)

        except Exception as e:
            atm_match_ui_log(f"❌ 自動配對失敗：{e}")
            st.session_state.atm_match_result = {
                **DEFAULT_RESULT,
                "failed": 1,
                "errors": [str(e)],
            }
            render_atm_result(st.session_state.atm_match_result, result_container_local)


def render_atm_list_mode():
    step("3", "待付款清單查詢")

    st.markdown(
        '<div class="info-strip">會用「訂購日期-迄」「勾選訂單統計表」「付款狀態：待付款」「付款方式：ATM」這組條件去查詢，'
        '整理成「訂單服務年月｜訂單編號｜客戶名稱｜總金額扣車馬費」，貼到跟 ATM 對帳相同的工作表（從 B 欄最後一筆資料下方 5 列開始的 I~L 欄）。</div>',
        unsafe_allow_html=True
    )

    c1, c2 = st.columns([1, 2])

    with c1:
        region = st.selectbox("要貼到哪個地區的工作表", ["台北", "台中"], key="atm_list_region")

    with c2:
        date_until = st.date_input(
            "訂購日期-迄（預設為前一天）",
            value=date.today() - timedelta(days=1),
            key="atm_list_date_until",
        )

    search_btn = st.button(
        "🔍 查詢待付款 ATM 名單",
        use_container_width=True,
        disabled=not st.session_state.credentials_ready,
    )

    with st.expander("執行 LOG", expanded=True):
        log_box_local = st.empty()
        log_box_local.code(
            "\n".join(st.session_state.logs[-3000:])
            if st.session_state.logs
            else "尚未執行"
        )

    def atm_list_ui_log(msg):
        st.session_state.logs.append(str(msg))
        try:
            log_box_local.code("\n".join(st.session_state.logs[-3000:]))
        except Exception:
            pass

    if search_btn:
        try:
            st.session_state.logs = []
            st.session_state.atm_list_rows = None
            st.session_state.atm_list_paste_result = None
            atm_list_ui_log("===== 開始查詢 ATM 待付款名單 =====")

            with st.spinner("查詢中，請稍候…"):
                session = get_session(ui_logger=atm_list_ui_log)
                rows = atm.search_atm_unpaid_orders(
                    session=session,
                    date_until=date_until.strftime("%Y-%m-%d"),
                    ui_logger=atm_list_ui_log,
                )

            st.session_state.atm_list_rows = rows
            atm_list_ui_log("===== 查詢完成 =====")
            st.rerun()

        except Exception as e:
            atm_list_ui_log(f"❌ 查詢失敗：{e}")
            st.error(str(e))

    rows = st.session_state.get("atm_list_rows")

    if rows is not None:
        st.markdown("---")
        step("4", "查詢結果")

        if not rows:
            st.info("查無符合條件的待付款 ATM 訂單。")
        else:
            st.metric("查到筆數", len(rows))

            preview_lines = [
                f"{r['year_month']}　{r['order_no']}　{r['name']}　${r['net_amount']}"
                for r in rows
            ]
            st.code("\n".join(preview_lines))

            st.markdown(
                f'<div class="warn-strip">⚠️ 確認貼上後，會把以上 {len(rows)} 筆資料寫入「{region}」ATM 對帳工作表的 I~L 欄，沒有逐筆預覽機制。</div>',
                unsafe_allow_html=True
            )

            paste_btn = st.button(
                f"🚀 貼上到「{region}」ATM 對帳工作表",
                type="primary",
                use_container_width=True,
            )

            if paste_btn:
                try:
                    atm_list_ui_log(f"===== 開始貼上到「{region}」ATM 對帳工作表 =====")
                    with st.spinner("貼上中，請稍候…"):
                        paste_result = atm.paste_atm_unpaid_list(
                            region=region,
                            rows=rows,
                            ui_logger=atm_list_ui_log,
                        )

                    st.session_state.atm_list_paste_result = paste_result
                    atm_list_ui_log("===== 貼上完成 =====")
                    st.rerun()

                except Exception as e:
                    atm_list_ui_log(f"❌ 貼上失敗：{e}")
                    st.error(str(e))

    if st.session_state.get("atm_list_paste_result") is not None:
        st.markdown("---")
        step("5", "貼上結果")

        pr = st.session_state.get("atm_list_paste_result")
        if pr.get("errors"):
            st.error("；".join(pr["errors"]))
        else:
            st.success(
                f"✅ 已從第 {pr.get('start_row')} 列開始，貼上 {pr.get('pasted', 0)} 筆資料到 I~L 欄。"
            )


# ============================================================
# 功能五：清空排班
# ============================================================

def render_clear_shift_section():
    clear_mode = st.radio(
        "",
        ["手動清空（某人 / 某段期間）", "自動清除候補檸檬人（從未配班清單）"],
        horizontal=True,
        label_visibility="collapsed",
        key="clear_shift_mode",
    )

    # --------------------------------------------------------
    # 模式一：手動清空某人 / 某段期間
    # --------------------------------------------------------
    if clear_mode == "手動清空（某人 / 某段期間）":
        step("3", "設定要清空的人員與期間")

        st.markdown(
            '<div class="info-strip">輸入專員姓名（含檸檬人，例如「檸檬人3」「檸檬人甲」），可用逗號分隔輸入多人'
            '（例如「檸檬人2,檸檬人4」），會把每個人在指定期間內，每一天的 全天/上午/下午/晚上 四個時段全部清空並儲存。</div>',
            unsafe_allow_html=True
        )
        st.markdown(
            '<div class="warn-strip">⚠️ 這個動作會直接覆寫後台真實排班資料，且沒有預覽機制，請務必確認姓名與日期區間正確再執行。</div>',
            unsafe_allow_html=True
        )

        c1, c2, c3 = st.columns([2, 1.3, 1.3])

        with c1:
            target_names_raw = st.text_input(
                "人員姓名",
                placeholder="例如：蔡立娟 或 檸檬人3，多人用逗號分隔：檸檬人2,檸檬人4"
            )

        with c2:
            range_start = st.date_input("開始日期", key="clear_range_start")

        with c3:
            range_end = st.date_input("結束日期", key="clear_range_end")

        target_names = [n.strip() for n in re.split(r"[,，]", target_names_raw) if n.strip()]

        if len(target_names) > 1:
            st.caption(f"將清空 {len(target_names)} 人：{'、'.join(target_names)}")

        execute_btn = st.button(
            "🚀 執行清空",
            use_container_width=True,
            disabled=not (st.session_state.credentials_ready and bool(target_names)),
        )

        with st.expander("執行 LOG", expanded=True):
            log_box_local = st.empty()
            log_box_local.code(
                "\n".join(st.session_state.logs[-3000:])
                if st.session_state.logs
                else "尚未執行"
            )

        def clear_ui_log(msg):
            st.session_state.logs.append(str(msg))
            try:
                log_box_local.code("\n".join(st.session_state.logs[-3000:]))
            except Exception:
                pass

        if st.session_state.clear_person_result is not None:
            results = st.session_state.clear_person_result
            if isinstance(results, dict):
                results = [results]
            st.markdown("---")
            step("4", "執行結果")

            total_cleared_dates = sum(len(r.get("cleared_dates", [])) for r in results)
            total_untouched = sum(len(r.get("untouched_dates", [])) for r in results)
            total_slots = sum(r.get("cleared_slot_count", 0) for r in results)

            c1, c2, c3 = st.columns(3)
            c1.metric("清到資料的天數", total_cleared_dates)
            c2.metric("原本就沒勾選的天數", total_untouched)
            c3.metric("移除的勾選筆數", total_slots)

            for r in results:
                if r.get("errors"):
                    with st.expander(f"⚠️ 「{r.get('name', '')}」錯誤明細（{len(r['errors'])} 筆）", expanded=True):
                        for i, err in enumerate(r["errors"], 1):
                            st.markdown(f"**{i}.** {err}")
                else:
                    st.success(
                        f"✅ 已清空「{r.get('name', '')}」指定期間的排班"
                        f"（{len(r.get('cleared_dates', []))} 天有清到資料）。"
                    )

        if execute_btn:
            try:
                st.session_state.logs = []
                st.session_state.clear_person_result = None
                clear_ui_log(f"===== 開始清空 {len(target_names)} 人的排班：{'、'.join(target_names)} =====")

                results = []
                with st.spinner("執行中，請稍候…"):
                    session = get_session(ui_logger=clear_ui_log)
                    for n in target_names:
                        clear_ui_log(f"\n----- 清空「{n}」-----")
                        result = shift.clear_person_shift_range(
                            session=session,
                            name=n,
                            date_start=range_start.strftime("%Y-%m-%d"),
                            date_end=range_end.strftime("%Y-%m-%d"),
                            ui_logger=clear_ui_log,
                        )
                        results.append(result)

                clear_ui_log("===== 執行完成 =====")
                st.session_state.clear_person_result = results
                st.rerun()

            except Exception as e:
                clear_ui_log(f"❌ 執行錯誤：{e}")
                st.error(str(e))

    # --------------------------------------------------------
    # 模式二：自動清除候補檸檬人（從未配班清單）
    # --------------------------------------------------------
    else:
        step("3", "設定要掃描的週次")

        st.markdown(
            '<div class="info-strip">輸入該週任一天的日期，會抓清潔班表（每頁一週）裡每一天「未配班」灰底清單，'
            '找出裡面出現的檸檬人（代表檸檬人目前佔用著該時段），先列出來給你確認，再決定要不要清空。</div>',
            unsafe_allow_html=True
        )

        scan_date = st.date_input("週次內任一天的日期", key="lemon_scan_date")

        scan_btn = st.button(
            "🔍 掃描未配班清單",
            use_container_width=True,
            disabled=not st.session_state.credentials_ready,
        )

        with st.expander("執行 LOG", expanded=True):
            log_box_local = st.empty()
            log_box_local.code(
                "\n".join(st.session_state.logs[-3000:])
                if st.session_state.logs
                else "尚未執行"
            )

        def clear_ui_log(msg):
            st.session_state.logs.append(str(msg))
            try:
                log_box_local.code("\n".join(st.session_state.logs[-3000:]))
            except Exception:
                pass

        if scan_btn:
            try:
                st.session_state.logs = []
                st.session_state.lemon_scan_entries = None
                st.session_state.lemon_clear_results = None
                clear_ui_log("===== 開始掃描未配班清單中的檸檬人 =====")

                with st.spinner("掃描中，請稍候…"):
                    session = get_session(ui_logger=clear_ui_log)
                    entries = shift.find_unassigned_lemon_bookings(
                        session=session,
                        query_date=scan_date.strftime("%Y-%m-%d"),
                        ui_logger=clear_ui_log,
                    )

                st.session_state.lemon_scan_entries = entries
                clear_ui_log("===== 掃描完成 =====")
                st.rerun()

            except Exception as e:
                clear_ui_log(f"❌ 掃描失敗：{e}")
                st.error(str(e))

        entries = st.session_state.lemon_scan_entries

        if entries is not None:
            st.markdown("---")
            step("4", "掃描結果")

            if not entries:
                st.info("這一週的未配班清單裡沒有發現檸檬人。")
            else:
                by_name = {}
                for e in entries:
                    by_name.setdefault(e["name"], []).append(e["date"])

                st.metric("發現的檸檬人數", len(by_name))

                for name, dates in by_name.items():
                    st.markdown(f"""
                    <div class="preview-card preview-ok">
                        <div class="preview-title">{name}</div>
                        <div class="preview-sub"><b>佔用日期：</b>{"、".join(sorted(set(dates)))}</div>
                    </div>
                    """, unsafe_allow_html=True)

                st.markdown(
                    '<div class="warn-strip">⚠️ 確認執行後，會把上面每個檸檬人在列出的日期，整天（全天/上午/下午/晚上）的勾選全部清空並儲存，沒有逐筆預覽機制。</div>',
                    unsafe_allow_html=True
                )

                confirm_btn = st.button(
                    "🚀 確認清空以上檸檬人佔用的時段",
                    type="primary",
                    use_container_width=True,
                )

                if confirm_btn:
                    try:
                        clear_ui_log("===== 開始清空候補檸檬人佔用的時段 =====")
                        with st.spinner("清空中，請稍候…"):
                            session = get_session(ui_logger=clear_ui_log)
                            results = shift.clear_unassigned_lemon_bookings(
                                session=session,
                                entries=entries,
                                ui_logger=clear_ui_log,
                            )

                        st.session_state.lemon_clear_results = results
                        clear_ui_log("===== 清空完成 =====")
                        st.rerun()

                    except Exception as e:
                        clear_ui_log(f"❌ 清空失敗：{e}")
                        st.error(str(e))

        if st.session_state.lemon_clear_results is not None:
            st.markdown("---")
            step("5", "清空結果")

            for r in st.session_state.lemon_clear_results:
                if r.get("errors"):
                    st.error(f"❌ {r['name']}：{'；'.join(r['errors'])}")
                else:
                    st.success(
                        f"✅ {r['name']}：清空 {len(r.get('cleared_dates', []))} 天，"
                        f"移除 {r.get('cleared_slot_count', 0)} 筆勾選"
                    )


# ============================================================
# 功能六：清潔異動（車馬費／異動服務收款／異動服務退款／加時／減時）
# ============================================================

def render_change_order_section():
    step("3", "選擇服務異動步驟")

    co_mode = st.radio(
        "",
        ["階段 A：查詢試算（寫入清潔異動工作表）", "階段 B：回填系統（讀工作表寫回後台）"],
        horizontal=True,
        label_visibility="collapsed",
        key="change_order_mode",
    )

    CHANGE_ORDER_MODE_HELP = {
        "階段 A：查詢試算（寫入清潔異動工作表）": '<div class="info-strip"><b>階段 A：</b>查詢訂單並試算車馬費、異動費或退款金額，確認後寫入清潔異動工作表。</div>',
        "階段 B：回填系統（讀工作表寫回後台）": '<div class="warn-strip"><b>階段 B：</b>讀取清潔異動工作表待處理列，將收款 / 退款 / 發票資料同步回後台。執行前請確認工作表資料正確。</div>',
    }
    st.markdown(CHANGE_ORDER_MODE_HELP.get(co_mode, ""), unsafe_allow_html=True)

    if co_mode.startswith("階段 A"):
        render_change_order_stage_a()
    else:
        render_change_order_stage_b()


# --------------------------------------------------------
# 階段 A：查詢試算
# --------------------------------------------------------

SCENARIO_OPTIONS = [
    "僅開車馬費發票",
    "異動費(待收款)",
    "異動費(待退款)",
    "異動平日轉週末(待收款)",
    "異動週末轉平日(待退款)",
    "加時(待收款)",
    "減時(待退款)",
    "客訴(待退款)",
    "物損(待退款)",
]


def render_change_order_stage_a():
    step("3", "選擇查詢方式，查詢目前已付款未服務訂單")

    st.markdown(
        '<div class="info-strip">輸入電話查詢，會列出目前「已付款且尚未服務」的訂單，並依服務日期由近到遠排序。'
        '也可以切換成「訂單編號」直接指定單一筆。選好訂單後，再往下做異動判斷；'
        '若是平日轉週末或週末轉平日，請選擇對應互轉情境計算每人時差額。'
        '（車馬費／異動／加時／減時／客訴／物損）。</div>',
        unsafe_allow_html=True
    )

    q1, q2 = st.columns([1, 1.5])
    with q1:
        region = st.selectbox("地區", ["台北", "台中"], key="co_region_a")
    with q2:
        query_by = st.radio("查詢方式", ["電話", "訂單編號"], horizontal=True, key="co_query_by")

    if query_by == "電話":
        keyword_input = st.text_input(
            "電話", placeholder="例：0912345678", key="co_phone_keyword"
        )
    else:
        keyword_input = st.text_input(
            "訂單編號", placeholder="例：LC00211483", key="co_orderno_keyword"
        )

    search_btn = st.button(
        "🔍 查詢訂單",
        use_container_width=True,
        disabled=not (st.session_state.credentials_ready and keyword_input.strip()),
    )

    with st.expander("執行 LOG", expanded=True):
        log_box_local = st.empty()
        log_box_local.code(
            "\n".join(st.session_state.logs[-3000:]) if st.session_state.logs else "尚未執行"
        )

    def co_log(msg):
        st.session_state.logs.append(str(msg))
        try:
            log_box_local.code("\n".join(st.session_state.logs[-3000:]))
        except Exception:
            pass

    if search_btn:
        try:
            st.session_state.logs = []
            st.session_state.co_phone_orders = []
            st.session_state.co_calc_rows = []
            co_log("===== 開始查詢訂單 =====")

            with st.spinner("查詢中，請稍候…"):
                session = get_session(ui_logger=co_log)

                if query_by == "電話":
                    orders = change_order.fetch_upcoming_paid_orders_by_phone(
                        keyword_input.strip(), session=session, ui_logger=co_log
                    )
                else:
                    single = change_order.fetch_order_basic(
                        keyword_input.strip(), session=session, ui_logger=co_log, by="orderNo"
                    )
                    orders = [single] if single else []

            st.session_state.co_phone_orders = orders
            co_log(f"✅ 查詢完成，共 {len(orders)} 筆")
            st.rerun()

        except Exception as e:
            co_log(f"❌ 查詢失敗：{e}")
            st.error(str(e))

    orders = st.session_state.get("co_phone_orders", [])

    if not orders:
        return

    st.markdown("---")
    step("4", "目前已付款未服務的訂單列表")

    selected_orders = []
    for o in orders:
        service_date_text = (
            o["service_date"].strftime("%Y-%m-%d") if o.get("service_date") else "（無日期資訊）"
        )
        label = (
            f"{o['order_no']}　{o.get('customer_name','')}　"
            f"服務日期：{service_date_text}　時數：{o.get('service_hours',0)}小時　"
            f"人數：{o.get('cleaner_count',0)}人　總金額：${o.get('total',0)}"
        )
        checked = st.checkbox(label, value=True, key=f"co_order_pick_{o['order_no']}")
        if checked:
            selected_orders.append(o)

    if not selected_orders:
        st.info("請至少勾選一筆訂單再繼續。")
        return

    st.markdown("---")
    step("5", "選擇異動情境")

    c1, c2 = st.columns([1, 1.5])
    with c1:
        scenario = st.radio("情境", SCENARIO_OPTIONS, key="co_scenario")

        is_time_change = scenario in ("加時(待收款)", "減時(待退款)")
        is_manual_refund = scenario in ("客訴(待退款)", "物損(待退款)")

        change_hours = None
        change_person = None
        if is_time_change:
            change_hours = st.number_input(
                "異動時數（小時）", min_value=0.0, step=0.5, value=1.0, key="co_time_hours"
            )
            change_person = st.number_input(
                "異動人數", min_value=1, step=1, value=1, key="co_time_person"
            )

        manual_amount = None
        if is_manual_refund:
            manual_amount = st.number_input(
                "退款金額", min_value=0, step=50, value=0, key="co_manual_amount"
            )

    with c2:
        customer_type = st.selectbox("客戶類別", ["一般", "VIP"], key="co_customer_type")
        default_service_date = selected_orders[0].get("service_date") or date.today()
        service_date_input = st.date_input(
            "服務日期（用於計算工作天數／平日假日，預設取自所選訂單）",
            value=default_service_date, key="co_service_date"
        )
        service_note = st.text_input("後台備註（寫入 K 欄）", placeholder="例：客通知停水異動服務", key="co_service_note")

    calc_btn = st.button(
        "🧮 試算",
        use_container_width=True,
        disabled=not st.session_state.credentials_ready,
    )

    if calc_btn:
        try:
            co_log("===== 開始試算 =====")
            calc_rows = []

            for order in selected_orders:
                if scenario == "僅開車馬費發票":
                    row = change_order.build_fare_row(order, service_date=service_date_input)
                    calc_rows.append(row)
                    continue

                if scenario == "加時(待收款)":
                    time_fee_info = change_order.calc_time_change_fee(
                        service_date_input, hours=change_hours, person=change_person
                    )
                    row = change_order.build_addtime_row(
                        order, time_fee_info, service_note, customer_type=customer_type,
                        service_date=service_date_input
                    )
                    calc_rows.append(row)
                    continue

                if scenario == "減時(待退款)":
                    time_fee_info = change_order.calc_time_change_fee(
                        service_date_input, hours=change_hours, person=change_person
                    )
                    row = change_order.build_reducetime_row(
                        order, time_fee_info, service_note, customer_type=customer_type,
                        service_date=service_date_input
                    )
                    calc_rows.append(row)
                    continue

                if scenario == "異動平日轉週末(待收款)":
                    time_fee_info = change_order.calc_flat_person_hour_fee(
                        hours=order.get("service_hours", 0),
                        person=order.get("cleaner_count", 0),
                        rate=change_order.TIME_RATE_DAY_TYPE_DIFF,
                        label="平日轉週末每人時差額",
                    )
                    row = change_order.build_weekday_to_weekend_row(
                        order, time_fee_info, service_note, customer_type=customer_type,
                        service_date=service_date_input
                    )
                    calc_rows.append(row)
                    continue

                if scenario == "異動週末轉平日(待退款)":
                    time_fee_info = change_order.calc_flat_person_hour_fee(
                        hours=order.get("service_hours", 0),
                        person=order.get("cleaner_count", 0),
                        rate=change_order.TIME_RATE_DAY_TYPE_DIFF,
                        label="週末轉平日每人時差額",
                    )
                    row = change_order.build_weekend_to_weekday_row(
                        order, time_fee_info, service_note, customer_type=customer_type,
                        service_date=service_date_input
                    )
                    calc_rows.append(row)
                    continue

                if scenario == "客訴(待退款)":
                    row = change_order.build_manual_refund_row(
                        order, manual_amount, change_order.TYPE_COMPLAINT_REFUND,
                        service_note, customer_type=customer_type,
                        service_date=service_date_input
                    )
                    calc_rows.append(row)
                    continue

                if scenario == "物損(待退款)":
                    row = change_order.build_manual_refund_row(
                        order, manual_amount, change_order.TYPE_DAMAGE_REFUND,
                        service_note, customer_type=customer_type,
                        service_date=service_date_input
                    )
                    calc_rows.append(row)
                    continue

                fee_info = change_order.calc_change_fee(
                    order, service_date=service_date_input
                )

                if scenario == "異動費(待收款)":
                    row = change_order.build_charge_row(
                        order, fee_info, service_note, customer_type=customer_type,
                        service_date=service_date_input
                    )
                else:
                    row = change_order.build_refund_row(
                        order, fee_info, service_note, customer_type=customer_type,
                        service_date=service_date_input
                    )
                calc_rows.append(row)

            st.session_state.co_calc_rows = calc_rows
            co_log(f"✅ 試算完成，共 {len(calc_rows)} 筆")
            st.rerun()

        except Exception as e:
            co_log(f"❌ 試算失敗：{e}")
            st.error(str(e))

    calc_rows = st.session_state.get("co_calc_rows", [])

    if calc_rows:
        st.markdown("---")
        step("6", "試算結果預覽（尚未寫入 Sheet）")

        for row in calc_rows:
            st.markdown(f"""
            <div class="preview-card preview-ok">
                <div class="preview-title">{row.get('G','')}　{row.get('H','')}</div>
                <div class="preview-sub">
                    <b>類型：</b>{row.get('C','')}　<b>狀態：</b>{row.get('B','')}<br>
                    <b>原服務時間：</b>{row.get('I','')}<br>
                    <b>試算金額：</b>${row.get('_calc_amount','')}<br>
                    <b>J 欄內容：</b>{row.get('J','')}<br>
                    <b>K 欄後台備註：</b>{row.get('K','')}<br>
                    <b>計算依據：</b>{row.get('_calc_note','')}
                </div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown(
            f'<div class="warn-strip">⚠️ 確認後會把以上 {len(calc_rows)} 筆寫入「{region}」清潔異動工作表最後一列之後。</div>',
            unsafe_allow_html=True
        )

        confirm_btn = st.button("🚀 確認寫入清潔異動工作表", type="primary", use_container_width=True)

        if confirm_btn:
            try:
                co_log("===== 開始寫入 Sheet =====")
                with st.spinner("寫入中，請稍候…"):
                    result = change_order.append_rows_to_sheet(region, calc_rows, ui_logger=co_log)

                if result["errors"]:
                    st.error("；".join(result["errors"]))
                else:
                    st.success(f"✅ 已寫入 {result['written']} 筆，從第 {result['start_row']} 列開始")
                    st.session_state.co_calc_rows = []
                    st.session_state.co_phone_orders = []

            except Exception as e:
                co_log(f"❌ 寫入失敗：{e}")
                st.error(str(e))


# --------------------------------------------------------
# 階段 B：回填系統
# --------------------------------------------------------

def render_change_order_stage_b():
    step("3", "讀取清潔異動工作表待處理列")

    st.markdown(
        '<div class="info-strip">會掃描 B 欄為「待收款」「待退款」「已收款」「已退款」且金額已填的列，'
        '依每列狀態回填後台訂單修改頁；完成後只寫入 AD 欄系統回填時間，不會改 B 欄狀態。</div>',
        unsafe_allow_html=True
    )

    region = st.selectbox("地區", ["台北", "台中"], key="co_region_b")

    scan_btn = st.button(
        "🔍 掃描待處理清單",
        use_container_width=True,
        disabled=not st.session_state.credentials_ready,
    )

    with st.expander("執行 LOG", expanded=True):
        log_box_local = st.empty()
        log_box_local.code(
            "\n".join(st.session_state.logs[-3000:]) if st.session_state.logs else "尚未執行"
        )

    def co_log(msg):
        st.session_state.logs.append(str(msg))
        try:
            log_box_local.code("\n".join(st.session_state.logs[-3000:]))
        except Exception:
            pass

    if scan_btn:
        try:
            st.session_state.logs = []
            st.session_state.co_pending_rows = []
            co_log("===== 開始掃描清潔異動工作表 =====")

            with st.spinner("掃描中，請稍候…"):
                pending = change_order.get_pending_rows(region, ui_logger=co_log)

            st.session_state.co_pending_rows = pending
            co_log(f"✅ 掃描完成，共 {len(pending)} 筆")
            st.rerun()

        except Exception as e:
            co_log(f"❌ 掃描失敗：{e}")
            st.error(str(e))

    pending = st.session_state.get("co_pending_rows", [])

    if pending:
        st.markdown("---")
        step("4", "待處理清單（請勾選要回填的項目）")

        selected = []
        for item in pending:
            status = item.get("status") or ("待收款" if item["kind"] == "charge" else "待退款")
            checked = st.checkbox(
                f"{item['order_no']}（{status}，Sheet 第 {item['sheet_row']} 列）",
                value=True,
                key=f"co_pick_{item['sheet_row']}",
            )
            detail = f"H 欄姓名：{item.get('customer_name','')}　｜　J 欄：{item.get('j_note','')}"
            if item.get("kind") == "refund":
                detail += f"　｜　Y 欄：{item.get('refund_invoice_type','')}"
            st.caption(detail)
            if checked:
                selected.append(item)

        st.metric("已勾選筆數", len(selected))

        st.markdown(
            '<div class="warn-strip">⚠️ 這個動作會依 B 欄狀態寫入後台待加收/待退款/已收款/已退款欄位；Sheet B 欄不會被自動改狀態，請確認金額與日期無誤再送出。</div>',
            unsafe_allow_html=True
        )

        sync_btn = st.button(
            "🚀 確認回填系統",
            type="primary",
            use_container_width=True,
            disabled=not selected,
        )

        if sync_btn:
            try:
                co_log(f"===== 開始回填 {len(selected)} 筆 =====")
                with st.spinner("回填中，請稍候…"):
                    session = get_session(ui_logger=co_log)
                    result = change_order.sync_pending_rows(region, selected, session=session, ui_logger=co_log)

                co_log("===== 回填完成 =====")
                st.session_state.co_pending_rows = []

                c1, c2, c3 = st.columns(3)
                c1.metric("執行筆數", result["processed"])
                c2.metric("成功", result["success"])
                c3.metric("失敗", result["failed"])

                if result["errors"]:
                    with st.expander(f"⚠️ 錯誤明細（{len(result['errors'])} 筆）", expanded=True):
                        for i, err in enumerate(result["errors"], 1):
                            st.markdown(f"**{i}.** {err}")
                else:
                    st.success("✅ 全部回填完成")

            except Exception as e:
                co_log(f"❌ 回填失敗：{e}")
                st.error(str(e))


# ============================================================
# 依目前選擇的功能渲染對應區塊
# ============================================================

if main_section == "📝 訂單客服備註":
    render_memo_section()

elif main_section == "📅 排班功能":
    if shift_sub_section == "排班匯入":
        render_shift_import_section()
    elif shift_sub_section == "檸檬人空檔查詢":
        render_lemon_ren_section()
    else:
        render_clear_shift_section()

elif main_section == "💳 ATM 對帳":
    render_atm_section()

elif main_section == "🔄 服務異動":
    render_change_order_section()
