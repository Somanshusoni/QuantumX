import redis
import json
import sys
import time
from database import SessionLocal, Holding, User, Notification

r = redis.Redis(host='localhost', port=6379, decode_responses=True)

# --- WEBHOOK & NOTIFICATION TUNNEL ---
def notify_order_placed(user_id, side, qty, symbol, order_type, price, order_id):
    db = SessionLocal()
    try:
        display_price = "MARKET RATE" if order_type == "MARKET" else f"₹{price}"
        msg = f"{side} Order Active: {qty} {symbol} @ {display_price}"
        
        db.add(Notification(user_id=user_id, message=msg))
        db.commit()
        
        r.publish(f"notify:{user_id}", json.dumps({
            "title": "Order in Book",
            "msg": msg,
            "money": "Awaiting Match...",
            "order_id": order_id
        }))
    except Exception as e:
        db.rollback()
    finally:
        db.close()

# --- DATABASE SETTLEMENT ---
def execute_trade_in_db(buyer_id, seller_id, symbol, qty, price):
    db = SessionLocal()
    try:
        total_value = qty * price
        
        # 🟢 Update Buyer
        buyer = db.query(User).filter(User.id == buyer_id).first()
        buyer.locked_fiat -= total_value
        buyer_holding = db.query(Holding).filter(Holding.user_id == buyer_id, Holding.symbol == symbol).first()
        
        if not buyer_holding:
            db.add(Holding(user_id=buyer_id, symbol=symbol, total_qty=qty, avg_buy_price=price))
        else:
            current_avg = buyer_holding.avg_buy_price if buyer_holding.avg_buy_price is not None else 0.0
            old_cost = buyer_holding.total_qty * current_avg
            buyer_holding.total_qty += qty
            buyer_holding.avg_buy_price = (old_cost + total_value) / buyer_holding.total_qty

        # 🔴 Update Seller
        seller = db.query(User).filter(User.id == seller_id).first()
        seller.fiat_balance += total_value
        seller_holding = db.query(Holding).filter(Holding.user_id == seller_id, Holding.symbol == symbol).first()
        
        seller_holding.locked_qty -= qty
        # 🔥 CRITICAL BUG FIX 1: Subtract total_qty so the portfolio actually updates!
        seller_holding.total_qty -= qty 
        
        if seller_holding.total_qty <= 0 and seller_holding.locked_qty <= 0:
            db.delete(seller_holding)

        # Notifications
        db.add(Notification(user_id=buyer_id, message=f"Bought {qty} {symbol} @ ₹{price}"))
        db.add(Notification(user_id=seller_id, message=f"Sold {qty} {symbol} @ ₹{price}"))
        db.commit()

        # WebSockets
        r.publish(f"notify:{buyer_id}", json.dumps({"title": "Executed", "msg": f"+{qty} {symbol}", "money": f"-₹{total_value}"}))
        r.publish(f"notify:{seller_id}", json.dumps({"title": "Executed", "msg": f"-{qty} {symbol}", "money": f"+₹{total_value}"}))
        print(f"💾 Trade Settled: {qty} {symbol} @ ₹{price}")
    except Exception as e:
        print(f"🚨 DB ERROR: {e}")
        db.rollback()
    finally:
        db.close()

def get_consolidated_book(detailed_bids, detailed_asks, depth=10):
    public_bids, public_asks = {}, {}
    for t in detailed_bids:
        public_bids[t["price"]] = public_bids.get(t["price"], 0) + t["quantity"]
    for t in detailed_asks:
        public_asks[t["price"]] = public_asks.get(t["price"], 0) + t["quantity"]
        
    return {
        "bids": [[p, q] for p, q in sorted(public_bids.items(), reverse=True)[:depth]],
        "asks": [[p, q] for p, q in sorted(public_asks.items())[:depth]]
    }

def end_of_day_settlement():
    print("\n🛑 ENGINE STOPPING: Initiating End of Day Settlement...")
    db = SessionLocal()
    try:
        # Refund Fiat
        users_with_locks = db.query(User).filter(User.locked_fiat > 0).all()
        for user in users_with_locks:
            user.fiat_balance += user.locked_fiat
            user.locked_fiat = 0
            
        # 🔥 CRITICAL BUG FIX 2: Release Locked Shares to prevent "Ghost Shares"
        holdings_with_locks = db.query(Holding).filter(Holding.locked_qty > 0).all()
        for holding in holdings_with_locks:
            holding.locked_qty = 0

        db.commit()
        print("✅ Refunded locked fiat and unlocked all pending shares.")

        # Wipe Redis Book
        keys_to_delete = []
        for key in r.scan_iter("bids:*"): keys_to_delete.append(key)
        for key in r.scan_iter("asks:*"): keys_to_delete.append(key)
        keys_to_delete.append("order_queue") 
        if keys_to_delete:
            r.delete(*keys_to_delete)
    except Exception as e:
        db.rollback()
    finally:
        db.close()
        print("🔌 Engine safely powered down. Goodnight, Wall Street.")
        sys.exit(0)


# ==========================================
# 🚀 THE MAIN ENGINE LOOP
# ==========================================
if __name__ == "__main__":
    print("🚀 Enterprise ZSET Engine Started. Waiting for orders...")
    # 🔥 CRITICAL FIX 3: The FIFO Time Multiplier
    TIMESTAMP_MULTIPLIER = 1_000_000_000 
    
    try:
        while True:
            # 1. Grab the next ticket
            queue_name, order_json = r.blpop("order_queue")
            ticket = json.loads(order_json)
            symbol = ticket["symbol"]
            order_type = ticket.get("order_type", "LIMIT")

            # 2. Add order to the correct Redis ZSET with TIME PRIORITY
            if order_type == "MARKET":
                # Market orders get extreme scores to skip the line instantly
                score = float('inf') if ticket["side"] == "BUY" else float('-inf')
            else:
                if ticket["side"] == "BUY":
                    score = (ticket["price"] * TIMESTAMP_MULTIPLIER) - ticket["timestamp"]
                else:
                    score = (ticket["price"] * TIMESTAMP_MULTIPLIER) + ticket["timestamp"]
            
            key = f"bids:{symbol}" if ticket["side"] == "BUY" else f"asks:{symbol}"
            r.zadd(key, {order_json: score})
            
            notify_order_placed(
                user_id=ticket["user_id"], side=ticket["side"], qty=ticket["quantity"],
                symbol=symbol, order_type=order_type, price=ticket["price"], order_id=ticket.get("order_id", "Unknown")
            )
            
            # 3. Redis Matchmaking Loop
            while True:
                top_bids = r.zrevrange(f"bids:{symbol}", 0, 0)
                top_asks = r.zrange(f"asks:{symbol}", 0, 0)

                # 🚨 CIRCUIT BREAKER 1: BOOK IS EMPTY
                if not top_bids or not top_asks:
                    if order_type == "MARKET":
                        r.zrem(f"bids:{symbol}", order_json)
                        r.zrem(f"asks:{symbol}", order_json)
                        print(f"🛑 Liquidity Exhausted for {symbol}. Market order remainder canceled.")
                    break 

                top_buyer_str, top_seller_str = top_bids[0], top_asks[0]
                top_buyer, top_seller = json.loads(top_buyer_str), json.loads(top_seller_str)

                # Market orders bypass the price check constraint
                is_market_match = top_buyer.get("order_type") == "MARKET" or top_seller.get("order_type") == "MARKET"

                if is_market_match or (top_buyer["price"] >= top_seller["price"]):
                    
                    # MAKER/TAKER RULE
                    matched_price = top_buyer["price"] if top_buyer["timestamp"] < top_seller["timestamp"] else top_seller["price"]
                    
                    # 🚨 CIRCUIT BREAKER 2: SLIPPAGE LIMIT (Protects against Flash Crashes)
                    current_ltp_raw = r.get(f"LTP:{symbol}")
                    if current_ltp_raw and is_market_match:
                        current_ltp = float(current_ltp_raw)
                        if current_ltp > 0 and (matched_price > current_ltp * 1.20 or matched_price < current_ltp * 0.80):
                            print(f"🛑 SLIPPAGE TRIPWIRE! {symbol} slipped to ₹{matched_price}. Canceling rogue MARKET order.")
                            r.zrem(f"bids:{symbol}", order_json)
                            r.zrem(f"asks:{symbol}", order_json)
                            break
                    
                    matched_qty = min(top_buyer["quantity"], top_seller["quantity"])
                    
                    # Settle in DB & Update Chart
                    execute_trade_in_db(top_buyer["user_id"], top_seller["user_id"], symbol, matched_qty, matched_price)
                    r.set(f"LTP:{symbol}", matched_price)
                    r.rpush(f"CHART:{symbol}", f"{int(time.time())}:{matched_price}")
                    r.ltrim(f"CHART:{symbol}", -500, -1)

                    # Delete old tickets
                    r.zrem(f"bids:{symbol}", top_buyer_str)
                    r.zrem(f"asks:{symbol}", top_seller_str)

                    # Adjust quantities and re-insert if partial fill
                    top_buyer["quantity"] -= matched_qty
                    top_seller["quantity"] -= matched_qty

                    # 🚨 CIRCUIT BREAKER 3: NO RESTING MARKET ORDERS
                    if top_buyer["quantity"] > 0:
                        if top_buyer.get("order_type", "LIMIT") != "MARKET":
                            r.zadd(f"bids:{symbol}", {json.dumps(top_buyer): (top_buyer["price"] * TIMESTAMP_MULTIPLIER) - top_buyer["timestamp"]})
                        else:
                            print("🛑 Market BUY exhausted. Remainder canceled.")
                            
                    if top_seller["quantity"] > 0:
                        if top_seller.get("order_type", "LIMIT") != "MARKET":
                            r.zadd(f"asks:{symbol}", {json.dumps(top_seller): (top_seller["price"] * TIMESTAMP_MULTIPLIER) + top_seller["timestamp"]})
                        else:
                            print("🛑 Market SELL exhausted. Remainder canceled.")
                else:
                    break 

            # 4. BROADCAST & SAVE THE ORDER BOOK
            raw_bids = r.zrevrange(f"bids:{symbol}", 0, -1)
            raw_asks = r.zrange(f"asks:{symbol}", 0, -1)
            
            consolidated_book = get_consolidated_book(
                [json.loads(b) for b in raw_bids], 
                [json.loads(a) for a in raw_asks]
            )
            
            r.set(f"OB:{symbol}", json.dumps(consolidated_book))

    except KeyboardInterrupt:
        end_of_day_settlement()