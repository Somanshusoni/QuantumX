import redis

# Connect to the Matrix
r = redis.Redis(host='localhost', port=6379, decode_responses=True)

# 1. Define your exact starting prices
ipo_prices = {
    "RIL": 2500.00,
    "ICICIBANK": 1050.00,
    "HDFCBANK": 1450.00,
    "TCS": 3900.00,
    "INFY": 1500.00
    # Add any other tickers you are using here!
}

print("🏦 RESTORING EXCHANGE PRICES...")

# 2. Inject the Last Traded Price (LTP) directly into Redis
for symbol, price in ipo_prices.items():
    r.set(f"LTP:{symbol}", price)
    print(f"✅ {symbol} price restored to ₹{price}")

print("🚀 Prices restored! You can start the Swarm now.")