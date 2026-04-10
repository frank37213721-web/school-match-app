import streamlit as st
from utils import supabase, send_email, is_valid_email

COURSE_TYPES = ["部定必修", "加深加廣選修", "校訂必修", "多元選修", "彈性課程"]
PAGE_SIZE = 5


def render_lobby():
    # ── 首頁 Landing Page ──
    if not st.session_state.get("entered_lobby", False):
        st.markdown("""
        <style>
        #MainMenu, footer, header { visibility: hidden; }
        [data-testid="stSidebar"] { display: none; }
        .stApp { background: linear-gradient(160deg, #10141f 0%, #172035 55%, #10141f 100%) !important; }
        .block-container { padding: 0 !important; max-width: 100% !important; }
        .hero {
            display: flex; flex-direction: column; align-items: center;
            text-align: center; padding-top: 18vh; padding-bottom: 2rem;
            padding-left: 1rem; padding-right: 1rem;
            font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'Helvetica Neue', sans-serif;
        }
        .hero-eyebrow { font-size:1rem; font-weight:500; letter-spacing:0.15em;
            text-transform:uppercase; color:#2997ff; margin-bottom:1.4rem; }
        .hero-title { font-size:clamp(2.8rem,7vw,5.5rem); font-weight:700;
            letter-spacing:-0.025em; line-height:1.05; color:#f5f5f7; margin-bottom:1.2rem; }
        .hero-subtitle { font-size:clamp(1rem,2.5vw,1.4rem); font-weight:300;
            color:rgba(245,245,247,0.55); letter-spacing:0.01em; margin-bottom:0; }
        .hero-divider { width:60px; height:1px; background:rgba(245,245,247,0.2);
            margin:0 auto 2rem; }
        .stApp .stButton > button, .stApp [data-testid="baseButton-secondary"],
        .stApp [data-testid="baseButton-primary"],
        .stApp .stButton > button span, .stApp [data-testid="baseButton-secondary"] span,
        .stApp [data-testid="baseButton-primary"] span {
            color:#ffffff !important; font-weight:600 !important; letter-spacing:0.02em !important; }
        </style>
        <div class="hero">
            <div class="hero-eyebrow">教育 × 合作 × 創新</div>
            <div class="hero-title">跨校課程<br>匯流平台</div>
            <div class="hero-divider"></div>
            <div class="hero-subtitle">Connecting everyone with curriculum</div>
        </div>
        """, unsafe_allow_html=True)

        col1, col2, col3 = st.columns([2, 1, 2])
        with col2:
            if st.button("學校帳號 Sign in / Sign Up", use_container_width=True):
                st.session_state.entered_lobby = True
                st.session_state.force_login = True
                st.rerun()
            st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
            if st.button("進入課程大廳 →", use_container_width=True, type="primary"):
                st.session_state.entered_lobby = True
                st.rerun()
        st.stop()

    # ── 課程大廳 ──
    st.header("📚 課程大廳")

    try:
        response = supabase.table("courses").select(
            "id, title, course_type, credits, start_time, max_students, max_schools, "
            "syllabus, plan_pdf_url, host_school_id, sps_min, sps_max, req_1, req_2, req_3, "
            "schools(name, district, registrant_name, registrant_email, academic_director_email, principal_email)"
        ).execute()
        courses = response.data
    except Exception as e:
        st.error(f"讀取資料失敗：{e}")
        return

    if not courses:
        st.info("目前尚無開課資訊。")
        return

    # 批次撈 matches
    all_course_ids = [c['id'] for c in courses]
    try:
        all_matches_res = supabase.table("matches")\
            .select("course_id, status")\
            .in_("course_id", all_course_ids)\
            .in_("status", ["pending", "approved"])\
            .execute()
        matches_by_course = {}
        for m in all_matches_res.data:
            matches_by_course.setdefault(m['course_id'], []).append(m)
    except Exception:
        matches_by_course = {}

    # ── 篩選列（單行）──
    all_districts = sorted({c['schools'].get('district', '') for c in courses if c.get('schools') and c['schools'].get('district')})
    col_kw, col_type, col_dist = st.columns([3, 3, 2])
    with col_kw:
        keyword = st.text_input("🔍 搜尋課程", placeholder="課程名稱或關鍵字", label_visibility="collapsed")
    with col_type:
        selected_types = st.multiselect("課程種類", COURSE_TYPES, placeholder="篩選課程種類", label_visibility="collapsed")
    with col_dist:
        selected_district = st.selectbox("分區", ["全部分區"] + all_districts, label_visibility="collapsed")

    # 篩選
    filtered = [
        c for c in courses
        if (selected_district == "全部分區" or c.get('schools', {}).get('district') == selected_district)
        and (not keyword or keyword in (c.get('title') or '') or keyword in (c.get('syllabus') or ''))
        and (not selected_types or c.get('course_type') in selected_types)
    ]

    total = len(filtered)
    if total == 0:
        st.caption("沒有符合條件的課程。")
        return

    # ── 分頁 ──
    total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    if "lobby_page" not in st.session_state:
        st.session_state.lobby_page = 0
    # 篩選條件變動時重設頁碼
    filter_key = f"{keyword}|{selected_types}|{selected_district}"
    if st.session_state.get("lobby_filter_key") != filter_key:
        st.session_state.lobby_filter_key = filter_key
        st.session_state.lobby_page = 0

    page = st.session_state.lobby_page
    page_courses = filtered[page * PAGE_SIZE: (page + 1) * PAGE_SIZE]

    # 結果數 + 分頁控制
    col_info, col_prev, col_page, col_next = st.columns([5, 1, 1, 1])
    with col_info:
        st.caption(f"共 **{total}** 門課程　第 {page + 1} / {total_pages} 頁")
    with col_prev:
        if st.button("◀", disabled=(page == 0), use_container_width=True):
            st.session_state.lobby_page -= 1
            st.rerun()
    with col_page:
        st.markdown(f"<div style='text-align:center;padding-top:0.4rem;font-size:0.85rem'>{page+1}/{total_pages}</div>", unsafe_allow_html=True)
    with col_next:
        if st.button("▶", disabled=(page >= total_pages - 1), use_container_width=True):
            st.session_state.lobby_page += 1
            st.rerun()

    st.divider()

    logged_in_school_id = (
        st.session_state.school_info['id']
        if st.session_state.get('logged_in') and st.session_state.get('school_info')
        else None
    )

    # ── 課程卡片 ──
    for c in page_courses:
        course_matches = matches_by_course.get(c['id'], [])
        approved_count = sum(1 for m in course_matches if m['status'] == 'approved')
        pending_count  = sum(1 for m in course_matches if m['status'] == 'pending')
        total_active   = approved_count + pending_count
        max_schools    = c.get('max_schools', 2)
        is_full        = total_active >= max_schools
        is_own         = logged_in_school_id is not None and c.get('host_school_id') == logged_in_school_id

        detail_key = f"detail_{c['id']}"
        apply_key  = f"show_matching_{c['id']}"
        if detail_key not in st.session_state:
            st.session_state[detail_key] = False
        if apply_key not in st.session_state:
            st.session_state[apply_key] = False

        school_info = c.get('schools', {})
        district    = school_info.get('district', '')
        school_name = school_info.get('name', '')
        time_str    = c.get('start_time', '未設定')

        # 狀態標籤 HTML
        if is_full:
            status_html = "<span style='color:#c0392b;font-weight:700;font-size:0.92rem'>🔴 名額已滿</span>"
        elif approved_count > 0:
            status_html = f"<span style='color:#b07800;font-weight:700;font-size:0.92rem'>🟡 {approved_count}/{max_schools} 所</span>"
        else:
            status_html = f"<span style='color:#1a7a40;font-weight:700;font-size:0.92rem'>🟢 開放中 {approved_count}/{max_schools}</span>"

        # 標籤列 HTML
        tags_html = ""
        if c.get('course_type'):
            tags_html += f"<span style='background:#dbeafe;color:#1d4ed8;padding:2px 10px;border-radius:20px;font-size:0.75rem;font-weight:600;margin-right:6px'>{c['course_type']}</span>"
        if c.get('credits'):
            tags_html += f"<span style='background:#ede9fe;color:#6d28d9;padding:2px 10px;border-radius:20px;font-size:0.75rem;font-weight:600'>{c['credits']} 學分</span>"

        # 卡片 HTML（白底＋藍左線＋陰影）
        is_expanded = st.session_state[detail_key]
        bottom_radius = "0 0 0 0" if is_expanded else "0 12px 12px 0"
        st.markdown(f"""
<div style="
    background: #ffffff;
    border-left: 4px solid #2563a8;
    border-radius: 12px 12px {bottom_radius};
    padding: 1.1rem 1.6rem 1rem 1.4rem;
    box-shadow: 0 4px 18px rgba(30,50,120,0.12), 0 1px 4px rgba(30,50,120,0.07);
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 1rem;
    margin-bottom: 0;
">
    <div style="flex:1; min-width:0">
        {f'<div style="margin-bottom:0.45rem">{tags_html}</div>' if tags_html else ''}
        <div style="font-size:1.05rem;font-weight:700;color:#1a2340;margin-bottom:0.3rem;
                    white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{c['title']}</div>
        <div style="font-size:0.82rem;color:#5a6a8a">
            🏫 {school_name}{'&nbsp;·&nbsp;' + district if district else ''}&nbsp;&nbsp;🗓️ {time_str}
        </div>
    </div>
    <div style="flex-shrink:0;text-align:right">
        {status_html}
    </div>
</div>
""", unsafe_allow_html=True)

        # 詳情按鈕列（緊接卡片底部）
        _, col_det = st.columns([8, 2])
        with col_det:
            if st.button(
                "收起 ▴" if is_expanded else "詳情 ▾",
                key=f"dtl_{c['id']}", use_container_width=True
            ):
                st.session_state[detail_key] = not is_expanded
                st.session_state[apply_key] = False
                st.rerun()

        # ── 詳情展開區 ──
        if is_expanded:
            with st.container():
                st.markdown("""
<div style="background:#f8faff;border-left:4px solid #2563a8;border-radius:0 0 12px 12px;
            padding:1rem 1.6rem 1.2rem 1.4rem;margin-top:-0.5rem;
            box-shadow:0 6px 18px rgba(30,50,120,0.10)">
</div>
""", unsafe_allow_html=True)
                col_d1, col_d2 = st.columns(2)
                with col_d1:
                    if c.get('course_type'):
                        st.write(f"**📚 課程種類：** {c['course_type']}")
                    if c.get('credits'):
                        st.write(f"**🎯 學分數：** {c['credits']} 學分")
                    st.write(f"**🗓️ 開課時間：** {c.get('start_time', '未設定')}")
                    st.write(f"**👥 跨校學生上限：** {c.get('max_students', 'N/A')} 人")
                    if c.get('sps_min') or c.get('sps_max'):
                        st.write(f"**🎓 每校學生人數：** {c.get('sps_min','?')} ~ {c.get('sps_max','?')} 人")
                with col_d2:
                    st.write(f"**🏫 合作學校上限：** {max_schools} 所")
                    st.write(f"**📊 目前：** ✅ 已核准 {approved_count} 所　⏳ 待審 {pending_count} 所")
                    if c.get('plan_pdf_url'):
                        st.link_button("📥 課程規劃表 PDF", c['plan_pdf_url'])
                if c.get('syllabus'):
                    st.write(f"**📝 課程大綱：**")
                    st.write(c['syllabus'])
                for req_key, label in [("req_1","合作要求一"), ("req_2","合作要求二"), ("req_3","合作要求三")]:
                    if c.get(req_key):
                        st.write(f"**📌 {label}：** {c[req_key]}")

                # 申請按鈕
                if is_own:
                    st.info("📌 此為您開設的課程，無法申請配對。")
                elif not st.session_state[apply_key]:
                    if st.button(
                        "🚫 名額已滿" if is_full else "申請配對 →",
                        key=f"btn_{c['id']}", disabled=is_full, type="primary"
                    ):
                        if not st.session_state.get('logged_in'):
                            st.warning("⚠️ 請先登入後再申請配對。")
                        else:
                            st.session_state[apply_key] = True
                            st.rerun()

                # ── 申請確認流程 ──
                if st.session_state.get(apply_key):
                    st.markdown("---")
                    st.subheader("📋 申請配對確認")
                    confirm_items = [
                        "確認授課時間段是否可以配合",
                        "確認課程計劃未來是否可以新增課程",
                        "確認合作學校端所準備之設備與環境是否可以安排妥當",
                        "未來如配對成功，基於誠信原則請與開課學校建立良好夥伴關係",
                    ]
                    for req_key in ["req_1", "req_2", "req_3"]:
                        if c.get(req_key):
                            confirm_items.append(f"【開課學校要求】{c[req_key]}")
                    all_confirmed = all(
                        st.checkbox(f"{i}. {item}", key=f"confirm_{c['id']}_{i}")
                        for i, item in enumerate(confirm_items, 1)
                    )
                    col_cancel, col_send = st.columns(2)
                    with col_cancel:
                        if st.button("取消", key=f"cancel_{c['id']}"):
                            st.session_state[apply_key] = False
                            st.rerun()
                    with col_send:
                        if st.button("確定送出申請", key=f"send_{c['id']}", disabled=not all_confirmed, type="primary"):
                            _submit_application(c, matches_by_course, max_schools, total_active)


def _submit_application(c, matches_by_course, max_schools, total_active):
    apply_key = f"show_matching_{c['id']}"
    with st.spinner("🔄 正在處理配對申請..."):
        try:
            existing = supabase.table("matches")\
                .select("id")\
                .eq("course_id", c['id'])\
                .eq("partner_school_id", st.session_state.school_info['id'])\
                .in_("status", ["pending", "approved"])\
                .execute()
            if existing.data:
                st.error("⚠️ 您已申請過此課程，且申請正在處理中或已通過！")
                return
            if total_active >= max_schools:
                st.error(f"⚠️ 此課程合作學校已滿！最多接受 {max_schools} 所。")
                return

            match_result = supabase.table("matches").insert({
                "course_id": c['id'],
                "partner_school_id": st.session_state.school_info['id'],
                "status": "pending"
            }).execute()
            match_id = match_result.data[0]['id']
            applicant = st.session_state.school_info
            host = c['schools']

            recipients = [
                {"email": host['registrant_email'], "name": host['registrant_name'], "type": "host"},
                {"email": host.get('academic_director_email'), "name": "承辦處室主任", "type": "host"},
                {"email": host.get('principal_email'), "name": "校長", "type": "host"},
                {"email": applicant['registrant_email'], "name": applicant['registrant_name'], "type": "applicant"},
                {"email": applicant.get('academic_director_email'), "name": "承辦處室主任", "type": "applicant"},
                {"email": applicant.get('principal_email'), "name": "校長", "type": "applicant"},
            ]
            failed = []
            for r in recipients:
                if is_valid_email(r.get('email') or ''):
                    if r['type'] == 'host':
                        subj = f"配對申請通知：{applicant['name']} 申請您的課程「{c['title']}」"
                        body = f"親愛的 {r['name']}：\n\n您開設的課程「{c['title']}」收到來自 {applicant['name']} 的配對申請。\n\n申請學校：{applicant['name']}\n承辦人：{applicant['registrant_name']}\n電話：{applicant['phone']}（分機：{applicant.get('registrant_extension','未提供')}）\n\n請登入系統處理此申請。\n\n跨校課程匯流平台"
                    else:
                        subj = f"配對申請確認：已申請「{c['title']}」"
                        body = f"親愛的 {r['name']}：\n\n您的學校已成功送出「{c['title']}」的配對申請（申請編號：{match_id}）。\n開課學校：{host['name']}\n\n請耐心等候對方回覆。\n\n跨校課程匯流平台"
                    ok, _ = send_email(r['email'], r['name'], subj, body)
                    if not ok:
                        failed.append(r['name'])

            if failed:
                st.warning(f"⚠️ 申請已送出，但部分 Email 發送失敗：{', '.join(failed)}")
            else:
                st.success("✅ 配對申請已成功送出！相關人員將收到通知 Email。")
            st.session_state[apply_key] = False
            st.rerun()
        except Exception as e:
            st.error(f"❌ 申請失敗：{e}")
