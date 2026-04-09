from datetime import datetime
import streamlit as st
from utils import supabase, require_login, is_valid_email, send_email


def _fmt_time(ts):
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        return dt.astimezone().strftime("%Y/%m/%d %H:%M")
    except Exception:
        return "不明時間"


def render_matches():
    require_login()
    st.header("🤝 課程配對進度追蹤")
    school = st.session_state.school_info

    tab1, tab2 = st.tabs(["我是開課學校 (收到的申請)", "我是合作學校 (寄出的申請)"])

    with tab1:
        st.subheader("📩 收到其他學校的配對請求")
        try:
            my_courses_res = supabase.table("courses")\
                .select("id, title, max_schools")\
                .eq("host_school_id", school['id'])\
                .execute()
            my_course_ids = [c['id'] for c in my_courses_res.data]
            my_course_map = {c['id']: c for c in my_courses_res.data}

            if my_course_ids:
                incoming = supabase.table("matches")\
                    .select("id, status, course_id, partner_school_id, updated_at")\
                    .in_("course_id", my_course_ids)\
                    .execute()

                partner_ids = list({m['partner_school_id'] for m in incoming.data})
                partner_map = {}
                if partner_ids:
                    schools_res = supabase.table("schools")\
                        .select("id, name, registrant_name, registrant_email, academic_director_email, principal_email")\
                        .in_("id", partner_ids)\
                        .execute()
                    partner_map = {s['id']: s for s in schools_res.data}

                if incoming.data:
                    for m in incoming.data:
                        course = my_course_map.get(m['course_id'], {})
                        course_title = course.get('title', '未知課程')
                        max_schools = course.get('max_schools', 2)
                        partner_info = partner_map.get(m['partner_school_id'], {})
                        partner_name = partner_info.get('name', '未知學校') if isinstance(partner_info, dict) else partner_info
                        status = m['status']

                        if status == "rejected":
                            status_label = f"您已於 {_fmt_time(m['updated_at'])} 婉拒該校的申請"
                        elif status == "approved":
                            status_label = f"✅ 您已於 {_fmt_time(m['updated_at'])} 答應對方的申請"
                        else:
                            status_label = "⏳ 待審核"

                        with st.container(border=True):
                            st.write(f"**{partner_name}** 申請了「{course_title}」　{status_label}")

                            if status == "pending":
                                col1, col2 = st.columns(2)
                                with col1:
                                    if st.button("✅ 確認正式合作", key=f"approve_{m['id']}"):
                                        approved_count = len([x for x in incoming.data
                                                              if x['course_id'] == m['course_id'] and x['status'] == 'approved'])
                                        if approved_count >= max_schools:
                                            st.error(f"已達合作學校上限（{max_schools} 所），無法再核准。")
                                        else:
                                            supabase.table("matches").update({"status": "approved"}).eq("id", m['id']).execute()
                                            for recipient_email, recipient_name in [
                                                (partner_info.get('registrant_email'), partner_info.get('registrant_name', '承辦人')),
                                                (partner_info.get('academic_director_email'), '承辦處室主任'),
                                                (partner_info.get('principal_email'), '校長'),
                                            ]:
                                                if is_valid_email(recipient_email):
                                                    send_email(
                                                        recipient_email, recipient_name,
                                                        f"配對成功通知：您的課程申請「{course_title}」已被核准",
                                                        f"親愛的 {recipient_name}：\n\n恭喜！{partner_name} 對課程「{course_title}」的配對申請已獲得開課學校「{school['name']}」正式核准，雙方合作正式成立。\n\n【開課學校聯絡資訊】\n- 承辦人姓名：{school.get('registrant_name', '未提供')}\n- 承辦人 Email：{school.get('registrant_email', '未提供')}\n- 承辦處室主任 Email：{school.get('academic_director_email', '未提供')}\n- 學校電話：{school.get('phone', '未提供')}\n- 承辦人分機：{school.get('registrant_extension', '未提供')}\n\n請盡快與開課學校聯繫，確認後續合作細節。\n\n跨校課程匯流平台"
                                                    )
                                            st.success(f"已確認與 {partner_name} 正式合作，通知 Email 已發送！")
                                            st.rerun()
                                with col2:
                                    if st.button("❌ 拒絕", key=f"reject_{m['id']}"):
                                        supabase.table("matches").update({"status": "rejected"}).eq("id", m['id']).execute()
                                        for recipient_email, recipient_name in [
                                            (partner_info.get('registrant_email'), partner_info.get('registrant_name', '承辦人')),
                                            (partner_info.get('academic_director_email'), '承辦處室主任'),
                                            (partner_info.get('principal_email'), '校長'),
                                        ]:
                                            if is_valid_email(recipient_email):
                                                send_email(
                                                    recipient_email, recipient_name,
                                                    f"配對申請通知：「{course_title}」申請未獲通過",
                                                    f"親愛的 {recipient_name}：\n\n很遺憾，{partner_name} 對課程「{course_title}」的配對申請已被開課學校「{school['name']}」婉拒。\n\n跨校課程匯流平台"
                                                )
                                        st.warning(f"已婉拒 {partner_name} 的申請，通知 Email 已發送。")
                                        st.rerun()
                else:
                    st.write("目前尚無收到申請。")
            else:
                st.write("目前尚無收到申請。")
        except Exception as e:
            st.error(f"讀取失敗（Tab1）：{e}")

    with tab2:
        st.subheader("📤 已寄出的配對請求")
        try:
            outgoing = supabase.table("matches")\
                .select("id, status, course_id, updated_at")\
                .eq("partner_school_id", school['id'])\
                .execute()

            if outgoing.data:
                course_ids = list({m['course_id'] for m in outgoing.data})
                courses_res = supabase.table("courses")\
                    .select("id, title, host_school_id")\
                    .in_("id", course_ids)\
                    .execute()
                course_map = {c['id']: c for c in courses_res.data}

                host_ids = list({c['host_school_id'] for c in courses_res.data})
                host_res = supabase.table("schools")\
                    .select("id, name")\
                    .in_("id", host_ids)\
                    .execute()
                host_map = {s['id']: s['name'] for s in host_res.data}

                for m in outgoing.data:
                    course = course_map.get(m['course_id'], {})
                    host_name = host_map.get(course.get('host_school_id'), '未知學校')
                    course_title = course.get('title', '未知課程')
                    ts = _fmt_time(m.get('updated_at', ''))
                    if m['status'] == 'approved':
                        st.success(f"🎉 **配對成功**　**{host_name}** 已於 {ts} 答應您對「{course_title}」的申請，合作正式成立！")
                        st.caption("📌 接下來請雙方進行實際聯繫，確認課程細節與行政事宜，祝學生都能學習順利！")
                    elif m['status'] == 'rejected':
                        st.warning(f"😔 **申請未獲通過**　**{host_name}** 已於 {ts} 婉拒您對「{course_title}」的申請。")
                    else:
                        st.info(f"⏳ **審核中**　您向 **{host_name}** 申請了「{course_title}」，已於 {ts} 送出，請等候回覆。")
            else:
                st.write("您尚未申請任何課程。")
        except Exception as e:
            st.error(f"讀取失敗（Tab2）：{e}")
