from pydantic import BaseModel, Field, EmailStr
from typing import Literal,Optional

class UserCreate(BaseModel):
    email: str
    password: str
    phone_number: str = Field(..., pattern=r"^\d{10}$")
    aadhaar_number: str = Field(..., pattern=r"^\d{12}$")

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class OrderTicket(BaseModel):
    symbol: str
    side: Literal["BUY", "SELL"]
    quantity: int
    price: float

class OrderTicket(BaseModel):
    symbol: str
    side: Literal["BUY", "SELL"]
    order_type: Literal["LIMIT", "MARKET"] = "LIMIT"  # Default to Limit
    quantity: int
    price: Optional[float] = 0.0  # Optional because Market orders don't have a price!


'''from pydantic import BaseModel, Field,EmailStr
from typing import Literal

from sqlalchemy.orm import declarative_base
Base =declarative_base()
class UserCreate(BaseModel):
    email: str
    password: str
    phone_number: str = Field(..., pattern=r"^\d{10}$")
    aadhaar_number: str = Field(..., pattern=r"^\d{12}$")

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class OrderTicket(BaseModel):
    symbol: str
    side: Literal["BUY", "SELL"]
    quantity: int
    price: float

class Company(Base):
    __tablename__ = "companies"
    symbol = Column(String, primary_key=True, index=True)
    name = Column(String, unique=True)
    total_shares_issued = Column(Integer)
    market_cap = Column(Float, default=0.0)
    description = Column(String)'''