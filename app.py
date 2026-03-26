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
if st.session_state.get("admin_logged_in"):
    # 管理員專用選單
    menu = ["課程大廳", "📊 系統管理面板", "🏫 已註冊學校清單", "📈 配對申請統計", "👨‍💼 創建管理帳號", "登出"]
elif not st.session_state.logged_in:
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
        email = st.text_input("帳號 (電話號碼)")
        pwd = st.text_input("密碼", type="password")
        if st.button("確認登入"):
            res = supabase.table("schools").select("*").eq("phone", email).eq("password", pwd).execute()
            if res.data:
                st.session_state.logged_in = True
                st.session_state.school_info = res.data[0]
                st.success(f"登入成功！歡迎 {res.data[0]['name']}。")
                st.rerun()
            else:
                st.error("帳號或密碼錯誤，請重新輸入。")
    
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
            ]
        }
        
        # 第一步：選擇分區
        selected_district = st.selectbox("1. 選擇分區", list(schools_by_district.keys()))
        
        # 第二步：選擇該分區下的學校
        schools_in_district = schools_by_district[selected_district]
        selected_school = st.selectbox("2. 選擇學校", schools_in_district)
        
        district = selected_district
        school_name = selected_school
        
        # 學校電話作為帳號
        school_phone = st.text_input("3. 學校電話 (帳號)", placeholder="例：073475181", max_chars=10)
        
        # 自動生成預設密碼（電話後4碼）
        default_password = school_phone[-4:] if len(school_phone) >= 4 else ""
        
        st.info(f"📞 預設密碼：{default_password if default_password else '請輸入完整電話號碼'}")
        
        # 聯絡人資訊
        st.write("### 4. 聯絡人資訊")
        handler_email = st.text_input("承辦人 Email")
        academic_director_email = st.text_input("教務主任 Email")
        principal_email = st.text_input("校長 Email")

        if st.button("確認註冊"):
            if not school_phone or len(school_phone) < 4:
                st.error("請輸入完整的學校電話號碼（至少4碼）")
            elif not handler_email or not academic_director_email or not principal_email:
                st.error("請填寫所有聯絡人 Email")
            elif "@" not in handler_email or "@" not in academic_director_email or "@" not in principal_email:
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
                            "password": default_password,
                            "handler_email": handler_email,  # 這裡的 Key 必須跟資料庫欄位名稱一模一樣
                            "academic_director_email": academic_director_email,
                            "principal_email": principal_email,
                            "is_host": True,
                            "is_partner": True
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
            
            admin_name = st.text_input("管理員姓名", key="admin_name")
            admin_email = st.text_input("管理員 Email", key="admin_email")
            admin_password = st.text_input("管理員密碼", type="password", key="admin_password")
            admin_role = st.selectbox("管理員角色", ["系統管理員", "課程管理員", "審核管理員"], key="admin_role")
            
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

elif choice == "學校基本資料":
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
            st.info(f"📧 承辦人 Email：{school.get('registrant_email', '未設定')}")
            st.info(f"📧 教務主任 Email：{school.get('academic_director_email', '未設定')}")
            st.info(f"📧 校長 Email：{school.get('principal_email', '未設定')}")
        
        st.divider()
        st.write("### ✏️ 修改資訊")
        
        with st.form("update_school_info"):
            st.write("#### 聯絡人資訊更新")
            new_registrant_email = st.text_input("承辦人 Email", value=school.get('registrant_email', ''))
            new_academic_director_email = st.text_input("教務主任 Email", value=school.get('academic_director_email', ''))
            new_principal_email = st.text_input("校長 Email", value=school.get('principal_email', ''))
            
            st.write("#### 密碼變更")
            current_password = st.text_input("目前密碼", type="password")
            new_password = st.text_input("新密碼", type="password")
            confirm_new_password = st.text_input("確認新密碼", type="password")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.form_submit_button("更新聯絡資訊"):
                    if new_registrant_email and new_academic_director_email and new_principal_email:
                        if "@" in new_registrant_email and "@" in new_academic_director_email and "@" in new_principal_email:
                            try:
                                update_data = {
                                    "registrant_email": new_registrant_email,
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
                        if current_password == school['password']:
                            if new_password == confirm_new_password:
                                if len(new_password) >= 4:
                                    try:
                                        supabase.table("schools").update({"password": new_password}).eq("id", school['id']).execute()
                                        st.success("✅ 密碼更新成功！")
                                        st.session_state.school_info['password'] = new_password
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
elif choice == "📊 系統管理面板":
    st.title("📊 系統管理面板")
    st.success("🎉 歡迎管理員！")
    
    # 系統統計
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # 統計已註冊學校數量
        schools = supabase.table("schools").select("*").execute()
        unique_schools = set([s['name'] for s in schools.data if not s.get('is_admin', False)])
        st.metric("🏫 已註冊學校", len(unique_schools))
    
    with col2:
        # 統計總帳號數量
        total_accounts = len([s for s in schools.data if not s.get('is_admin', False)])
        st.metric("👥 總帳號數", total_accounts)
    
    with col3:
        # 統計配對申請數量
        matches = supabase.table("matches").select("*").execute()
        st.metric("📋 配對申請", len(matches.data))

elif choice == "🏫 已註冊學校清單":
    st.title("🏫 已註冊學校清單")
    
    # 獲取所有非管理員帳號
    schools = supabase.table("schools").select("*").execute()
    non_admin_accounts = [s for s in schools.data if not s.get('is_admin', False)]
    
    if non_admin_accounts:
        # 按學校分組
        school_groups = {}
        for account in non_admin_accounts:
            school_name = account['name']
            if school_name not in school_groups:
                school_groups[school_name] = []
            school_groups[school_name].append(account)
        
        for school_name, accounts in school_groups.items():
            with st.expander(f"🏫 {school_name} ({len(accounts)} 個帳號)"):
                for account in accounts:
                    st.write(f"👤 **{account['registrant_name']}** - {account['identity']}")
                    st.write(f"📧 {account['email']}")
                    st.write(f"🎓 開課: {'✅' if account['is_host'] else '❌'} | 合作: {'✅' if account['is_partner'] else '❌'}")
                    st.divider()
    else:
        st.info("目前尚無學校註冊帳號。")

elif choice == "📈 配對申請統計":
    st.title("📈 配對申請統計")
    
    # 獲取所有配對申請
    matches = supabase.table("matches")\
        .select("*, courses(title), schools(name)")\
        .execute()
    
    if matches.data:
        # 按狀態統計
        status_counts = {}
        school_applications = {}
        
        for match in matches.data:
            # 狀態統計
            status = match.get('status', 'pending')
            status_counts[status] = status_counts.get(status, 0) + 1
            
            # 學校申請統計
            applicant_school = match.get('partner_school_id')
            if applicant_school:
                school_applications[applicant_school] = school_applications.get(applicant_school, 0) + 1
        
        # 顯示統計圖表
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📊 申請狀態分布")
            for status, count in status_counts.items():
                st.write(f"🔸 {status}: {count} 件")
        
        with col2:
            st.subheader("🏫 申請最活躍學校")
            sorted_schools = sorted(school_applications.items(), key=lambda x: x[1], reverse=True)
            for school_id, count in sorted_schools[:5]:
                st.write(f"🔸 學校ID {school_id}: {count} 件申請")
        
        # 詳細申請列表
        st.subheader("📋 詳細申請列表")
        for match in matches.data:
            course_title = match.get('courses', {}).get('title', '未知課程')
            status = match.get('status', 'pending')
            created_at = match.get('created_at', '')[:16]
            st.info(f"📅 {created_at} - {course_title} - 狀態: {status}")
    else:
        st.info("目前尚無配對申請記錄。")

elif choice == "👨‍💼 創建管理帳號":
    st.title("👨‍💼 創建管理帳號")
    
    admin_name = st.text_input("管理員姓名", key="admin_create_name")
    admin_email = st.text_input("管理員 Email", key="admin_create_email")
    admin_password = st.text_input("管理員密碼", type="password", key="admin_create_password")
    admin_role = st.selectbox("管理員角色", ["系統管理員", "課程管理員", "審核管理員"], key="admin_create_role")
    
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