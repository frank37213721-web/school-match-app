import re
import smtplib
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

import streamlit as st
from supabase import create_client
from passlib.context import CryptContext

# ── Supabase client ──
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

# ── Password hashing ──
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

PDF_BUCKET = "course-pdfs"
MAX_PDF_BYTES = 2 * 1024 * 1024  # 2 MB


def is_valid_email(email):
    pattern = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
    return bool(email) and re.match(pattern, email) is not None


def hash_password(raw_password: str) -> str:
    return pwd_context.hash(raw_password)


def verify_password(raw_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(raw_password, hashed_password)


def upload_pdf(uploaded_file, school_id) -> str | None:
    """上傳 PDF 至 Supabase Storage，回傳公開 URL；失敗時回傳 None。"""
    file_bytes = uploaded_file.read()
    if len(file_bytes) > MAX_PDF_BYTES:
        st.error("檔案超過 2MB 上限，請壓縮後再上傳。")
        return None
    path = f"{school_id}/{int(time.time())}.pdf"
    try:
        supabase.storage.from_(PDF_BUCKET).upload(
            path, file_bytes, {"content-type": "application/pdf"}
        )
        return supabase.storage.from_(PDF_BUCKET).get_public_url(path)
    except Exception as e:
        st.error(f"PDF 上傳失敗：{e}")
        return None


def delete_course_cascade(course_id):
    """刪除課程前，先刪除所有關聯的 matches，避免 FK 報錯"""
    supabase.table("matches").delete().eq("course_id", course_id).execute()
    supabase.table("courses").delete().eq("id", course_id).execute()


def delete_school_cascade(school_id):
    """刪除學校前，依序刪除 matches → courses → schools，避免 FK 報錯"""
    courses_res = supabase.table("courses").select("id").eq("host_school_id", school_id).execute()
    course_ids = [c["id"] for c in courses_res.data]
    for cid in course_ids:
        supabase.table("matches").delete().eq("course_id", cid).execute()
    supabase.table("matches").delete().eq("partner_school_id", school_id).execute()
    supabase.table("courses").delete().eq("host_school_id", school_id).execute()
    supabase.table("schools").delete().eq("id", school_id).execute()


def require_login():
    if not st.session_state.get("logged_in"):
        st.warning("⚠️ 請先登入學校帳號")
        st.stop()


def require_admin():
    if not st.session_state.get("admin_logged_in"):
        st.error("🚫 您沒有管理權限，請以管理員身份登入")
        st.stop()


def is_admin():
    return st.session_state.get("admin_logged_in", False)


def is_logged_in():
    return st.session_state.get("logged_in", False)


def send_email(to_email, to_name, subject, content):
    """發送 Email 給指定收件人"""
    try:
        gmail_user = st.secrets["GMAIL_USER"]
        gmail_password = st.secrets["GMAIL_PASSWORD"]

        msg = MIMEMultipart()
        msg['From'] = gmail_user
        msg['To'] = to_email
        msg['Subject'] = subject

        body = f"""{content}

---
跨校課程匯流平台
        """
        msg.attach(MIMEText(body, 'plain', 'utf-8'))

        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(gmail_user, gmail_password)
            server.sendmail(gmail_user, to_email, msg.as_string())

        return True, "Email 發送成功"
    except Exception as e:
        return False, f"Email 發送失敗：{str(e)}"
