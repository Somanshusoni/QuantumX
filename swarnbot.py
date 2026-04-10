import asyncio,math
import httpx
import random
import time

API_URL = "http://127.0.0.1:8000"
NUM_BOTS = 10
BOT_PASS = "system!"
# The Global Baseline Memory
market_baselines = {}
# Create the bot profiles
bots = [{"email": f"trader{i}@exchange.com", "token": None} for i in range(1, NUM_BOTS + 1)]

async def login_bot(client, bot):
    """Logs the bot in and grabs its JWT token"""
    try:
        res = await client.post(f"{API_URL}/login", data={"username": bot["email"], "password": BOT_PASS})
        if res.status_code == 200:
            bot["token"] = res.json()["access_token"]
            print(f"🟢 {bot['email']} Online.")
        else:
            print(f"🔴 Failed to login {bot['email']}")
    except:
        pass

async def get_market(client):
    """Fetches the live prices"""
    try:
        res = await client.get(f"{API_URL}/stocks")
        return res.json().get("market", [])
    except:
        return []

async def trader_logic(bot_id, bot, client):
    """The brain of a single bot. It runs forever."""
    if not bot["token"]: return
    
    headers = {"Authorization": f"Bearer {bot['token']}"}
    name = bot["email"].split('@')[0].upper()

    while True:
        try:
            market = await get_market(client)
            if not market:
                await asyncio.sleep(20)
                continue

            # Pick a random stock to trade
            stock = random.choice(market)
            symbol = stock["symbol"]
            ltp = float(stock["live_price"])

            # If LTP is 0 (Brand new exchange), set an IPO price
            if ltp == 0.0: ltp = random.uniform(100.0, 1000.0)

            # --- THE ALGORITHM ---
           # --- THE NEW ALGORITHM (Mean Reversion) ---
           # --- THE ALGORITHM (Dynamic Mean Reversion) ---
            side = random.choice(["BUY", "SELL"])
            qty = random.randint(5, 50)
            
          # --- THE ALGORITHM (Sine Wave Market Cycles) ---
            # 1. INITIALIZE BASELINE (The Anchor)
            # --- THE ALGORITHM (High Volatility Sine Wave) ---
            # 1. INITIALIZE BASELINE
           # --- THE ALGORITHM (Dynamic High Volatility) ---
            
            # 1. INITIALIZE & ADAPT BASELINE (The Whale Fix)
            if symbol not in market_baselines:
                market_baselines[symbol] = ltp if ltp > 0 else random.uniform(100.0, 2000.0)
            else:
                # 🛡️ THE FIX: The bots "learn" the new price! 
                # If you pump the price, the baseline slowly follows you up.
                market_baselines[symbol] = (market_baselines[symbol] * 0.95) + (ltp * 0.05)
            
            # 2. THE MACRO CYCLE (Forces natural dips and peaks)
            cycle = math.sin(time.time() / 10.0 + (hash(symbol) % 100))
            
            # Fair value swings by 40% around the adapting baseline
            current_fair_value = market_baselines[symbol] * (1.0 + (cycle * 0.40))
            
            # 3. MOOD SWINGS (FOMO vs Panic)
            if cycle > 0.6:
                side = random.choices(["BUY", "SELL"], weights=[85, 15])[0] 
            elif cycle < -0.6:
                side = random.choices(["BUY", "SELL"], weights=[15, 85])[0] 
            else:
                side = random.choice(["BUY", "SELL"]) 
                
            qty = random.randint(10, 100) 
            
            # 4. CALCULATE VOLATILITY (THE SPREAD)
           # 4. CALCULATE VOLATILITY (THE SPREAD)
            gravity = (current_fair_value - ltp) * 0.20 
            variance = ltp * 0.05 
            raw_price = random.uniform(ltp - variance, ltp + variance)
            
            price = round(raw_price + gravity, 2)
            
            # 🛡️ THE FLOOR: Never go to zero
            if price < 1.0: price = 1.0
            
            # 🛡️ THE TITANIUM CEILING (NEW): Cap it at 500% so it never hits infinity!
            if price > (market_baselines[symbol] * 5.0): 
                price = round(market_baselines[symbol] * 5.0, 2)

            # Fire the Order
            payload = {"symbol": symbol, "side": side, "order_type": "LIMIT", "quantity": qty, "price": price}
            res = await client.post(f"{API_URL}/order", json=payload, headers=headers)

            # Console Output Matrix Style
            if res.status_code == 200:
                color = "\033[92m" if side == "BUY" else "\033[91m"
                price_str = "MKT" if "order_type"== "MARKET" else f"₹{price}"
                print(f"{color}[{name}] {side} {qty} {symbol} @ {price_str}\033[0m")

            # 🛡️ THE SLEEP FIX: Change 20 back to 2.0!
            await asyncio.sleep(random.uniform(0.1, 2.0))
        except Exception as e:
            await asyncio.sleep(20)

async def main():
    print("🌪️ INITIALIZING HFT SWARM...")
    async with httpx.AsyncClient() as client:
        # 1. Log all bots in simultaneously 
        login_tasks = [login_bot(client, bot) for bot in bots]
        await asyncio.gather(*login_tasks)
        
        print("\n🚀 UNLEASHING THE BOTS... PRESS CTRL+C TO STOP\n")
        
        # 2. Start all 10 infinite trading loops simultaneously
        trading_tasks = [trader_logic(i, bot, client) for i, bot in enumerate(bots)]
        await asyncio.gather(*trading_tasks)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Swarm Deactivated.")