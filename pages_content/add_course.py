import re
import streamlit as st
from utils import supabase, require_login, upload_pdf, delete_course_cascade

COURSE_TYPES = ["部定必修", "加深加廣選修", "校訂必修", "多元選修", "彈性課程"]
DAYS = ["週一", "週二", "週三", "週四", "週五", "週六"]


def _parse_time(time_str):
    """從已儲存的時間字串解析出 (day_idx, start_h, end_h)，解析失敗回傳預設值。"""
    if not time_str:
        return 0, 8, 10
    m = re.match(r"(週[一二三四五六])\s*(\d{1,2}):00\s*[~～\-]\s*(\d{1,2}):00", time_str)
    if m:
        day_idx = DAYS.index(m.group(1)) if m.group(1) in DAYS else 0
        return day_idx, int(m.group(2)), int(m.group(3))
    return 0, 8, 10


def render_add_course():
    require_login()
    st.header("✍️ 管理您的課程")
    if not st.session_state.school_info:
        return

    school = st.session_state.school_info
    st.write(f"開課單位：**{school['name']}**")

    tab_add, tab_edit = st.tabs(["➕ 新增課程", "✏️ 修改／刪除課程"])

    with tab_add:
        with st.form("course_form_add"):
            c_title    = st.text_input("課程名稱")
            col_type, col_credits = st.columns(2)
            with col_type:
                c_type = st.selectbox("課程種類", COURSE_TYPES)
            with col_credits:
                c_credits = st.number_input("學分數（一學期）", min_value=0, max_value=4, value=0)
            st.write("**🗓️ 開課時間**")
            col_day, col_sh, col_eh = st.columns([2, 2, 2])
            with col_day:
                c_day = st.selectbox("星期", DAYS, key="add_day")
            with col_sh:
                c_start_h = st.number_input("開始時間（時）", min_value=0, max_value=23, value=8, step=1, key="add_sh", format="%02d")
            with col_eh:
                c_end_h = st.number_input("結束時間（時）", min_value=0, max_value=23, value=10, step=1, key="add_eh", format="%02d")
            c_time = f"{c_day} {c_start_h:02d}:00 ~ {c_end_h:02d}:00"
            st.caption(f"📅 開課時間：{c_time}")
            c_students  = st.number_input("跨校學生人數上限", min_value=0, value=20)
            c_schools   = st.number_input("跨校學校數目上限", min_value=0, value=2)
            st.write("**🎓 每校希望學生人數範圍（選填）**")
            col_sps1, col_sps2 = st.columns(2)
            with col_sps1:
                c_sps_min = st.number_input("最少人數", min_value=0, max_value=5, value=0, key="add_sps_min")
            with col_sps2:
                c_sps_max = st.number_input("最多人數", min_value=0, max_value=5, value=0, key="add_sps_max")
            c_pdf_file  = st.file_uploader("課程規劃表 PDF（2MB 以內）", type=["pdf"])
            c_syllabus  = st.text_area("課程大綱／內容說明")
            st.write("**📋 開課學校合作要求（選填，最多三點）**")
            c_req1 = st.text_input("要求一", placeholder="例：合作學校需自備視訊設備")
            c_req2 = st.text_input("要求二")
            c_req3 = st.text_input("要求三")
            if st.form_submit_button("確認新增課程"):
                if not c_title:
                    st.error("請填寫課程名稱。")
                else:
                    pdf_url = ""
                    if c_pdf_file:
                        pdf_url = upload_pdf(c_pdf_file, school['id']) or ""
                    if c_pdf_file and not pdf_url:
                        pass  # upload_pdf 已顯示錯誤
                    else:
                        try:
                            supabase.table("courses").insert({
                                "host_school_id": school['id'],
                                "title": c_title,
                                "course_type": c_type,
                                "credits": c_credits if c_credits > 0 else None,
                                "start_time": c_time,
                                "max_students": c_students,
                                "max_schools": c_schools,
                                "sps_min": c_sps_min if c_sps_min > 0 else None,
                                "sps_max": c_sps_max if c_sps_max > 0 else None,
                                "plan_pdf_url": pdf_url,
                                "syllabus": c_syllabus,
                                "req_1": c_req1 or None,
                                "req_2": c_req2 or None,
                                "req_3": c_req3 or None,
                            }).execute()
                            st.success("🎉 課程新增成功！已同步顯示於課程大廳。")
                        except Exception as e:
                            st.error(f"新增失敗：{e}")

    with tab_edit:
        try:
            my_courses = supabase.table("courses")\
                .select("id, title, course_type, credits, start_time, max_students, max_schools, syllabus, plan_pdf_url, sps_min, sps_max, req_1, req_2, req_3")\
                .eq("host_school_id", school['id'])\
                .execute()
            if not my_courses.data:
                st.info("您目前尚無開設任何課程。")
            else:
                for c in my_courses.data:
                    with st.expander(f"📖 {c['title']}"):
                        with st.form(f"edit_form_{c['id']}"):
                            e_title    = st.text_input("課程名稱", value=c['title'])
                            col_type_e, col_credits_e = st.columns(2)
                            with col_type_e:
                                cur_type = c.get('course_type') or COURSE_TYPES[0]
                                type_idx = COURSE_TYPES.index(cur_type) if cur_type in COURSE_TYPES else 0
                                e_type = st.selectbox("課程種類", COURSE_TYPES, index=type_idx, key=f"type_{c['id']}")
                            with col_credits_e:
                                e_credits = st.number_input("學分數（一學期）", min_value=0, max_value=4, value=c.get('credits') or 0, key=f"credits_{c['id']}")
                            st.write("**🗓️ 開課時間**")
                            _day_idx, _sh, _eh = _parse_time(c.get('start_time', ''))
                            col_day_e, col_sh_e, col_eh_e = st.columns([2, 2, 2])
                            with col_day_e:
                                e_day = st.selectbox("星期", DAYS, index=_day_idx, key=f"day_{c['id']}")
                            with col_sh_e:
                                e_start_h = st.number_input("開始時間（時）", min_value=0, max_value=23, value=_sh, step=1, key=f"sh_{c['id']}", format="%02d")
                            with col_eh_e:
                                e_end_h = st.number_input("結束時間（時）", min_value=0, max_value=23, value=_eh, step=1, key=f"eh_{c['id']}", format="%02d")
                            e_time = f"{e_day} {e_start_h:02d}:00 ~ {e_end_h:02d}:00"
                            st.caption(f"📅 開課時間：{e_time}")
                            e_students  = st.number_input("跨校學生人數上限", min_value=0, value=c.get('max_students', 20))
                            e_schools   = st.number_input("跨校學校數目上限", min_value=0, value=c.get('max_schools', 2))
                            st.write("**🎓 每校希望學生人數範圍（選填）**")
                            col_sps1, col_sps2 = st.columns(2)
                            with col_sps1:
                                e_sps_min = st.number_input("最少人數", min_value=0, max_value=5, value=c.get('sps_min') or 0, key=f"sps_min_{c['id']}")
                            with col_sps2:
                                e_sps_max = st.number_input("最多人數", min_value=0, max_value=5, value=c.get('sps_max') or 0, key=f"sps_max_{c['id']}")
                            if c.get('plan_pdf_url'):
                                st.markdown(f"📄 目前 PDF：[查看現有檔案]({c['plan_pdf_url']})")
                            e_pdf_file  = st.file_uploader("更換課程規劃表 PDF（2MB 以內，不上傳則保留原檔）", type=["pdf"], key=f"pdf_{c['id']}")
                            e_syllabus  = st.text_area("課程大綱／內容說明", value=c.get('syllabus', '') or '')
                            st.write("**📋 開課學校合作要求（選填）**")
                            e_req1 = st.text_input("要求一", value=c.get('req_1', '') or '', key=f"req1_{c['id']}")
                            e_req2 = st.text_input("要求二", value=c.get('req_2', '') or '', key=f"req2_{c['id']}")
                            e_req3 = st.text_input("要求三", value=c.get('req_3', '') or '', key=f"req3_{c['id']}")
                            col_save, col_del = st.columns(2)
                            with col_save:
                                if st.form_submit_button("💾 儲存修改"):
                                    if not e_title:
                                        st.error("課程名稱不得為空。")
                                    else:
                                        new_pdf_url = c.get('plan_pdf_url', '') or ''
                                        if e_pdf_file:
                                            uploaded = upload_pdf(e_pdf_file, school['id'])
                                            if not uploaded:
                                                st.stop()
                                            new_pdf_url = uploaded
                                        try:
                                            supabase.table("courses").update({
                                                "title": e_title,
                                                "course_type": e_type,
                                                "credits": e_credits if e_credits > 0 else None,
                                                "start_time": e_time,
                                                "max_students": e_students,
                                                "max_schools": e_schools,
                                                "sps_min": e_sps_min if e_sps_min > 0 else None,
                                                "sps_max": e_sps_max if e_sps_max > 0 else None,
                                                "plan_pdf_url": new_pdf_url,
                                                "syllabus": e_syllabus,
                                                "req_1": e_req1 or None,
                                                "req_2": e_req2 or None,
                                                "req_3": e_req3 or None,
                                            }).eq("id", c['id']).execute()
                                            st.success("✅ 修改已儲存！")
                                            st.rerun()
                                        except Exception as e:
                                            st.error(f"修改失敗：{e}")
                            with col_del:
                                if st.form_submit_button("🗑️ 刪除此課程", type="secondary"):
                                    confirm_key = f"del_confirm_{c['id']}"
                                    st.session_state[confirm_key] = True

                        # 刪除二次確認（在 form 外）
                        confirm_key = f"del_confirm_{c['id']}"
                        if st.session_state.get(confirm_key):
                            # 檢查是否有其他學校已送出媒合申請
                            try:
                                pending_res = supabase.table("matches")\
                                    .select("id, partner_school_id, status, schools(name)")\
                                    .eq("course_id", c['id'])\
                                    .in_("status", ["pending", "approved"])\
                                    .execute()
                                pending_matches = pending_res.data or []
                            except Exception:
                                pending_matches = []

                            if pending_matches:
                                school_names = []
                                for m in pending_matches:
                                    n = (m.get('schools') or {}).get('name', '（未知學校）')
                                    status_label = "已核准" if m['status'] == 'approved' else "待審中"
                                    school_names.append(f"**{n}**（{status_label}）")
                                st.error(
                                    f"🚫 無法刪除「{c['title']}」\n\n"
                                    f"以下學校已送出媒合申請，請先在「配對情形」頁面處理後再刪除：\n\n"
                                    + "\n".join(f"- {s}" for s in school_names)
                                )
                                if st.button("知道了", key=f"blocked_del_{c['id']}"):
                                    st.session_state[confirm_key] = False
                                    st.rerun()
                            else:
                                st.warning(f"⚠️ 確定刪除「{c['title']}」？此操作將同時刪除所有配對記錄，且**無法復原**。")
                                col_yes, col_no = st.columns(2)
                                with col_yes:
                                    if st.button("✅ 確認刪除", key=f"yes_del_{c['id']}", type="primary"):
                                        try:
                                            delete_course_cascade(c['id'])
                                            st.session_state[confirm_key] = False
                                            st.success(f"已刪除「{c['title']}」。")
                                            st.rerun()
                                        except Exception as e:
                                            st.error(f"刪除失敗：{e}")
                                with col_no:
                                    if st.button("❌ 取消", key=f"no_del_{c['id']}"):
                                        st.session_state[confirm_key] = False
                                        st.rerun()
        except Exception as e:
            st.error(f"讀取課程失敗：{e}")
