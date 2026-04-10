# pass:admin 
#C:\Users\soman\Downloads\Redis-x64-5.0.14.1
from fastapi import FastAPI, Depends, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy import or_
import jwt
import redis
import redis.asyncio as aioredis
import json
import bcrypt
import asyncio
import uuid
import time,os
from datetime import datetime, timedelta
from typing import Optional

from database import SessionLocal, engine, Base, User, Holding, Notification, Company

# 2. SCHEMA IMPORTS (Pydantic Models)
# Notice Company is NOT here anymore!
from schemas import UserCreate, Token, OrderTicket

# 3. WEBSOCKET MANAGER
from websocketmanager import manager


app = FastAPI()
redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)
Base.metadata.create_all(bind=engine)

# --- SECURITY UTILS ---
# --- SECURITY UTILS ---
# We upgraded to a 64-character key for maximum security
SECRET_KEY = "my_super_secret_key_which_is_very_long_and_secure_12345678901234"
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        # Convert the string back to an integer to search the database!
        user_id: int = int(payload.get("sub")) 
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired. Please log in again.")
    except jwt.PyJWTError as e:
        # This will now print the EXACT error from the PyJWT library to your screen!
        raise HTTPException(status_code=401, detail=f"Token Error: {str(e)}")
        
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User no longer exists.")
    
    return user

@app.get("/")
async def serve_ui():
    try:
        # 🛡️ THE FIX: Added encoding="utf-8" so Windows doesn't crash on emojis!
        with open("index.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(content="<h1>index.html not found!</h1>", status_code=404)

# --- 🟢 PUBLIC MARKET WATCH ---

# Route 1: List all stocks with their Live Price
@app.get("/stocks")
def get_all_stocks(db: Session = Depends(get_db)):
    companies = db.query(Company).all()
    market_watch = []
    
    for c in companies:
        # Fetch the live price from Redis (Default to 0 if it hasn't traded yet)
        live_price_str = redis_client.get(f"LTP:{c.symbol}")

        live_price = float(live_price_str) if live_price_str else 0.0
        
        market_watch.append({
            "symbol": c.symbol,
            "name": c.name,
            "live_price": live_price
        })
        
    return {"market": market_watch}

# Route 2: Get specific details for a single company
@app.get("/stocks/{cmp}")
def get_company_details(cmp: str, db: Session = Depends(get_db)):
    cmp = cmp.upper()
    company = db.query(Company).filter(Company.symbol == cmp).first()
    
    if not company:
        raise HTTPException(status_code=404, detail="Company not listed")
        
    live_price_str = redis_client.get(f"LTP:{cmp}")
    live_price = float(live_price_str) if live_price_str else 0.0
    
    return {
        "symbol": company.symbol,
        "name": company.name,
        "description": company.description,
        "fundamentals": {
            "total_shares": company.total_shares_issued,
            "market_cap": company.total_shares_issued * live_price if live_price > 0 else company.market_cap
        },
        "live_price": live_price
    }



# 🛑 PRIVATE APIs (Require Identity/Login)
# ==========================================
from database import SessionLocal # Make sure this is imported at the top!

@app.websocket("/ws/ticker")
async def ticker_websocket(websocket: WebSocket):
    await websocket.accept()
    
    # 1. Open DB manually, grab what we need, and close it immediately.
    db = SessionLocal()
    try:
        companies = [{"symbol": c.symbol, "name": c.name} for c in db.query(Company).all()]
    finally:
        db.close() # Free up the database!

    # 2. Start the infinite stream using only Redis (Super fast, no DB crashes)
    try:
        while True:
            market_data = []
            for c in companies:
                ltp = float(redis_client.get(f"LTP:{c['symbol']}") or 0.0)
                market_data.append({"symbol": c['symbol'], "name": c['name'], "live_price": ltp})
            
            await websocket.send_json({"market": market_data})
            await asyncio.sleep(0.5) 
            
    except Exception as e:
        print(f"🔌 Client Disconnected from Ticker")


@app.post("/register")
def register(user: UserCreate, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(
        or_(
            User.email == user.email,
            User.phone_number == user.phone_number,
            User.aadhaar_nu__mmber == user.aadhaar_number
        )
    ).first()

    if existing_user:
        raise HTTPException(status_code=400, detail="User already exists (Email/Phone/Aadhaar conflict).")

    new_user = User(
        email=user.email, 
        hashed_password=hash_password(user.password),
        phone_number=user.phone_number,
        aadhaar_number=user.aadhaar_number
    )
    db.add(new_user)
    db.commit()
    return {"message": "User registered! Proceed to /verify-kyc"}

@app.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == form_data.username).first()
    if not db_user or not verify_password(form_data.password, db_user.hashed_password):
        raise HTTPException(status_code=400, detail="Invalid credentials")
    
    # Wrap db_user.id in str()
    token = jwt.encode({"sub": str(db_user.id), "exp": datetime.utcnow() + timedelta(hours=2)}, SECRET_KEY, algorithm="HS256")
    #token = jwt.encode({"sub": db_user.id, "exp": datetime.utcnow() + timedelta(hours=2)}, SECRET_KEY, algorithm="HS256")
    return {"access_token": token, "token_type": "bearer"}

@app.post("/verify-kyc")
def verify_kyc(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    current_user.is_kyc_verified = True
    db.commit()
    return {"message": "✅ KYC Verified Instantly! Account unlocked."}

# --- UPGRADED PORTFOLIO ROUTE (LIVE P&L) ---
@app.get("/portfolio")
def get_portfolio(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    holdings = db.query(Holding).filter(Holding.user_id == current_user.id).all()
    notifications = db.query(Notification).filter(Notification.user_id == current_user.id).order_by(Notification.id.desc()).limit(5).all()
    
    assets = []
    total_invested = 0.0
    current_portfolio_value = 0.0

    for h in holdings:
        # 1. How much did they originally spend?
        invested = h.total_qty * h.avg_buy_price
        total_invested += invested

        # 2. Fetch the LIVE price from Redis
        live_price_str = redis_client.get(f"LTP:{h.symbol}")
        
        # If no trades have happened yet, default to what they bought it for
        live_price = float(live_price_str) if live_price_str else h.avg_buy_price

        # 3. What is it worth right now?
        current_value = h.total_qty * live_price
        current_portfolio_value += current_value

        # 4. The Magic Math (P&L)
        pnl_rupees = current_value - invested
        pnl_percentage = (pnl_rupees / invested * 100) if invested > 0 else 0.0

        assets.append({
            "symbol": h.symbol,
            "free_qty": h.total_qty,
            "locked_qty": h.locked_qty,
            "avg_buy_price": round(h.avg_buy_price, 2),
            "live_market_price": round(live_price, 2),
            "total_pnl_rupees": round(pnl_rupees, 2),
            "total_pnl_percent": round(pnl_percentage, 2)
        })

    # Total account P&L
    total_pnl = current_portfolio_value - total_invested

    return {
        "wallet": {
            "free_cash": round(current_user.fiat_balance, 2), 
            "locked_cash": round(current_user.locked_fiat, 2)
        },
        "portfolio_summary": {
            "total_invested": round(total_invested, 2),
            "current_value": round(current_portfolio_value, 2),
            "net_profit_loss": round(total_pnl, 2)
        },
        "assets": assets,
        "recent_notifications": [n.message for n in notifications]
    }


# --- 🟢 PORTFOLIO API (For the new UI) ---
@app.get("/ui/portfolio")
def get_user_portfolio(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # 1. Grab all the user's shares from the database
    user_holdings = db.query(Holding).filter(Holding.user_id == current_user.id).all()
    
    # 2. Format them exactly how the Javascript expects
    holdings_list = []
    for h in user_holdings:
        holdings_list.append({
            "symbol": h.symbol,
            "total_qty": h.total_qty,
            "locked_qty": h.locked_qty,
            "avg_buy_price": float(h.avg_buy_price) if h.avg_buy_price else 0.0
        })
        
    # 3. Ship the fiat and the shares to the frontend
    return {
        "fiat_balance": current_user.fiat_balance,
        "holdings": holdings_list
    }


@app.post("/order")
def place_order(order: OrderTicket, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not current_user.is_kyc_verified:
        raise HTTPException(status_code=403, detail="Complete your KYC before trading!")

    # 1. THE BLANK CHECK MATH
    lock_price = order.price
    
    if order.order_type == "MARKET":
        ltp_str = redis_client.get(f"LTP:{order.symbol}")
        if not ltp_str:
            raise HTTPException(status_code=400, detail="Cannot place Market order. No trade history exists yet.")
        ltp = float(ltp_str)
        
        # If BUYING at Market, lock LTP + 5% buffer. If SELLING, just use 0 (we only lock shares).
        lock_price = ltp * 1.05 if order.side == "BUY" else 0.0

    total_cost = order.quantity * lock_price

    # 2. LOCK FUNDS / SHARES
    if order.side == "BUY":
        # --- YOUR BUY LOGIC (Unchanged and Safe) ---
        if current_user.fiat_balance < total_cost:
            raise HTTPException(status_code=400, detail=f"Insufficient fiat. You need at least ₹{total_cost} for this Market/Limit order.")
        current_user.fiat_balance -= total_cost
        current_user.locked_fiat += total_cost
        
    else: 
        # --- THE UPGRADED SELL LOGIC ---
        holding = db.query(Holding).filter(Holding.user_id == current_user.id, Holding.symbol == order.symbol).first()
        
        if not holding or holding.total_qty < order.quantity:
            raise HTTPException(status_code=400, detail="Insufficient shares to sell")
            
        # The NoneType Fix!
        if holding.locked_qty is None:
            holding.locked_qty = 0
            
        # Prevent double-selling (check unlocked available shares)
        available_qty = holding.total_qty - holding.locked_qty
        if available_qty < order.quantity:
            raise HTTPException(status_code=400, detail="Shares are already locked in another pending order")
            
        # Lock the shares (DO NOT subtract from total_qty here)
        holding.locked_qty += order.quantity
        
    db.commit()

    # 3. THE INFINITY HACK & REDIS PUSH
    import uuid # Make sure this is imported at the top of your file!
    import time
    
    ticket_dict = order.model_dump()
    ticket_dict["user_id"] = current_user.id
    ticket_dict["order_id"] = str(uuid.uuid4())
    ticket_dict["timestamp"] = time.time()
    
    if order.order_type == "MARKET":
        # A Market Buyer is willing to pay INFINITY. A Market Seller is willing to accept ZERO.
        ticket_dict["price"] = 999999999.0 if order.side == "BUY" else 0.0

    redis_client.rpush("order_queue", json.dumps(ticket_dict))
    
    # Return the order_id so the frontend can use it to cancel later!
    return {"message": f"{order.order_type} Order sent to Engine.", "order_id": ticket_dict["order_id"]}


# ==========================================
# 🟢 PUBLIC APIs (Anonymous Access allowed)
# ==========================================
@app.get("/chart/{symbol}")
def get_chart_history(symbol: str):
    # Pull the entire 500-item list from Redis instantly
    raw_history = redis_client.lrange(f"CHART:{symbol}", 0, -1)
    
    times = []
    prices = []
    
    for item in raw_history:
        # Split the string "1710000000:2500.50"
        timestamp_str, price_str = item.split(":")
        
        # Convert Unix timestamp back to a readable "HH:MM:SS" format for the UI
        dt = datetime.fromtimestamp(int(timestamp_str))
        times.append(dt.strftime("%H:%M:%S"))
        prices.append(float(price_str))
        
    return {"times": times, "prices": prices}

@app.websocket("/market/{company_name}")
async def market_feed(websocket: WebSocket, company_name: str):
    # Notice: No Depends(get_current_user) here! Anyone can connect.
    company_name = company_name.upper()
    await manager.connect(websocket, company_name)
    
    async_redis = await aioredis.from_url("redis://localhost:6379", decode_responses=True)
    pubsub = async_redis.pubsub()
    await pubsub.subscribe(f"market_updates:{company_name}")
    
    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                await websocket.send_text(message["data"])
    except WebSocketDisconnect:
        manager.disconnect(websocket, company_name)

# --- 🟢 PUBLIC ORDER BOOK (READING FROM REDIS ZSETS) ---
@app.get("/orderbook/{cmp}")
def get_public_orderbook(cmp: str):
    cmp = cmp.upper()
    
    # 1. Ask Redis for all open orders instantly
    raw_bids = redis_client.zrevrange(f"bids:{cmp}", 0, -1)
    raw_asks = redis_client.zrange(f"asks:{cmp}", 0, -1)

    public_bids = {}
    public_asks = {}

    # 2. Consolidate Bids (Group by Price)
    for b in raw_bids:
        t = json.loads(b)
        public_bids[t["price"]] = public_bids.get(t["price"], 0) + t["quantity"]
        
    # 3. Consolidate Asks (Group by Price)
    for a in raw_asks:
        t = json.loads(a)
        public_asks[t["price"]] = public_asks.get(t["price"], 0) + t["quantity"]

    # 4. Sort and return the top 5 levels
    return {
        "symbol": cmp,
        "live_price": redis_client.get(f"LTP:{cmp}") or 0.0,
        "bids": [{"price": p, "total_qty": q} for p, q in sorted(public_bids.items(), reverse=True)[:5]],
        "asks": [{"price": p, "total_qty": q} for p, q in sorted(public_asks.items())[:5]]
    }

@app.get("/notifications")
def get_notifications(
    limit: int = 20, 
    days_ago: Optional[int] = None, 
    search: Optional[str] = None, 
    current_user: User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    # 1. Start the base query (Only get THIS user's notifications)
    query = db.query(Notification).filter(Notification.user_id == current_user.id)

    # 2. FILTER: Date Range
    if days_ago:
        cutoff_date = datetime.utcnow() - timedelta(days=days_ago)
        query = query.filter(Notification.created_at >= cutoff_date)

    # 3. FILTER: Search Text (e.g., search="Sold" or search="TATA")
    # ilike() makes it case-insensitive!
    if search:
        query = query.filter(Notification.message.ilike(f"%{search}%"))

    # 4. Execute the query, sort newest first, and apply the limit
    nots = query.order_by(Notification.id.desc()).limit(limit).all()
    
    return {
        "total_returned": len(nots),
        "notifications": [{"time": n.created_at, "message": n.message} for n in nots]
    }


# --- 🟢 PUBLIC ORDER BOOK (READING DIRECTLY FROM REDIS) ---
@app.get("/orderbook/{cmp}")
def get_public_orderbook(cmp: str, depth: int = 5):
    cmp = cmp.upper()
    
    # 1. Ask Redis for all open orders instantly
    # zrevrange gets Buyers (Highest price first)
    # zrange gets Sellers (Lowest price first)
    raw_bids = redis_client.zrevrange(f"bids:{cmp}", 0, -1)
    raw_asks = redis_client.zrange(f"asks:{cmp}", 0, -1)

    public_bids = {}
    public_asks = {}

    # 2. Consolidate the Bids (Group by Price)
    for b in raw_bids:
        ticket = json.loads(b)
        price = ticket["price"]
        public_bids[price] = public_bids.get(price, 0) + ticket["quantity"]
        
    # 3. Consolidate the Asks (Group by Price)
    for a in raw_asks:
        ticket = json.loads(a)
        price = ticket["price"]
        public_asks[price] = public_asks.get(price, 0) + ticket["quantity"]

    # 4. Sort and return exactly what the frontend needs
    return {
        "symbol": cmp,
        "live_price": float(redis_client.get(f"LTP:{cmp}") or 0.0),
        "bids": [{"price": p, "total_qty": q} for p, q in sorted(public_bids.items(), reverse=True)[:depth]],
        "asks": [{"price": p, "total_qty": q} for p, q in sorted(public_asks.items())[:depth]]
    }

# --- 🛠️ ADMIN ROUTE: SEED NIFTY 50 COMPANIES ---
import os

# --- 🛠️ UPGRADED ADMIN ROUTE: JSON SEEDER ---
@app.post("/admin/seed-companies")
def seed_initial_companies(db: Session = Depends(get_db)):
    file_path = "nifty50.json"
    
    # 1. Safety check: Does the file exist?
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="nifty50.json file not found in the project folder!")
        
    # 2. Open and read the JSON vault
    with open(file_path, "r") as file:
        companies_data = json.load(file)
        
    count = 0
    
    # 3. Loop through the JSON and build the Database Rows
    for comp_data in companies_data:
        existing = db.query(Company).filter(Company.symbol == comp_data["symbol"]).first()
        
        if not existing:
            new_company = Company(
                symbol=comp_data["symbol"],
                name=comp_data["name"],
                total_shares_issued=comp_data["total_shares_issued"],
                eps=comp_data["eps"],
                debt_to_equity=comp_data["debt_to_equity"],
                description=comp_data["description"]
            )
            db.add(new_company)
            count += 1
            
    db.commit()
    return {"message": f"✅ Successfully loaded {count} companies from JSON into the Exchange!"}

@app.get("/stocks/{cmp}")
def get_company_details(cmp: str, db: Session = Depends(get_db)):
    cmp = cmp.upper()
    company = db.query(Company).filter(Company.symbol == cmp).first()
    
    if not company:
        raise HTTPException(status_code=404, detail="Company not listed")
        
    # Get Live Data from Redis
    live_price = float(redis_client.get(f"LTP:{cmp}") or 0.0)
    day_high = float(redis_client.get(f"HIGH:{cmp}") or live_price)
    day_low = float(redis_client.get(f"LOW:{cmp}") or live_price)
    
    # Calculate Live P/E Ratio (LTP / Earnings Per Share)
    live_pe = round(live_price / company.eps, 2) if company.eps > 0 and live_price > 0 else 0.0
    
    return {
        "symbol": company.symbol,
        "name": company.name,
        "live_price": live_price,
        "day_high": day_high,
        "day_low": day_low,
        "fundamentals": {
            "pe_ratio": live_pe,
            "eps": company.eps,
            "debt_to_equity": company.debt_to_equity,
            "market_cap": company.total_shares_issued * live_price if live_price > 0 else company.market_cap
        }
    }



if __name__ == "__main__":
    import uvicorn
    # 🛡️ THE FIX: 0.0.0.0 opens the server to your entire Wi-Fi network!
    uvicorn.run(app, host="0.0.0.0", port=8000)