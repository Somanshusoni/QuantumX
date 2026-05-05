from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, BigInteger
from datetime import datetime

# Change password/details to match your local Postgres!
SQLALCHEMY_DATABASE_URL = "postgresql://postgres:admin@localhost:5432/exchange_db"
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

from sqlalchemy import Column, Boolean, Integer, String, Float

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    
    phone_number = Column(String, unique=True)
    aadhaar_number = Column(String, unique=True)
    is_kyc_verified = Column(Boolean, default=False)
    
    
    fiat_balance = Column(Float, default=100000.0)  
    locked_fiat = Column(Float, default=0.0)        
    
    is_admin = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)

class Trade(Base):
    __tablename__ = "trades"
    id = Column(Integer, primary_key=True, index=True)
    buyer_id = Column(Integer)
    seller_id = Column(Integer)
    symbol = Column(String)
    price = Column(Float)
    quantity = Column(Integer)
    total_value = Column(Float) # price * quantity
    timestamp = Column(DateTime, default=datetime.utcnow)
    
class Holding(Base):
    __tablename__ = "holdings"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    symbol = Column(String, index=True)
    total_qty = Column(Integer, default=0)
    locked_qty = Column(Integer, default=0)         
    avg_buy_price = Column(Float, default=0.0)

class Notification(Base):
    __tablename__ = "notifications"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    message = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

# 👇 MOVED FROM SCHEMAS.PY TO HERE 👇
class Company(Base):
    __tablename__ = "companies"
    symbol = Column(String, primary_key=True, index=True)
    name = Column(String, unique=True)
    total_shares_issued = Column(BigInteger)  # 👈 CHANGED THIS TO BigInteger
    market_cap = Column(Float, default=0.0)
    description = Column(String)
    eps = Column(Float, default=0.0) # Earnings Per Share (Needed for P/E)
    debt_to_equity = Column(Float, default=0.0)

# Tells Postgres to build all the tables above!
Base.metadata.create_all(bind=engine)

class FiatRequest(Base):
    __tablename__ = "fiat_requests"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    amount = Column(Float)
    status = Column(String, default="PENDING")


'''from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime

# Change password/details to match your local Postgres!
SQLALCHEMY_DATABASE_URL = "postgresql://postgres:admin@localhost:5432/exchange_db"
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    
    # KYC Fields
    phone_number = Column(String, unique=True)
    aadhaar_number = Column(String, unique=True)
    is_kyc_verified = Column(Boolean, default=False)
    
    # Wallet
    fiat_balance = Column(Float, default=100000.0)  
    locked_fiat = Column(Float, default=0.0)        

class Holding(Base):
    __tablename__ = "holdings"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    symbol = Column(String, index=True)
    total_qty = Column(Integer, default=0)
    locked_qty = Column(Integer, default=0)         
    avg_buy_price = Column(Float, default=0.0)

class Notification(Base):
    __tablename__ = "notifications"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    message = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(bind=engine)'''