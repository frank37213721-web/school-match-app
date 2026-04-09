import streamlit as st
from utils import supabase, require_login, upload_pdf, delete_course_cascade


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
            c_time     = st.text_input("開課時間", placeholder="例：每週三 14:00-16:00")
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
                .select("id, title, start_time, max_students, max_schools, syllabus, plan_pdf_url, sps_min, sps_max, req_1, req_2, req_3")\
                .eq("host_school_id", school['id'])\
                .execute()
            if not my_courses.data:
                st.info("您目前尚無開設任何課程。")
            else:
                for c in my_courses.data:
                    with st.expander(f"📖 {c['title']}"):
                        with st.form(f"edit_form_{c['id']}"):
                            e_title    = st.text_input("課程名稱", value=c['title'])
                            e_time     = st.text_input("開課時間", value=c.get('start_time', ''))
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
