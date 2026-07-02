from flask import Flask, request
import requests
import os

app = Flask(__name__)

# ── Set these two in Railway environment variables ──────────────────────────
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")   # From BotFather
CHAT_ID   = os.environ.get("TELEGRAM_CHAT_ID",   "")   # Your chat/group ID
# ───────────────────────────────────────────────────────────────────────────

TELEGRAM_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

@app.route("/", methods=["GET"])
def home():
    return "Gold CHoCH Webhook Server is running.", 200

@app.route("/webhook", methods=["POST"])
def webhook():
    # TradingView sends the alert message as plain text in the request body
    message = request.get_data(as_text=True).strip()

    if not message:
        return "Empty message", 400

    if not BOT_TOKEN or not CHAT_ID:
        print("ERROR: TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set.")
        return "Server config missing", 500

    payload = {
        "chat_id": CHAT_ID,
        "text":    message,
        "parse_mode": "HTML"
    }

    response = requests.post(TELEGRAM_URL, json=payload, timeout=10)

    if response.status_code == 200:
        print(f"[OK] Telegram message sent: {message[:60]}...")
        return "OK", 200
    else:
        print(f"[ERROR] Telegram API error: {response.text}")
        return "Telegram error", 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
