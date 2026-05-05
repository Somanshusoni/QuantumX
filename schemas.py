from pydantic import BaseModel, Field
from typing import Literal, Optional

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
    order_type: Literal["LIMIT", "MARKET"] = "LIMIT"
    quantity: int
    price: Optional[float] = 0.0 

class DepositRequest(BaseModel):
    amount: float