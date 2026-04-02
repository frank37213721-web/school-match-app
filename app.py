import streamlit as st
from supabase import create_client
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from passlib.context import CryptContext
from datetime import datetime

# 密碼雜湊設定
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(raw_password: str) -> str:
    return pwd_context.hash(raw_password)

def verify_password(raw_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(raw_password, hashed_password)

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
        # 讀取課程與關聯的學校資訊
        response = supabase.table("courses").select("*, schools(name, registrant_email, registrant_name)").execute()
        courses = response.data
        if not courses:
            st.info("目前尚無開課資訊。")
        else:
            for c in courses:
                # 謝老師，這裡使用 expander 讓資訊簡化一目瞭然
                with st.expander(f"📖 {c['title']} - {c['schools']['name']}"):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"**🗓️ 開課時間：** {c.get('start_time', '未設定')}")
                        st.write(f"**👥 跨校學生上限：** {c.get('max_students', 'N/A')} 人")
                    with col2:
                        # 顯示目前申請狀況
                        current_matches = supabase.table("matches")\
                            .select("*")\
                            .eq("course_id", c['id'])\
                            .in_("status", ["pending", "approved"])\
                            .execute()
                        
                        approved_count = len([m for m in current_matches.data if m['status'] == 'approved'])
                        pending_count = len([m for m in current_matches.data if m['status'] == 'pending'])
                        total_active = approved_count + pending_count
                        max_schools = c.get('max_schools', 2)
                        
                        st.write(f"**🏫 合作學校上限：** {max_schools} 所")
                        st.write(f"**📊 目前申請：** {total_active}/{max_schools} 所")
                        st.write(f"  - ✅ 已通過：{approved_count} 所")
                        st.write(f"  - ⏳ 待審核：{pending_count} 所")
                        
                        if c.get('plan_pdf_url'):
                            st.link_button("📥 查看課程規劃表 (PDF)", c['plan_pdf_url'])
                    st.write(f"**📝 課程大綱：**\n{c['syllabus']}")
                    # 媒合申請邏輯
                    if f"show_matching_{c['id']}" not in st.session_state:
                        st.session_state[f"show_matching_{c['id']}"] = False
                    if f"show_success_{c['id']}" not in st.session_state:
                        st.session_state[f"show_success_{c['id']}"] = False
                    
                    # 檢查是否可以申請
                    can_apply = True
                    button_disabled = False
                    button_text = "申請媒合"
                    
                    if total_active >= max_schools:
                        can_apply = False
                        button_disabled = True
                        button_text = "🚫 名額已滿"
                    
                    if st.button(button_text, key=f"btn_{c['id']}", disabled=button_disabled):
                        if not st.session_state.logged_in:
                            st.warning("⚠️ 老師請先登入後再進行媒合申請喔！")
                        else:
                            st.session_state[f"show_matching_{c['id']}"] = True
                            st.rerun()
                    
                    # 顯示媒合確認介面
                    if st.session_state[f"show_matching_{c['id']}"]:
                        st.subheader(f"📋 媒合確認事項 - {c['title']}")
                        st.write(f"**開課學校：** {c['schools']['name']}")
                        
                        # 5點確認事項
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
                                        # 1. 先檢查是否已經申請過（只檢查未完成的申請）
                                        existing_match = supabase.table("matches")\
                                            .select("*")\
                                            .eq("course_id", c['id'])\
                                            .eq("partner_school_id", st.session_state.school_info['id'])\
                                            .in_("status", ["pending", "approved"])\
                                            .execute()
                                        
                                        if existing_match.data:
                                            st.error("⚠️ 您已經申請過此課程的媒合，且申請正在處理中或已通過！")
                                        else:
                                            # 2. 檢查課程容量是否已滿
                                            current_matches = supabase.table("matches")\
                                                .select("*")\
                                                .eq("course_id", c['id'])\
                                                .in_("status", ["pending", "approved"])\
                                                .execute()
                                            
                                            approved_count = len([m for m in current_matches.data if m['status'] == 'approved'])
                                            pending_count = len([m for m in current_matches.data if m['status'] == 'pending'])
                                            total_active = approved_count + pending_count
                                            
                                            max_schools = c.get('max_schools', 2)  # 預設值 2
                                            max_students = c.get('max_students', 20)  # 預設值 20
                                            
                                            # 檢查學校數量限制
                                            if total_active >= max_schools:
                                                st.error(f"⚠️ 此課程合作學校已滿！最多接受 {max_schools} 所學校，目前已有 {approved_count} 所通過，{pending_count} 所待審核。")
                                            else:
                                                # 3. 先寫入 matches 資料表 (確保數據一致性)
                                                match_data = {
                                                    "course_id": c['id'],
                                                    "partner_school_id": st.session_state.school_info['id'],
                                                    "status": "pending",
                                                    "email_status": "pending",
                                                    "requested_students": None  # 暫時為空，未來可擴展
                                                }
                                                match_result = supabase.table("matches").insert(match_data).execute()
                                                match_id = match_result.data[0]['id']
                                                
                                                # 4. 準備 Email 發送給所有相關人員
                                                applicant_school = st.session_state.school_info
                                                host_school = c['schools']
                                                
                                                # 收集所有需要發送 Email 的收件人
                                                email_recipients = []
                                            
                                            # 開課學校的收件人
                                                email_recipients.extend([
                                                    {"email": host_school['registrant_email'], "name": host_school['registrant_name'], "type": "host"},
                                                    {"email": host_school.get('academic_director_email'), "name": "承辦處室主任", "type": "host"},
                                                    {"email": host_school.get('principal_email'), "name": "校長", "type": "host"}
                                                ])
                                                
                                                # 申請學校的收件人
                                                email_recipients.extend([
                                                    {"email": applicant_school['registrant_email'], "name": applicant_school['registrant_name'], "type": "applicant"},
                                                    {"email": applicant_school.get('academic_director_email'), "name": "承辦處室主任", "type": "applicant"},
                                                    {"email": applicant_school.get('principal_email'), "name": "校長", "type": "applicant"}
                                                ])
                                                
                                                # 5. 發送 Email 給所有收件人
                                                email_success = True
                                                failed_emails = []
                                                
                                                for recipient in email_recipients:
                                                    if recipient['email'] and '@' in recipient['email']:
                                                        try:
                                                            if recipient['type'] == 'host':
                                                                # 給開課學校：收到媒合申請通知
                                                                subject = f"媒合申請通知：{applicant_school['name']} 申請您的課程「{c['title']}」"
                                                                content = f"""
親愛的 {recipient['name']}：

您開設的課程「{c['title']}」收到來自 {applicant_school['name']} 的媒合申請。

申請學校資訊：
- 學校：{applicant_school['name']}
- 承辦人：{applicant_school['registrant_name']}
- 聯絡電話：{applicant_school['phone']}
- 分機：{applicant_school.get('registrant_extension', '未提供')}

請登入系統查看詳細資訊並處理此申請。

跨校課程媒合平台
                                                                """
                                                            else:
                                                                # 給申請學校：已遞交媒合申請確認
                                                                subject = f"媒合申請確認：已申請「{c['title']}」課程"
                                                                content = f"""
親愛的 {recipient['name']}：

您的學校已成功遞交課程「{c['title']}」的媒合申請。

申請資訊：
- 申請課程：{c['title']}
- 開課學校：{host_school['name']}
- 申請時間：{match_result.data[0]['created_at'][:16]}

我們將通知開課學校處理您的申請，請耐心等候回覆。

跨校課程媒合平台
                                                                """
                                                            
                                                            success, msg = send_email(recipient['email'], recipient['name'], subject, content)
                                                            if not success:
                                                                email_success = False
                                                                failed_emails.append(f"{recipient['name']} ({recipient['email']})")
                                                                
                                                        except Exception as e:
                                                            email_success = False
                                                            failed_emails.append(f"{recipient['name']} ({recipient['email']})")
                                                
                                                # 6. 更新 Email 狀態
                                                if email_success:
                                                    supabase.table("matches").update({"email_status": "sent"}).eq("id", match_id).execute()
                                                    st.success("✅ 媒合申請已成功提交！所有相關人員都會收到通知 Email。")
                                                else:
                                                    supabase.table("matches").update({"email_status": "failed"}).eq("id", match_id).execute()
                                                    st.warning(f"⚠️ 媒合申請已提交，但部分 Email 發送失敗：{', '.join(failed_emails)}")
                                                
                                                # 7. 清除表單狀態
                                                st.session_state[f"show_matching_{c['id']}"] = False
                                                st.rerun()
                                            
                                    except Exception as e:
                                        st.error(f"❌ 申請失敗：{e}")
                                        st.info("請稍後再試或聯繫管理員")
                    
                    # 顯示成功對話框
                    if st.session_state[f"show_success_{c['id']}"]:
                        # 使用 Streamlit 原生元件建立對話框效果
                        st.success("✅ **媒合信件已成功發射！**")
                        st.info("📧 信件已搭乘「超導體特快車」飛向開課老師的信箱。")
                        st.info("🔬 物理學告訴我們：能量守恆，您的熱誠也一定會傳達到對方那裡！")
                        st.info("⏰ 請靜待佳音，說不定緣分就在下一秒。")
                        
                        # 慶祝動畫
                        st.balloons()
                        
                        # 確認按鈕
                        col1, col2, col3 = st.columns([1, 2, 1])
                        with col2:
                            if st.button("🎯 確認，回到課程大廳", key=f"confirm_success_{c['id']}", use_container_width=True):
                                st.session_state[f"show_success_{c['id']}"] = False
                                st.rerun()
    except Exception as e:
        st.error(f"讀取資料失敗：{e}")

elif choice == "學校帳號登入":
    auth_mode = st.radio("請選擇操作", ["學校帳號登入", "註冊學校帳號", "管理人員登入"], horizontal=True)

    if auth_mode == "學校帳號登入":
        st.subheader("🔑 學校帳號登入")
        email = st.text_input("帳號 (電話號碼)")
        pwd = st.text_input("密碼", type="password")
        if st.button("確認登入"):
            # 先查詢 phone 對應的用戶
            res = supabase.table("schools").select("*").eq("phone", email).execute()
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
                                if school.get('academic_director_email') and '@' in school.get('academic_director_email', ''):
                                    additional_recipients.append({
                                        'email': school['academic_director_email'],
                                        'name': '承辦處室主任'
                                    })
                                if school.get('principal_email') and '@' in school.get('principal_email', ''):
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
                "新竹市數位實驗高中"
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
        school_phone = st.text_input("4. 學校電話 (帳號)", placeholder="例：073475181", max_chars=10)

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
            elif "@" not in registrant_email or "@" not in academic_director_email or "@" not in principal_email:
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
                        if "@" in new_academic_director_email and "@" in new_principal_email:
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
    require_login()  # 要求登入權限
    st.header("✍️ 上傳/管理您的課程")
    if st.session_state.school_info:
        school = st.session_state.school_info
        st.write(f"開課單位：**{school['name']}")

        with st.form("course_form"):
            c_title = st.text_input("課程名稱")
            c_time = st.text_input("開課時間 (例如：每週三 14:00-16:00)")
            c_students = st.number_input("跨校學生人數上限", min_value=0, value=20)
            c_schools = st.number_input("跨校學校數目上限", min_value=0, value=2)
            c_pdf = st.text_input("課程規劃表 PDF 連結 (Google Drive 分享連結等)")
            c_syllabus = st.text_area("課程大綱/內容說明")
            
            submitted = st.form_submit_button("確認上傳課程")
            if submitted:
                new_course = {
                    "host_school_id": school['id'],
                    "title": c_title,
                    "start_time": c_time,
                    "max_students": c_students,
                    "max_schools": c_schools,
                    "plan_pdf_url": c_pdf,
                    "syllabus": c_syllabus
                }
                try:
                    supabase.table("courses").insert(new_course).execute()
                    st.success("🎉 課程上傳成功！已同步顯示於首頁課程大廳。")
                except Exception as e:
                    st.error(f"上傳失敗：{e}")

elif choice == "配對情形":
    require_login()  # 要求登入權限
    st.header("🤝 課程配對進度追蹤")
    school = st.session_state.school_info
    
    # 分成兩個區塊：我是開課端 / 我是申請端
    tab1, tab2 = st.tabs(["我是開課學校 (收到的申請)", "我是合作學校 (寄出的申請)"])
    
    with tab1:
        st.subheader("📩 收到其他學校的配對請求")
        # 查詢我開的課有哪些人申請 (關聯查詢)
        # 邏輯：找 course_id 屬於我的 matches，並顯示申請學校名稱
        incoming = supabase.table("matches")\
            .select("created_at, status, courses(title, host_school_id), schools(name)")\
            .execute()
        
        # 這裡需要稍微過濾一下，只顯示給「我」的
        my_incoming = [m for m in incoming.data if m['courses']['host_school_id'] == school['id']]
        
        if my_incoming:
            for m in my_incoming:
                st.info(f"📍 **{m['schools']['name']}** 在 {m['created_at'][:16]} 申請了您的「{m['courses']['title']}」")
        else:
            st.write("目前尚無收到申請。")

    with tab2:
        st.subheader("📤 已寄出的配對請求")
        # 查詢我申請了哪些課
        outgoing = supabase.table("matches")\
            .select("created_at, status, courses(title, schools(name))")\
            .eq("partner_school_id", school['id'])\
            .execute()
            
        if outgoing.data:
            for m in outgoing.data:
                st.success(f"🚀 您於 {m['created_at'][:16]} 向 **{m['courses']['schools']['name']}** 申請了「{m['courses']['title']}」")
        else:
            st.write("您尚未申請任何課程。")

# 管理員專用頁面
elif choice == "📊 系統管理":
    require_admin()  # 要求管理員權限
    st.title("📊 系統管理")
    st.success("🎉 歡迎管理員！")
    
    # 建立兩個頁籤
    tab1, tab2 = st.tabs(["🏫 學校資訊", "📚 課程資訊"])
    
    with tab1:
        st.subheader("🏫 已註冊學校資訊")
        
        # 獲取所有非管理員帳號
        try:
            schools = supabase.table("schools").select("*").execute()
            non_admin_accounts = [s for s in schools.data if not s.get('is_admin', False)]
            
            if non_admin_accounts:
                # 按分區分組顯示
                districts = {}
                for account in non_admin_accounts:
                    district = account.get('district', '未分區')
                    if district not in districts:
                        districts[district] = []
                    districts[district].append(account)
                
                for district, accounts in districts.items():
                    st.write(f"### 🗺️ {district}")
                    
                    for account in accounts:
                        with st.expander(f"🏫 {account['name']} - {account['registrant_name']}"):
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                st.write("**🔐 登入資訊**")
                                st.code(f"帳號: {account['phone']}")
                                st.code("密碼: [已雜湊加密]")  # 不顯示實際雜湊值，更安全
                                st.write("**📋 基本資料**")
                                st.write(f"📞 電話: {account['phone']}")
                                st.write(f"� 分機: {account.get('registrant_extension', '未設定')}")
                                st.write(f"�🗺️ 分區: {account.get('district', '未設定')}")
                                st.write(f"👤 承辦人: {account.get('registrant_name', '未設定')}")
                            
                            with col2:
                                st.write("**📧 聯絡資訊**")
                                st.write(f"承辦處室主任: {account.get('academic_director_email', '未設定')}")
                                st.write(f"校長: {account.get('principal_email', '未設定')}")
                                st.write("**🎓 權限設定**")
                                st.write(f"開課: {'✅' if account.get('is_host') else '❌'}")
                                st.write(f"合作: {'✅' if account.get('is_partner') else '❌'}")
                            
                            st.divider()
            else:
                st.info("目前尚無學校註冊帳號。")
                
        except Exception as e:
            st.error(f"讀取學校資料失敗：{e}")
    
    with tab2:
        st.subheader("� 各校課程資訊")
        
        try:
            # 獲取所有課程與學校資訊
            courses = supabase.table("courses")\
                .select("*, schools(name, district)")\
                .execute()
            
            if courses.data:
                # 按學校分組顯示課程
                schools_courses = {}
                for course in courses.data:
                    school_name = course['schools']['name']
                    if school_name not in schools_courses:
                        schools_courses[school_name] = {
                            'district': course['schools'].get('district', '未分區'),
                            'courses': []
                        }
                    schools_courses[school_name]['courses'].append(course)
                
                for school_name, school_data in schools_courses.items():
                    st.write(f"### 🏫 {school_name} ({school_data['district']})")
                    
                    for course in school_data['courses']:
                        with st.expander(f"📖 {course['title']}"):
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                st.write("**⏰ 開課資訊**")
                                st.write(f"🕐 時間: {course.get('start_time', '未設定')}")
                                st.write(f"� 學生上限: {course.get('max_students', 'N/A')} 人")
                                st.write(f"🏫 合作學校上限: {course.get('max_schools', 'N/A')} 所")
                            
                            with col2:
                                st.write("**📝 課程內容**")
                                if course.get('plan_pdf_url'):
                                    st.link_button("📥 課程規劃表", course['plan_pdf_url'])
                                st.write("**📋 課程大綱:**")
                                st.write(course.get('syllabus', '未設定'))
                            
                            st.divider()
            else:
                st.info("目前尚無任何課程資訊。")
                
        except Exception as e:
            st.error(f"讀取課程資料失敗：{e}")