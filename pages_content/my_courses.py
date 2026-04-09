import streamlit as st
from utils import supabase, require_login


def render_my_courses():
    require_login()
    st.title("⚙️ 學校管理中心")
    if st.session_state.school_info:
        school = st.session_state.school_info
        st.subheader(f"單位：{school['name']}")
        res = supabase.table("courses").select("*").eq("host_school_id", school['id']).execute()
        if res.data:
            st.write("您已開設的課程：")
            st.table(res.data)
        else:
            st.info("您目前尚未開設任何課程。")
