import streamlit as st
from supabase import create_client
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

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
def send_email(to_email, to_name, course_title, applicant_school):
    """發送媒合申請通知信給開課老師"""
    try:
        # 修正：從 st.secrets 取得資訊並統一變數名稱
        gmail_user = st.secrets["GMAIL_USER"]
        gmail_password = st.secrets["GMAIL_PASSWORD"]
        
        # 建立郵件內容
        msg = MIMEMultipart()
        msg['From'] = gmail_user
        msg['To'] = to_email
        msg['Subject'] = f"【跨校課程媒合平台】有學校申請媒合您的課程：{course_title}"
        
        body = f"""
親愛的 {to_name} 老師：

您好！

有學校透過「跨校課程媒合平台」申請媒合您的課程：

📚 課程名稱：{course_title}
🏫 申請學校：{applicant_school}

請您登入平台查看詳細資訊並處理媒合申請。

平台網址：http://localhost:8501

祝 順心

跨校課程媒合平台 自動通知系統
        """
        
        msg.attach(MIMEText(body, 'plain', 'utf-8'))
        
        # 透過 Gmail SMTP 發送 (修正變數名稱)
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls() # 啟動安全傳輸
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
if not st.session_state.logged_in:
    menu = ["課程大廳", "學校帳號登入"]
else:
    # 加入「配對情形」
    menu = ["課程大廳", "管理中心 (我的課程)", "配對情形", "新增/修改課程", "登出"]

choice = st.sidebar.selectbox("選單", menu)

# --- 登出邏輯 ---
if choice == "登出":
    st.session_state.logged_in = False
    st.session_state.school_info = None
    st.rerun()

# --- 頁面內容 ---
if choice == "課程大廳":
    st.header("📚 現有跨校課程一覽")
    try:
        # 讀取課程與關聯的學校資訊
        response = supabase.table("courses").select("*, schools(name, email, registrant_name)").execute()
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
                        st.write(f"**🏫 合作學校上限：** {c.get('max_schools', 'N/A')} 所")
                        if c.get('plan_pdf_url'):
                            st.link_button("📥 查看課程規劃表 (PDF)", c['plan_pdf_url'])
                    st.write(f"**📝 課程大綱：**\n{c['syllabus']}")
                    # 媒合申請邏輯
                    if f"show_matching_{c['id']}" not in st.session_state:
                        st.session_state[f"show_matching_{c['id']}"] = False
                    if f"show_success_{c['id']}" not in st.session_state:
                        st.session_state[f"show_success_{c['id']}"] = False
                    
                    if st.button(f"申請媒合", key=f"btn_{c['id']}"):
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
                            if st.button("確定發送媒合Email", key=f"send_{c['id']}", disabled=not all_confirmed):
                                # 取得資訊
                                host_email = c['schools']['email']
                                host_name = c['schools']['registrant_name']
                                applicant_school = st.session_state.school_info['name']
                                
                                with st.spinner('🚀 媒合信件正在穿越光纖，請稍候...'):
                                    # 執行發信
                                    success, msg = send_email(host_email, host_name, c['title'], applicant_school)
                                    
                                    if success:
                                        # 新增：同步將配對紀錄寫入 Supabase 的 matches 資料表
                                        try:
                                            match_data = {
                                                "course_id": c['id'],
                                                "partner_school_id": st.session_state.school_info['id'],
                                                "status": "pending"
                                            }
                                            supabase.table("matches").insert(match_data).execute()
                                            st.success("✅ 媒合申請已送出並記錄在案！")
                                        except Exception as db_error:
                                            st.warning(f"信件發送成功，但資料庫記錄失敗：{db_error}")
                                        
                                        # 顯示成功對話框
                                        st.session_state[f"show_success_{c['id']}"] = True
                                        st.session_state[f"show_matching_{c['id']}"] = False
                                        st.rerun()
                                    else:
                                        st.error(f"糟糕，通訊衛星出了一點狀況：{msg}")
                    
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
        email = st.text_input("帳號 (Email)")
        pwd = st.text_input("密碼", type="password")
        if st.button("確認登入"):
            res = supabase.table("schools").select("*").eq("email", email).eq("password", pwd).execute()
            if res.data:
                st.session_state.logged_in = True
                st.session_state.school_info = res.data[0]
                st.success(f"登入成功！歡迎 {res.data[0]['name']}。")
                st.rerun()
            else:
                st.error("帳號或密碼錯誤，請重新輸入。")
    
    elif auth_mode == "註冊學校帳號":
        # --- 註冊功能 (已恢復並完整保留) ---
        st.subheader("📝 建立新帳號")
        school_list = ["高雄市三民高中", "高雄市中山高中", "高雄女中"]
        selected_school = st.selectbox("1. 選擇學校", school_list)
        user_name = st.text_input("2. 註冊者姓名")
        user_email = st.text_input("3. 註冊者 Email (即登入帳號)")
        user_identity = st.selectbox("4. 註冊者身份", ["校長", "主任", "行政人員"])
        
        col1, col2 = st.columns(2)
        with col1:
            pwd = st.text_input("5. 設定密碼", type="password")
        with col2:
            confirm_pwd = st.text_input("請再次確認密碼", type="password")
            
        st.write("6. 您的學校參與類型 (可重複勾選)")
        is_host = st.checkbox("開課學校 (提供遠距課程)")
        is_partner = st.checkbox("合作學校 (申請加入他人課程)")

        if st.button("確認註冊"):
            if pwd != confirm_pwd:
                st.error("兩次輸入的密碼不一致，請重新檢查。")
            elif not user_email or not user_name:
                st.error("請完整填寫姓名與 Email。")
            else:
                # 檢查該學校是否已有此身分的帳號
                existing_identity = supabase.table("schools")\
                    .select("*")\
                    .eq("name", selected_school)\
                    .eq("identity", user_identity)\
                    .execute()
                
                if existing_identity.data:
                    st.error(f"⚠️ 此學校的「{user_identity}」帳號已存在，每個身分限註冊一名。")
                else:
                    # 檢查該學校總帳號數量
                    existing_accounts = supabase.table("schools")\
                        .select("*")\
                        .eq("name", selected_school)\
                        .execute()
                    
                    if len(existing_accounts.data) >= 3:
                        st.error("⚠️ 此學校已達到三名帳號上限（校長、主任、行政人員各一名）。")
                    else:
                        new_user = {
                            "name": selected_school,
                            "registrant_name": user_name,
                            "email": user_email,
                            "password": pwd,
                            "identity": user_identity,
                            "is_host": is_host,
                            "is_partner": is_partner
                        }
                        try:
                            data = supabase.table("schools").insert(new_user).execute()
                            st.success(f"🎉 註冊成功！歡迎 {selected_school} 的 {user_name} {user_identity}。")
                            st.balloons()
                        except Exception as e:
                            st.error(f"註冊失敗：{e}")
    
    elif auth_mode == "管理人員登入":
        st.subheader("🔐 管理人員登入")
        admin_username = st.text_input("管理員帳號")
        admin_password = st.text_input("管理員密碼", type="password")
        
        if st.button("管理員登入"):
            if admin_username == "match" and admin_password == "match":
                st.session_state.admin_logged_in = True
                st.success("🎉 管理員登入成功！")
                st.rerun()
            else:
                st.error("❌ 管理員帳號或密碼錯誤！")
        
        # 如果管理員已登入，顯示創建管理帳號功能
        if st.session_state.get("admin_logged_in"):
            st.divider()
            st.subheader("👨‍💼 創建管理帳號")
            
            admin_name = st.text_input("管理員姓名")
            admin_email = st.text_input("管理員 Email")
            admin_password = st.text_input("管理員密碼", type="password")
            admin_role = st.selectbox("管理員角色", ["系統管理員", "課程管理員", "審核管理員"])
            
            if st.button("創建管理帳號"):
                if admin_name and admin_email and admin_password:
                    try:
                        admin_data = {
                            "name": "管理部門",
                            "registrant_name": admin_name,
                            "email": admin_email,
                            "password": admin_password,
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

elif choice == "新增/修改課程":
    st.header("✍️ 上傳/管理您的課程")
    if st.session_state.school_info:
        school = st.session_state.school_info
        st.write(f"開課單位：**{school['name']}**")

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