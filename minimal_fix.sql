-- 最簡單的修復：移除 password 欄位的 NOT NULL 約束
-- 在 Supabase Dashboard 的 SQL Editor 中執行

-- 移除 password 欄位的 NOT NULL 約束
ALTER TABLE schools ALTER COLUMN password DROP NOT NULL;

-- 檢查約束是否已移除
SELECT 
    column_name, 
    is_nullable, 
    data_type
FROM information_schema.columns 
WHERE table_name = 'schools' 
  AND column_name = 'password';

-- 額外檢查：查看目前 schools 表的結構
SELECT column_name, data_type, is_nullable 
FROM information_schema.columns 
WHERE table_name = 'schools' 
ORDER BY ordinal_position;
