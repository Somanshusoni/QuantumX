# Quantum Exchange - Real-Time Trading Simulation Platform
## Project Report

### 1. Abstract
The **Quantum Exchange** is a high-performance, real-time stock market and trading simulation platform. Designed to replicate the intricacies of a live financial exchange, the system provides users with real-time market data, portfolio management, instant order execution, and an algorithmic matchmaking engine. By leveraging modern web technologies and a decoupled backend architecture, the project serves as a comprehensive study in building robust, low-latency financial applications.

### 2. Introduction
Financial exchanges require high-throughput, low-latency systems capable of processing thousands of orders simultaneously without data races or integrity issues. The objective of this project was to develop a full-stack trading platform that simulates a live stock market. It includes real-time charting, order book management, limit and market order execution, and comprehensive user portfolio tracking. The project demonstrates advanced concepts in system architecture, including Publisher/Subscriber models, WebSockets, and in-memory data caching.

### 3. Technology Stack
The platform is built using a modern, scalable technology stack:
- **Frontend**: NiceGUI (Python-based framework) combined with Tailwind CSS for a minimalist, responsive, and dark-themed UI. ECharts is utilized for rendering real-time financial charts.
- **Backend**: FastAPI (Python), providing asynchronous API endpoints and WebSocket management for live ticker feeds.
- **Database**: SQLite with SQLAlchemy ORM for persistent data storage (Users, Holdings, Trades, and KYC details).
- **In-Memory Cache & Message Broker**: Redis, serving as the core engine for order queuing, order book management (using Sorted Sets), and Pub/Sub notifications.
- **Authentication**: JWT (JSON Web Tokens) with Bcrypt password hashing.

### 4. System Architecture
The architecture follows a microservices-inspired design, decoupling the user-facing APIs from the order execution engine:
- **API Gateway (FastAPI)**: Handles user authentication, KYC verification, portfolio queries, and accepts incoming trading orders. Orders are pushed to a Redis queue rather than executed synchronously.
- **Order Engine (`engine.py`)**: A continuous background worker that consumes the Redis order queue. It utilizes Redis Sorted Sets (ZSET) to maintain time-price priority for the Order Book. It matches buyers and sellers, calculates maker/taker fees, updates user portfolios in the SQL database, and triggers WebSocket notifications.
- **WebSocket Manager**: Broadcasts live price updates and trade notifications directly to connected frontend clients, ensuring zero-latency UI updates.

### 5. Key Features
- **Real-Time Market Data**: Live ticker and candlestick charts powered by WebSockets and ECharts.
- **Advanced Order Types**: Support for both Limit Orders (price-specific) and Market Orders (instant execution at current liquidity).
- **Order Matching Engine**: A FIFO (First-In, First-Out) time-priority matching algorithm that prevents slippage and calculates trading fees.
- **Portfolio & Wallet Management**: Tracks fiat balances, locked fiat for pending orders, and exact stock holdings with average buy prices.
- **Automated Market Makers (Bots)**: Integration of trading bots (`chaos_bot`, `swarnbot`, `vbot`) to simulate market liquidity and dynamic price movements.
- **Security & KYC**: Enforced KYC checks before trading, bcrypt password hashing, and JWT-based session management.

### 6. Implementation Details
#### 6.1 Order Execution Flow
1. A user submits an order via the NiceGUI frontend.
2. FastAPI validates user balances (fiat or stock) and locks the necessary assets.
3. The order ticket is serialized and pushed to a Redis `order_queue`.
4. The Matching Engine pops the order, assigns a time-priority score, and adds it to the Order Book (Redis ZSET).
5. The engine continuously cross-references the top bids and asks. If a match is found, it calculates the settlement, records the trade in SQLite, and publishes an execution event.

#### 6.2 Slippage and Ghost Order Protection
The engine includes specific tripwires to prevent "flash crashes." If a matched price deviates more than 20% from the Last Traded Price (LTP), a slippage tripwire blocks the execution. Additionally, an End-of-Day settlement script refunds any locked fiat or ghost shares if the engine shuts down.

### 7. Conclusion
The Quantum Exchange successfully demonstrates the complexities of financial technology engineering. By utilizing Redis for high-speed order matching and WebSockets for real-time data delivery, the platform achieves the performance characteristics required of modern trading systems. The project provides a solid foundation for further enhancements, such as options trading, margin accounts, and advanced algorithmic market predictors.
