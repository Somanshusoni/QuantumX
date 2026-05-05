from database import engine, Base, SessionLocal, User
import bcrypt

print("⚠️ INITIATING TOTAL DATABASE WIPE...")

# 1. Drop every single table in the database
Base.metadata.drop_all(bind=engine)
print("🗑️ All tables destroyed.")

# 2. Recreate them instantly (completely empty)
Base.metadata.create_all(bind=engine)
print("✨ Database rebuilt.")

# 3. AUTO-CREATE USER 1 (THE TREASURY / GOD ADMIN)
print("👑 Forging User 1 (The God Admin)...")

db = SessionLocal()
try:
    # Hash the default admin password
    admin_password = "admin"
    hashed_pw = bcrypt.hashpw(admin_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    # Create the God Account
    treasury_admin = User(
        email="admin@quantumx.com",
        hashed_password=hashed_pw,
        phone_number="0000000000",
        aadhaar_number="000000000000",
        is_kyc_verified=True,
        fiat_balance=10000000.0, # Give the Treasury 1 Crore starting fiat!
        is_admin=True,           # Instant Admin access (No pgAdmin needed!)
        is_active=True
    )
    
    db.add(treasury_admin)
    db.commit()
    print("✅ User 1 Created Successfully!")
    print("📧 Email: admin@quantumx.com")
    print("🔑 Passcode: admin")
except Exception as e:
    print(f"🚨 Failed to create User 1: {e}")
    db.rollback()
finally:
    db.close()

print("🚀 SYSTEM READY. Start your servers!")