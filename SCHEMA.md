# Schools 表欄位結構定義

## 📋 統一 Schema

```sql
CREATE TABLE schools (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,                    -- 學校名稱
    district TEXT NOT NULL,                -- 所屬分區
    phone TEXT UNIQUE NOT NULL,            -- 電話號碼 (登入帳號)
    password_hash TEXT NOT NULL,           -- 雜湊後的密碼
    registrant_name TEXT NOT NULL,         -- 承辦人姓名
    registrant_email TEXT NOT NULL,        -- 承辦人 Email (主聯絡窗口)
    registrant_extension TEXT,             -- 承辦人分機
    academic_director_email TEXT,          -- 承辦處室主任 Email
    principal_email TEXT,                  -- 校長 Email
    identity TEXT,                         -- 身份/職稱
    is_host BOOLEAN DEFAULT true,          -- 是否為主辦方
    is_partner BOOLEAN DEFAULT true,       -- 是否為合作方
    is_admin BOOLEAN DEFAULT false,        -- 是否為管理員
    created_at TIMESTAMP DEFAULT now()     -- 建立時間
);
```

## 🔄 欄位名稱對照

| 舊欄位名 | 新欄位名 | 說明 |
|----------|----------|------|
| password | password_hash | 明確標示為雜湊密碼 |
| email | registrant_email | 統一使用承辦人 Email |
| (無) | registrant_extension | 新增承辦人分機欄位 |
(無) | created_at | 新增建立時間 |

## 📧 Email 欄位使用原則

- **registrant_email**: 主要聯絡窗口 (承辦人)
- **academic_director_email**: 承辦處室主任 Email
- **principal_email**: 校長
- **移除 email 欄位**: 避免與 registrant_email 混淆

## 🔐 密碼欄位原則

- **password_hash**: 儲存 bcrypt 雜湊值
- **移除 password**: 避免明文密碼混淆

## 📝 修復清單

### 需要修改的檔案和位置：

1. ✅ **app.py 註冊功能** (line 369-382)
   - `"password"` → `"password_hash"`
   - 移除 `"email"` 欄位
   - 新增 `"identity"` 和 `"is_admin"` 欄位

2. ✅ **app.py 登入功能** (line 252)
   - `user['password']` → `user['password_hash']`

3. ✅ **app.py 學校資料更新** (line 531)
   - `"password"` → `"password_hash"`

4. ✅ **app.py 管理員創建** (line 433)
   - `"password"` → `"password_hash"`
   - `"email"` → `"registrant_email"`

5. ✅ **app.py 查詢語句** (line 134)
   - `email` → `registrant_email`

6. ✅ **app.py Email 發送** (line 191)
   - `c['schools']['email']` → `c['schools']['registrant_email']`

7. ✅ **app.py 管理頁面顯示** (line 652)
   - `account['password']` → 隱藏密碼顯示

8. ✅ **創建遷移腳本**
   - `migrate_database.py` - 自動遷移現有資料

## 🎯 實施步驟

1. ✅ 定義統一 Schema
2. ✅ 修改所有程式碼中的欄位引用
3. 🔄 更新資料庫結構 (需要遷移腳本)
4. 🔄 測試所有功能
5. ✅ 更新文檔
