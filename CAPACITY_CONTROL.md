# 課程容量控制系統

## 🎯 功能概述

為課程媒合申請加入真正的容量控制，確保 `max_students` 和 `max_schools` 不只是展示文字，而是實際的業務規則。

## 🔧 實現的功能

### 1. 課程容量顯示
在課程大廳中顯示實時申請狀況：
```
🏫 合作學校上限：2 所
📊 目前申請：1/2 所
  - ✅ 已通過：0 所
  - ⏳ 待審核：1 所
```

### 2. 申請前容量檢查
在提交申請前進行嚴格的容量檢查：

```python
# 檢查課程容量是否已滿
current_matches = supabase.table("matches")\
    .select("*")\
    .eq("course_id", course_id)\
    .in_("status", ["pending", "approved"])\
    .execute()

approved_count = len([m for m in current_matches.data if m['status'] == 'approved'])
pending_count = len([m for m in current_matches.data if m['status'] == 'pending'])
total_active = approved_count + pending_count

max_schools = course.get('max_schools', 2)

# 檢查學校數量限制
if total_active >= max_schools:
    st.error(f"⚠️ 此課程合作學校已滿！最多接受 {max_schools} 所學校，目前已有 {approved_count} 所通過，{pending_count} 所待審核。")
```

### 3. 按鈕狀態控制
根據容量狀態動態調整申請按鈕：

```python
if total_active >= max_schools:
    button_disabled = True
    button_text = "🚫 名額已滿"
else:
    button_disabled = False
    button_text = "申請媒合"

st.button(button_text, disabled=button_disabled)
```

### 4. 資料庫欄位擴展
在 `matches` 表中新增欄位支援未來擴展：

```sql
matches 表新增欄位：
- requested_students: INTEGER  -- 申請學生人數（未來功能）
```

## 📋 業務規則

### 狀態計算規則
- **pending**: 待審核的申請（占用名額）
- **approved**: 已通過的申請（占用名額）
- **rejected**: 已拒絕的申請（不占用名額）

### 容量檢查時機
1. **課程列表顯示時** - 計算並顯示目前申請狀況
2. **申請按鈕點擊時** - 檢查是否可以申請
3. **申請提交前** - 最終容量驗證

### 錯誤處理
- **名額已滿**: 顯示詳細的容量資訊
- **按鈕禁用**: 防止用戶無效操作
- **明確提示**: 說明目前申請狀況

## 🎨 用戶體驗改進

### 視覺化資訊
- 📊 實時申請進度條（未來可加入）
- 🚫 名額已滿的明確標示
- ✅ 已通過 / ⏳ 待審核的狀態圖示

### 互動體驗
- **即時反饋**: 按鈕狀態即時更新
- **預防性提示**: 在操作前就告知限制
- **詳細說明**: 錯誤訊息包含具體數字

## 🚀 未來擴展方向

### 1. 學生人數控制
```python
# 未來可以加入學生人數申請
requested_students = st.number_input("申請學生人數", min_value=1, max_value=remaining_capacity)

# 檢查學生總數是否超限
total_requested_students = sum(m['requested_students'] for m in active_matches) + requested_students
if total_requested_students > max_students:
    st.error("學生總人數超過課程容量！")
```

### 2. 動態容量調整
- 管理員可以調整課程容量
- 容量變更時通知相關人員
- 容量歷史記錄追蹤

### 3. 申請排隊機制
- 名額滿時加入等待列表
- 有取消時自動通知候補
- 排隊順序管理

### 4. 容量報表
- 課程容量使用率統計
- 申請趨勢分析
- 容量配置建議

## 🔧 技術實現細節

### 效能優化
- 使用資料庫索引優化查詢
- 快取目前申請狀況
- 批量查詢減少 API 呼叫

### 資料一致性
- 交易性操作確保資料完整性
- 樂觀鎖定防止並發問題
- 狀態變更日誌記錄

### 測試覆蓋
- 邊界條件測試（剛好滿、超過等）
- 並發申請測試
- 狀態轉換測試

## 📊 監控指標

### 業務指標
- 課程容量使用率
- 申請成功率
- 平均申請處理時間

### 技術指標
- 容量檢查回應時間
- 資料庫查詢效能
- 錯誤率統計
