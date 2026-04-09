import re
import streamlit as st
from supabase import create_client
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def is_valid_email(email):
    pattern = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
    return bool(email) and re.match(pattern, email) is not None
from passlib.context import CryptContext
from datetime import datetime

# 密碼雜湊設定
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(raw_password: str) -> str:
    return pwd_context.hash(raw_password)

def verify_password(raw_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(raw_password, hashed_password)

# 連鎖刪除函數
def delete_course_cascade(course_id):
    """刪除課程前，先刪除所有關聯的 matches，避免 FK 報錯"""
    supabase.table("matches").delete().eq("course_id", course_id).execute()
    supabase.table("courses").delete().eq("id", course_id).execute()

def delete_school_cascade(school_id):
    """刪除學校前，依序刪除 matches → courses → schools，避免 FK 報錯"""
    # 1. 找出該學校所有課程 id
    courses_res = supabase.table("courses").select("id").eq("host_school_id", school_id).execute()
    course_ids = [c["id"] for c in courses_res.data]

    # 2. 刪除這些課程的所有 matches
    for cid in course_ids:
        supabase.table("matches").delete().eq("course_id", cid).execute()

    # 3. 刪除該學校作為 partner 的 matches
    supabase.table("matches").delete().eq("partner_school_id", school_id).execute()

    # 4. 刪除該學校所有課程
    supabase.table("courses").delete().eq("host_school_id", school_id).execute()

    # 5. 刪除學校本身
    supabase.table("schools").delete().eq("id", school_id).execute()

# 權限控制函數
def require_login():
    """要求用戶登入，否則顯示警告並停止執行"""
    if not st.session_state.get("logged_in"):
        st.warning("⚠️ 請先登入學校帳號")
        st.stop()

def require_admin():
    """要求管理員權限，否則顯示錯誤並停止執行"""
    if not st.session_state.get("admin_logged_in"):
        st.error("🚫 您沒有管理權限，請以管理員身份登入")
        st.stop()

def is_admin():
    """檢查是否為管理員"""
    return st.session_state.get("admin_logged_in", False)

def is_logged_in():
    """檢查是否已登入"""
    return st.session_state.get("logged_in", False)

# 1. 連接 Supabase (建議將金鑰移至 secrets.toml)
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

st.set_page_config(page_title="跨校課程媒合平台", layout="wide")

# 顯示登入狀態 - 在 Deploy 按鈕旁邊顯示
if st.session_state.get("logged_in") and st.session_state.get("school_info"):
    school = st.session_state.school_info
    # 使用 Streamlit 的 columns 來在頂部創建一個橫幅
    with st.container():
        col1, col2, col3 = st.columns([2, 1, 1])
        with col3:
            st.markdown(f"""
            <div style="background-color: #e8f4fd; padding: 8px 12px; border-radius: 8px; border-left: 4px solid #1f77b4; margin-top: 10px;">
                👋 你好，{school['name']}{school['registrant_name']}{school['identity']}
            </div>
            """, unsafe_allow_html=True)

    # 拒絕通知：查詢此學校被拒絕的媒合申請
    if 'dismissed_rejections' not in st.session_state:
        st.session_state.dismissed_rejections = set()
    try:
        rejected_res = supabase.table("matches")\
            .select("id, course_id")\
            .eq("partner_school_id", school['id'])\
            .eq("status", "rejected")\
            .execute()
        for rm in rejected_res.data:
            if rm['id'] not in st.session_state.dismissed_rejections:
                course_res = supabase.table("courses")\
                    .select("id, title, max_schools")\
                    .eq("id", rm['course_id'])\
                    .execute()
                if course_res.data:
                    c = course_res.data[0]
                    approved_res = supabase.table("matches")\
                        .select("id")\
                        .eq("course_id", c['id'])\
                        .eq("status", "approved")\
                        .execute()
                    has_slots = len(approved_res.data) < c.get('max_schools', 2)
                    slot_msg = "該課程目前仍有名額，您可以再次送出媒合申請。" if has_slots else "該課程目前已無剩餘名額。"
                    st.warning(f"😔 **媒合申請通知**\n\n很遺憾，您對課程「**{c['title']}**」的媒合申請已被開課學校拒絕。{slot_msg}")
                    if st.button("知道了", key=f"dismiss_{rm['id']}"):
                        st.session_state.dismissed_rejections.add(rm['id'])
                        st.rerun()
    except Exception:
        pass

# Email 發送函數
def send_email(to_email, to_name, subject, content):
    """發送 Email 給指定收件人"""
    try:
        # 修正：從 st.secrets 取得資訊並統一變數名稱
        gmail_user = st.secrets["GMAIL_USER"]
        gmail_password = st.secrets["GMAIL_PASSWORD"]
        
        # 建立郵件內容
        msg = MIMEMultipart()
        msg['From'] = gmail_user
        msg['To'] = to_email
        msg['Subject'] = subject
        
        body = f"""{content}

---
跨校課程媒合平台
https://your-app-url.com
        """
        
        msg.attach(MIMEText(body, 'plain', 'utf-8'))
        
        # 發送郵件
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(gmail_user, gmail_password) # 使用正確的變數
            text = msg.as_string()
            server.sendmail(gmail_user, to_email, text)
        
        return True, "Email 發送成功"
        
    except Exception as e:
        return False, f"Email 發送失敗：{str(e)}"

# 初始化登入狀態
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.school_info = None

# --- 側邊欄選單 ---
if is_admin():
    # 管理員專用選單
    menu = ["課程大廳", "📊 系統管理", "登出"]
elif not is_logged_in():
    menu = ["課程大廳", "學校帳號登入"]
else:
    # 加入「配對情形」和「學校基本資料」
    menu = ["課程大廳", "管理中心 (我的課程)", "配對情形", "學校基本資料", "新增/修改課程", "登出"]

choice = st.sidebar.selectbox("選單", menu)

# --- 登出邏輯 ---
if choice == "登出":
    st.session_state.logged_in = False
    st.session_state.school_info = None
    st.session_state.admin_logged_in = False
    st.rerun()

# --- 頁面內容 ---
if choice == "課程大廳":
    st.header("📚 現有跨校課程一覽")
    try:
        # 精確欄位查詢，含學校分區
        response = supabase.table("courses").select(
            "id, title, start_time, max_students, max_schools, syllabus, plan_pdf_url, host_school_id, "
            "schools(name, district, registrant_name, registrant_email, academic_director_email, principal_email)"
        ).execute()
        courses = response.data
        if not courses:
            st.info("目前尚無開課資訊。")
        else:
            # 一次批次撈所有課程的 matches，避免 N+1 查詢
            all_course_ids = [c['id'] for c in courses]
            all_matches_res = supabase.table("matches")\
                .select("course_id, status")\
                .in_("course_id", all_course_ids)\
                .in_("status", ["pending", "approved"])\
                .execute()
            matches_by_course = {}
            for m in all_matches_res.data:
                matches_by_course.setdefault(m['course_id'], []).append(m)

            # --- 篩選 UI ---
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
                        st.info("📌 此為您開設的課程，無法申請媒合。")
                    else:
                        button_disabled = total_active >= max_schools
                        button_text = "🚫 名額已滿" if button_disabled else "申請媒合"

                    if not is_own_course and st.button(button_text, key=f"btn_{c['id']}", disabled=button_disabled):
                        if not st.session_state.logged_in:
                            st.warning("⚠️ 老師請先登入後再進行媒合申請喔！")
                        else:
                            st.session_state[f"show_matching_{c['id']}"] = True
                            st.rerun()

                    if st.session_state[f"show_matching_{c['id']}"]:
                        st.subheader(f"📋 媒合確認事項 - {c['title']}")
                        st.write(f"**開課學校：** {c['schools']['name']}")
                        confirm_items = [
                            "確認授課時間段是否可以配合",
                            "確認是否課程計劃未來是否可以新增課程",
                            "確認合作學校端所準備之設備與環境是否可以安排妥當",
                            "開課學校希望要求確認事項I、II、III",
                            "未來如媒合成功基於誠信原則請與開課學校建立良好夥伴關係"
                        ]
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
                            if st.button("確定申請媒合", key=f"send_{c['id']}", disabled=not all_confirmed):
                                with st.spinner('🔄 正在處理媒合申請...'):
                                    try:
                                        existing_match = supabase.table("matches")\
                                            .select("id")\
                                            .eq("course_id", c['id'])\
                                            .eq("partner_school_id", st.session_state.school_info['id'])\
                                            .in_("status", ["pending", "approved"])\
                                            .execute()
                                        if existing_match.data:
                                            st.error("⚠️ 您已經申請過此課程的媒合，且申請正在處理中或已通過！")
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
                                                            subject = f"媒合申請通知：{applicant_school['name']} 申請您的課程「{c['title']}」"
                                                            content = f"親愛的 {recipient['name']}：\n\n您開設的課程「{c['title']}」收到來自 {applicant_school['name']} 的媒合申請。\n\n申請學校資訊：\n- 學校：{applicant_school['name']}\n- 承辦人：{applicant_school['registrant_name']}\n- 聯絡電話：{applicant_school['phone']}\n- 分機：{applicant_school.get('registrant_extension', '未提供')}\n\n請登入系統查看詳細資訊並處理此申請。\n\n跨校課程媒合平台"
                                                        else:
                                                            subject = f"媒合申請確認：已申請「{c['title']}」課程"
                                                            content = f"親愛的 {recipient['name']}：\n\n您的學校已成功遞交課程「{c['title']}」的媒合申請。\n\n申請資訊：\n- 申請課程：{c['title']}\n- 開課學校：{host_school['name']}\n- 申請編號：{match_id}\n\n我們將通知開課學校處理您的申請，請耐心等候回覆。\n\n跨校課程媒合平台"
                                                        success, msg = send_email(recipient['email'], recipient['name'], subject, content)
                                                        if not success:
                                                            email_success = False
                                                            failed_emails.append(f"{recipient['name']} ({recipient['email']})")
                                                    except Exception:
                                                        email_success = False
                                                        failed_emails.append(f"{recipient['name']} ({recipient['email']})")
                                            if email_success:
                                                st.success("✅ 媒合申請已成功提交！所有相關人員都會收到通知 Email。")
                                            else:
                                                st.warning(f"⚠️ 媒合申請已提交，但部分 Email 發送失敗：{', '.join(failed_emails)}")
                                            st.session_state[f"show_matching_{c['id']}"] = False
                                            st.rerun()
                                    except Exception as e:
                                        st.error(f"❌ 申請失敗：{e}")
                                        st.info("請稍後再試或聯繫管理員")
    except Exception as e:
        st.error(f"讀取資料失敗：{e}")

elif choice == "學校帳號登入":
    auth_mode = st.radio("請選擇操作", ["學校帳號登入", "註冊學校帳號", "管理人員登入"], horizontal=True)

    if auth_mode == "學校帳號登入":
        st.subheader("🔑 學校帳號登入")
        phone = st.text_input("帳號（學校電話）")
        pwd = st.text_input("密碼", type="password")
        if st.button("確認登入"):
            res = supabase.table("schools").select("*").eq("phone", phone).execute()
            if res.data:
                user = res.data[0]
                if verify_password(pwd, user['password_hash']):  # 使用統一的欄位名稱
                    st.session_state.logged_in = True
                    st.session_state.school_info = user
                    st.success(f"登入成功！歡迎 {user['name']}")
                    st.rerun()
                else:
                    st.error("密碼錯誤！")
            else:
                st.error("找不到此帳號！")
        
        # 忘記密碼功能
        st.divider()
        st.subheader("🔐 忘記密碼")
        st.write("如果您忘記密碼，可以透過以下方式重置為預設密碼")
        
        with st.expander("📋 重置密碼說明"):
            st.info("""
            **重置密碼流程：**
            1. 輸入學校帳號（電話號碼）
            2. 輸入承辦人姓名進行身分驗證
            3. 輸入承辦人 Email 進行驗證
            4. 驗證成功後，密碼將重置為預設密碼（電話號碼後4碼）
            5. 重置密碼會 Email 通知相關人員
            """)
        
        # 忘記密碼表單
        forgot_phone = st.text_input("學校帳號 (電話號碼)", key="forgot_phone")
        forgot_name = st.text_input("承辦人姓名", key="forgot_name")
        forgot_email = st.text_input("承辦人 Email", key="forgot_email")
        
        if st.button("🔄 重置密碼", key="reset_password"):
            if forgot_phone and forgot_name and forgot_email:
                with st.spinner("🔍 正在驗證身分資訊..."):
                    try:
                        # 查詢學校資料
                        school_res = supabase.table("schools").select("*").eq("phone", forgot_phone).execute()
                        
                        if not school_res.data:
                            st.error("❌ 找不到此帳號！請確認電話號碼正確。")
                        else:
                            school = school_res.data[0]
                            
                            # 驗證承辦人姓名
                            if school['registrant_name'] != forgot_name:
                                st.error("❌ 承辦人姓名不符！請確認輸入正確。")
                            # 驗證承辦人 Email
                            elif school['registrant_email'] != forgot_email:
                                st.error("❌ 承辦人 Email 不符！請確認輸入正確。")
                            else:
                                # 驗�通過，重置密碼
                                default_password = forgot_phone[-4:] if len(forgot_phone) >= 4 else "0000"
                                hashed_password = hash_password(default_password)
                                
                                # 更新密碼
                                supabase.table("schools").update({"password_hash": hashed_password}).eq("id", school['id']).execute()
                                
                                # 發送通知 Email
                                subject = "🔐 密碼重置通知 - 跨校課程媒合平台"
                                content = f"""
親愛的 {school['registrant_name']}：

您的密碼已成功重置。

重置資訊：
- 學校：{school['name']}
- 帳號：{school['phone']}
- 新密碼：{default_password}

**重要提醒：**
- 請使用新密碼登入系統
- 建議登入後立即修改密碼
- 如有問題請聯繫系統管理員

登入網址：[您的應用程式網址]

跨校課程媒合平台
                                """
                                
                                # 發送給承辦人
                                email_success, email_msg = send_email(
                                    school['registrant_email'], 
                                    school['registrant_name'], 
                                    subject, 
                                    content
                                )
                                
                                # 同時通知承辦處室主任和校長（如果有 Email）
                                additional_recipients = []
                                if is_valid_email(school.get('academic_director_email', '')):
                                    additional_recipients.append({
                                        'email': school['academic_director_email'],
                                        'name': '承辦處室主任'
                                    })
                                if is_valid_email(school.get('principal_email', '')):
                                    additional_recipients.append({
                                        'email': school['principal_email'],
                                        'name': '校長'
                                    })
                                
                                for recipient in additional_recipients:
                                    admin_content = f"""
親愛的 {recipient['name']}：

通知：{school['name']} 的承辦人 {school['registrant_name']} 已重置密碼。

重置時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

如非授權操作，請立即聯繫系統管理員。

跨校課程媒合平台
                                    """
                                    send_email(recipient['email'], recipient['name'], subject, admin_content)
                                
                                if email_success:
                                    st.success(f"✅ 密碼重置成功！")
                                    st.info(f"🔑 新密碼：{default_password}")
                                    st.info("📧 已發送通知 Email 給相關人員")
                                    st.balloons()
                                else:
                                    st.success(f"✅ 密碼重置成功！")
                                    st.info(f"🔑 新密碼：{default_password}")
                                    st.warning("⚠️ Email 發送失敗，請記錄新密碼")
                                
                    except Exception as e:
                        st.error(f"❌ 重置失敗：{e}")
            else:
                st.error("⚠️ 請填寫所有必填欄位！")
    
    elif auth_mode == "註冊學校帳號":
        # --- 註冊功能 (全新邏輯) ---
        st.subheader("📝 建立學校帳號")
        
        # 按分區分組的學校列表
        schools_by_district = {
            "北一區": [
                "國立羅東高級中學", "國立蘭陽女子高級中學", "國立花蓮高級中學", 
                "慈濟大學附屬高級中學", "國立基隆高級中學", "新北市立中和高級中學",
                "新北市立北大高級中學", "新北市立石碇高級中學", "新北市立板橋高中",
                "新北市立錦和高級中學", "新北市私立徐匯高級中學", "新北市金陵女子高級中學",
                "新北市南山高級中學"
            ],
            "北二區": [
                "國立臺灣師範大學附屬高級中學", "臺北市立中山女子高級中學",
                "臺北市立中正高級中學", "臺北市立中崙高級中學", "臺北市立內湖高級中學",
                "臺北市立永春高級中學", "臺北市立百齡高級中學", "臺北市立育成高級中學",
                "臺北市立松山高級中學", "臺北市立建國高級中學", "臺北市立第一女子高級中學",
                "臺北市立景美女子高級中學", "臺北市立陽明高級中學", "臺北市立萬芳高級中學",
                "臺北市立麗山高級中學", "臺北市數位實驗高級中等學校"
            ],
            "北三區": [
                "桃園市立內壢高級中等學校", "桃園市立桃園高級中等學校", "桃園市立陽明高級中等學校",
                "桃園市立楊梅高級中等學校", "桃園市立壽山高級中等學校", "國立新竹女子高級中學",
                "新竹市私立曙光女子高級中學"
            ],
            "中區": [
                "國立溪湖高級中學", "臺中市立大甲高級中等學校", "臺中市立中港高級中學",
                "臺中市立文華高級中學", "臺中市立清水高級中學", "臺中市立第一高級中學",
                "臺中市立第二高級中學", "臺中市立惠文高級中學", "臺中市立新社高級中學",
                "臺中市立臺中女子高級中等學校", "臺中市私立弘文高級中學", "國立竹山高級中學",
                "國立斗六高級中學", "國立嘉義女子高級中學", "國立嘉義高級中學",
                "嘉義縣立竹崎高級中學"
            ],
            "南區": [
                "國立臺南第一高級中學", "國立臺南第二高級中學", "臺南市天主教聖功女子高級中學",
                "臺南市立大灣高級中學", "臺南市立永仁高級中學", "臺南市光華高級中學",
                "臺南市私立南光高級中學", "臺南市德光高級中學", "高雄市立三民高級中學",
                "高雄市立中山高級中學", "高雄市立前鎮高級中學", "高雄市立高雄女子高級中學",
                "高雄市立路竹高級中學", "國立中山大學附屬國光高級中學", "國立屏東女子高級中學",
                "國立潮州高級中學", "國立臺東高級中學"
            ],
            "其他": [
                "新竹縣立竹北實驗高中"
            ]
        }
        
        # 第一步：選擇分區
        selected_district = st.selectbox("1. 選擇分區", list(schools_by_district.keys()))
        
        # 第二步：選擇該分區下的學校
        schools_in_district = schools_by_district[selected_district]
        selected_school = st.selectbox("2. 選擇學校", schools_in_district)
        
        district = selected_district
        school_name = selected_school
        
        # 聯絡人基本資訊
        st.write("### 3. 承辦人資訊")
        registrant_name = st.text_input("承辦人姓名", placeholder="例：王小明")
        registrant_extension = st.text_input("承辦人分機", placeholder="例：123", max_chars=10)

        # 學校電話作為帳號
        school_phone = st.text_input("4. 學校電話（帳號，請含區域號碼）", placeholder="例：073475181", max_chars=10)
        st.caption("⚠️ 請輸入含區域號碼的完整電話，例如高雄市為 07、台北市為 02")

        # 自動生成預設密碼（電話後4碼）
        default_password = school_phone[-4:] if len(school_phone) >= 4 else ""
        
        # 將預設密碼進行雜湊處理
        hashed_password = hash_password(default_password) if default_password else ""

        st.info(f"📞 預設密碼：{default_password if default_password else '請輸入完整電話號碼'}")

        # 聯絡人 Email
        st.write("### 聯絡人資訊")
        registrant_email = st.text_input("承辦人 Email")  # 補回這個輸入框
        academic_director_email = st.text_input("承辦處室主任 Email")
        principal_email = st.text_input("校長 Email")

        if st.button("確認註冊"):
            if not registrant_name:
                st.error("請填寫承辦人姓名")
            elif not school_phone or len(school_phone) < 4:
                st.error("請輸入完整的學校電話號碼（至少4碼）")
            elif not registrant_email or not academic_director_email or not principal_email:
                st.error("請填寫所有聯絡人 Email")
            elif not is_valid_email(registrant_email) or not is_valid_email(academic_director_email) or not is_valid_email(principal_email):
                st.error("請輸入正確的 Email 格式")
            else:
                # 檢查該學校是否已有帳號
                existing_school = supabase.table("schools")\
                    .select("*")\
                    .eq("name", school_name)\
                    .execute()

                if existing_school.data:
                    st.error(f"⚠️ 此學校「{school_name}」已經註冊過帳號了，每校限一個帳號。")
                else:
                    # 檢查電話號碼是否已被使用
                    existing_phone = supabase.table("schools")\
                        .select("*")\
                        .eq("phone", school_phone)\
                        .execute()

                    if existing_phone.data:
                        st.error("⚠️ 此電話號碼已被其他學校使用，請聯繫管理員。")
                    else:
                        new_school = {
                            "name": school_name,
                            "district": district,
                            "phone": school_phone,
                            "password_hash": hashed_password,  # 使用統一的欄位名稱
                            "registrant_name": registrant_name,
                            "registrant_extension": registrant_extension,
                            "registrant_email": registrant_email,  # 統一使用承辦人 Email
                            "academic_director_email": academic_director_email,
                            "principal_email": principal_email,
                            "identity": "學校承辦人",  # 新增身份欄位
                            "is_host": True,
                            "is_partner": True,
                            "is_admin": False
                        }
                        try:
                            data = supabase.table("schools").insert(new_school).execute()
                            st.success(f"🎉 註冊成功！歡迎 {school_name}。")
                            st.info(f"📞 帳號：{school_phone}")
                            st.info(f"🔐 預設密碼：{default_password}")
                            st.balloons()
                        except Exception as e:
                            st.error(f"註冊失敗：{e}")
    
    elif auth_mode == "管理人員登入":
        st.subheader("🔐 管理人員登入")
        admin_username = st.text_input("管理員帳號")
        admin_password = st.text_input("管理員密碼", type="password")
        
        if st.button("管理員登入"):
            try:
                # 從 st.secrets 獲取管理員憑證
                admin_user = st.secrets["ADMIN_USER"]
                admin_password_hash = st.secrets["ADMIN_PASSWORD_HASH"]
                
                if admin_username == admin_user and verify_password(admin_password, admin_password_hash):
                    st.session_state.admin_logged_in = True
                    st.success("🎉 管理員登入成功！")
                    st.rerun()
                else:
                    st.error("❌ 管理員帳號或密碼錯誤！")
            except Exception as e:
                st.error(f"❌ 登入失敗：{e}")
                st.info("⚠️ 請確認 st.secrets 中已設定 ADMIN_USER 和 ADMIN_PASSWORD_HASH")
        
        # 如果管理員已登入，顯示創建管理帳號功能
        if is_admin():
            st.divider()
            st.subheader("👨‍💼 創建管理帳號")
            
            admin_name = st.text_input("管理員姓名", key="admin_name")
            admin_email = st.text_input("管理員 Email", key="admin_email")
            admin_password = st.text_input("管理員密碼", type="password", key="admin_password")
            admin_role = st.selectbox("管理員角色", ["系統管理員", "課程管理員", "審核管理員"], key="admin_role")
            
            if st.button("創建管理帳號"):
                if admin_name and admin_email and admin_password:
                    try:
                        # 雜湊管理員密碼
                        hashed_admin_password = hash_password(admin_password)
                        
                        admin_data = {
                            "name": "管理部門",
                            "registrant_name": admin_name,
                            "registrant_email": admin_email,  # 使用統一的欄位名稱
                            "password_hash": hashed_admin_password,  # 使用統一的欄位名稱
                            "identity": admin_role,
                            "is_host": True,
                            "is_partner": True,
                            "is_admin": True
                        }
                        supabase.table("schools").insert(admin_data).execute()
                        st.success(f"✅ 管理帳號創建成功！{admin_name} ({admin_role})")
                        st.balloons()
                    except Exception as e:
                        st.error(f"創建失敗：{e}")
                else:
                    st.error("請填寫完整的管理員資訊！")
            
            if st.button("🚪 管理員登出"):
                st.session_state.admin_logged_in = False
                st.rerun()

# 修復此處名稱與選單一致
elif choice == "管理中心 (我的課程)":
    require_login()  # 要求登入權限
    st.title("⚙️ 學校管理中心")
    if st.session_state.school_info:
        school = st.session_state.school_info
        st.subheader(f"單位：{school['name']}")
        # 顯示該校已開設的課程
        res = supabase.table("courses").select("*").eq("host_school_id", school['id']).execute()
        if res.data:
            st.write("您已開設的課程：")
            st.table(res.data)
        else:
            st.info("您目前尚未開設任何課程。")

elif choice == "學校基本資料":
    require_login()  # 要求登入權限
    st.header("🏫 學校基本資料管理")
    if st.session_state.school_info:
        school = st.session_state.school_info
        st.subheader(f"學校：{school['name']}")
        
        # 顯示現有資訊
        st.write("### 📋 現有資訊")
        col1, col2 = st.columns(2)
        
        with col1:
            st.info(f"📞 帳號（電話）：{school['phone']}")
            st.info(f"🏫 學校：{school['name']}")
            st.info(f"🗺️ 分區：{school.get('district', '未設定')}")
            
        with col2:
            st.info(f"📧 承辦處室主任 Email：{school.get('academic_director_email', '未設定')}")
            st.info(f"📧 校長 Email：{school.get('principal_email', '未設定')}")
        
        st.divider()
        st.write("### ✏️ 修改資訊")
        
        with st.form("update_school_info"):
            st.write("#### 聯絡人資訊更新")
            new_academic_director_email = st.text_input("承辦處室主任 Email", value=school.get('academic_director_email', ''))
            new_principal_email = st.text_input("校長 Email", value=school.get('principal_email', ''))
            
            st.write("#### 密碼變更")
            current_password = st.text_input("目前密碼", type="password")
            new_password = st.text_input("新密碼", type="password")
            confirm_new_password = st.text_input("確認新密碼", type="password")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.form_submit_button("更新聯絡資訊"):
                    if new_academic_director_email and new_principal_email:
                        if is_valid_email(new_academic_director_email) and is_valid_email(new_principal_email):
                            try:
                                update_data = {
                                    "academic_director_email": new_academic_director_email,
                                    "principal_email": new_principal_email
                                }
                                supabase.table("schools").update(update_data).eq("id", school['id']).execute()
                                st.success("✅ 聯絡資訊更新成功！")
                                # 更新 session_state
                                st.session_state.school_info.update(update_data)
                                st.rerun()
                            except Exception as e:
                                st.error(f"更新失敗：{e}")
                        else:
                            st.error("請輸入正確的 Email 格式")
                    else:
                        st.error("請填寫所有 Email 欄位")
            
            with col2:
                if st.form_submit_button("更新密碼"):
                    if current_password and new_password and confirm_new_password:
                        # 驗證目前密碼
                        if verify_password(current_password, school['password_hash']):  # 使用統一的欄位名稱
                            if new_password == confirm_new_password:
                                if len(new_password) >= 4:
                                    try:
                                        # 將新密碼雜湊後儲存
                                        hashed_new_password = hash_password(new_password)
                                        supabase.table("schools").update({"password_hash": hashed_new_password}).eq("id", school['id']).execute()  # 使用統一的欄位名稱
                                        st.success("✅ 密碼更新成功！")
                                        st.session_state.school_info['password_hash'] = hashed_new_password  # 更新 session_state
                                    except Exception as e:
                                        st.error(f"密碼更新失敗：{e}")
                                else:
                                    st.error("新密碼至少需要4個字元")
                            else:
                                st.error("新密碼與確認密碼不一致")
                        else:
                            st.error("目前密碼錯誤")
                    else:
                        st.error("請填寫所有密碼欄位")

elif choice == "新增/修改課程":
    require_login()
    st.header("✍️ 管理您的課程")
    if st.session_state.school_info:
        school = st.session_state.school_info
        st.write(f"開課單位：**{school['name']}**")

        tab_add, tab_edit = st.tabs(["➕ 新增課程", "✏️ 修改／刪除課程"])

        # ── 新增課程 ──
        with tab_add:
            with st.form("course_form_add"):
                c_title    = st.text_input("課程名稱")
                c_time     = st.text_input("開課時間", placeholder="例：每週三 14:00-16:00")
                c_students = st.number_input("跨校學生人數上限", min_value=0, value=20)
                c_schools  = st.number_input("跨校學校數目上限", min_value=0, value=2)
                c_pdf      = st.text_input("課程規劃表 PDF 連結")
                c_syllabus = st.text_area("課程大綱／內容說明")
                if st.form_submit_button("確認新增課程"):
                    if not c_title:
                        st.error("請填寫課程名稱。")
                    else:
                        try:
                            supabase.table("courses").insert({
                                "host_school_id": school['id'],
                                "title": c_title,
                                "start_time": c_time,
                                "max_students": c_students,
                                "max_schools": c_schools,
                                "plan_pdf_url": c_pdf,
                                "syllabus": c_syllabus,
                            }).execute()
                            st.success("🎉 課程新增成功！已同步顯示於課程大廳。")
                        except Exception as e:
                            st.error(f"新增失敗：{e}")

        # ── 修改／刪除課程 ──
        with tab_edit:
            try:
                my_courses = supabase.table("courses")\
                    .select("id, title, start_time, max_students, max_schools, syllabus, plan_pdf_url")\
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
                                e_students = st.number_input("跨校學生人數上限", min_value=0, value=c.get('max_students', 20))
                                e_schools  = st.number_input("跨校學校數目上限", min_value=0, value=c.get('max_schools', 2))
                                e_pdf      = st.text_input("課程規劃表 PDF 連結", value=c.get('plan_pdf_url', '') or '')
                                e_syllabus = st.text_area("課程大綱／內容說明", value=c.get('syllabus', '') or '')
                                col_save, col_del = st.columns(2)
                                with col_save:
                                    if st.form_submit_button("💾 儲存修改"):
                                        if not e_title:
                                            st.error("課程名稱不得為空。")
                                        else:
                                            try:
                                                supabase.table("courses").update({
                                                    "title": e_title,
                                                    "start_time": e_time,
                                                    "max_students": e_students,
                                                    "max_schools": e_schools,
                                                    "plan_pdf_url": e_pdf,
                                                    "syllabus": e_syllabus,
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
                                st.warning(f"⚠️ 確定刪除「{c['title']}」？此操作將同時刪除所有媒合記錄，且**無法復原**。")
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

elif choice == "配對情形":
    require_login()  # 要求登入權限
    st.header("🤝 課程配對進度追蹤")
    school = st.session_state.school_info
    
    # 分成兩個區塊：我是開課端 / 我是申請端
    tab1, tab2 = st.tabs(["我是開課學校 (收到的申請)", "我是合作學校 (寄出的申請)"])
    
    with tab1:
        st.subheader("📩 收到其他學校的配對請求")
        try:
            # Step 1: 取得我開的所有課程
            my_courses_res = supabase.table("courses")\
                .select("id, title, max_schools")\
                .eq("host_school_id", school['id'])\
                .execute()
            my_course_ids = [c['id'] for c in my_courses_res.data]
            my_course_map = {c['id']: c for c in my_courses_res.data}

            if my_course_ids:
                # Step 2: 查詢這些課程收到的申請
                incoming = supabase.table("matches")\
                    .select("id, status, course_id, partner_school_id")\
                    .in_("course_id", my_course_ids)\
                    .execute()

                # Step 3: 批次取得申請學校名稱
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

                        status_label = {"pending": "⏳ 待審核", "approved": "✅ 媒合成功", "rejected": "❌ 已拒絕"}.get(status, status)

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
                                            # 寄信給申請學校三位收件人
                                            for recipient_email, recipient_name in [
                                                (partner_info.get('registrant_email'), partner_info.get('registrant_name', '承辦人')),
                                                (partner_info.get('academic_director_email'), '承辦處室主任'),
                                                (partner_info.get('principal_email'), '校長'),
                                            ]:
                                                if is_valid_email(recipient_email):
                                                    send_email(
                                                        recipient_email, recipient_name,
                                                        f"媒合成功通知：您的課程申請「{course_title}」已被核准",
                                                        f"親愛的 {recipient_name}：\n\n恭喜！{partner_name} 對課程「{course_title}」的媒合申請已獲得開課學校「{school['name']}」正式核准，雙方合作正式成立。\n\n請與開課學校聯繫後續合作事宜。\n\n跨校課程媒合平台"
                                                    )
                                            st.success(f"已確認與 {partner_name} 正式合作，通知 Email 已發送！")
                                            st.rerun()
                                with col2:
                                    if st.button("❌ 拒絕", key=f"reject_{m['id']}"):
                                        supabase.table("matches").update({"status": "rejected"}).eq("id", m['id']).execute()
                                        # 寄信給申請學校三位收件人
                                        for recipient_email, recipient_name in [
                                            (partner_info.get('registrant_email'), partner_info.get('registrant_name', '承辦人')),
                                            (partner_info.get('academic_director_email'), '承辦處室主任'),
                                            (partner_info.get('principal_email'), '校長'),
                                        ]:
                                            if is_valid_email(recipient_email):
                                                send_email(
                                                    recipient_email, recipient_name,
                                                    f"媒合申請通知：「{course_title}」申請未獲通過",
                                                    f"親愛的 {recipient_name}：\n\n很遺憾，{partner_name} 對課程「{course_title}」的媒合申請未獲開課學校「{school['name']}」核准。\n\n若該課程仍有名額，您的學校可以再次送出媒合申請。\n\n跨校課程媒合平台"
                                                )
                                        st.warning(f"已拒絕 {partner_name} 的申請，通知 Email 已發送。")
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
            # Step 1: 查詢我申請的 matches（含 course_id）
            outgoing = supabase.table("matches")\
                .select("id, status, course_id")\
                .eq("partner_school_id", school['id'])\
                .execute()

            if outgoing.data:
                # Step 2: 批次取得課程與開課學校名稱
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
                    st.success(f"🚀 您向 **{host_name}** 申請了「{course.get('title', '未知課程')}」（狀態：{m['status']}）")
            else:
                st.write("您尚未申請任何課程。")
        except Exception as e:
            st.error(f"讀取失敗（Tab2）：{e}")

# 管理員專用頁面
elif choice == "📊 系統管理":
    require_admin()
    st.title("📊 系統管理")

    ALL_SCHOOLS_BY_DISTRICT = {
        "北一區": ["國立羅東高級中學","國立蘭陽女子高級中學","國立花蓮高級中學","慈濟大學附屬高級中學","國立基隆高級中學","新北市立中和高級中學","新北市立北大高級中學","新北市立石碇高級中學","新北市立板橋高中","新北市立錦和高級中學","新北市私立徐匯高級中學","新北市金陵女子高級中學","新北市南山高級中學"],
        "北二區": ["國立臺灣師範大學附屬高級中學","臺北市立中山女子高級中學","臺北市立中正高級中學","臺北市立中崙高級中學","臺北市立內湖高級中學","臺北市立永春高級中學","臺北市立百齡高級中學","臺北市立育成高級中學","臺北市立松山高級中學","臺北市立建國高級中學","臺北市立第一女子高級中學","臺北市立景美女子高級中學","臺北市立陽明高級中學","臺北市立萬芳高級中學","臺北市立麗山高級中學","臺北市數位實驗高級中等學校"],
        "北三區": ["桃園市立內壢高級中等學校","桃園市立桃園高級中等學校","桃園市立陽明高級中等學校","桃園市立楊梅高級中等學校","桃園市立壽山高級中等學校","國立新竹女子高級中學","新竹市私立曙光女子高級中學"],
        "中區": ["國立溪湖高級中學","臺中市立大甲高級中等學校","臺中市立中港高級中學","臺中市立文華高級中學","臺中市立清水高級中學","臺中市立第一高級中學","臺中市立第二高級中學","臺中市立惠文高級中學","臺中市立新社高級中學","臺中市立臺中女子高級中等學校","臺中市私立弘文高級中學","國立竹山高級中學","國立斗六高級中學","國立嘉義女子高級中學","國立嘉義高級中學","嘉義縣立竹崎高級中學"],
        "南區": ["國立臺南第一高級中學","國立臺南第二高級中學","臺南市天主教聖功女子高級中學","臺南市立大灣高級中學","臺南市立永仁高級中學","臺南市光華高級中學","臺南市私立南光高級中學","臺南市德光高級中學","高雄市立三民高級中學","高雄市立中山高級中學","高雄市立前鎮高級中學","高雄市立高雄女子高級中學","高雄市立路竹高級中學","國立中山大學附屬國光高級中學","國立屏東女子高級中學","國立潮州高級中學","國立臺東高級中學"],
        "其他": ["新竹縣立竹北實驗高中"],
    }

    tab1, tab2 = st.tabs(["🏫 學校帳號基本資訊", "🤝 配對狀況"])

    # ── Tab 1：學校帳號基本資訊 ──
    with tab1:
        try:
            all_schools_res = supabase.table("schools").select("*").execute()
            registered = [s for s in all_schools_res.data if not s.get("is_admin", False)]
            registered_names = {s["name"] for s in registered}

            district_options = ["全部"] + list(ALL_SCHOOLS_BY_DISTRICT.keys())
            sel_district = st.selectbox("🗺️ 篩選分區", district_options, key="admin_district_filter")

            st.subheader("✅ 已註冊學校")
            filtered_registered = [
                s for s in registered
                if sel_district == "全部" or s.get("district") == sel_district
            ]
            if filtered_registered:
                for account in filtered_registered:
                    with st.expander(f"🏫 {account['name']}　（{account.get('district','未分區')}）"):
                        col1, col2 = st.columns(2)
                        with col1:
                            st.write("**📋 基本資料**")
                            st.write(f"帳號（電話）：{account.get('phone','—')}")
                            st.write(f"分機：{account.get('registrant_extension','—')}")
                            st.write(f"承辦人：{account.get('registrant_name','—')}")
                            st.write(f"承辦人 Email：{account.get('registrant_email','—')}")
                        with col2:
                            st.write("**📧 主管信箱**")
                            st.write(f"承辦處室主任：{account.get('academic_director_email','—')}")
                            st.write(f"校長：{account.get('principal_email','—')}")
                            st.write("**🎓 權限**")
                            st.write(f"開課：{'✅' if account.get('is_host') else '❌'}　合作：{'✅' if account.get('is_partner') else '❌'}")
                        st.divider()
                        delete_key = f"confirm_delete_school_{account['id']}"
                        if delete_key not in st.session_state:
                            st.session_state[delete_key] = False
                        if not st.session_state[delete_key]:
                            if st.button(f"🗑️ 刪除「{account['name']}」", key=f"del_school_{account['id']}", type="secondary"):
                                st.session_state[delete_key] = True
                                st.rerun()
                        else:
                            st.warning(f"⚠️ 確定要刪除「{account['name']}」？將同時刪除所有課程與媒合記錄，且**無法復原**。")
                            col_yes, col_no = st.columns(2)
                            with col_yes:
                                if st.button("✅ 確認刪除", key=f"yes_school_{account['id']}", type="primary"):
                                    try:
                                        delete_school_cascade(account["id"])
                                        st.success(f"已刪除「{account['name']}」。")
                                        st.session_state[delete_key] = False
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"刪除失敗：{e}")
                            with col_no:
                                if st.button("❌ 取消", key=f"no_school_{account['id']}"):
                                    st.session_state[delete_key] = False
                                    st.rerun()
            else:
                st.info("此分區尚無已註冊學校。")

            st.subheader("⬜ 尚未註冊學校")
            unregistered_found = False
            for district, names in ALL_SCHOOLS_BY_DISTRICT.items():
                if sel_district != "全部" and district != sel_district:
                    continue
                missing = [n for n in names if n not in registered_names]
                if missing:
                    unregistered_found = True
                    st.write(f"**{district}**：" + "、".join(missing))
            if not unregistered_found:
                st.info("所有學校皆已註冊帳號。")

        except Exception as e:
            st.error(f"讀取失敗：{e}")

    # ── Tab 2：配對狀況 ──
    with tab2:
        try:
            courses_res = supabase.table("courses")                .select("id, title, max_schools, host_school_id, schools(name)")                .execute()

            matches_res = supabase.table("matches")                .select("id, course_id, partner_school_id, status")                .execute()
            all_matches = matches_res.data

            partner_ids = list({m["partner_school_id"] for m in all_matches})
            partner_map = {}
            if partner_ids:
                p_res = supabase.table("schools").select("id, name").in_("id", partner_ids).execute()
                partner_map = {s["id"]: s["name"] for s in p_res.data}

            st.subheader("📤 開課學校配對狀況")
            if courses_res.data:
                host_courses: dict = {}
                for c in courses_res.data:
                    sname = c["schools"]["name"]
                    host_courses.setdefault(sname, []).append(c)

                for school_name, courses_list in host_courses.items():
                    st.write(f"**🏫 {school_name}**")
                    for c in courses_list:
                        c_matches = [m for m in all_matches if m["course_id"] == c["id"]]
                        approved = sum(1 for m in c_matches if m["status"] == "approved")
                        pending  = sum(1 for m in c_matches if m["status"] == "pending")
                        max_s    = c.get("max_schools", 2)
                        if approved >= max_s:
                            badge = f"🔴 {approved}/{max_s} 已配對額滿"
                        elif approved > 0:
                            badge = f"🟡 {approved}/{max_s} 仍有配對名額"
                        else:
                            badge = f"⚪ 0/{max_s} 尚無配對學校"
                        st.write(f"　　📖 {c['title']}　{badge}　⏳待審核 {pending} 所")
                    st.divider()
            else:
                st.info("目前尚無任何課程。")

            st.subheader("📥 申請學校配對狀況")
            if all_matches:
                from collections import defaultdict
                stats: dict = defaultdict(lambda: {"total": 0, "approved": 0})
                for m in all_matches:
                    stats[m["partner_school_id"]]["total"] += 1
                    if m["status"] == "approved":
                        stats[m["partner_school_id"]]["approved"] += 1
                for pid, s in stats.items():
                    sname = partner_map.get(pid, f"學校 {pid}")
                    st.write(f"**{sname}**　共送出 {s['total']} 次申請，已成功配對 {s['approved']} 次")
            else:
                st.info("目前尚無任何媒合申請記錄。")

        except Exception as e:
            st.error(f"讀取配對資料失敗：{e}")
