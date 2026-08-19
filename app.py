from flask import Flask, request
import requests
import os
import json
import io
import pandas as pd
import mplfinance as mpf

app = Flask(__name__)

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
TWELVE_DATA_KEY = os.environ.get("TWELVE_DATA_KEY", "")

TELEGRAM_SEND_MSG_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
TELEGRAM_SEND_PHOTO_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"


def send_text(message):
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "HTML"}
    return requests.post(TELEGRAM_SEND_MSG_URL, json=payload, timeout=15)


def send_photo(photo_bytes, caption):
    files = {"photo": ("setup.png", photo_bytes)}
    data = {"chat_id": CHAT_ID, "caption": caption, "parse_mode": "HTML"}
    return requests.post(TELEGRAM_SEND_PHOTO_URL, data=data, files=files, timeout=25)


def fetch_candles(symbol="XAU/USD", interval="15min", outputsize=250):
    url = "https://api.twelvedata.com/time_series"
    params = {"symbol": symbol, "interval": interval, "outputsize": outputsize, "apikey": TWELVE_DATA_KEY, "format": "JSON"}
    r = requests.get(url, params=params, timeout=20)
    data = r.json()
    if "values" not in data:
        print("Twelve Data error:", data)
        return None
    df = pd.DataFrame(data["values"])
    df["datetime"] = pd.to_datetime(df["datetime"])
    df = df.set_index("datetime").sort_index()
    df = df.astype({"open": "float", "high": "float", "low": "float", "close": "float"})
    return df


def build_chart(df, entry, sl, tp1, tp2, tp3, signal):
    up_color = "#26a69a"
    dn_color = "#ef5350"
    mc = mpf.make_marketcolors(up=up_color, down=dn_color, edge="inherit", wick="inherit")
    style = mpf.make_mpf_style(base_mpf_style="nightclouds", marketcolors=mc, gridstyle="")
    hlines = dict(hlines=[entry, sl, tp1, tp2, tp3], colors=["#2962ff", "#ef5350", "#26a69a", "#26a69a", "#26a69a"], linestyle="--", linewidths=1.1)
    buf = io.BytesIO()
    title = "XAUUSD — " + signal + " SETUP"
    mpf.plot(df, type="candle", style=style, hlines=hlines, volume=False, title=title, figsize=(11, 6), savefig=dict(fname=buf, dpi=150, bbox_inches="tight"))
    buf.seek(0)
    return buf


def build_caption(symbol, signal, entry, sl, tp1, tp2, tp3):
    header = "🟡" if signal == "BUY" else "🔴"
    caption = header + " <b>" + symbol + " / GOLD</b>\n\n<b>" + signal + " SETUP</b>\n\nEntry: " + entry + "\nSL: " + sl + "\n\nTP1: " + tp1 + "\nTP2: " + tp2 + "\nTP3: " + tp3
    return caption


@app.route("/", methods=["GET"])
def home():
    return "Gold CHoCH Webhook Server is running.", 200


@app.route("/webhook", methods=["POST"])
def webhook():
    raw = request.get_data(as_text=True).strip()

    if not raw:
        return "Empty message", 400
    if not BOT_TOKEN or not CHAT_ID:
        print("ERROR: TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set.")
        return "Server config missing", 500

    payload = None
    try:
        payload = json.loads(raw)
    except Exception:
        payload = None

    if payload is None:
        r = send_text(raw)
        return ("OK", 200) if r.status_code == 200 else ("Telegram error", 500)

    symbol = payload.get("symbol", "XAUUSD")
    signal = payload.get("signal", "")
    entry = payload.get("entry", "")
    sl = payload.get("sl", "")
    tp1 = payload.get("tp1", "")
    tp2 = payload.get("tp2", "")
    tp3 = payload.get("tp3", "")

    caption = build_caption(symbol, signal, entry, sl, tp1, tp2, tp3)

    chart_sent = False
    if TWELVE_DATA_KEY:
        try:
            df = fetch_candles()
            if df is not None and len(df) > 10:
                chart_buf = build_chart(df, float(entry), float(sl), float(tp1), float(tp2), float(tp3), signal)
                r = send_photo(chart_buf, caption)
                chart_sent = r.status_code == 200
        except Exception as e:
            print("Chart generation failed:", e)

    if not chart_sent:
        send_text(caption)

    return "OK", 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
