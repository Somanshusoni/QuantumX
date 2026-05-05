import requests

res = requests.get("http://127.0.0.1:8000/stocks")
print("\n🕵️ RAW SERVER DATA:")
print(res.text[:500])  # Prints just the first 500 characters
print("\n")