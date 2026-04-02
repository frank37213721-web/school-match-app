#!/usr/bin/env python3
"""
Generate bcrypt password hash for admin credentials
Usage: python generate_admin_hash.py [password]
"""

from passlib.context import CryptContext

def generate_hash(password: str) -> str:
    """Generate bcrypt hash for given password"""
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    return pwd_context.hash(password)

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        password = sys.argv[1]
    else:
        password = input("Enter password to hash: ")
    
    hash_result = generate_hash(password)
    print(f"Password: {password}")
    print(f"Hash: {hash_result}")
    print("\nAdd this to your secrets.toml:")
    print(f'[ADMIN_PASSWORD_HASH]\nvalue = "{hash_result}"')
