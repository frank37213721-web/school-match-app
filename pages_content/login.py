from datetime import datetime
import streamlit as st
from utils import supabase, hash_password, verify_password, is_valid_email, send_email, is_admin
from school_codes_data import SCHOOL_CODE_MAP, SCHOOLS_BY_DISTRICT


def render_login():
    auth_mode = st.radio("請選擇操作", ["學校帳號登入", "註冊學校帳號", "管理人員登入"], horizontal=True)

    if auth_mode == "學校帳號登入":
        _render_school_login()
    elif auth_mode == "註冊學校帳號":
        _render_register()
    elif auth_mode == "管理人員登入":
        _render_admin_login()


def _render_school_login():
    st.subheader("🔑 學校帳號登入")
    phone = st.text_input("帳號（學校電話）")
    pwd = st.text_input("密碼", type="password")
    if st.button("確認登入"):
        res = supabase.table("schools").select("*").eq("phone", phone).execute()
        if res.data:
            user = res.data[0]
            if verify_password(pwd, user['password_hash']):
                st.session_state.logged_in = True
                st.session_state.school_info = user
                st.success(f"登入成功！歡迎 {user['name']}")
                st.rerun()
            else:
                st.error("密碼錯誤！")
        else:
            st.error("找不到此帳號！")

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

    forgot_phone = st.text_input("學校帳號 (電話號碼)", key="forgot_phone")
    forgot_name = st.text_input("承辦人姓名", key="forgot_name")
    forgot_email = st.text_input("承辦人 Email", key="forgot_email")

    if st.button("🔄 重置密碼", key="reset_password"):
        if forgot_phone and forgot_name and forgot_email:
            with st.spinner("🔍 正在驗證身分資訊..."):
                try:
                    school_res = supabase.table("schools").select("*").eq("phone", forgot_phone).execute()
                    if not school_res.data:
                        st.error("❌ 找不到此帳號！請確認電話號碼正確。")
                    else:
                        school = school_res.data[0]
                        if school['registrant_name'] != forgot_name:
                            st.error("❌ 承辦人姓名不符！請確認輸入正確。")
                        elif school['registrant_email'] != forgot_email:
                            st.error("❌ 承辦人 Email 不符！請確認輸入正確。")
                        else:
                            default_password = forgot_phone[-4:] if len(forgot_phone) >= 4 else "0000"
                            hashed_password = hash_password(default_password)
                            supabase.table("schools").update({"password_hash": hashed_password}).eq("id", school['id']).execute()

                            subject = "🔐 密碼重置通知 - 跨校課程匯流平台"
                            content = f"""親愛的 {school['registrant_name']}：

您的密碼已成功重置。

重置資訊：
- 學校：{school['name']}
- 帳號：{school['phone']}
- 新密碼：{default_password}

**重要提醒：**
- 請使用新密碼登入系統
- 建議登入後立即修改密碼

跨校課程匯流平台"""

                            email_success, email_msg = send_email(
                                school['registrant_email'], school['registrant_name'], subject, content
                            )
                            for recip_email, recip_name in [
                                (school.get('academic_director_email'), '承辦處室主任'),
                                (school.get('principal_email'), '校長'),
                            ]:
                                if is_valid_email(recip_email or ''):
                                    admin_content = f"親愛的 {recip_name}：\n\n通知：{school['name']} 的承辦人 {school['registrant_name']} 已重置密碼。\n\n重置時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n如非授權操作，請立即聯繫系統管理員。\n\n跨校課程匯流平台"
                                    send_email(recip_email, recip_name, subject, admin_content)

                            if email_success:
                                st.success("✅ 密碼重置成功！")
                                st.info(f"🔑 新密碼：{default_password}")
                                st.info("📧 已發送通知 Email 給相關人員")
                                st.balloons()
                            else:
                                st.success("✅ 密碼重置成功！")
                                st.info(f"🔑 新密碼：{default_password}")
                                st.warning("⚠️ Email 發送失敗，請記錄新密碼")
                except Exception as e:
                    st.error(f"❌ 重置失敗：{e}")
        else:
            st.error("⚠️ 請填寫所有必填欄位！")


TERMS_HTML = """
<div id="terms-scroll-box" style="
    height: 320px;
    overflow-y: scroll;
    border: 1px solid #b0c4e0;
    border-radius: 8px;
    padding: 1.2rem 1.4rem;
    background: rgba(255,255,255,0.85);
    color: #1a2340;
    font-size: 0.93rem;
    line-height: 1.7;
    margin-bottom: 0.5rem;
" onscroll="
    var el = document.getElementById('terms-scroll-box');
    var atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 10;
    var cb = window.parent.document.querySelector('[data-testid=stCheckbox] input');
    if (cb && atBottom) { cb.disabled = false; cb.closest('[data-testid=stCheckbox]').style.opacity = '1'; }
">
<h4 style="margin-top:0;color:#1a2a4a">跨校課程串聯平台：註冊須知與約定事項</h4>
<p>感謝您加入本平台。為確保校際合作之順暢，請於註冊前詳閱以下事項：</p>

<p><strong>1. 平台的角色定位：資訊鏈結與輔助</strong><br>
本平台定位為「教育資源資訊交換中心」，僅提供各校課程需求與開課資訊之展示。平台之功能在於輔助學校發現潛在合作對象，而非課程決策單位。</p>

<p><strong>2. 積極洽談之義務：學校需主動出擊</strong><br>
本平台採「被動式資訊彙整」模式。相關課程之細節洽談、排課協調及行政作業，需由註冊學校雙方主動聯繫。平台不介入後續的行政決策與過程。</p>

<p><strong>3. 免責聲明：不保證合作成功</strong><br>
開發者（及平台方）致力於優化資訊鏈結之精準度，但不保證註冊學校一定能達成跨校課程之合作。合作是否成功，取決於各校課程性質、距離、時間及雙方合作意願等客觀因素，開發者不負任何配對成功之保證責任。</p>

<p><strong>4. 資訊真實性責任</strong><br>
註冊學校應確保上傳至平台之課程資訊、聯繫方式及合作需求皆為真實。若因資訊有誤導致合作受阻或產生行政缺失，應由提供資訊之學校自行負責。</p>

<p><strong>5. 行政主體性原則</strong><br>
跨校課程之開設應符合教育部（局）相關法規，平台所提供之配對建議僅供參考。所有行政契約、合作備忘錄（MOU）之簽署及學分認定，皆需回歸各校現行行政流程與法規處理。</p>

<p style="margin-bottom:0;padding-bottom:0.5rem;color:#4a6a9a;font-size:0.85rem">
― 已閱讀至本頁底部，請勾選下方同意按鈕繼續 ―
</p>
</div>
"""


def _render_register():
    st.subheader("📝 建立學校帳號")

    # ── 使用者須知 ──
    st.write("#### 📋 使用者權利須知與合作約定")
    st.caption("請閱讀並滑至底部後勾選同意，方可進行註冊。")
    st.markdown(TERMS_HTML, unsafe_allow_html=True)

    terms_agreed = st.checkbox("我已閱讀並同意以上《使用者權利須知與合作約定》", key="terms_agreed")

    if not terms_agreed:
        st.info("☝️ 請閱讀上方說明並滑至底部，勾選同意後繼續填寫註冊資料。")
        return

    st.divider()

    # 從 school_registry 載入（優先），fallback 至 hardcode
    try:
        _reg = supabase.table("school_registry").select("code,name,district").execute().data
        _has_db = bool(_reg)
    except Exception:
        _reg = []
        _has_db = False

    schools_by_district = SCHOOLS_BY_DISTRICT.copy()
    if _has_db:
        _sd: dict = {}
        for _e in _reg:
            _d = (_e.get("district") or "").strip()
            if _d:
                _sd.setdefault(_d, []).append(_e["name"])
        if _sd:
            schools_by_district = _sd

    # ── 1. 選擇學校名稱 ──
    st.write("### 1. 選擇學校名稱")

    code_input = st.text_input("輸入學校代碼（快速帶出學校名稱）",
                               max_chars=10, placeholder="例：183314")
    code_input = code_input.strip().upper()

    auto_district = None
    auto_school = None
    if code_input:
        matched_entry = next((e for e in _reg if (e.get("code") or "").upper() == code_input), None)
        if matched_entry:
            auto_school = matched_entry["name"]
            auto_district = (matched_entry.get("district") or "").strip() or None
        else:
            matched_name = SCHOOL_CODE_MAP.get(code_input)
            if matched_name:
                auto_school = matched_name
                for dist, slist in schools_by_district.items():
                    if matched_name in slist:
                        auto_district = dist
                        break
            else:
                st.error("找不到此代碼對應的學校，請確認代碼或直接從下方選單選取。")

    if auto_school:
        selected_school = st.text_input("學校名稱", value=auto_school)
        selected_district = auto_district or ""
        if auto_district:
            st.caption(f"分區：{auto_district}")
    else:
        district_list = list(schools_by_district.keys())
        district_idx = district_list.index(auto_district) if auto_district and auto_district in district_list else 0
        col_d, col_s = st.columns(2)
        with col_d:
            selected_district = st.selectbox("選擇分區", district_list, index=district_idx)
        with col_s:
            schools_in_district = schools_by_district.get(selected_district, [])
            selected_school = st.selectbox("選擇學校", schools_in_district)

    district = selected_district
    school_name = selected_school

    st.divider()

    # ── 2. 承辦人資訊 ──
    st.write("### 2. 承辦人資訊")
    col_n, col_ext = st.columns(2)
    with col_n:
        registrant_name = st.text_input("承辦人姓名", placeholder="例：王小明")
    with col_ext:
        registrant_extension = st.text_input("承辦人分機", placeholder="例：123", max_chars=10)

    school_phone = st.text_input("學校電話（作為登入帳號，請含區域號碼）",
                                 placeholder="例：073475181", max_chars=10)
    st.caption("⚠️ 請輸入含區域號碼的完整電話，例如高雄市為 07、台北市為 02")

    default_password = school_phone[-4:] if len(school_phone) >= 4 else ""
    hashed_password = hash_password(default_password) if default_password else ""
    st.info(f"🔒 預設密碼（電話後4碼）：{'**' + default_password + '**' if default_password else '請輸入完整電話號碼'}")

    st.divider()

    # ── 3. 學校重要聯絡人 Email ──
    st.write("### 3. 學校重要聯絡人 Email")
    registrant_email = st.text_input("承辦人 Email")
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
            existing_school = supabase.table("schools").select("*").eq("name", school_name).execute()
            if existing_school.data:
                st.error(f"⚠️ 此學校「{school_name}」已經註冊過帳號了，每校限一個帳號。")
            else:
                existing_phone = supabase.table("schools").select("*").eq("phone", school_phone).execute()
                if existing_phone.data:
                    st.error("⚠️ 此電話號碼已被其他學校使用，請聯繫管理員。")
                else:
                    new_school = {
                        "name": school_name,
                        "district": district,
                        "phone": school_phone,
                        "password_hash": hashed_password,
                        "registrant_name": registrant_name,
                        "registrant_extension": registrant_extension,
                        "registrant_email": registrant_email,
                        "academic_director_email": academic_director_email,
                        "principal_email": principal_email,
                        "identity": "學校承辦人",
                        "is_host": True,
                        "is_partner": True,
                        "is_admin": False
                    }
                    try:
                        supabase.table("schools").insert(new_school).execute()
                        st.success(f"🎉 註冊成功！歡迎 {school_name}。")
                        st.info(f"📞 帳號：{school_phone}")
                        st.info(f"🔐 預設密碼：{default_password}")
                        st.balloons()
                    except Exception as e:
                        st.error(f"註冊失敗：{e}")


def _render_admin_login():
    st.subheader("🔐 管理人員登入")
    admin_username = st.text_input("管理員帳號")
    admin_password = st.text_input("管理員密碼", type="password")

    if st.button("管理員登入"):
        try:
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

    if is_admin():
        st.divider()
        st.subheader("👨‍💼 創建管理帳號")
        admin_name = st.text_input("管理員姓名", key="admin_name")
        admin_email = st.text_input("管理員 Email", key="admin_email")
        admin_pwd = st.text_input("管理員密碼", type="password", key="admin_password")
        admin_role = st.selectbox("管理員角色", ["系統管理員", "課程管理員", "審核管理員"], key="admin_role")

        if st.button("創建管理帳號"):
            if admin_name and admin_email and admin_pwd:
                try:
                    hashed_admin_password = hash_password(admin_pwd)
                    admin_data = {
                        "name": "管理部門",
                        "registrant_name": admin_name,
                        "registrant_email": admin_email,
                        "password_hash": hashed_admin_password,
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
