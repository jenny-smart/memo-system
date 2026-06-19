# memoapp.py
# -*- coding: utf-8 -*-
import streamlit as st
import re
import memo
import shift
import atm

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
    "clear_person_result": None,
    "lemon_scan_entries": None,
    "lemon_clear_results": None,
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
        '<div class="info-strip">每一列是「目標訂單」；若有來源訂單，代表已找到最近一筆同地址＋已付款＋已處理＋有備註的來源。</div>',
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
            can_autofill = row.get("can_autofill", False)

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
                    <b>來源備註：</b>{source_notice_preview or "無"}
                </div>
                <div class="preview-sub" style="margin-top:8px;">
                    <b>建議：</b>{"建議執行" if can_autofill else "無可參照來源，請人工確認"}
                </div>
            </div>
            """, unsafe_allow_html=True)

            if checked and order_id:
                selected_ids.append(order_id)

    render_section("可自動回填", can_rows, "can_autofill", True)
    render_section("無可參照來源", no_rows, "no_source", False)

    st.markdown("---")
    step("5", "執行確認")

    st.metric("目前勾選", len(selected_ids))
    st.caption("執行後會把來源客服備註寫入目標訂單，並把目標訂單服務狀態改為已處理。")

    return selected_ids


# ============================================================
# Hero
# ============================================================

st.markdown("""
<div class="hero">
  <div class="hero-emoji">📝</div>
  <div>
    <div class="hero-title">檸檬訂單備忘錄</div>
    <div class="hero-sub">Memo 回填・排班管理・ATM 對帳 整合工具</div>
  </div>
</div>
""", unsafe_allow_html=True)

# ============================================================
# Step 1：登入與環境設定（所有功能共用同一組登入狀態）
# 已登入後改成摺疊狀態，畫面比較乾淨；要換帳號再展開即可。
# ============================================================

step("1", "登入")

login_expanded = not st.session_state.is_logged_in

with st.expander(
    f"✅ 已登入：{st.session_state.login_identity}" if st.session_state.is_logged_in else "🔐 尚未登入，請輸入帳密",
    expanded=login_expanded,
):
    col_e, col_p, col_env = st.columns([2.4, 2.4, 1.2])

    with col_e:
        email = st.text_input("後台帳號", placeholder="jenny@lemonclean.com.tw")

    with col_p:
        password = st.text_input("後台密碼", type="password")

    with col_env:
        env_option = st.selectbox("環境", ["prod", "dev"], index=0)

    memo.set_env(env_option)

    col_login, col_unlock = st.columns(2)

    with col_login:
        login_clicked = st.button("🔐 Login", use_container_width=True)

    with col_unlock:
        unlock_clicked = st.button("解除鎖定", use_container_width=True)

    if unlock_clicked:
        st.session_state.is_running = False
        st.session_state.logs = []
        st.success("已解除鎖定")

    if login_clicked:
        try:
            reset_before_action(clear_preview=True, clear_selection=True)

            if not email or not password:
                st.error("請先輸入 Email / Password")
            else:
                st.session_state.is_running = True
                ui_log("===== 開始登入 =====")
                memo.set_env(env_option)
                memo.set_runtime_credentials(email, password)

                with st.spinner("登入中，請稍候…"):
                    memo.login(ui_logger=ui_log)

                st.session_state.is_logged_in = True
                st.session_state.login_identity = email
                ui_log("✅ Login 成功")
                st.success("登入成功，請往下選擇功能。")
                st.rerun()

        except Exception as e:
            st.session_state.is_logged_in = False
            st.session_state.login_identity = ""
            ui_log(f"❌ Login 失敗：{e}")
            st.error(f"登入失敗：{e}")
        finally:
            st.session_state.is_running = False

if not st.session_state.is_logged_in:
    st.markdown(
        '<div class="info-strip">⚠️ 尚未登入，請先在上方輸入帳密並點擊 Login，才能使用下方功能。</div>',
        unsafe_allow_html=True
    )

st.markdown("---")

# ============================================================
# Step 2：選擇功能（排班相關功能放一起，ATM 對帳放最後）
# ============================================================

step("2", "選擇功能")

app_section = st.selectbox(
    "功能",
    [
        "Memo 自動回填",
        "排班勾選（匯入檔）",
        "檸檬人空檔勾選",
        "清空排班",
        "ATM 對帳",
    ],
    label_visibility="collapsed",
)

st.markdown("---")


# ============================================================
# 功能一：Memo 自動回填
# ============================================================

def render_memo_section():
    step("3", "設定查詢條件")

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
                disabled=not st.session_state.is_logged_in
            )

        else:
            c1, c2 = st.columns(2)

            with c1:
                sheet_summary_btn = st.button(
                    "🔍 查詢目前筆數",
                    use_container_width=True,
                    disabled=not st.session_state.is_logged_in
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
                disabled=not st.session_state.is_logged_in
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
                disabled=not st.session_state.is_logged_in
            )

        with c2:
            execute_btn = st.button(
                "🚀 執行勾選項目",
                use_container_width=True,
                disabled=not st.session_state.is_logged_in
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
                disabled=not st.session_state.is_logged_in
            )

        with c6:
            execute_btn = st.button(
                "🚀 執行勾選項目",
                use_container_width=True,
                disabled=not st.session_state.is_logged_in
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
                if mode == "By 電話":
                    if not phone_text.strip():
                        raise ValueError("請輸入至少一支電話")

                    preview_rows = memo.preview_by_phone_multi(
                        phone_text=phone_text.strip(),
                        ui_logger=ui_log
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
                    if sheet_run_mode == "指定列號":
                        result = memo.main(
                            row_spec=row_spec,
                            force=force,
                            ui_logger=ui_log
                        )
                    else:
                        result = memo.main_first_n_pending(
                            limit=int(sheet_limit),
                            ui_logger=ui_log
                        )

            else:
                if not st.session_state.preview_rows:
                    raise RuntimeError("請先查詢列表")

                current_selected_ids = []

                for row in st.session_state.preview_rows:
                    oid = str(safe_get(row, "order_id", default="")).strip()

                    if oid and st.session_state.get(f"pick_{oid}", False):
                        current_selected_ids.append(oid)

                if not current_selected_ids:
                    raise RuntimeError("請先勾選要執行的資料")

                ui_log("===== 開始執行勾選項目 =====")
                ui_log(f"勾選筆數：{len(current_selected_ids)}")

                with st.spinner("執行中，請稍候…"):
                    result = memo.main_by_selected_order_ids(
                        order_ids=current_selected_ids,
                        ui_logger=ui_log
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
            disabled=not (st.session_state.is_logged_in and uploaded_file is not None),
        )
    with c2:
        execute_btn = st.button(
            "🚀 正式儲存",
            use_container_width=True,
            disabled=not (
                st.session_state.is_logged_in
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
                result = shift.process_import_file(rows, dry_run=True, ui_logger=shift_ui_log)

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
                result = shift.process_import_file(rows, dry_run=False, ui_logger=ui_log)

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
        disabled=not st.session_state.is_logged_in,
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

            with st.spinner("登入並查詢中，請稍候…"):
                session = memo.login(ui_logger=lemon_ui_log)
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
                        session = memo.login(ui_logger=ui_log)
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
    step("3", "設定要處理的 ATM 對帳列")

    st.markdown(
        '<div class="info-strip">會依序對每一列：搜尋訂單 → 按已付款 → 開立發票 → 發確認信，'
        '完成後把付款時間 / 發票號碼回填到 P / Q 欄，並把 R 欄填上「已發送」。</div>',
        unsafe_allow_html=True
    )
    st.markdown(
        '<div class="warn-strip">⚠️ 這三個動作（尤其是發確認信）都是「點了就送出」，沒有預覽機制，輸入列號後按執行就會直接全部跑，請務必先確認列號正確再送出。</div>',
        unsafe_allow_html=True
    )

    c1, c2 = st.columns([1, 3])

    with c1:
        region = st.selectbox("地區", ["台北", "台中"])

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
        disabled=not (st.session_state.is_logged_in and bool(row_spec.strip())),
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

    if st.session_state.atm_result is not None:
        render_atm_result(st.session_state.atm_result, atm_result_container)

    if execute_btn:
        try:
            st.session_state.logs = []
            st.session_state.atm_result = None
            atm_ui_log(f"===== 開始處理 ATM 對帳（{region}）=====")

            if not (do_mark_paid or do_issue_invoice or do_send_mail):
                raise ValueError("請至少勾選一項要執行的動作")

            with st.spinner("執行中，請稍候…"):
                result = atm.process_atm_rows(
                    region=region,
                    row_spec=row_spec,
                    do_mark_paid=do_mark_paid,
                    do_issue_invoice=do_issue_invoice,
                    do_send_mail=do_send_mail,
                    ui_logger=atm_ui_log,
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
            disabled=not (st.session_state.is_logged_in and bool(target_names)),
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
                    session = memo.login(ui_logger=clear_ui_log)
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
            disabled=not st.session_state.is_logged_in,
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
                    session = memo.login(ui_logger=clear_ui_log)
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
                            session = memo.login(ui_logger=clear_ui_log)
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
# 依目前選擇的功能渲染對應區塊
# ============================================================

if app_section == "Memo 自動回填":
    render_memo_section()
elif app_section == "排班勾選（匯入檔）":
    render_shift_import_section()
elif app_section == "檸檬人空檔勾選":
    render_lemon_ren_section()
elif app_section == "ATM 對帳":
    render_atm_section()
else:
    render_clear_shift_section()
