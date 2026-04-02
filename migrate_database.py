#!/usr/bin/env python3
"""
Database Migration Script
Migrate from old field names to new consistent schema

Old -> New:
- password -> password_hash
- email -> registrant_email
- Add: identity, is_admin fields
"""

import os
from supabase import create_client
from passlib.context import CryptContext

def migrate_database():
    """執行資料庫遷移"""
    
    # 連接 Supabase
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    
    if not url or not key:
        print("❌ 請設定 SUPABASE_URL 和 SUPABASE_KEY 環境變數")
        return
    
    supabase = create_client(url, key)
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    
    print("🔄 開始資料庫遷移...")
    
    try:
        # 1. 獲取所有 schools 記錄
        response = supabase.table("schools").select("*").execute()
        
        if not response.data:
            print("📭 沒有找到需要遷移的資料")
            return
        
        print(f"📊 找到 {len(response.data)} 筆記錄需要遷移")
        
        # 2. 逐筆遷移
        migrated = 0
        for record in response.data:
            updates = {}
            
            # 遷移 password -> password_hash (如果還是明文)
            if 'password' in record and 'password_hash' not in record:
                # 檢查是否已經是雜湊值 (以 $2b$ 開頭)
                if record['password'].startswith('$2b$'):
                    updates['password_hash'] = record['password']
                else:
                    # 如果是明文密碼，進行雜湊
                    updates['password_hash'] = pwd_context.hash(record['password'])
                
                # 標記要刪除舊欄位
                updates['password'] = None
            
            # 遷移 email -> registrant_email
            if 'email' in record and 'registrant_email' not in record:
                updates['registrant_email'] = record['email']
                updates['email'] = None  # 標記要刪除舊欄位
            
            # 新增預設欄位
            if 'identity' not in record:
                if record.get('is_admin', False):
                    updates['identity'] = record.get('identity', '系統管理員')
                else:
                    updates['identity'] = '學校承辦人'
            
            if 'is_admin' not in record:
                updates['is_admin'] = record.get('is_admin', False)
            
            # 執行更新
            if updates:
                supabase.table("schools").update(updates).eq("id", record['id']).execute()
                migrated += 1
                print(f"✅ 已遷移: {record['name']}")
        
        print(f"🎉 遷移完成！共處理 {migrated} 筆記錄")
        
        # 3. 驗證遷移結果
        print("\n🔍 驗證遷移結果...")
        verify_response = supabase.table("schools").select("id, name, password_hash, registrant_email, identity, is_admin").execute()
        
        for record in verify_response.data:
            missing_fields = []
            if not record.get('password_hash'):
                missing_fields.append('password_hash')
            if not record.get('registrant_email'):
                missing_fields.append('registrant_email')
            if not record.get('identity'):
                missing_fields.append('identity')
            
            if missing_fields:
                print(f"⚠️ {record['name']} 缺少欄位: {', '.join(missing_fields)}")
            else:
                print(f"✅ {record['name']} 遷移成功")
        
        print("\n🎯 遷移腳本執行完成！")
        
    except Exception as e:
        print(f"❌ 遷移失敗：{e}")

if __name__ == "__main__":
    print("🗃️ 資料庫遷移工具")
    print("=" * 40)
    print("⚠️ 請確認已備份資料庫！")
    print("⚠️ 這個操作會修改資料庫結構！")
    print()
    
    confirm = input("確定要執行遷移嗎？(yes/no): ")
    if confirm.lower() in ['yes', 'y', '是']:
        migrate_database()
    else:
        print("❌ 已取消遷移")
