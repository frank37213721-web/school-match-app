# 媒合申請流程改進說明

## 🔄 新的媒合申請流程

### 🎯 解決的問題

**舊流程問題：**
1. ❌ 先寄信再寫資料庫，容易造成數據不一致
2. ❌ 信寄出但 DB 寫入失敗 → 用戶認為申請成功，但系統無記錄
3. ❌ DB 還沒寫成功，但使用者已認為申請完成
4. ❌ 只通知開課學校承辦人，資訊不完整

**新流程改進：**
1. ✅ 先寫入資料庫確保數據一致性
2. ✅ 同時通知所有相關人員（6人）
3. ✅ 追蹤 Email 發送狀態
4. ✅ 防止重複申請

## 📋 新流程步驟

### 1. 重複申請檢查
```python
# 檢查是否有未完成的申請（pending 或 approved 狀態）
existing_match = supabase.table("matches")\
    .select("*")\
    .eq("course_id", course_id)\
    .eq("partner_school_id", applicant_school_id)\
    .in_("status", ["pending", "approved"])\
    .execute()

if existing_match.data:
    # 顯示錯誤，不允許重複申請
    st.error("⚠️ 您已經申請過此課程的媒合，且申請正在處理中或已通過！")
```

**重要改進：**
- ✅ 只檢查 `pending` 和 `approved` 狀態的申請
- ✅ 允許對已拒絕（`rejected`）的課程重新申請
- ✅ 更精確的錯誤訊息，說明申請狀態

### 2. 先寫入 matches 資料表
```python
match_data = {
    "course_id": course_id,
    "partner_school_id": applicant_school_id,
    "status": "pending",
    "email_status": "pending"  # 新增 Email 狀態追蹤
}
```

### 3. 批量 Email 發送（6人）

**開課學校（3人）：**
- 承辦人：收到媒合申請通知
- 承辦處室主任：收到媒合申請通知  
- 校長：收到媒合申請通知

**申請學校（3人）：**
- 承辦人：已遞交媒合申請確認
- 承辦處室主任：已遞交媒合申請確認
- 校長：已遞交媒合申請確認

### 4. Email 狀態更新
```python
if email_success:
    supabase.table("matches").update({"email_status": "sent"}).eq("id", match_id).execute()
else:
    supabase.table("matches").update({"email_status": "failed"}).eq("id", match_id).execute()
```

## 📧 Email 內容設計

### 給開課學校的通知
```
主題：媒合申請通知：{申請學校} 申請您的課程「{課程名稱}」

內容：
- 課程資訊
- 申請學校完整資訊
- 聯絡方式
- 處理指引
```

### 給申請學校的確認
```
主題：媒合申請確認：已申請「{課程名稱}」課程

內容：
- 申請課程資訊
- 開課學校資訊
- 申請時間
- 後續流程說明
```

## 🛡️ 數據一致性保障

### 資料庫欄位更新
```sql
matches 表新增欄位：
- email_status: pending/sent/failed
- created_at: 申請時間戳記
```

### 錯誤處理機制
1. **重複申請防護** - 檢查是否已存在相同申請
2. **Email 失敗處理** - 記錄失敗狀態，不影響申請記錄
3. **部分失敗通知** - 明確告知哪些 Email 發送失敗

## 🎯 用戶體驗改進

### 按鈕文案更新
- 舊：「確定發送媒合Email」
- 新：「確定申請媒合」

### 成功訊息優化
- 舊：只提到信件發送
- 新：提到申請提交和 Email 通知

### 錯誤處理
- 明確區分申請失敗和 Email 失敗
- 提供具體的錯誤訊息和建議

## 📊 狀態追蹤

### Email 狀態
- `pending` - 準備發送
- `sent` - 發送成功
- `failed` - 發送失敗

### 申請狀態
- `pending` - 待處理
- `approved` - 已同意
- `rejected` - 已拒絕

## 🔧 管理功能

### 管理員可以：
1. 查看所有申請記錄
2. 追蹤 Email 發送狀態
3. 重新發送失敗的 Email
4. 處理異常申請

### 統計資訊
- 申請成功率
- Email 發送成功率
- 處理時長統計

## 🚀 未來改進方向

1. **Email 範本管理** - 可自訂 Email 內容
2. **批量通知** - 支援其他通知方式（如 Line、Slack）
3. **申請追蹤** - 申請進度實時通知
4. **自動提醒** - 逾期未處理申請自動提醒
