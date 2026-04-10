from collections import defaultdict
import io
import pandas as pd
import streamlit as st
from utils import supabase, require_admin, delete_school_cascade
from school_codes_data import SCHOOL_CODE_MAP, SCHOOLS_BY_DISTRICT


def render_admin():
    require_admin()
    st.title("📊 系統管理")

    tab1, tab2, tab3 = st.tabs(["🏫 學校帳號基本資訊", "🤝 配對狀況", "📋 學校清單管理"])

    with tab1:
        _render_accounts_tab()

    with tab2:
        _render_matches_tab()

    with tab3:
        _render_registry_tab()


def _render_accounts_tab():
    try:
        all_schools_res = supabase.table("schools").select("*").execute()
        registered = [s for s in all_schools_res.data if not s.get("is_admin", False)]
        registered_names = {s["name"] for s in registered}

        district_options = ["全部"] + list(SCHOOLS_BY_DISTRICT.keys())
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
                        st.warning(f"⚠️ 確定要刪除「{account['name']}」？將同時刪除所有課程與配對記錄，且**無法復原**。")
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
        for district, names in SCHOOLS_BY_DISTRICT.items():
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


def _render_matches_tab():
    try:
        courses_res = supabase.table("courses")\
            .select("id, title, max_schools, host_school_id, schools(name)")\
            .execute()
        matches_res = supabase.table("matches")\
            .select("id, course_id, partner_school_id, status")\
            .execute()
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
            stats: dict = defaultdict(lambda: {"total": 0, "approved": 0})
            for m in all_matches:
                stats[m["partner_school_id"]]["total"] += 1
                if m["status"] == "approved":
                    stats[m["partner_school_id"]]["approved"] += 1
            for pid, s in stats.items():
                sname = partner_map.get(pid, f"學校 {pid}")
                st.write(f"**{sname}**　共送出 {s['total']} 次申請，已成功配對 {s['approved']} 次")
        else:
            st.info("目前尚無任何配對申請記錄。")

    except Exception as e:
        st.error(f"讀取配對資料失敗：{e}")


def _render_registry_tab():
    st.subheader("📋 學校代碼與分區管理")
    st.caption("此清單決定學校帳號申請頁面可選擇的學校。代碼欄位供學校申請時快速帶入學校名稱。")

    try:
        reg_res = supabase.table("school_registry").select("*").order("district").order("name").execute()
        all_reg = reg_res.data
    except Exception as e:
        st.error(f"讀取學校清單失敗：{e}（請先至 Supabase 建立 school_registry 資料表）")
        all_reg = []

    # ── 一鍵匯入 ──
    with st.expander("🔄 一鍵匯入（匯入所有教育部代碼 + 現有分區設定）"):
        st.write("將會把下列資料匯入 school_registry：")
        st.write(f"- 教育部代碼表：**{len(SCHOOL_CODE_MAP)} 筆**（代碼 + 學校名稱，分區留空）")
        st.write(f"- 現有分區設定：**{sum(len(v) for v in SCHOOLS_BY_DISTRICT.values())} 筆**（學校名稱 + 分區，代碼留空）")
        st.info("已存在的學校名稱不會重複匯入。")
        if st.button("▶️ 開始匯入", type="primary", key="bulk_import"):
            imported = 0
            skipped = 0
            existing_names = {r["name"] for r in all_reg}
            existing_codes = {r.get("code") for r in all_reg if r.get("code")}

            for code, name in SCHOOL_CODE_MAP.items():
                if name in existing_names or code in existing_codes:
                    skipped += 1
                    continue
                try:
                    supabase.table("school_registry").insert({"code": code, "name": name, "district": ""}).execute()
                    imported += 1
                    existing_names.add(name)
                    existing_codes.add(code)
                except Exception:
                    skipped += 1

            for district, names in SCHOOLS_BY_DISTRICT.items():
                for name in names:
                    existing = next((r for r in all_reg if r["name"] == name), None)
                    if existing:
                        if not existing.get("district"):
                            supabase.table("school_registry").update({"district": district}).eq("id", existing["id"]).execute()
                    elif name not in existing_names:
                        try:
                            supabase.table("school_registry").insert({"name": name, "district": district}).execute()
                            imported += 1
                            existing_names.add(name)
                        except Exception:
                            skipped += 1

            st.success(f"匯入完成：新增 {imported} 筆，略過 {skipped} 筆")
            st.rerun()

    # ── 下載目前清單 ──
    if all_reg:
        df_dl = pd.DataFrame([
            {"代碼": r.get("code") or "", "學校名稱": r["name"], "分區": r.get("district") or ""}
            for r in all_reg
        ])
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as writer:
            df_dl.to_excel(writer, index=False, sheet_name="school_registry")
        st.download_button(
            "📥 下載目前學校清單（Excel）",
            data=buf.getvalue(),
            file_name="school_registry.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    # ── 上傳 Excel 更新 ──
    with st.expander("📤 上傳 Excel 更新學校清單"):
        st.caption("欄位需包含：**代碼**（選填）、**學校名稱**（必填）、**分區**（選填）。相同代碼或名稱的資料若有差異則覆蓋，不存在則新增，原有但未出現在檔案中的資料保留不刪除。")
        uploaded = st.file_uploader("選擇 Excel 檔案（.xlsx）", type=["xlsx"], key="reg_upload")
        if uploaded:
            try:
                df_up = pd.read_excel(uploaded, dtype=str).fillna("")
                # 欄位對應（允許中英文欄名）
                col_map = {}
                for col in df_up.columns:
                    if col in ("代碼", "code", "Code"):
                        col_map["code"] = col
                    elif col in ("學校名稱", "name", "Name"):
                        col_map["name"] = col
                    elif col in ("分區", "district", "District"):
                        col_map["district"] = col

                if "name" not in col_map:
                    st.error("❌ 找不到「學校名稱」欄位，請確認欄位名稱。")
                else:
                    rows = []
                    for _, row in df_up.iterrows():
                        rows.append({
                            "code": row.get(col_map.get("code", ""), "").strip().upper() or None,
                            "name": row[col_map["name"]].strip(),
                            "district": row.get(col_map.get("district", ""), "").strip(),
                        })
                    rows = [r for r in rows if r["name"]]  # 過濾空名稱

                    st.write(f"讀取到 **{len(rows)}** 筆資料，預覽：")
                    st.dataframe(pd.DataFrame(rows).head(10), use_container_width=True, hide_index=True)

                    if st.button("✅ 確認匯入", type="primary", key="confirm_upload"):
                        existing_by_code = {r["code"]: r for r in all_reg if r.get("code")}
                        existing_by_name = {r["name"]: r for r in all_reg}
                        added = updated = skipped = 0
                        for r in rows:
                            # 優先以代碼比對，否則以名稱比對
                            existing = existing_by_code.get(r["code"]) if r["code"] else None
                            if existing is None:
                                existing = existing_by_name.get(r["name"])

                            if existing is None:
                                supabase.table("school_registry").insert(r).execute()
                                added += 1
                            else:
                                changed = {
                                    k: v for k, v in r.items()
                                    if v != (existing.get(k) or "") and not (v is None and not existing.get(k))
                                }
                                if changed:
                                    supabase.table("school_registry").update(changed).eq("id", existing["id"]).execute()
                                    updated += 1
                                else:
                                    skipped += 1
                        st.success(f"✅ 完成：新增 {added} 筆，更新 {updated} 筆，未變動 {skipped} 筆")
                        st.rerun()
            except Exception as e:
                st.error(f"讀取 Excel 失敗：{e}")

    st.divider()

    if all_reg:
        all_districts_reg = sorted({r.get("district", "") for r in all_reg})
        col_f1, col_f2 = st.columns([1, 3])
        with col_f1:
            dist_filter = st.selectbox(
                "篩選分區",
                ["全部（含未分區）"] + [d for d in all_districts_reg if d] + (["（未分區）"] if "" in all_districts_reg else []),
                key="reg_dist_filter"
            )
        with col_f2:
            name_filter = st.text_input("搜尋學校名稱", placeholder="輸入關鍵字...", key="reg_name_filter")

        if dist_filter == "全部（含未分區）":
            show_reg = all_reg
        elif dist_filter == "（未分區）":
            show_reg = [r for r in all_reg if not r.get("district")]
        else:
            show_reg = [r for r in all_reg if r.get("district") == dist_filter]
        if name_filter:
            show_reg = [r for r in show_reg if name_filter in r["name"]]

        st.write(f"顯示 **{len(show_reg)}** 筆（共 {len(all_reg)} 筆）")

        edit_id = st.session_state.get("reg_edit_id")

        for r in show_reg:
            if edit_id == r["id"]:
                with st.container():
                    st.markdown("---")
                    col_c, col_n, col_d, col_btn = st.columns([1.2, 2.5, 1.5, 1])
                    with col_c:
                        new_code = st.text_input("代碼", value=r.get("code") or "", max_chars=10, key=f"ec_{r['id']}")
                    with col_n:
                        new_name = st.text_input("學校名稱", value=r["name"], key=f"en_{r['id']}")
                    with col_d:
                        new_dist = st.text_input("分區", value=r.get("district") or "", key=f"ed_{r['id']}")
                    with col_btn:
                        st.markdown("<div style='height:1.8rem'></div>", unsafe_allow_html=True)
                        if st.button("💾 儲存", key=f"save_{r['id']}"):
                            supabase.table("school_registry").update({
                                "code": new_code.strip().upper() or None,
                                "name": new_name.strip(),
                                "district": new_dist.strip()
                            }).eq("id", r["id"]).execute()
                            st.session_state.reg_edit_id = None
                            st.rerun()
                        if st.button("✖ 取消", key=f"cancel_{r['id']}"):
                            st.session_state.reg_edit_id = None
                            st.rerun()
                    st.markdown("---")
            else:
                col_c, col_n, col_d, col_e, col_del = st.columns([1.2, 2.5, 1.5, 0.6, 0.6])
                col_c.text(r.get("code") or "—")
                col_n.text(r["name"])
                col_d.text(r.get("district") or "未分區")
                with col_e:
                    if st.button("✏️", key=f"edit_{r['id']}", help="編輯"):
                        st.session_state.reg_edit_id = r["id"]
                        st.rerun()
                with col_del:
                    if st.button("🗑️", key=f"dreg_{r['id']}", help="刪除"):
                        supabase.table("school_registry").delete().eq("id", r["id"]).execute()
                        st.rerun()
    else:
        st.info("學校清單為空，請點選上方「一鍵匯入」建立初始資料。")

    # ── 新增單筆 ──
    st.divider()
    st.write("#### ➕ 新增學校")
    col_a, col_b, col_c2 = st.columns([1.2, 2.5, 1.5])
    with col_a:
        add_code = st.text_input("代碼（選填）", max_chars=10, key="add_reg_code", placeholder="例：183314")
    with col_b:
        add_name = st.text_input("學校名稱", key="add_reg_name", placeholder="例：新竹市數位實驗高中")
    with col_c2:
        add_dist = st.text_input("分區", key="add_reg_dist", placeholder="例：北三區")
    if st.button("新增", key="add_reg_btn"):
        if add_name.strip():
            try:
                supabase.table("school_registry").insert({
                    "code": add_code.strip().upper() or None,
                    "name": add_name.strip(),
                    "district": add_dist.strip()
                }).execute()
                st.success(f"已新增：{add_name}")
                st.rerun()
            except Exception as e:
                st.error(f"新增失敗：{e}")
        else:
            st.error("請輸入學校名稱")
