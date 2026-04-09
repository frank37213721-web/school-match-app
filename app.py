import streamlit as st
from utils import supabase, is_admin, is_logged_in
from styles import GLOBAL_CSS
from pages_content.lobby import render_lobby
from pages_content.login import render_login
from pages_content.my_courses import render_my_courses
from pages_content.school_info import render_school_info
from pages_content.add_course import render_add_course
from pages_content.matches import render_matches
from pages_content.admin import render_admin

st.set_page_config(page_title="跨校課程匯流平台", layout="wide")
st.markdown(GLOBAL_CSS, unsafe_allow_html=True)

# ── 初始化登入狀態 ──
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.school_info = None

# ── 登入歡迎訊息 ──
if st.session_state.get("logged_in") and st.session_state.get("school_info"):
    school = st.session_state.school_info
    st.sidebar.markdown(
        f"**{school['name']}**  \n{school.get('registrant_name', '')} 承辦人，您好 👋",
        unsafe_allow_html=False
    )
    st.sidebar.divider()

# ── 配對回覆通知（答應 / 拒絕），登入後持續顯示直到按知道了 ──
if st.session_state.get("logged_in") and st.session_state.get("school_info"):
    school = st.session_state.school_info
    if 'dismissed_notifications' not in st.session_state:
        st.session_state.dismissed_notifications = set()
    try:
        notif_res = supabase.table("matches")\
            .select("id, status, course_id")\
            .eq("partner_school_id", school['id'])\
            .in_("status", ["approved", "rejected"])\
            .execute()
        for m in notif_res.data:
            if m['id'] not in st.session_state.dismissed_notifications:
                course_res = supabase.table("courses")\
                    .select("title, schools(name)")\
                    .eq("id", m['course_id'])\
                    .execute()
                if course_res.data:
                    c = course_res.data[0]
                    host_name = c['schools']['name'] if c.get('schools') else '開課學校'
                    if m['status'] == 'approved':
                        st.success(
                            f"🎉 **配對申請通知**\n\n"
                            f"恭喜！**{host_name}** 已答應您對課程「**{c['title']}**」的申請，合作正式成立！\n\n"
                            f"📌 請盡快與對方聯繫，確認課程細節與行政事宜。"
                        )
                    else:
                        st.warning(
                            f"😔 **配對申請通知**\n\n"
                            f"很遺憾，**{host_name}** 婉拒了您對課程「**{c['title']}**」的申請。"
                        )
                    if st.button("知道了", key=f"dismiss_notif_{m['id']}"):
                        st.session_state.dismissed_notifications.add(m['id'])
                        st.rerun()
    except Exception:
        pass

# ── 側邊欄選單 ──
if is_admin():
    menu = ["課程大廳", "📊 系統管理", "登出"]
elif not is_logged_in():
    menu = ["課程大廳", "學校帳號登入"]
else:
    menu = ["課程大廳", "管理中心 (我的課程)", "配對情形", "學校基本資料", "新增/修改課程", "登出"]

# 強制跳轉至登入頁（首頁按鈕觸發）
if st.session_state.get("force_login") and "學校帳號登入" in menu:
    st.session_state["sidebar_menu"] = "學校帳號登入"
    st.session_state.force_login = False

# 若目前記憶的選項不在當前選單（例如登入/登出後選單改變），重設至第一項
if st.session_state.get("sidebar_menu") not in menu:
    st.session_state["sidebar_menu"] = menu[0]

choice = st.sidebar.selectbox("選單", menu, key="sidebar_menu")

# ── 登出邏輯 ──
if choice == "登出":
    st.session_state.logged_in = False
    st.session_state.school_info = None
    st.session_state.entered_lobby = False
    st.session_state.admin_logged_in = False
    st.rerun()

# ── 頁面路由 ──
if choice == "課程大廳":
    render_lobby()
elif choice == "學校帳號登入":
    render_login()
elif choice == "管理中心 (我的課程)":
    render_my_courses()
elif choice == "學校基本資料":
    render_school_info()
elif choice == "新增/修改課程":
    render_add_course()
elif choice == "配對情形":
    render_matches()
elif choice == "📊 系統管理":
    render_admin()
