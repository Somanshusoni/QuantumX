import json
import os
from passlib.context import CryptContext

# Set up the bcrypt hasher
# 🟢 UPDATED: This tells passlib to handle long passwords correctly without crashing
pwd_context = CryptContext(
    schemes=["bcrypt"], 
    deprecated="auto",
    bcrypt__truncate_error=False  # 👈 Add this line!
)
# 🟢 1. Import all the necessary models from your database file
from database import SessionLocal, Company, User, Holding

def seed_database():
    print("⚡ QUANTUMX TREASURY SEEDER INITIATED ⚡")
    
    if not os.path.exists('company.json'):
        print("❌ Error: companies.json file not found! Make sure it's in the same folder.")
        return

    db = SessionLocal()
    
    # 🟢 2. THE GENESIS WALLET (User 1)
    admin_email = "admin@quantumx.com"
    admin_user = db.query(User).filter(User.email == admin_email).first()
    
    # If the Admin doesn't exist, create the God account
    if not admin_user:
        admin_user = User(
            email=admin_email,
            hashed_password=pwd_context.hash("BotPassword123!"), # 🟢 THIS HASHES THE PASSWORD
            is_admin=True,
            is_kyc_verified=True,
            fiat_balance=999999999.0 
        )
        db.add(admin_user)
        db.commit() # Commit immediately so Postgres assigns the 'id' (which will likely be 1)
        db.refresh(admin_user)
        print(f"👑 Genesis Admin Created! ID: {admin_user.id} | Email: {admin_email}")
    else:
        print(f"👑 Genesis Admin found. ID: {admin_user.id}")

    # 🟢 3. READ THE JSON DATA
    with open('company.json', 'r') as file:
        companies_data = json.load(file)

    added_count = 0
    skipped_count = 0

    # 🟢 4. SEED COMPANIES AND AIRDROP HOLDINGS
    for data in companies_data:
        existing_company = db.query(Company).filter(Company.symbol == data['symbol']).first()
        
        if existing_company:
            print(f"⏩ Skipped {data['symbol']} (Already in Database)")
            skipped_count += 1
        else:
            # Step A: Insert into the Company table
            new_company = Company(
                symbol=data['symbol'],
                name=data['name'],
                description=data['description'],
                market_cap=data['market_cap'],
                eps=data['eps'],
                debt_to_equity=data['debt_to_equity'],
                total_shares_issued=data['total_shares']
            )
            db.add(new_company)
            
            # Step B: Insert into the Holding table (The Airdrop)
            new_holding = Holding(
                user_id=admin_user.id,
                symbol=data['symbol'],
                total_qty=data['total_shares'], # Admin gets 100% of the supply
                locked_qty=0,
                avg_buy_price=data['base_price'] # Set the cost basis to the starting price
            )
            db.add(new_holding)
            
            print(f"✅ Minted {data['symbol']} -> {data['total_shares']} shares sent to Treasury.")
            added_count += 1

    # 🟢 5. COMMIT THE MASTER TRANSACTION
    try:
        db.commit()
        print(f"\n🚀 TREASURY SEEDING COMPLETE! Added: {added_count} | Skipped: {skipped_count}")
    except Exception as e:
        db.rollback()
        print(f"❌ Database Error during commit: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()