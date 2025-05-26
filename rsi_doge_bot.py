
import os
import time
import requests
import hmac
import hashlib
import json

# === KONFIGURATION ===
SYMBOL = "DOGEUSDT"
COIN = "DOGE"
USDT_EINSATZ = 10
CHECK_INTERVAL = 60  # 1 Minute

BASE_URL = "https://api.bybit.com"

# === ENV Variablen ===
API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

has_open_position = False

# === Signatur für Bybit Unified V5 ===
def create_signature(payload):
    return hmac.new(API_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()

# === Telegram Nachricht senden ===
def send_telegram(text):
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            data={"chat_id": TELEGRAM_CHAT_ID, "text": text},
        )
    except Exception as e:
        print("Telegram Fehler:", e)

# === Preis abfragen ===
def get_price():
    r = requests.get(f"{BASE_URL}/v5/market/tickers", params={"category": "spot", "symbol": SYMBOL})
    return float(r.json()["result"]["list"][0]["lastPrice"])

# === Wallet-Balance ===
def get_balance(coin):
    ts = str(int(time.time() * 1000))
    query = f"accountType=UNIFIED&coin={coin}&timestamp={ts}"
    sign = create_signature(query)
    headers = {
        "X-BAPI-API-KEY": API_KEY,
        "X-BAPI-TIMESTAMP": ts,
        "X-BAPI-SIGN": sign
    }
    url = f"{BASE_URL}/v5/account/wallet-balance?{query}"
    r = requests.get(url, headers=headers)
    try:
        coins = r.json()["result"]["list"][0]["coin"]
        for c in coins:
            if c["coin"] == coin:
                return float(c["availableBalance"])
    except Exception as e:
        send_telegram(f"Wallet Fehler: {str(e)}")
    return 0.0

# === Order platzieren ===
def place_order(side, qty, price):
    timestamp = str(int(time.time() * 1000))
    body = {
        "category": "spot",
        "symbol": SYMBOL,
        "side": side,
        "orderType": "Limit",
        "qty": str(qty),
        "price": str(price),
        "timeInForce": "GTC"
    }
    payload = timestamp + API_KEY + "5000" + json.dumps(body)
    sign = create_signature(payload)
    headers = {
        "X-BAPI-API-KEY": API_KEY,
        "X-BAPI-TIMESTAMP": timestamp,
        "X-BAPI-SIGN": sign,
        "Content-Type": "application/json"
    }
    url = f"{BASE_URL}/v5/order/create"
    r = requests.post(url, headers=headers, data=json.dumps(body))
    send_telegram(f"📨 {side}-Order ➜ {qty} @ {price} USDT\nAntwort: {r.text}")

# === MAIN LOOP (Einmaliger Testlauf) ===
def run():
    global has_open_position
    send_telegram("🤖 TEST-Bot gestartet – sofortiger KAUF & VERKAUF wird getestet")

    price = get_price()
    usdt = get_balance("USDT")
    doge = get_balance("DOGE")

    if usdt >= USDT_EINSATZ and not has_open_position:
        qty = round(USDT_EINSATZ / price, 2)
        place_order("Buy", qty, round(price, 4))
        has_open_position = True
        send_telegram("✅ Test-KAUF ausgelöst")

    time.sleep(10)

    doge = get_balance("DOGE")
    price = get_price()

    if doge >= 5 and has_open_position:
        place_order("Sell", round(doge, 2), round(price, 4))
        send_telegram("✅ Test-VERKAUF ausgelöst")
    else:
        send_telegram("⚠️ Nicht genug DOGE für Test-Verkauf")

if __name__ == "__main__":
    run()
