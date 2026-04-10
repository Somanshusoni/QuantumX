import requests
import time
import random

API_URL = "http://localhost:8000"

# The 3 Instances
BOTS = [
    {"email": "chaos1@exchange.com", "pass": "bot123", "token": None},
    {"email": "chaos2@exchange.com", "pass": "bot123", "token": None},
    {"email": "chaos3@exchange.com", "pass": "bot123", "token": None}
]

def authenticate_bots():
    """Logs all 3 bots in and saves their JWT tokens"""
    print("🔐 Authenticating Chaos Bots...")
    for bot in BOTS:
        res = requests.post(f"{API_URL}/login", data={"username": bot["email"], "password": bot["pass"]})
        if res.status_code == 200:
            bot["token"] = res.json()["access_token"]
            print(f"✅ {bot['email']} Online.")
        else:
            print(f"🚨 Failed to login {bot['email']}. Did you register them?")

def get_market_data():
    """Fetches the latest prices so the bots know what to trade"""
    try:
        res = requests.get(f"{API_URL}/stocks")
        return res.json().get("market", [])
    except:
        return []

def unleash_chaos():
    authenticate_bots()
    
    # Ensure at least one bot logged in
    active_bots = [b for b in BOTS if b["token"] is not None]
    if not active_bots:
        print("🛑 No bots authenticated. Exiting.")
        return

    print("\n🌪️ UNLEASHING THE CHAOS... Press Ctrl+C to stop.\n")

    while True:
        try:
            # 1. Pick a random bot
            bot = random.choice(active_bots)
            
            # 2. Get live market data and pick a random stock
            market = get_market_data()
            if not market:
                time.sleep(2)
                continue
                
            stock = random.choice(market)
            symbol = stock["symbol"]
            ltp = float(stock["live_price"])

            # Skip if the stock hasn't IPO'd yet (Needs Market Maker to establish price first)
            if ltp == 0.0:
                continue

            # 3. The Random Brain (The Logic)
            side = random.choice(["BUY", "SELL"])
            qty = random.randint(1, 50) # Small random quantities
            
            # 80% chance of LIMIT order, 20% chance of MARKET order
            order_type = "MARKET" if random.random() < 0.20 else "LIMIT"
            
            price = 0.0
            if order_type == "LIMIT":
                # Pick a random price within 2% of the LTP to ensure it stays relevant
                variance = ltp * 0.02
                price = round(random.uniform(ltp - variance, ltp + variance), 2)

            # 4. Fire the Order!
            headers = {"Authorization": f"Bearer {bot['token']}", "Content-Type": "application/json"}
            payload = {
                "symbol": symbol,
                "side": side,
                "order_type": order_type,
                "quantity": qty,
                "price": price
            }
            
            res = requests.post(f"{API_URL}/order", json=payload, headers=headers)
            
            if res.status_code == 200:
                price_str = "MKT" if order_type == "MARKET" else f"₹{price}"
                print(f"💥 {bot['email'].split('@')[0]} -> {side} {qty} {symbol} @ {price_str}")
            elif res.status_code == 400:
                # This is normal! It means the bot ran out of money or shares.
                print(f"🚫 {bot['email'].split('@')[0]} blocked: {res.json()['detail']}")

            # 5. Sleep for a random interval (0.5 to 3 seconds) to simulate real human clicking
            time.sleep(random.uniform(0.5, 3.0))

        except Exception as e:
            print(f"⚠️ Chaos Loop Error: {e}")
            time.sleep(2)

if __name__ == "__main__":
    unleash_chaos()