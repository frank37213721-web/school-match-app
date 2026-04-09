import pandas as pd
import streamlit as st
from utils import supabase, require_login

COLUMN_NAMES = {
    "title": "課程名稱",
    "course_type": "課程種類",
    "credits": "學分數",
    "syllabus": "課程大綱",
    "plan_details": "課程計畫說明",
    "start_time": "開課時間",
    "max_students": "跨校學生上限",
    "max_schools": "合作學校上限",
    "plan_pdf_url": "課程規劃表 PDF",
    "req_1": "合作要求一",
    "req_2": "合作要求二",
    "req_3": "合作要求三",
    "sps_min": "每校最少學生數",
    "sps_max": "每校最多學生數",
}


def render_my_courses():
    require_login()
    st.title("📚 本校開課課程")
    if not st.session_state.school_info:
        return

    school = st.session_state.school_info
    st.subheader(f"單位：{school['name']}")

    res = supabase.table("courses").select("*").eq("host_school_id", school['id']).execute()
    if not res.data:
        st.info("您目前尚未開設任何課程。")
        return

    df = pd.DataFrame(res.data)
    # 只保留有定義中文名的欄位（依順序）
    cols = [c for c in COLUMN_NAMES if c in df.columns]
    df = df[cols].rename(columns=COLUMN_NAMES)
    st.dataframe(df, use_container_width=True, hide_index=True)
