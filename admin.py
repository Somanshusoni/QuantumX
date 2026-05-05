from fastapi import FastAPI, Depends, HTTPException, Security
from fastapi.security import OAuth2PasswordBearer, HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import or_
import uvicorn
from jose import jwt, JWTError
from database import SessionLocal, User, Trade, FiatRequest, Notification
from fastapi.staticfiles import StaticFiles
security = HTTPBearer()
SECRET_KEY = "QUANTUM_MASTER_KEY_123"
ALGORITHM = "HS256"

app = FastAPI(title="Exchange Control Panel")
app.mount("/static", StaticFiles(directory="static"), name="static")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

def get_current_admin(credentials: HTTPAuthorizationCredentials = Security(security)):
    token = credentials.credentials
    db = SessionLocal()
    try:
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            user_id = int(payload.get("sub"))
        except JWTError:
            raise HTTPException(status_code=401, detail="Token invalid")
        
        user = db.query(User).filter(User.id == user_id).first()
        if not user: raise HTTPException(status_code=401, detail="User missing")
        if not getattr(user, 'is_admin', False): raise HTTPException(status_code=403, detail="Not admin")
        return user
    finally:
        db.close()

@app.get("/")
async def serve_admin_ui():
    try:
        with open("admin.html", "r", encoding="utf-8") as f: return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(content="<h1>admin.html missing</h1>", status_code=404)

@app.get("/api/fiat-requests", dependencies=[Depends(get_current_admin)])
def get_pending_fiat_requests():
    db = SessionLocal() 
    try:
        return db.query(FiatRequest).filter(FiatRequest.status == "PENDING").all()
    finally:
        db.close()

@app.post("/api/fiat-requests/{req_id}/action", dependencies=[Depends(get_current_admin)])
def process_fiat_request(req_id: int, action: str):
    db = SessionLocal()
    try:
        fiat_req = db.query(FiatRequest).filter(FiatRequest.id == req_id).first()
        if not fiat_req or fiat_req.status != "PENDING": raise HTTPException(status_code=400, detail="Invalid")

        target_user = db.query(User).filter(User.id == fiat_req.user_id).first()
        if action == "APPROVE":
            fiat_req.status = "APPROVED"
            target_user.fiat_balance += fiat_req.amount
            db.add(Notification(user_id=target_user.id, message=f"Deposit of ₹{fiat_req.amount:.2f} APPROVED."))
        elif action == "REJECT":
            fiat_req.status = "REJECTED"
            db.add(Notification(user_id=target_user.id, message=f"Deposit of ₹{fiat_req.amount:.2f} REJECTED."))

        db.commit()
        return {"msg": f"Request {action}."}
    finally:
        db.close()

@app.get("/api/users", dependencies=[Depends(get_current_admin)])
async def get_all_users():
    db = SessionLocal()
    try:
        users = db.query(User).all()
        return [{"id": u.id, "email": u.email, "fiat_balance": u.fiat_balance, "is_active": getattr(u, 'is_active', True)} for u in users]
    finally:
        db.close()

@app.post("/api/users/{user_id}/toggle-ban", dependencies=[Depends(get_current_admin)])
async def toggle_user_ban(user_id: int):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user: raise HTTPException(status_code=404, detail="User not found")
        user.is_active = not getattr(user, 'is_active', True)
        db.commit()
        return {"msg": "Success"}
    finally:
        db.close()

@app.post("/fiat", dependencies=[Depends(get_current_admin)])
async def admin_inject_fiat(payload: dict):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == payload["user_id"]).first()
        user.fiat_balance += payload["amount"]
        db.commit()
        return {"msg": "Success"}
    finally:
        db.close()

@app.get("/api/trades", dependencies=[Depends(get_current_admin)])
async def get_global_trades():
    db = SessionLocal()
    try:
        return db.query(Trade).order_by(Trade.timestamp.desc()).limit(200).all()
    finally:
        db.close()

@app.get("/api/users/{user_id}/trades", dependencies=[Depends(get_current_admin)])
async def get_user_trades(user_id: int):
    db = SessionLocal()
    try:
        return db.query(Trade).filter(or_(Trade.buyer_id == user_id, Trade.seller_id == user_id)).order_by(Trade.timestamp.desc()).all()
    finally:
        db.close()

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8001)