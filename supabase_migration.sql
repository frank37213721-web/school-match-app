-- Supabase SQL Migration Script
-- 在 Supabase Dashboard 的 SQL Editor 中執行這些腳本

-- 1. 新增 password_hash 欄位
ALTER TABLE schools 
ADD COLUMN IF NOT EXISTS password_hash TEXT;

-- 2. 新增 identity 欄位
ALTER TABLE schools 
ADD COLUMN IF NOT EXISTS identity TEXT DEFAULT '學校承辦人';

-- 3. 新增 is_admin 欄位
ALTER TABLE schools 
ADD COLUMN IF NOT EXISTS is_admin BOOLEAN DEFAULT false;

-- 4. 新增 created_at 欄位（如果不存在）
ALTER TABLE schools 
ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT now();

-- 5. 遷移現有的 password 資料到 password_hash
-- 如果 password 欄位存在且不是雜湊值，則進行雜湊
UPDATE schools 
SET password_hash = password 
WHERE password IS NOT NULL 
  AND password_hash IS NULL
  AND password NOT LIKE '$2b$%';

-- 如果 password 已經是雜湊值，直接複製
UPDATE schools 
SET password_hash = password 
WHERE password IS NOT NULL 
  AND password_hash IS NULL
  AND password LIKE '$2b$%';

-- 6. 遷移 email 到 registrant_email（如果 registrant_email 為空）
UPDATE schools 
SET registrant_email = email 
WHERE email IS NOT NULL 
  AND registrant_email IS NULL;

-- 7. 為管理員設定正確的 identity
UPDATE schools 
SET identity = '系統管理員' 
WHERE is_admin = true 
  AND identity = '學校承辦人';

-- 8. 為現有管理員記錄設定 identity（根據 email 判斷）
UPDATE schools 
SET identity = '系統管理員' 
WHERE email LIKE '%admin%' 
  OR registrant_email LIKE '%admin%';

-- 9. 檢查遷移結果
SELECT 
    id,
    name,
    CASE 
        WHEN password_hash IS NOT NULL THEN '✅ 已遷移'
        ELSE '❌ 未遷移'
    END as password_status,
    CASE 
        WHEN registrant_email IS NOT NULL THEN '✅ 已設定'
        ELSE '❌ 未設定'
    END as email_status,
    identity,
    is_admin
FROM schools 
ORDER BY created_at DESC;

-- 10. 可選：移除舊的 password 和 email 欄位（確認無問題後執行）
-- ALTER TABLE schools DROP COLUMN IF EXISTS password;
-- ALTER TABLE schools DROP COLUMN IF EXISTS email;
