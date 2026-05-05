import redis
from database import SessionLocal, User, Holding

# Connect to the Matrix
r = redis.Redis(host='localhost', port=6379, decode_responses=True)
db = SessionLocal()

print("🚨 INITIATING TOTAL SYSTEM WIPE 🚨")

try:
    # 1. THE REDIS NUKE (Wipes all memory)
    r.flushall()
    print("💥 Redis Matrix completely incinerated (Books, Charts, Queues cleared).")

    # 2. THE POSTGRES UNLOCK (Saves the users' money)
    users = db.query(User).filter(User.locked_fiat > 0).all()
    for user in users:
        user.fiat_balance += user.locked_fiat
        user.locked_fiat = 0
        
    holdings = db.query(Holding).filter(Holding.locked_qty > 0).all()
    for holding in holdings:
        holding.locked_qty = 0

    db.commit()
    print("🔓 Postgres Database unlocked. All trapped funds and shares refunded.")
    
except Exception as e:
    print(f"Error during nuke: {e}")
    db.rollback()
finally:
    db.close()
    print("🧹 CLEAN SLATE ACHIEVED.")