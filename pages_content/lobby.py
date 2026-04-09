import streamlit as st
from utils import supabase, send_email, is_valid_email


def render_lobby():
    # ── 首頁 Landing Page ──
    if not st.session_state.get("entered_lobby", False):
        st.markdown("""
        <style>
        /* 隱藏 Streamlit 預設 UI */
        #MainMenu, footer, header { visibility: hidden; }
        [data-testid="stSidebar"] { display: none; }
        .stApp { background: linear-gradient(160deg, #10141f 0%, #172035 55%, #10141f 100%) !important; }
        .block-container { padding: 0 !important; max-width: 100% !important; }

        .hero {
            display: flex;
            flex-direction: column;
            align-items: center;
            text-align: center;
            padding-top: 18vh;
            padding-bottom: 2rem;
            padding-left: 1rem;
            padding-right: 1rem;
            font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'Helvetica Neue', sans-serif;
        }
        .hero-eyebrow {
            font-size: 1rem;
            font-weight: 500;
            letter-spacing: 0.15em;
            text-transform: uppercase;
            color: #2997ff;
            margin-bottom: 1.4rem;
        }
        .hero-title {
            font-size: clamp(2.8rem, 7vw, 5.5rem);
            font-weight: 700;
            letter-spacing: -0.025em;
            line-height: 1.05;
            color: #f5f5f7;
            margin-bottom: 1.2rem;
        }
        .hero-subtitle {
            font-size: clamp(1rem, 2.5vw, 1.4rem);
            font-weight: 300;
            color: rgba(245,245,247,0.55);
            letter-spacing: 0.01em;
            margin-bottom: 0;
        }
        .hero-divider {
            width: 60px;
            height: 1px;
            background: rgba(245,245,247,0.2);
            margin: 0 auto 2rem;
        }
        /* 首頁按鈕強制白字（高 specificity 覆蓋全域規則） */
        .stApp .stButton > button,
        .stApp [data-testid="baseButton-secondary"],
        .stApp [data-testid="baseButton-primary"],
        .stApp .stButton > button span,
        .stApp [data-testid="baseButton-secondary"] span,
        .stApp [data-testid="baseButton-primary"] span {
            color: #ffffff !important;
            font-weight: 600 !important;
            letter-spacing: 0.02em !important;
        }
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

    st.header("📚 現有跨校課程一覽")
    try:
        response = supabase.table("courses").select(
            "id, title, start_time, max_students, max_schools, syllabus, plan_pdf_url, host_school_id, "
            "sps_min, sps_max, req_1, req_2, req_3, "
            "schools(name, district, registrant_name, registrant_email, academic_director_email, principal_email)"
        ).execute()
        courses = response.data
        if not courses:
            st.info("目前尚無開課資訊。")
        else:
            all_course_ids = [c['id'] for c in courses]
            all_matches_res = supabase.table("matches")\
                .select("course_id, status")\
                .in_("course_id", all_course_ids)\
                .in_("status", ["pending", "approved"])\
                .execute()
            matches_by_course = {}
            for m in all_matches_res.data:
                matches_by_course.setdefault(m['course_id'], []).append(m)

            all_districts = sorted({c['schools'].get('district', '其他') for c in courses if c.get('schools')})
            col_f1, col_f2 = st.columns(2)
            with col_f1:
                selected_district = st.selectbox("🗺️ 篩選開課學校分區", ["全部"] + all_districts)
            with col_f2:
                time_keyword = st.text_input("🕐 搜尋時段關鍵字", placeholder="例：週三、14:00")

            filtered_courses = [
                c for c in courses
                if (selected_district == "全部" or c.get('schools', {}).get('district') == selected_district)
                and (not time_keyword or time_keyword in (c.get('start_time') or ''))
            ]
            st.caption(f"共 {len(filtered_courses)} 門課程")

            for c in filtered_courses:
                course_matches = matches_by_course.get(c['id'], [])
                approved_count = sum(1 for m in course_matches if m['status'] == 'approved')
                pending_count = sum(1 for m in course_matches if m['status'] == 'pending')
                total_active = approved_count + pending_count
                max_schools = c.get('max_schools', 2)

                with st.expander(f"📖 {c['title']} - {c['schools']['name']}"):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"**🗓️ 開課時間：** {c.get('start_time', '未設定')}")
                        st.write(f"**👥 跨校學生上限：** {c.get('max_students', 'N/A')} 人")
                        if c.get('sps_min') or c.get('sps_max'):
                            st.write(f"**🎓 每校希望學生人數：** {c.get('sps_min', '?')} ~ {c.get('sps_max', '?')} 人")
                    with col2:
                        st.write(f"**🏫 合作學校上限：** {max_schools} 所")
                        st.write(f"**📊 目前申請：** {total_active}/{max_schools} 所")
                        st.write(f"  - ✅ 已通過：{approved_count} 所")
                        st.write(f"  - ⏳ 待審核：{pending_count} 所")
                        if c.get('plan_pdf_url'):
                            st.link_button("📥 查看課程規劃表 (PDF)", c['plan_pdf_url'])
                    st.write(f"**📝 課程大綱：**\n{c['syllabus']}")

                    if f"show_matching_{c['id']}" not in st.session_state:
                        st.session_state[f"show_matching_{c['id']}"] = False

                    logged_in_school_id = st.session_state.school_info['id'] if st.session_state.get('logged_in') and st.session_state.get('school_info') else None
                    is_own_course = logged_in_school_id is not None and c.get('host_school_id') == logged_in_school_id

                    if is_own_course:
                        st.info("📌 此為您開設的課程，無法申請配對。")
                    else:
                        button_disabled = total_active >= max_schools
                        button_text = "🚫 名額已滿" if button_disabled else "申請配對"

                    if not is_own_course and st.button(button_text, key=f"btn_{c['id']}", disabled=button_disabled):
                        if not st.session_state.logged_in:
                            st.warning("⚠️ 老師請先登入後再進行配對申請喔！")
                        else:
                            st.session_state[f"show_matching_{c['id']}"] = True
                            st.rerun()

                    if st.session_state[f"show_matching_{c['id']}"]:
                        st.subheader(f"📋 配對確認事項 - {c['title']}")
                        st.write(f"**開課學校：** {c['schools']['name']}")
                        confirm_items = [
                            "確認授課時間段是否可以配合",
                            "確認是否課程計劃未來是否可以新增課程",
                            "確認合作學校端所準備之設備與環境是否可以安排妥當",
                            "未來如配對成功基於誠信原則請與開課學校建立良好夥伴關係",
                        ]
                        for req_key in ["req_1", "req_2", "req_3"]:
                            req_val = c.get(req_key, "")
                            if req_val:
                                confirm_items.append(f"【開課學校要求】{req_val}")
                        all_confirmed = True
                        for i, item in enumerate(confirm_items, 1):
                            if not st.checkbox(f"{i}. {item}", key=f"confirm_{c['id']}_{i}"):
                                all_confirmed = False

                        col1, col2 = st.columns(2)
                        with col1:
                            if st.button("取消申請", key=f"cancel_{c['id']}"):
                                st.session_state[f"show_matching_{c['id']}"] = False
                                st.rerun()
                        with col2:
                            if st.button("確定申請配對", key=f"send_{c['id']}", disabled=not all_confirmed):
                                with st.spinner('🔄 正在處理配對申請...'):
                                    try:
                                        existing_match = supabase.table("matches")\
                                            .select("id")\
                                            .eq("course_id", c['id'])\
                                            .eq("partner_school_id", st.session_state.school_info['id'])\
                                            .in_("status", ["pending", "approved"])\
                                            .execute()
                                        if existing_match.data:
                                            st.error("⚠️ 您已經申請過此課程的配對，且申請正在處理中或已通過！")
                                        elif total_active >= max_schools:
                                            st.error(f"⚠️ 此課程合作學校已滿！最多接受 {max_schools} 所學校。")
                                        else:
                                            match_result = supabase.table("matches").insert({
                                                "course_id": c['id'],
                                                "partner_school_id": st.session_state.school_info['id'],
                                                "status": "pending"
                                            }).execute()
                                            match_id = match_result.data[0]['id']
                                            applicant_school = st.session_state.school_info
                                            host_school = c['schools']
                                            email_recipients = [
                                                {"email": host_school['registrant_email'], "name": host_school['registrant_name'], "type": "host"},
                                                {"email": host_school.get('academic_director_email'), "name": "承辦處室主任", "type": "host"},
                                                {"email": host_school.get('principal_email'), "name": "校長", "type": "host"},
                                                {"email": applicant_school['registrant_email'], "name": applicant_school['registrant_name'], "type": "applicant"},
                                                {"email": applicant_school.get('academic_director_email'), "name": "承辦處室主任", "type": "applicant"},
                                                {"email": applicant_school.get('principal_email'), "name": "校長", "type": "applicant"},
                                            ]
                                            email_success = True
                                            failed_emails = []
                                            for recipient in email_recipients:
                                                if is_valid_email(recipient['email']):
                                                    try:
                                                        if recipient['type'] == 'host':
                                                            subject = f"配對申請通知：{applicant_school['name']} 申請您的課程「{c['title']}」"
                                                            content = f"親愛的 {recipient['name']}：\n\n您開設的課程「{c['title']}」收到來自 {applicant_school['name']} 的配對申請。\n\n申請學校資訊：\n- 學校：{applicant_school['name']}\n- 承辦人：{applicant_school['registrant_name']}\n- 聯絡電話：{applicant_school['phone']}\n- 分機：{applicant_school.get('registrant_extension', '未提供')}\n\n請登入系統查看詳細資訊並處理此申請。\n\n跨校課程匯流平台"
                                                        else:
                                                            subject = f"配對申請確認：已申請「{c['title']}」課程"
                                                            content = f"親愛的 {recipient['name']}：\n\n您的學校已成功遞交課程「{c['title']}」的配對申請。\n\n申請資訊：\n- 申請課程：{c['title']}\n- 開課學校：{host_school['name']}\n- 申請編號：{match_id}\n\n我們將通知開課學校處理您的申請，請耐心等候回覆。\n\n跨校課程匯流平台"
                                                        success, msg = send_email(recipient['email'], recipient['name'], subject, content)
                                                        if not success:
                                                            email_success = False
                                                            failed_emails.append(f"{recipient['name']} ({recipient['email']})")
                                                    except Exception:
                                                        email_success = False
                                                        failed_emails.append(f"{recipient['name']} ({recipient['email']})")
                                            if email_success:
                                                st.success("✅ 配對申請已成功提交！所有相關人員都會收到通知 Email。")
                                            else:
                                                st.warning(f"⚠️ 配對申請已提交，但部分 Email 發送失敗：{', '.join(failed_emails)}")
                                            st.session_state[f"show_matching_{c['id']}"] = False
                                            st.rerun()
                                    except Exception as e:
                                        st.error(f"❌ 申請失敗：{e}")
                                        st.info("請稍後再試或聯繫管理員")
    except Exception as e:
        st.error(f"讀取資料失敗：{e}")
