from fastapi import FastAPI, Depends, HTTPException, WebSocket, WebSocketDisconnect, Security
from fastapi.responses import HTMLResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm, HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from sqlalchemy import or_
from jose import jwt, JWTError
import redis
import redis.asyncio as aioredis
import json
import bcrypt
import asyncio
import uuid
import time, os
from datetime import datetime, timedelta
from typing import Optional
from fastapi.staticfiles import StaticFiles
from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from database import SessionLocal, engine, Base, User, Holding, Notification, Company, FiatRequest
from schemas import UserCreate, Token, OrderTicket, DepositRequest
from websocketmanager import manager

security = HTTPBearer()
app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)
Base.metadata.create_all(bind=engine)

SECRET_KEY = "QUANTUM_MASTER_KEY_123" # Must be a hardcoded string!
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1440 # 24 hours

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

# 🟢 THE BULLETPROOF TOKEN GENERATOR
def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    print(f"✅ TOKEN GENERATED: {encoded_jwt[:15]}...") 
    return encoded_jwt

# 🟢 THE DIAGNOSTIC USER VALIDATOR
def get_current_user(credentials: HTTPAuthorizationCredentials = Security(security), db: Session = Depends(get_db)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token structure")
        user_id = int(user_id)
    except JWTError as e:
        raise HTTPException(status_code=401, detail=f"JWT Error: {e}")
        
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
        
    if getattr(user, 'is_active', None) is False:
        raise HTTPException(status_code=403, detail="Banned")
        
    return user

# ==========================================
# 🟢 UI ROUTES
# ==========================================
@app.get("/")
async def serve_gateway():
    with open("auth.html", "r", encoding="utf-8") as f: return HTMLResponse(content=f.read())

@app.get("/exchange")
async def serve_exchange():
    with open("index.html", "r", encoding="utf-8") as f: return HTMLResponse(content=f.read())

@app.get("/about")
async def serve_about_page():
    with open("about.html", "r", encoding="utf-8") as f: return HTMLResponse(content=f.read())

# ==========================================
# 🟢 AUTH & ACCOUNT ROUTES
# ==========================================
@app.post("/register")
def register(user: UserCreate, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(
        or_(
            User.email == user.email,
            User.phone_number == user.phone_number,
            User.aadhaar_number == user.aadhaar_number
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

@app.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    
    # 🛡️ THE SHIELD: Stop massive passwords before they crash the algorithm!
    if len(form_data.password) > 72:
        raise HTTPException(status_code=400, detail="Incorrect email or passcode")

    user = db.query(User).filter(User.email == form_data.username).first()
    
    # Check if user exists and password matches
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect email or passcode")
        
    if getattr(user, 'is_active', None) is False:
         raise HTTPException(status_code=403, detail="Account is banned. Contact Admin.")

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={"sub": str(user.id)}, expires_delta=access_token_expires)
    
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/verify-kyc")
def verify_kyc(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    current_user.is_kyc_verified = True
    db.commit()
    return {"message": "✅ KYC Verified Instantly! Account unlocked."}

@app.post("/deposit")
async def request_fiat_deposit(req: DepositRequest, user = Depends(get_current_user), db: Session = Depends(get_db)):
    if req.amount <= 0 or req.amount > 10000000:
        raise HTTPException(status_code=400, detail="Invalid amount.")
        
    new_request = FiatRequest(user_id=user.id, amount=req.amount, status="PENDING")
    db.add(new_request)
    db.commit()
    return {"msg": "Request sent to Admin for approval."}

# ==========================================
# 🟢 MARKET & PORTFOLIO ROUTES
# ==========================================
@app.get("/stocks")
def get_all_stocks(db: Session = Depends(get_db)):
    companies = db.query(Company).all()
    market_watch = []
    for c in companies:
        live_price_str = redis_client.get(f"LTP:{c.symbol}")
        live_price = float(live_price_str) if live_price_str else 0.0
        market_watch.append({"symbol": c.symbol, "name": c.name, "live_price": live_price})
    return {"market": market_watch}

@app.get("/stocks/{cmp}")
def get_company_details(cmp: str, db: Session = Depends(get_db)):
    cmp = cmp.upper()
    company = db.query(Company).filter(Company.symbol == cmp).first()
    if not company: raise HTTPException(status_code=404, detail="Company not listed")
        
    live_price = float(redis_client.get(f"LTP:{cmp}") or 0.0)
    day_high = float(redis_client.get(f"HIGH:{cmp}") or live_price)
    day_low = float(redis_client.get(f"LOW:{cmp}") or live_price)
    live_pe = round(live_price / company.eps, 2) if company.eps > 0 and live_price > 0 else 0.0
    
    return {
        "symbol": company.symbol, "name": company.name, "live_price": live_price,
        "day_high": day_high, "day_low": day_low,
        "fundamentals": { "pe_ratio": live_pe, "eps": company.eps, "debt_to_equity": company.debt_to_equity, "market_cap": company.total_shares_issued * live_price if live_price > 0 else company.market_cap }
    }

@app.get("/ui/portfolio")
def get_user_portfolio(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    user_holdings = db.query(Holding).filter(Holding.user_id == current_user.id).all()
    holdings_list = []
    for h in user_holdings:
        holdings_list.append({
            "symbol": h.symbol, "total_qty": h.total_qty, "locked_qty": h.locked_qty, "avg_buy_price": float(h.avg_buy_price) if h.avg_buy_price else 0.0
        })
    return {"fiat_balance": current_user.fiat_balance, "holdings": holdings_list}

@app.get("/notifications")
def get_notifications(
    limit: int = 50, 
    days_ago: Optional[int] = None, 
    search: Optional[str] = None, 
    current_user: User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    # Base query for this specific user
    query = db.query(Notification).filter(Notification.user_id == current_user.id)

    # Apply Filters if the frontend requests them
    if days_ago:
        cutoff_date = datetime.utcnow() - timedelta(days=days_ago)
        query = query.filter(Notification.created_at >= cutoff_date)
    if search:
        query = query.filter(Notification.message.ilike(f"%{search}%"))

    nots = query.order_by(Notification.id.desc()).limit(limit).all()
    
    return [
        {"id": n.id, "message": n.message, "time": getattr(n, 'created_at', getattr(n, 'timestamp', None))} 
        for n in nots
    ]

# ==========================================
# 🟢 ORDER ENGINE ROUTES
# ==========================================
@app.post("/order")
def place_order(order: OrderTicket, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # 🚨 1. THE SECURITY LOCK: Block fake stocks like "asianpainz" immediately
    stock_exists = db.query(Company).filter(Company.symbol == order.symbol).first()
    if not stock_exists:
        raise HTTPException(status_code=400, detail=f"Invalid Order: '{order.symbol}' does not exist on this exchange.")

    # 🟢 Your existing validations
    if order.quantity <= 0: raise HTTPException(status_code=400, detail="Quantity must be greater than zero.")
    if order.price < 0: raise HTTPException(status_code=400, detail="Price cannot be negative.")
    if not current_user.is_kyc_verified: raise HTTPException(status_code=403, detail="Complete your KYC before trading!")

    lock_price = order.price
    if order.order_type == "MARKET":
        ltp_str = redis_client.get(f"LTP:{order.symbol}")
        if not ltp_str: raise HTTPException(status_code=400, detail="Cannot place Market order. No trade history exists yet.")
        lock_price = float(ltp_str) * 1.05 if order.side == "BUY" else 0.0

    total_cost = order.quantity * lock_price

    if order.side == "BUY":
        if current_user.fiat_balance < total_cost:
            raise HTTPException(status_code=400, detail=f"Insufficient fiat. You need at least ₹{total_cost} for this order.")
        current_user.fiat_balance -= total_cost
        current_user.locked_fiat += total_cost
    else: 
        holding = db.query(Holding).filter(Holding.user_id == current_user.id, Holding.symbol == order.symbol).first()
        if not holding or holding.total_qty < order.quantity: raise HTTPException(status_code=400, detail="Insufficient shares to sell")
        if holding.locked_qty is None: holding.locked_qty = 0
            
        available_qty = holding.total_qty - holding.locked_qty
        if available_qty < order.quantity: raise HTTPException(status_code=400, detail="Shares are already locked in another pending order")
        holding.locked_qty += order.quantity
        
    db.commit()
    
    ticket_dict = order.model_dump()
    ticket_dict["user_id"] = current_user.id
    ticket_dict["order_id"] = str(uuid.uuid4())
    ticket_dict["timestamp"] = time.time()
    
    if order.order_type == "MARKET":
        ticket_dict["price"] = 999999999.0 if order.side == "BUY" else 0.0

    redis_client.rpush("order_queue", json.dumps(ticket_dict))
    return {"message": f"{order.order_type} Order sent to Engine.", "order_id": ticket_dict["order_id"]}

@app.delete("/order/{order_id}")
def cancel_order(order_id: str, symbol: str, side: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    pass # Add your cancellation logic if you have it!

@app.get("/chart/{symbol}")
def get_chart_history(symbol: str):
    raw_history = redis_client.lrange(f"CHART:{symbol}", 0, -1)
    times = []
    prices = []
    for item in raw_history:
        timestamp_str, price_str = item.split(":")
        dt = datetime.fromtimestamp(int(timestamp_str))
        times.append(dt.strftime("%H:%M:%S"))
        prices.append(float(price_str))
    return {"times": times, "prices": prices}

@app.get("/orderbook/{cmp}")
def get_public_orderbook(cmp: str, depth: int = 5):
    cmp = cmp.upper()
    raw_bids = redis_client.zrevrange(f"bids:{cmp}", 0, -1)
    raw_asks = redis_client.zrange(f"asks:{cmp}", 0, -1)

    public_bids = {}
    public_asks = {}

    for b in raw_bids:
        ticket = json.loads(b)
        price = ticket["price"]
        public_bids[price] = public_bids.get(price, 0) + ticket["quantity"]
        
    for a in raw_asks:
        ticket = json.loads(a)
        price = ticket["price"]
        public_asks[price] = public_asks.get(price, 0) + ticket["quantity"]

    return {
        "symbol": cmp,
        "live_price": float(redis_client.get(f"LTP:{cmp}") or 0.0),
        "bids": [{"price": p, "total_qty": q} for p, q in sorted(public_bids.items(), reverse=True)[:depth]],
        "asks": [{"price": p, "total_qty": q} for p, q in sorted(public_asks.items())[:depth]]
    }

# ==========================================
# 🟢 ADMIN SEEDING ROUTE
# ==========================================
@app.post("/admin/seed-companies")
def seed_initial_companies(db: Session = Depends(get_db)):
    file_path = "nifty50.json"
    if not os.path.exists(file_path): raise HTTPException(status_code=404, detail="nifty50.json file not found!")
        
    with open(file_path, "r") as file: companies_data = json.load(file)
        
    count = 0
    for comp_data in companies_data:
        existing = db.query(Company).filter(Company.symbol == comp_data["symbol"]).first()
        if not existing:
            new_company = Company(
                symbol=comp_data["symbol"], name=comp_data["name"], total_shares_issued=comp_data["total_shares_issued"],
                eps=comp_data["eps"], debt_to_equity=comp_data["debt_to_equity"], description=comp_data["description"]
            )
            db.add(new_company)
            count += 1
            
    db.commit()
    return {"message": f"✅ Successfully loaded {count} companies!"}

# ==========================================
# 🟢 WEBSOCKET ROUTES
# ==========================================
@app.websocket("/ws/ticker")
async def ticker_websocket(websocket: WebSocket):
    await websocket.accept()
    db = SessionLocal()
    try:
        companies = [{"symbol": c.symbol, "name": c.name} for c in db.query(Company).all()]
    finally:
        db.close()

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

@app.websocket("/market/{company_name}")
async def market_feed(websocket: WebSocket, company_name: str):
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

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    try:
        # Grab the exact field that is missing (e.g., 'quantity')
        missing_field = exc.errors()[0].get("loc")[-1]
        # Grab the error reason (e.g., 'field required')
        error_msg = exc.errors()[0].get("msg")
        
        clean_message = f"Missing or invalid input: '{missing_field}' ({error_msg})"
    except:
        clean_message = "Invalid input provided."

    # Send it back to the mobile app as a simple string exactly like your custom errors!
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": clean_message},
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)