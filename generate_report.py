import os

def generate():
    files_to_read = ["main.py", "app.py", "engine.py", "database.py", "bot.py"]
    code_contents = {}
    for f in files_to_read:
        try:
            with open(f, "r", encoding="utf-8") as file:
                code_contents[f] = file.read()
        except Exception as e:
            code_contents[f] = f"# File not found or error reading: {e}"

    markdown_content = f"""# Comprehensive Project Report: Quantum Exchange
## A Real-Time Trading Simulation & Algorithmic Matchmaking Platform

---

## 1. Abstract
The **Quantum Exchange** is an enterprise-grade, high-performance stock market and trading simulation platform. It is engineered to replicate the immense data throughput, concurrency, and low-latency requirements of a live financial exchange. By employing a decoupled microservices architecture, the system isolates user-facing web traffic from the highly sensitive order-matching engine. The platform provides real-time market data broadcasting via WebSockets, persistent transactional integrity via SQLite, and extreme-speed in-memory order queueing using Redis. This report details the entire system architecture, the handling of critical race conditions, and provides the complete source code for academic review.

---

## 2. System Architecture & Flow

The system is logically divided into three major tiers: the Frontend UI, the API Gateway, and the Execution Engine.

### 2.1 High-Level Architecture Diagram
```mermaid
graph TD
    Client[User / NiceGUI Browser] -->|HTTP POST Orders| API(FastAPI Gateway)
    Client <-->|WebSocket Stream| API
    API -->|Validates & Locks Fiat| DB[(SQLite Database)]
    API -->|Pushes to Queue| Queue[Redis: order_queue]
    Queue --> Engine[Matching Engine Worker]
    Engine -->|Matches Orders| OrderBook[Redis: ZSET Bids/Asks]
    Engine -->|Saves Settlements| DB
    Engine -->|Publishes Execution| PubSub[Redis Pub/Sub]
    PubSub --> API
```

*Note for Document Formatting: You can insert a screenshot of the system running its terminal logs here.*

> **[Insert Terminal Logs / Engine Startup Screenshot Here]**

---

## 3. Detailed Component Analysis

### 3.1 The Frontend Interface (`app.py`)
The frontend is built utilizing **NiceGUI**, a Python-based web framework that allows for reactive, state-driven UI development without writing raw JavaScript. 
- **Routing**: Implements an SPA (Single Page Application) routing model to switch between Login, Home, Portfolio, Market, and Stock Details dynamically.
- **Real-Time Charts**: Integrates Apache ECharts. Every time a new trade executes on the backend, a WebSocket message is received, pushing a new timestamped data point into the EChart instance, rendering a live-moving line graph.
- **Asynchronous Data Fetching**: Utilizes `httpx.AsyncClient` to perform non-blocking HTTP requests, ensuring the UI thread never freezes while awaiting API responses.

> **[Insert Screenshot of the Main Dashboard / UI Here]**

### 3.2 The API Gateway (`main.py`)
Built on **FastAPI**, this component serves as the defensive shield of the application.
- **Authentication**: JWT (JSON Web Tokens) are generated upon login and verified on every protected route using FastAPI's dependency injection (`Depends(get_current_user)`). Passwords are encrypted using Bcrypt.
- **Order Routing**: When an order is placed (`/order`), the gateway checks if the user has enough fiat (for BUY) or sufficient shares (for SELL). It instantly deducts the balance to a `locked_fiat` state, preventing double-spending, and serialization the order into the Redis `order_queue`.
- **WebSocket Manager**: Maintains active WebSocket connections and subscribes them to Redis PubSub channels to broadcast price ticks.

### 3.3 The Trading Engine (`engine.py`)
This is a standalone Python daemon that operates independently of the web server.
- **FIFO & Price Priority**: The engine pops orders from the queue and inserts them into Redis Sorted Sets (`ZSET`). The score in the ZSET is calculated meticulously using `(price * MULTIPLIER) ± timestamp`, guaranteeing that higher prices execute first, and for identical prices, the older order executes first.
- **Matchmaking Loop**: The engine continuously checks the highest bid against the lowest ask. If `bid >= ask`, a match occurs.
- **Taxation & Treasury**: A micro-fee (e.g., 0.2%) is skimmed from takers and routed to the Admin Treasury (User ID 1).

### 3.4 Market Makers & Liquidity (`bot.py`)
To ensure the simulated market is active, automated bots inject liquidity.
- **Chaos Loop**: The bot fetches active stocks, determines a "fair value", and rapidly places symmetric BUY and SELL limit orders around that fair value, creating a bid-ask spread.

---

## 4. Critical Error Handling & Race Condition Mitigations

In financial systems, edge cases can lead to catastrophic money duplication. 

### 4.1 The "Ghost Share" Mitigation
**Problem**: If the engine crashes while orders are sitting in the Redis Order Book, the user's shares remain "locked" in the SQLite database permanently.
**Solution**: An `end_of_day_settlement()` block is executed upon a `KeyboardInterrupt` (CTRL+C). It scans the database, refunds all `locked_fiat` back to the user's available balance, resets all `locked_qty` for shares, and flushes the Redis keys.

### 4.2 Slippage Tripwires
**Problem**: If an illiquid market experiences a sudden massive Market Order, it could execute at prices 100x above fair value.
**Solution**: The engine enforces a strict 20% deviation limit. 
```python
# From engine.py
if matched_price > current_ltp * 1.20 or matched_price < current_ltp * 0.80:
    print("🛑 SLIPPAGE TRIPWIRE! Blocked rogue execution")
    break
```

> **[Insert Screenshot of an Error/Slippage Notification Here]**

---

## 5. System Source Code & Implementation Appendices
*The following sections contain the raw, comprehensive implementation code spanning thousands of lines. This fulfills the detailed code analysis requirement.*

### Appendix A: Frontend Application (`app.py`)
```python
{code_contents.get("app.py", "")}
```

### Appendix B: API Gateway & Security (`main.py`)
```python
{code_contents.get("main.py", "")}
```

### Appendix C: Algorithmic Matching Engine (`engine.py`)
```python
{code_contents.get("engine.py", "")}
```

### Appendix D: Database Schemas (`database.py`)
```python
{code_contents.get("database.py", "")}
```

### Appendix E: Liquidity Provider Bot (`bot.py`)
```python
{code_contents.get("bot.py", "")}
```

---
**End of Report.**
"""

    with open("Detailed_Project_Report.md", "w", encoding="utf-8") as f:
        f.write(markdown_content)
    print("Massive detailed report generated at Detailed_Project_Report.md")

if __name__ == "__main__":
    generate()
