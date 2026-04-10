'''import requests
import random
import time

# Let's say RIL is trading around ₹2500
TARGET_PRICE = 250000.0

def run_market_maker():
    print("Market Maker Bot Started. Flooding the exchange...")
    
    while True:
        a=random.choice([a])
        random_price = TARGET_PRICE + random.uniform(-1000, 1000)
        side = random.choice(["BUY", "SELL"])
        qty = random.randint(1,1000000)
        
        payload = {
            "symbol": a,
            "side": side,
            "order_type": "LIMIT",
            "quantity": qty,
            "price": random_price
        }
        
        # ⚠️ (You would need to log the bot in first to get a token)
        # headers = {"Authorization": f"Bearer {BOT_TOKEN}"}
        # requests.post("http://localhost:8000/order", json=payload, headers=headers)
        
        print(f"Bot Placed: {side} {qty} {a} @ ₹{random_price}")
        time.sleep(2) 

if __name__ == "__main__":
    run_market_maker()



'''
import requests
import time
import random
import argparse  # 👈 NEW: The library to read terminal flags!

# Configuration
API_URL = "http://localhost:8000" # Change to "http://api:8000" if running INSIDE Docker

def login(email, password):
    """Logs a specific bot in and returns its JWT token."""
    print(f"🤖 Authenticating {email}...")
    response = requests.post(f"{API_URL}/login", data={"username": email, "password": password})
    if response.status_code == 200:
        return response.json()["access_token"]
    else:
        print(f"❌ Login failed for {email}! Did you create the account?")
        exit()

def fetch_active_stocks():
    """Fetches the dynamic list of all companies from the Exchange."""
    print("📡 Fetching active stock list from Exchange...")
    response = requests.get(f"{API_URL}/stocks")
    
    if response.status_code != 200:
        print("❌ Failed to reach the exchange API.")
        exit()
        
    market_data = response.json()["market"]
    assets = {}
    for stock in market_data:
        symbol = stock["symbol"]
        live_price = stock["live_price"]
        
        if live_price == 0.0:
            assets[symbol] = round(random.uniform(500.0, 4000.0), 2)
        else:
            assets[symbol] = live_price
            
    print(f"📊 Downloaded {len(assets)} companies to provide liquidity for.")
    return assets

def place_order(token, symbol, side, price, qty):
    """Sends the order to your FastAPI backend."""
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "symbol": symbol,
        "side": side,
        "order_type": "LIMIT",
        "quantity": qty,
        "price": price
    }
    requests.post(f"{API_URL}/order", json=payload, headers=headers)

def run_chaos_loop(token_buy, token_sell, assets):
    """The infinite loop that provides liquidity."""
    print("📈 Injecting Two-Bot liquidity into the order books. Press Ctrl+C to stop.")
    
    while True:
        symbol = random.choice(list(assets.keys()))
        base_price = assets[symbol]
        swing = random.uniform(-5.0, 5.0)
        current_fair_value = base_price + swing
        
        bid_qty = random.randint(10, 100)
        ask_qty = random.randint(10, 100)
        
        bid_price = round(current_fair_value - random.uniform(0.5, 2.0), 2)
        ask_price = round(current_fair_value + random.uniform(0.5, 2.0), 2)
        
        # Pass the correct tokens!
        place_order(token_buy, symbol, "BUY", bid_price, bid_qty)
        place_order(token_sell, symbol, "SELL", ask_price, ask_qty)
        
        print(f"[{symbol}] MM Placed: BUY {bid_qty} @ ₹{bid_price} | SELL {ask_qty} @ ₹{ask_price}")
        assets[symbol] = current_fair_value
        time.sleep(0.5)

if __name__ == "__main__":
    # 👇 THIS IS THE NEW COMMAND-LINE PARSER BLOCK 👇
    parser = argparse.ArgumentParser(description="Wall Street Market Maker Bot")
    
    # Define the flags we expect the user to type
    parser.add_argument("--BE", required=True, help="Email of the Buyer Bot")
    parser.add_argument("--SE", required=True, help="Email of the Seller Bot")
    parser.add_argument("--BP_S", required=True, help="Password for both bots")
    parser.add_argument("--BP_B", required=True, help="Password for both bots")
        
    # Parse the terminal command
    args = parser.parse_args()
    
    print("🤖 Initializing Flag-Driven Market Makers...")
    
    # Grab the variables exactly as you typed them in the terminal
    buyer_token = login(args.BE, args.BP_B)
    seller_token = login(args.SE, args.BP_S)
    
    print("✅ Both bots authenticated successfully!")
    
    dynamic_assets = fetch_active_stocks()
    
    try:
        run_chaos_loop(buyer_token, seller_token, dynamic_assets)
    except KeyboardInterrupt:
        print("\n🛑 Market Makers deactivated.")