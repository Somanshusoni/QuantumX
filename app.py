from nicegui import ui,app
import httpx
import time
from datetime import datetime
import websockets
import json
import asyncio

# --- CONFIGURATION & GLOBAL STATE ---
API_URL = "http://127.0.0.1:8000"

state = {
    "token": "",
    "current_page": "login", # SPA Routing: login, home, portfolio, market, stock_detail
    "market": [],
    "portfolio": {"fiat_balance": 0.0, "locked_fiat": 0.0, "holdings": []},
    "selected_stock": None,
    "chart_time_data": [],
    "chart_price_data": []
}

# --- THEME STRINGS (Minimalist Dark) ---
CARD_BG = "bg-[#1e293b] rounded-2xl shadow-xl border border-slate-800 p-6"
TEXT_MUTED = "text-slate-400 text-sm font-bold tracking-wider"
TEXT_PRIMARY = "text-emerald-400 font-bold"

# --- API FUNCTIONS ---
async def live_ticker_stream():
    uri = "ws://127.0.0.1:8000/ws/ticker"
    while True:
        try:
            async with websockets.connect(uri) as ws:
                print("🟢 Connected to Live Market Ticker!")
                while True:
                    # 1. Wait for data to arrive from FastAPI
                    msg = await ws.recv()
                    data = json.loads(msg)
                    
                    # 2. Update the global state
                    state["market"] = data["market"]
                    
                    # 3. ONLY redraw the exact screen the user is currently looking at!
                    if state["current_page"] == "market":
                        market_view.refresh()
                    elif state["current_page"] == "stock_detail":
                        update_chart()
                    elif state["current_page"] == "portfolio":
                        portfolio_view.refresh()
                        
        except Exception as e:
            print("🔴 Stream Disconnected. Reconnecting in 3 seconds...")
            await asyncio.sleep(3)
            
async def do_login(email, password):
    async with httpx.AsyncClient() as client:
        try:
            # Assuming you use the FastAPI form-data login
            res = await client.post(f"{API_URL}/login", data={"username": email, "password": password})
            if res.status_code == 200:
                state["token"] = res.json()["access_token"]
                ui.notify("Access Granted", type="positive")
                navigate("home")
            else:
                ui.notify("Invalid Credentials", type="negative")
        except Exception as e:
            ui.notify("Backend Offline!", type="negative")

async def fetch_data():
    if not state["token"]: return
    async with httpx.AsyncClient() as client:
        headers = {"Authorization": f"Bearer {state['token']}"}
        try:
            # Fetch Market
            m_res = await client.get(f"{API_URL}/stocks")
            if m_res.status_code == 200: state["market"] = m_res.json().get("market", [])
            
            # Fetch Portfolio
            p_res = await client.get(f"{API_URL}/ui/portfolio", headers=headers)
            if p_res.status_code == 200: state["portfolio"] = p_res.json()
            
            # Refresh the UI components
            if state["current_page"] == "portfolio": portfolio_view.refresh()
            if state["current_page"] == "market": market_view.refresh()
            if state["current_page"] == "stock_detail": update_chart()
        except: pass

# --- ROUTING LOGIC ---
def navigate(page_name):
    state["current_page"] = page_name
    main_layout.refresh()

# 1. The Instant Click Handler
def view_stock(symbol, name, live_price):
    # 1. Update the global state
    state["selected_stock"] = {"symbol": symbol, "name": name, "live_price": live_price}
    state["chart_time_data"] = []
    state["chart_price_data"] = []
    
    # 2. Tell the SPA to change the page!
    navigate("stock_detail")
    
    # 3. Tell the background worker to fetch the historical graph
    ui.timer(0, fetch_chart_history, once=True)

    
# 2. The Background Worker
async def fetch_chart_history():
    if not state["selected_stock"]: return
    symbol = state["selected_stock"]["symbol"]
    
    async with httpx.AsyncClient() as client:
        try:
            res = await client.get(f"{API_URL}/chart/{symbol}")
            if res.status_code == 200:
                data = res.json()
                state["chart_time_data"] = data["times"]
                state["chart_price_data"] = data["prices"]
                update_chart() # Push the new data into the graph!
        except Exception as e:
            print(f"Chart fetch error: {e}")

# ==========================================
# 🎨 UI COMPONENTS
# ==========================================
ui.colors(primary='#10b981', dark='#0f172a')
ui.query('body').classes('bg-[#0f172a] text-slate-200 font-sans')

# --- TOP NAVBAR ---
with ui.header().classes('w-full items-center justify-between bg-[#1e293b] border-b border-slate-800 p-4 shadow-md'):
    ui.label('⚡ QUANTUM TERMINAL').classes('text-xl font-black tracking-widest text-emerald-500 cursor-pointer').on('click', lambda: navigate("home") if state["token"] else None)
    
    # Nav Links (Only show if logged in)
    with ui.row().classes('items-center gap-6').bind_visibility_from(state, 'token', backward=bool):
        ui.button('HOME', on_click=lambda: navigate("home")).props('flat color=white').classes('font-bold')
        ui.button('PORTFOLIO', on_click=lambda: navigate("portfolio")).props('flat color=white').classes('font-bold')
        ui.button('MARKET', on_click=lambda: navigate("market")).props('flat color=white').classes('font-bold')
        
        # Notification Bell with a red dot badge
        with ui.button().props('flat round icon=notifications color=white').classes('relative'):
            ui.badge('3', color='red').props('floating')

# --- MAIN DYNAMIC CONTAINER ---
@ui.refreshable
def main_layout():
    with ui.column().classes('w-full max-w-6xl mx-auto mt-8 px-4 gap-6'):
        
        # 1️⃣ LOGIN PAGE
        if state["current_page"] == "login":
            with ui.column().classes('w-full max-w-sm mx-auto mt-20'):
                with ui.card().classes(CARD_BG):
                    ui.label('SYSTEM LOGIN').classes(TEXT_MUTED + ' mb-4 text-center w-full')
                    email = ui.input('Email').classes('w-full bg-[#0f172a]').props('dark')
                    password = ui.input('Password').classes('w-full bg-[#0f172a] mt-2').props('dark type=password')
                    ui.button('AUTHENTICATE', on_click=lambda: do_login(email.value, password.value)).classes('w-full mt-6 py-3 font-bold bg-emerald-600')

        # 2️⃣ HOME DASHBOARD
        elif state["current_page"] == "home":
            ui.label('WELCOME BACK').classes('text-3xl font-black text-white')
            with ui.row().classes('w-full gap-6'):
                with ui.card().classes(CARD_BG + ' grow cursor-pointer hover:bg-slate-800').on('click', lambda: navigate("portfolio")):
                    ui.label('WALLET BALANCE').classes(TEXT_MUTED)
                    ui.label(f"₹{state['portfolio']['fiat_balance']:,.2f}").classes('text-3xl font-bold text-emerald-400 mt-2')
                with ui.card().classes(CARD_BG + ' grow cursor-pointer hover:bg-slate-800').on('click', lambda: navigate("market")):
                    ui.label('ACTIVE MARKETS').classes(TEXT_MUTED)
                    ui.label(f"{len(state['market'])} TICKERS").classes('text-3xl font-bold text-blue-400 mt-2')

        # 3️⃣ PORTFOLIO PAGE
        elif state["current_page"] == "portfolio":
            portfolio_view()

        # 4️⃣ STOCKS / MARKET PAGE
        elif state["current_page"] == "market":
            market_view()

        # 5️⃣ STOCK DETAIL & CHART PAGE
        elif state["current_page"] == "stock_detail":
            stock_detail_view()

# --- REFRESHABLE SUB-VIEWS ---
@ui.refreshable
def portfolio_view():
    p = state["portfolio"]
    
    # Complex Math: Calculate Total Invested and Current Value
    total_invested = 0.0
    current_value = 0.0
    
    for h in p["holdings"]:
        # Find live price from market data
        live_price = next((m["live_price"] for m in state["market"] if m["symbol"] == h["symbol"]), 0.0)
        avg_price = h.get("avg_buy_price", 0.0) # Assuming backend sends this!
        qty = h["total_qty"]
        
        total_invested += (qty * avg_price)
        current_value += (qty * live_price)
        h["live_price"] = live_price # Save for table rendering
    
    pnl = current_value - total_invested
    pnl_color = "text-emerald-500" if pnl >= 0 else "text-rose-500"

    # Top Stats Row
    with ui.row().classes('w-full gap-4 mb-4'):
        with ui.card().classes(CARD_BG + ' grow'):
            ui.label('CURRENT ASSET VALUE').classes(TEXT_MUTED)
            ui.label(f"₹{current_value:,.2f}").classes('text-2xl font-bold text-white')
        with ui.card().classes(CARD_BG + ' grow'):
            ui.label('TOTAL P&L').classes(TEXT_MUTED)
            ui.label(f"₹{pnl:,.2f}").classes(f'text-2xl font-bold {pnl_color}')
        with ui.card().classes(CARD_BG + ' grow'):
            ui.label('FIAT FUNDS').classes(TEXT_MUTED)
            ui.label(f"Free: ₹{p['fiat_balance']:,.2f}").classes('font-bold text-emerald-400')
            ui.label(f"Locked: ₹{p.get('locked_fiat', 0):,.2f}").classes('text-sm text-slate-500')

    # Holdings Table
    with ui.card().classes(CARD_BG + ' w-full'):
        ui.label('ASSET HOLDINGS').classes(TEXT_MUTED + ' mb-4')
        for h in p["holdings"]:
            with ui.row().classes('w-full justify-between items-center py-3 border-b border-slate-700/50'):
                with ui.column().classes('gap-0'):
                    ui.label(h['symbol']).classes('font-bold text-lg text-white')
                    ui.label("Avg Buy: ₹" + str(h.get('avg_buy_price', 0))).classes('text-xs text-slate-400')
                ui.label(f"{h['total_qty']} Shares").classes('font-mono text-slate-300')
                ui.label(f"₹{h['live_price'] * h['total_qty']:,.2f}").classes('font-bold text-emerald-400')
@ui.refreshable
def market_view():
    with ui.card().classes(CARD_BG + ' w-full'):
        ui.label('LIVE MARKET').classes(TEXT_MUTED + ' mb-4')
        
        with ui.row().classes('w-full text-slate-500 text-xs font-bold px-2 mb-2'):
            ui.label('TICKER').classes('w-1/3')
            ui.label('COMPANY').classes('w-1/3')
            ui.label('PRICE').classes('w-1/3 text-right')

        # 🛡️ THE FIX: A helper function that permanently "traps" the stock data
        def create_clickable_row(s):
            # Notice we don't need 'lambda e:' anymore, just a clean lambda
            with ui.row().classes('w-full justify-between items-center p-3 rounded-lg hover:bg-slate-800 cursor-pointer transition-all').on('click', lambda: view_stock(s["symbol"], s["name"], s["live_price"])):
                ui.label(s['symbol']).classes('w-1/3 font-black text-lg text-white')
                ui.label(s['name']).classes('w-1/3 text-sm text-slate-400 truncate')
                ui.label(f"₹{s['live_price']:,.2f}").classes('w-1/3 font-mono font-bold text-emerald-400 text-right')

        # Generate the rows
        for stock in state["market"]:
            create_clickable_row(stock)

def stock_detail_view():
    stock = state["selected_stock"]
    
    with ui.row().classes('w-full justify-between items-end mb-4'):
        with ui.column().classes('gap-0'):
            ui.label(stock['name']).classes(TEXT_MUTED)
            ui.label(stock['symbol']).classes('text-4xl font-black text-white')
        ui.label(f"₹{stock['live_price']:,.2f}").classes('text-4xl font-mono font-bold text-emerald-400')

    with ui.row().classes('w-full gap-6 flex-wrap'):
        # 📈 THE CHART (Left Side)
        with ui.card().classes(CARD_BG + ' grow w-full lg:w-2/3 p-0 overflow-hidden'):
            global chart_ui
            chart_ui = ui.echarts({
                'backgroundColor': '#1e293b',
                'tooltip': {'trigger': 'axis'},
                'grid': {'left': '5%', 'right': '5%', 'bottom': '10%', 'top': '10%'},
                'xAxis': {'type': 'category', 'data': [], 'axisLine': {'lineStyle': {'color': '#475569'}}},
                'yAxis': {'type': 'value', 'scale': True, 'splitLine': {'lineStyle': {'color': '#334155'}}},
                'series': [{
                    'name': 'Price', 'type': 'line', 'data': [],
                    'itemStyle': {'color': '#10b981'},
                    'areaStyle': {'color': 'rgba(16, 185, 129, 0.1)'},
                    'smooth': True
                }]
            }).classes('w-full h-[400px]')

        # 📊 TECHNICAL INFO & TRADING POD (Right Side)
        with ui.column().classes('w-full lg:w-1/4 gap-4 shrink-0'):
            
            # Technical Overview
            with ui.card().classes(CARD_BG + ' w-full'):
                ui.label('TECHNICAL OVERVIEW').classes(TEXT_MUTED + ' mb-2')
                techs = {"52W High": f"₹{stock['live_price'] * 1.2:,.2f}", "Volume": "1.2M", "P/E Ratio": "24.5"}
                for key, val in techs.items():
                    with ui.row().classes('w-full justify-between py-1 border-b border-slate-700/50 last:border-0'):
                        ui.label(key).classes('text-slate-400 text-sm')
                        ui.label(val).classes('font-bold text-white text-sm')

            # ⚡ THE NEW TRADING POD
            with ui.card().classes(CARD_BG + ' w-full'):
                ui.label('INSTANT EXECUTION').classes(TEXT_MUTED + ' mb-4')
                
                # Toggles instead of dropdowns for a much cleaner mobile look
                with ui.row().classes('w-full gap-2 mb-3'):
                    side_toggle = ui.toggle(['BUY', 'SELL'], value='BUY').classes('grow bg-[#0f172a] text-white').props('dark rounded')
                    type_toggle = ui.toggle(['LIMIT', 'MARKET'], value='LIMIT').classes('grow bg-[#0f172a] text-white').props('dark rounded')

                # Inputs
                qty_input = ui.number('Quantity', value=1, format='%.0f').classes('w-full bg-[#0f172a] mb-2').props('dark')
                price_input = ui.number('Limit Price (₹)', value=stock['live_price'], format='%.2f').classes('w-full bg-[#0f172a] mb-4').props('dark')

                # MAGIC: Hide the price input instantly if they click "MARKET"
                price_input.bind_visibility_from(type_toggle, 'value', value='LIMIT')

                # API Execution Function
                async def submit_instant_trade():
                    if not qty_input.value or qty_input.value <= 0:
                        ui.notify("Invalid quantity", type="warning")
                        return

                    payload = {
                        "symbol": stock['symbol'],
                        "side": side_toggle.value,
                        "order_type": type_toggle.value,
                        "quantity": int(qty_input.value),
                        "price": float(price_input.value) if type_toggle.value == 'LIMIT' else 0.0
                    }
                    
                    async with httpx.AsyncClient() as client:
                        try:
                            res = await client.post(f"{API_URL}/order", json=payload, headers={"Authorization": f"Bearer {state['token']}"})
                            if res.status_code == 200:
                                ui.notify(f"Order Active: {res.json().get('order_id')[-6:]}", type="positive")
                                await fetch_data() # Refresh portfolio instantly!
                            else:
                                ui.notify(f"Rejected: {res.json().get('detail')}", type="negative")
                        except Exception:
                            ui.notify("Engine Disconnected", type="negative")

                # The Dynamic Execute Button
                trade_btn = ui.button('SUBMIT ORDER', on_click=submit_instant_trade).classes('w-full py-3 font-black tracking-widest rounded-xl text-white shadow-lg')
                
                # Make the button change colors based on BUY/SELL
                def update_btn_color():
                    if side_toggle.value == 'BUY':
                        trade_btn.classes(replace='bg-rose-600 bg-emerald-600 shadow-emerald-900/50')
                    else:
                        trade_btn.classes(replace='bg-emerald-600 bg-rose-600 shadow-rose-900/50')
                
                side_toggle.on('change', update_btn_color)
                update_btn_color() # Run once to set initial color


def update_chart():
    """Pushes new live data into the EChart to draw the line"""
    if state["current_page"] != "stock_detail" or not state["selected_stock"]: return
    
    # Get the latest price for the currently viewed stock
    live_price = next((m["live_price"] for m in state["market"] if m["symbol"] == state["selected_stock"]["symbol"]), state["selected_stock"]["live_price"])
    state["selected_stock"]["live_price"] = live_price # update title
    
    # Add current timestamp and price
    now = datetime.now().strftime("%H:%M:%S")
    state["chart_time_data"].append(now)
    state["chart_price_data"].append(live_price)
    
    # Keep chart from getting too crowded (Keep last 30 seconds)
    if len(state["chart_time_data"]) > 30:
        state["chart_time_data"].pop(0)
        state["chart_price_data"].pop(0)

    # Inject data into the chart
    chart_ui.options['xAxis']['data'] = state["chart_time_data"]
    chart_ui.options['series'][0]['data'] = state["chart_price_data"]
    chart_ui.update()

# --- THE HEARTBEAT ---
# Automatically fetch data every 2 seconds
# 1. Fetch only portfolio balances (Fiat/Locked Shares) quietly in the background

async def fetch_wallet_balances():
    if not state["token"]: return
    async with httpx.AsyncClient() as client:
        try:
            res = await client.get(f"{API_URL}/ui/portfolio", headers={"Authorization": f"Bearer {state['token']}"})
            if res.status_code == 200: state["portfolio"] = res.json()
        except: pass

ui.timer(3.0, fetch_wallet_balances)

# 2. 🚀 IGNITE THE WEBSOCKET STREAM ON STARTUP!
ui.timer(0, live_ticker_stream, once=True)
main_layout()
ui.run(title="Quantum Exchange", port=8080, host="0.0.0.0", dark=True)