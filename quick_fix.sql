-- 緊急修復：處理 password_hash 欄位和 NOT NULL 約束
-- 在 Supabase Dashboard 的 SQL Editor 中執行

-- 1. 新增 password_hash 欄位
ALTER TABLE schools ADD COLUMN IF NOT EXISTS password_hash TEXT;

-- 2. 將現有的 password 複製到 password_hash
UPDATE schools 
SET password_hash = password 
WHERE password IS NOT NULL AND password_hash IS NULL;

-- 3. 移除 password 欄位的 NOT NULL 約束（如果存在）
ALTER TABLE schools ALTER COLUMN password DROP NOT NULL;

-- 4. 或者，如果不想保留 password 欄位，可以設定預設值
-- UPDATE schools SET password = '' WHERE password IS NULL;

-- 5. 檢查結果
SELECT 
    id, 
    name, 
    password IS NOT NULL as has_password,
    password_hash IS NOT NULL as has_password_hash,
    is_admin
FROM schools 
WHERE password IS NOT NULL OR password_hash IS NOT NULL
ORDER BY id DESC;
