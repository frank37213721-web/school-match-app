# 權限控制系統說明

## 🔐 權限控制函數

### 基本權限檢查函數

```python
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
```

## 🛡️ 頁面權限保護

### 需要登入權限的頁面
- `管理中心 (我的課程)` - require_login()
- `學校基本資料` - require_login()
- `新增/修改課程` - require_login()
- `配對情形` - require_login()

### 需要管理員權限的頁面
- `📊 系統管理` - require_admin()

### 管理員專用功能
- 創建管理帳號 - is_admin()

## 🔄 使用方式

### 在頁面開頭加入權限檢查
```python
elif choice == "需要權限的頁面":
    require_login()  # 或 require_admin()
    st.title("頁面標題")
    # 頁面內容...
```

### 在條件判斷中使用
```python
# 側邊欄選單
if is_admin():
    menu = ["課程大廳", "📊 系統管理", "登出"]
elif not is_logged_in():
    menu = ["課程大廳", "學校帳號登入"]
else:
    menu = ["課程大廳", "管理中心", "登出"]

# 管理員功能
if is_admin():
    # 管理員專用功能
    pass
```

## 🎯 安全特性

1. **統一權限檢查** - 所有權限驗證都通過標準化函數
2. **明確錯誤訊息** - 用戶知道為什麼無法訪問
3. **立即停止執行** - 使用 `st.stop()` 防止未授權訪問
4. **清晰的權限層級** - 區分一般用戶和管理員權限

## 📋 實作狀態

✅ 已完成的權限保護：
- 管理員系統管理頁面
- 學校管理中心頁面
- 學校基本資料頁面
- 新增/修改課程頁面
- 配對情形頁面
- 側邊欄選單邏輯
- 管理員帳號創建功能

## 🔧 維護建議

1. **新頁面** - 每個新增的需要權限的頁面都要加上適當的權限檢查
2. **權限測試** - 定期測試各種權限場景確保安全性
3. **權限日誌** - 可考慮加入權限檢查的日誌記錄
