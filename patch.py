from database import SessionLocal
from sqlalchemy import text

db = SessionLocal()

print("🛠️ Injecting 'is_active' Ban Flag into PostgreSQL...")

try:
    # 🛡️ THE FIX: PostgreSQL requires the word TRUE, not the number 1
    db.execute(text("ALTER TABLE users ADD COLUMN is_active BOOLEAN DEFAULT TRUE;"))
    db.commit()
    print("✅ Patch successful! All users are currently ACTIVE.")
except Exception as e:
    print(f"🚨 Error: {e}")
    db.rollback()
finally:
    db.close()