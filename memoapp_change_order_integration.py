# ============================================================
# 整合說明：請把下面內容加進現有 memoapp.py
# ============================================================
#
# 1) 在檔案最上方 import 區塊加入：
#       import change_order
#
# 2) 在「選擇功能」selectbox 的選項清單中加入「清潔異動」：
#       app_section = st.selectbox(
#           "功能",
#           [
#               "Memo 自動回填",
#               "排班勾選（匯入檔）",
#               "檸檬人空檔勾選",
#               "清空排班",
#               "ATM 對帳",
#               "清潔異動",   # <-- 新增這行
#           ],
#           ...
#       )
#
# 3) 在檔案最下方的 dispatch 區塊加入：
#       elif app_section == "清潔異動":
#           render_change_order_section()
#
# 4) 把下面整段 render_change_order_section() 函式貼到 memoapp.py
#    （建議貼在 render_clear_shift_section() 之後）
# ============================================================

import re
from datetime import date

import change_order


def render_change_order_section():
    co_mode = st.radio(
        "",
        ["階段 A：查詢試算（寫入清潔異動工作表）", "階段 B：回填系統（讀工作表寫回後台）"],
        horizontal=True,
        label_visibility="collapsed",
        key="change_order_mode",
    )

    if co_mode.startswith("階段 A"):
        render_change_order_stage_a()
    else:
        render_change_order_stage_b()


# ------------------------------------------------------------
# 階段 A：查詢試算
# ------------------------------------------------------------

def render_change_order_stage_a():
    step("3", "輸入要查詢試算的訂單")

    st.markdown(
        '<div class="info-strip">支援「電話」或「訂單編號」查詢，可一次輸入多筆（逗號或換行分隔）。'
        '查到資料後會試算車馬費／異動費／應退款，確認沒問題再寫入清潔異動工作表。</div>',
        unsafe_allow_html=True
    )

    c1, c2 = st.columns([1, 1.5])
    with c1:
        region = st.selectbox("地區", ["台北", "台中"], key="co_region_a")
        query_by = st.radio("查詢方式", ["訂單編號", "電話"], horizontal=True, key="co_query_by")
        scenario = st.radio(
            "情境", ["不退服務（收異動費）", "退服務（收異動費＋退餘額）", "僅開車馬費發票"],
            key="co_scenario"
        )
    with c2:
        keywords_text = st.text_area(
            "訂單編號 / 電話清單",
            placeholder="一行一筆，例如：\nLC00211084\nLC00211081",
            key="co_keywords"
        )
        customer_type = st.selectbox("客戶類別", ["一般", "VIP"], key="co_customer_type")
        service_date_input = st.date_input("服務日期（用於計算工作天數）", value=date.today(), key="co_service_date")
        service_note = st.text_input("服務註記（寫入 J 欄）", placeholder="例：客通知停水異動服務", key="co_service_note")

    query_btn = st.button(
        "🔍 查詢並試算",
        use_container_width=True,
        disabled=not (st.session_state.credentials_ready and keywords_text.strip()),
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

    if query_btn:
        try:
            st.session_state.logs = []
            st.session_state.co_calc_rows = []
            co_log("===== 開始查詢試算 =====")

            keywords = [k.strip() for k in re.split(r"[,\n，]", keywords_text) if k.strip()]
            by = "orderNo" if query_by == "訂單編號" else "phone"

            calc_rows = []
            with st.spinner("查詢中，請稍候…"):
                session = get_session(ui_logger=co_log)

                for kw in keywords:
                    order = change_order.fetch_order_basic(kw, session=session, ui_logger=co_log, by=by)
                    if not order:
                        continue

                    if scenario == "僅開車馬費發票":
                        row = change_order.build_fare_row(order)
                        calc_rows.append(row)
                        continue

                    fee_info = change_order.calc_change_fee(
                        order, service_date=service_date_input
                    )

                    if scenario.startswith("不退服務"):
                        row = change_order.build_charge_row(
                            order, fee_info, service_note, customer_type=customer_type
                        )
                    else:
                        row = change_order.build_refund_row(
                            order, fee_info, service_note, customer_type=customer_type
                        )
                    calc_rows.append(row)

            st.session_state.co_calc_rows = calc_rows
            co_log(f"✅ 試算完成，共 {len(calc_rows)} 筆")
            st.rerun()

        except Exception as e:
            co_log(f"❌ 查詢試算失敗：{e}")
            st.error(str(e))

    calc_rows = st.session_state.get("co_calc_rows", [])

    if calc_rows:
        st.markdown("---")
        step("4", "試算結果預覽（尚未寫入 Sheet）")

        for row in calc_rows:
            st.markdown(f"""
            <div class="preview-card preview-ok">
                <div class="preview-title">{row.get('G','')}　{row.get('H','')}</div>
                <div class="preview-sub">
                    <b>類型：</b>{row.get('C','')}　<b>狀態：</b>{row.get('B','')}<br>
                    <b>原服務時間：</b>{row.get('I','')}<br>
                    <b>試算金額：</b>${row.get('_calc_amount','')}<br>
                    <b>備註：</b>{row.get('J','')}<br>
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

            except Exception as e:
                co_log(f"❌ 寫入失敗：{e}")
                st.error(str(e))


# ------------------------------------------------------------
# 階段 B：回填系統
# ------------------------------------------------------------

def render_change_order_stage_b():
    step("3", "讀取清潔異動工作表待處理列")

    st.markdown(
        '<div class="info-strip">會掃描「待收款」「待退款」且金額已填的列，'
        '逐筆把 isCharge / isRefund 等欄位回填到後台訂單修改頁，完成後自動把 Sheet 狀態改為已收款/已退款。</div>',
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
            checked = st.checkbox(
                f"{item['order_no']}（{'待收款' if item['kind']=='charge' else '待退款'}，Sheet 第 {item['sheet_row']} 列）",
                value=True,
                key=f"co_pick_{item['sheet_row']}",
            )
            if checked:
                selected.append(item)

        st.metric("已勾選筆數", len(selected))

        st.markdown(
            '<div class="warn-strip">⚠️ 這個動作會直接寫入後台訂單的待加收/待退款欄位，並回寫 Sheet 狀態，請確認金額無誤再送出。</div>',
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
