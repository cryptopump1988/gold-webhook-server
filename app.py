from flask import Flask, request
import requests
import os
import json

app = Flask(name)

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
TWELVE_DATA_KEY = os.environ.get("TWELVE_DATA_KEY", "")

TELEGRAM_SEND_MSG_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
TELEGRAM_SEND_PHOTO_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"


def send_text(message):
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "HTML"}
    return requests.post(TELEGRAM_SEND_MSG_URL, json=payload, timeout=15)


def send_photo_from_url(photo_url, caption):
    img = requests.get(photo_url, timeout=25)
    files = {"photo": ("setup.png", img.content)}
    data = {"chat_id": CHAT_ID, "caption": caption, "parse_mode": "HTML"}
    return requests.post(TELEGRAM_SEND_PHOTO_URL, data=data, files=files, timeout=25)


def fetch_closes(symbol="XAU/USD", interval="15min", outputsize=200):
    url = "https://api.twelvedata.com/time_series"
    params = {"symbol": symbol, "interval": interval, "outputsize": outputsize, "apikey": TWELVE_DATA_KEY, "format": "JSON"}
    r = requests.get(url, params=params, timeout=20)
    data = r.json()
    if "values" not in data:
        print("Twelve Data error:", data)
        return None
    values = list(reversed(data["values"]))
    closes = [float(v["close"]) for v in values]
    return closes


def build_chart_url(closes, entry, sl, tp1, tp2, tp3, signal):
    n = len(closes)
    labels = [str(i) for i in range(n)]
    flat_entry = [entry] * n
    flat_sl = [sl] * n
    flat_tp1 = [tp1] * n
    flat_tp2 = [tp2] * n
    flat_tp3 = [tp3] * n

    config = {
        "type": "line",
        "data": {
            "labels": labels,
            "datasets": [
                {"label": "Price", "data": closes, "borderColor": "#d1d4dc", "borderWidth": 1.5, "pointRadius": 0, "fill": False},
                {"label": "Entry", "data": flat_entry, "borderColor": "#2962ff", "borderWidth": 1, "borderDash": [6, 4], "pointRadius": 0, "fill": False},
                {"label": "SL", "data": flat_sl, "borderColor": "#ef5350", "borderWidth": 1, "borderDash": [6, 4], "pointRadius": 0, "fill": False},
                {"label": "TP1", "data": flat_tp1, "borderColor": "#26a69a", "borderWidth": 1, "borderDash": [3, 3], "pointRadius": 0, "fill": False},
                {"label": "TP2", "data": flat_tp2, "borderColor": "#26a69a", "borderWidth": 1, "borderDash": [3, 3], "pointRadius": 0, "fill": False},
                {"label": "TP3", "data": flat_tp3, "borderColor": "#26a69a", "borderWidth": 1, "borderDash": [3, 3], "pointRadius": 0, "fill": False}
            ]
        },
        "options": {
            "title": {"display": True, "text": "XAUUSD - " + signal + " SETUP", "fontColor": "#ffffff"},
            "legend": {"labels": {"fontColor": "#ffffff"}},
            "scales": {
                "xAxes": [{"ticks": {"fontColor": "#ffffff", "maxTicksLimit": 8}, "gridLines": {"color": "#2a2e39"}}],
                "yAxes": [{"ticks": {"fontColor": "#ffffff"}, "gridLines": {"color": "#2a2e39"}}]
            }
        }
    }

    params = {"c": json.dumps(config), "width": 900, "height": 500, "backgroundColor": "#131722", "devicePixelRatio": 2}
    req = requests.Request("GET", "https://quickchart.io/chart", params=params)
    prepared = req.prepare()
    return prepared.url


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
            closes = fetch_closes()
            if closes and len(closes) > 10:
                chart_url = build_chart_url(closes, float(entry), float(sl), float(tp1), float(tp2), float(tp3), signal)
                r = send_photo_from_url(chart_url, caption)
                chart_sent = r.status_code == 200
        except Exception as e:
            print("Chart generation failed:", e)

    if not chart_sent:
        send_text(caption)

    return "OK", 200


if name == "main":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
