# Quantum Exchange

Welcome to the Quantum Exchange project! This is a real-time trading platform featuring a decoupled backend, live matchmaking, and automated trading bots.

## Features
- **Real-Time Matchmaking:** High-speed order matching engine.
- **Automated Bots:** Includes various bots (`vbot.py`, `chaos_bot.py`, `swarnbot.py`) to simulate market activity and trading strategies.
- **Web Interface:** Interactive frontend for users and administrators.
- **Decoupled Architecture:** Separation of the trading engine, database operations, and web server for scalability.

## Getting Started

### Prerequisites
1. **Python:** Make sure you have Python installed. Install the required dependencies using:
2. **Redis:** This project uses Redis for the high-speed matchmaking engine and message brokering. You must have a Redis server running locally.
   - Download Redis: [https://redis.io/download](https://redis.io/download)
   - Windows Users: You can install Redis via [WSL (Windows Subsystem for Linux)](https://redis.io/docs/install/install-redis/install-redis-on-windows/) or use a native Windows alternative like [Memurai](https://www.memurai.com/).
```bash
pip install -r req.txt
```

### Running the Application
To start the main web application, run:
```bash
python main.py
```
*(or `python app.py` depending on your primary entry point)*

To start the trading engine or bots, you can run their respective scripts in separate terminals:
```bash
python engine.py
python vbot.py
```

## Project Structure
- `main.py` / `app.py`: Main web server and routing.
- `engine.py`: The core matchmaking and trading engine.
- `database.py`: Handles connections and operations for the local `exchange.db`.
- `static/` & HTML files: Frontend templates and static assets.
- `*bot.py`: Automated trading scripts.

## Version Control
This project uses Git for version control. Be sure to check the `.gitignore` to see which files (like local databases and test scripts) are excluded from the main repository.
