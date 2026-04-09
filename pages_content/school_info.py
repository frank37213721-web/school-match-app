import streamlit as st
from utils import supabase, require_login, is_valid_email, verify_password, hash_password


def render_school_info():
    require_login()
    st.header("🏫 學校基本資料管理")
    if not st.session_state.school_info:
        return

    school = st.session_state.school_info
    st.subheader(f"學校：{school['name']}")

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
                    if verify_password(current_password, school['password_hash']):
                        if new_password == confirm_new_password:
                            if len(new_password) >= 4:
                                try:
                                    hashed_new_password = hash_password(new_password)
                                    supabase.table("schools").update({"password_hash": hashed_new_password}).eq("id", school['id']).execute()
                                    st.success("✅ 密碼更新成功！")
                                    st.session_state.school_info['password_hash'] = hashed_new_password
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
