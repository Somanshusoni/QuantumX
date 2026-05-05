import threading, requests

TOKEN   = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI3IiwiZXhwIjoxNzc3OTg2NjQxfQ.UILq0IvFRSaYTYKGBbVpOvJqMOep-6FN6yonQuHDp5A'
HEADERS = {'Authorization': f'Bearer {TOKEN}'}
ORDER   = {'symbol':'RELIANCE','side':'BUY',
           'order_type':'LIMIT','quantity':1,'price':4900}

results = []
def send_order():
    r = requests.post('http://127.0.0.1:8000/order',
                      json=ORDER, headers=HEADERS)
    results.append((r.status_code, r.json()))

# Launch two threads simultaneously
t1 = threading.Thread(target=send_order)
t2 = threading.Thread(target=send_order)
t1.start(); t2.start()
t1.join();  t2.join()

print(results)
# Expected: [(200, {...}), (400, {'detail': 'Insufficient fiat...'})]
