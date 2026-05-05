import requests
import time
import random
import math
import threading

# 🟢 CONFIGURATION
API_BASE_URL = "http://127.0.0.1:8000"
NUM_BOTS = 15
TRADE_DELAY = 3

# 🟢 ENDPOINTS
ENDPOINTS = {
    "register": f"{API_BASE_URL}/register",
    "login": f"{API_BASE_URL}/login",
    "trade": f"{API_BASE_URL}/order",
    "stocks": f"{API_BASE_URL}/stocks" 
}

class TradingBot:
    def __init__(self, bot_id):
        self.bot_id = bot_id
        self.session = requests.Session()
        self.email = f"quantum_bot_{bot_id}@exchange.com"
        self.password = "BotPassword123!"
        self.token = None
        self.symbols = []
        self.stock_data = {}
        self.time_step = 0

    def boot_sequence(self):
        print(f"🤖 [Bot-{self.bot_id}] Initiating boot sequence...")
        reg_data = {
            "email": self.email,
            "password": self.password,
            "phone_number": f"999000000{self.bot_id}",
            "aadhaar_number": f"12345678000{self.bot_id}"
        }
        
        try:
            res = self.session.post(ENDPOINTS["register"], json=reg_data)
            if res.status_code == 200:
                print(f"✅ [Bot-{self.bot_id}] Registered new account: {self.email}")
        except Exception:
            pass 

        login_data = {"username": self.email, "password": self.password}
        try:
            res = self.session.post(ENDPOINTS["login"], data=login_data)
            if res.status_code == 200:
                self.token = res.json().get("access_token")
                self.session.headers.update({"Authorization": f"Bearer {self.token}"})
                print(f"🔓 [Bot-{self.bot_id}] Logged in successfully.")
                return True
            else:
                print(f"❌ [Bot-{self.bot_id}] Login failed!")
                return False
        except Exception as e:
            print(f"❌ [Bot-{self.bot_id}] Server not reachable: {e}")
            return False

    def fetch_symbols(self):
        """Pulls pure live market data using the exact 'live_price' key from your DB"""
        self.stock_data = {} 
        try:
            res = self.session.get(ENDPOINTS["stocks"])
            if res.status_code == 200:
                api_response = res.json()
                stock_list = []

                if isinstance(api_response, dict):
                    for key, value in api_response.items():
                        if isinstance(value, list):
                            stock_list = value
                            break
                elif isinstance(api_response, list):
                    stock_list = api_response
                
                self.symbols = []
                for stock in stock_list:
                    if isinstance(stock, dict):
                        symbol = stock.get("symbol")
                        
                        if symbol and str(symbol).lower() != "market":
                            # 🟢 THE SMOKING GUN FIX: Grab the exact key your DB uses!
                            # If it's missing, default to 0.0 so math doesn't crash
                            db_price = stock.get("live_price", 0.0)
                            
                            self.symbols.append(symbol)
                            self.stock_data[symbol] = {
                                "current": float(db_price)
                            }
        except Exception as e:
            pass

    def start_trading(self):
        print(f"📈 [Bot-{self.bot_id}] Swarm agent active. Entering Free Market mode.")
        
        while True:
            self.fetch_symbols()
            
            if not self.symbols:
                time.sleep(2)
                continue

            self.time_step += 1
            symbol = random.choice(self.symbols)
            
            momentum = math.sin(self.time_step / 10.0) 
            action = "BUY" if momentum > 0 and random.random() < 0.7 else "SELL"
            quantity = random.randint(1,5)
            
            stock_info = self.stock_data.get(symbol, {"current": 0.0})
            db_price = stock_info["current"]

            trade_payload = {
                "symbol": symbol,
                "side": action,
                "quantity": quantity
            }

            # 🟢 THE DECISION ENGINE
            if db_price == 0.0:
                # Cold Start for Zero-Priced Stocks (Like TCS in your DB dump)
                trade_payload["order_type"] = "LIMIT"
                # Keep it above 0 so the backend doesn't reject it for being negative
                trade_payload["price"] = round(random.uniform(1.0, 5.0), 2)
            else:
                # Free Market Mode (Like RELIANCE which is at 2500)
                chosen_type = random.choice(["MARKET", "LIMIT"])
                trade_payload["order_type"] = chosen_type
                if chosen_type == "LIMIT":
                    variation = random.uniform(-10.0, 10.0)
                    target_price = round(db_price + variation, 2)
                    # Don't let variations push prices below 1
                    trade_payload["price"] = max(1.0, target_price)

            # 🚨 🟢 THE RAW EXECUTION DUMP 🟢 🚨
            try:
                res = self.session.post(ENDPOINTS["trade"], json=trade_payload)
                
                if res.status_code == 200:
                    print(f"✅ [Bot-{self.bot_id}] SUCCESS | {action} {quantity}x {symbol} @ {trade_payload.get('price', 'MARKET')}")
                else:
                    print(f"❌ [Bot-{self.bot_id}] SERVER REJECTED")
                    print(f"   ↳ SERVER REPLIED: {res.text}")
                    print(f"   ↳ BOT REQUESTED:  {trade_payload}")
                    print("-" * 70)
                    
            except Exception as e:
                print(f"⚠️ [Bot-{self.bot_id}] Connection Failed: {e}")

            time.sleep(TRADE_DELAY + random.uniform(0.1, 1.5))

def launch_swarm():
    print("🚀 INITIALIZING QUANTUMX BOT SWARM...")
    bots = [TradingBot(i) for i in range(1, NUM_BOTS + 1)]
    
    active_bots = []
    for bot in bots:
        if bot.boot_sequence():
            active_bots.append(bot)
            
    print(f"\n🔥 SWARM ONLINE: {len(active_bots)} Agents Ready.\n")
    
    threads = []
    for bot in active_bots:
        t = threading.Thread(target=bot.start_trading)
        t.daemon = True
        t.start()
        threads.append(t)

    try:
        while True:
            time.sleep(1) 
    except KeyboardInterrupt:
        print("\n🛑 SWARM SHUTDOWN INITIATED.")

if __name__ == "__main__":
    launch_swarm()