from flask import Flask, request, Response
import requests
import os
import json
import base64
from datetime import datetime

app = Flask(__name__)

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
TWELVE_DATA_KEY = os.environ.get("TWELVE_DATA_KEY", "")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
GITHUB_REPO = os.environ.get("GITHUB_REPO", "")  # format: username/gold-webhook-server
HISTORY_PATH = "data/history.json"
MAX_HISTORY = 100

TELEGRAM_SEND_MSG_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
TELEGRAM_SEND_PHOTO_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"

ICON_192_B64 = "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"
ICON_512_B64 = "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"


def send_text(message):
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "HTML"}
    return requests.post(TELEGRAM_SEND_MSG_URL, json=payload, timeout=15)


def send_photo_from_url(photo_url, caption):
    img = requests.get(photo_url, timeout=25)
    files = {"photo": ("setup.png", img.content)}
    data = {"chat_id": CHAT_ID, "caption": caption, "parse_mode": "HTML"}
    return requests.post(TELEGRAM_SEND_PHOTO_URL, data=data, files=files, timeout=25)


def gh_headers():
    return {"Authorization": "token " + GITHUB_TOKEN, "Accept": "application/vnd.github+json"}


def gh_load_history():
    if not GITHUB_TOKEN or not GITHUB_REPO:
        return [], None
    url = "https://api.github.com/repos/" + GITHUB_REPO + "/contents/" + HISTORY_PATH
    r = requests.get(url, headers=gh_headers(), timeout=15)
    if r.status_code == 200:
        j = r.json()
        content = base64.b64decode(j["content"]).decode("utf-8")
        try:
            data = json.loads(content)
        except Exception:
            data = []
        return data, j["sha"]
    return [], None


def gh_save_history(history_list, sha):
    if not GITHUB_TOKEN or not GITHUB_REPO:
        return False
    url = "https://api.github.com/repos/" + GITHUB_REPO + "/contents/" + HISTORY_PATH
    content_str = json.dumps(history_list, indent=2)
    content_b64 = base64.b64encode(content_str.encode("utf-8")).decode("utf-8")
    body = {"message": "Update signal history", "content": content_b64, "branch": "main"}
    if sha:
        body["sha"] = sha
    r = requests.put(url, headers=gh_headers(), json=body, timeout=15)
    return r.status_code in (200, 201)


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


def build_caption(symbol, signal, kind, entry, sl, tp1, tp2, tp3):
    dot = "\ud83d\udfe2" if signal == "BUY" else "\ud83d\udd34"
    title = (signal + " SETUP") if kind == "signal" else (signal + " ZONE TOUCHED AGAIN")
    caption = dot + " <b>" + symbol + " / GOLD</b>\n\n<b>" + title + "</b>\n\nEntry: " + entry + "\nSL: " + sl + "\n\nTP1: " + tp1 + "\nTP2: " + tp2 + "\nTP3: " + tp3
    return caption


@app.route("/", methods=["GET"])
def home():
    html = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no">
<title>Gold Signals</title>
<link rel="manifest" href="/manifest.json">
<link rel="icon" href="/icon192.png">
<link rel="apple-touch-icon" href="/icon192.png">
<meta name="theme-color" content="#0d1117">
<style>
:root {
  --bg: #0d1117; --card: #161b22; --card2: #1c2129; --border: #262c36;
  --text: #e6edf3; --muted: #8b949e; --accent: #d4af37;
  --buy: #3fb950; --buy-bg: rgba(63,185,80,0.12);
  --sell: #f85149; --sell-bg: rgba(248,81,73,0.12);
  --shadow: 0 8px 24px rgba(0,0,0,0.35);
}
html[data-theme="light"] {
  --bg: #f4f6f8; --card: #ffffff; --card2: #f0f2f5; --border: #e2e6ea;
  --text: #16181d; --muted: #6a7280; --accent: #b8860b;
  --buy: #1a7f37; --buy-bg: rgba(26,127,55,0.10);
  --sell: #cf222e; --sell-bg: rgba(207,34,46,0.10);
  --shadow: 0 8px 24px rgba(0,0,0,0.08);
}
* { box-sizing: border-box; -webkit-tap-highlight-color: transparent; }
body {
  margin:0; background:var(--bg); color:var(--text);
  font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Arial,sans-serif;
  padding-bottom:50px; transition: background 0.35s ease, color 0.35s ease;
}
.header {
  padding:16px 18px; background:var(--card); border-bottom:1px solid var(--border);
  position:sticky; top:0; z-index:10; display:flex; justify-content:space-between; align-items:center;
  backdrop-filter: blur(10px); transition: background 0.35s ease, border-color 0.35s ease;
}
.brand { display:flex; align-items:center; gap:10px; }
.brand .logo {
  width:34px; height:34px; border-radius:50%; background:linear-gradient(135deg,#f2c94c,#b8860b);
  display:flex; align-items:center; justify-content:center; font-weight:800; color:#161b22; font-size:16px;
}
.brand h1 { font-size:16px; margin:0; font-weight:700; letter-spacing:0.2px; }
.brand .sub { font-size:11px; color:var(--muted); margin-top:1px; }
.header-actions { display:flex; align-items:center; gap:10px; }
.theme-toggle {
  width:44px; height:26px; border-radius:20px; background:var(--card2); border:1px solid var(--border);
  position:relative; cursor:pointer; transition:background 0.3s;
}
.theme-toggle .knob {
  position:absolute; top:2px; left:2px; width:20px; height:20px; border-radius:50%;
  background:var(--accent); transition: transform 0.3s ease; display:flex; align-items:center; justify-content:center; font-size:11px;
}
html[data-theme="light"] .theme-toggle .knob { transform: translateX(18px); }
.refresh-btn {
  background:linear-gradient(135deg,#2ea043,#238636); color:white; border:none; border-radius:10px;
  padding:9px 14px; font-size:13px; font-weight:600; display:flex; align-items:center; gap:6px; cursor:pointer;
  box-shadow: 0 3px 10px rgba(46,160,67,0.3); transition: transform 0.15s;
}
.refresh-btn:active { transform: scale(0.94); }
.refresh-btn.spinning svg { animation: spin 0.8s linear infinite; }
@keyframes spin { from{transform:rotate(0deg);} to{transform:rotate(360deg);} }

.stats-strip { display:flex; gap:10px; padding:14px 16px 4px; overflow-x:auto; }
.stat-pill {
  background:var(--card); border:1px solid var(--border); border-radius:12px; padding:10px 16px;
  min-width:84px; text-align:center; flex-shrink:0; box-shadow: var(--shadow);
}
.stat-pill .num { font-size:20px; font-weight:800; }
.stat-pill .lbl { font-size:11px; color:var(--muted); margin-top:2px; }
.stat-pill.buy .num { color:var(--buy); }
.stat-pill.sell .num { color:var(--sell); }

.filters { display:flex; gap:8px; padding:14px 16px 4px; overflow-x:auto; }
.chip {
  padding:7px 14px; border-radius:20px; border:1px solid var(--border); background:var(--card);
  color:var(--muted); font-size:13px; font-weight:600; cursor:pointer; flex-shrink:0; transition: all 0.2s;
}
.chip.active { background:var(--accent); color:#161b22; border-color:var(--accent); }

.chart-embed-card {
  margin:14px 16px 4px; background:var(--card); border:1px solid var(--border); border-radius:16px;
  overflow:hidden; box-shadow: var(--shadow);
}
.chart-embed-header { padding:12px 16px; display:flex; justify-content:space-between; align-items:center; border-bottom:1px solid var(--border); }
.chart-embed-header h2 { font-size:14px; margin:0; font-weight:700; }
.chart-embed-header .live-dot { display:inline-block; width:7px; height:7px; border-radius:50%; background:var(--buy); margin-right:6px; animation: pulse 1.5s infinite; }
@keyframes pulse { 0%,100%{opacity:1;} 50%{opacity:0.3;} }
#tvChartContainer { height:340px; }
.card-link { text-decoration:none; color:inherit; display:block; }
.tap-hint { font-size:10.5px; color:var(--muted); padding:0 16px 12px; display:flex; align-items:center; gap:4px; }
.card { margin:14px 16px; background:var(--card); border:1px solid var(--border); border-radius:16px;
  overflow:hidden; box-shadow: var(--shadow); opacity:0; transform:translateY(10px);
  animation: cardIn 0.4s ease forwards; transition: transform 0.15s; }
.card:active { transform: scale(0.98); }
@keyframes cardIn { to { opacity:1; transform:translateY(0); } }
.card img { width:100%; display:block; background:var(--card2); }
.card-body { padding:16px; }
.badge-row { display:flex; justify-content:space-between; align-items:center; }
.badge { display:inline-flex; align-items:center; gap:5px; padding:5px 13px; border-radius:20px; font-weight:800; font-size:13px; letter-spacing:0.3px; }
.badge.buy { background:var(--buy-bg); color:var(--buy); }
.badge.sell { background:var(--sell-bg); color:var(--sell); }
.kind-tag { font-size:11px; padding:4px 10px; border-radius:8px; background:var(--card2); color:var(--muted); font-weight:600; }
.rows { margin-top:14px; }
.row { display:flex; justify-content:space-between; padding:9px 0; border-bottom:1px solid var(--border); font-size:15px; }
.row:last-child { border-bottom:none; }
.row .label { color:var(--muted); font-size:13px; }
.row .value { font-weight:700; font-variant-numeric: tabular-nums; }
.entry .value { color:#58a6ff; }
.sl .value { color:var(--sell); }
.tp .value { color:var(--buy); }
.time { color:var(--muted); font-size:11.5px; padding:0 16px 14px; }
.empty { text-align:center; color:var(--muted); padding:80px 24px; }
.empty .emoji { font-size:42px; margin-bottom:14px; }
.section-title { padding:10px 16px 0; color:var(--muted); font-size:12px; text-transform:uppercase; letter-spacing:0.6px; font-weight:700; }
</style>
</head>
<body>
<div class="header">
  <div class="brand">
    <div class="logo">G</div>
    <div>
      <h1>Gold Signals</h1>
      <div class="sub">CHoCH Live Feed</div>
    </div>
  </div>
  <div class="header-actions">
    <div class="theme-toggle" id="themeToggle" onclick="toggleTheme()"><div class="knob" id="themeKnob">\ud83c\udf19</div></div>
    <button class="refresh-btn" id="refreshBtn" onclick="load(true)">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="3"><path d="M21 2v6h-6M3 22v-6h6M3.5 9a9 9 0 0114.6-3.4L21 8M20.5 15a9 9 0 01-14.6 3.4L3 16"/></svg>
      Refresh
    </button>
  </div>
</div>

<div class="chart-embed-card">
  <div class="chart-embed-header">
    <h2><span class="live-dot"></span>XAUUSD Live Chart</h2>
  </div>
  <div id="tvChartContainer"></div>
</div>

<div class="stats-strip" id="statsStrip"></div>
<div class="filters" id="filters"></div>
<div id="content"><div class="empty"><div class="emoji">\u23f3</div>Loading signals...</div></div>

<script>
let allSignals = [];
let currentFilter = "all";

function applyTheme(t) {
  document.documentElement.setAttribute("data-theme", t);
  document.getElementById("themeKnob").textContent = t === "light" ? "\u2600\ufe0f" : "\ud83c\udf19";
  localStorage.setItem("theme", t);
  initTVWidget(t);
}
function toggleTheme() {
  const cur = document.documentElement.getAttribute("data-theme") || "dark";
  applyTheme(cur === "dark" ? "light" : "dark");
}

let tvScriptLoaded = false;
function initTVWidget(theme) {
  const container = document.getElementById("tvChartContainer");
  container.innerHTML = "";
  function draw() {
    new TradingView.widget({
      "autosize": true,
      "symbol": "FOREXCOM:XAUUSD",
      "interval": "15",
      "timezone": "Etc/UTC",
      "theme": theme === "light" ? "light" : "dark",
      "style": "1",
      "locale": "en",
      "toolbar_bg": theme === "light" ? "#ffffff" : "#131722",
      "enable_publishing": false,
      "hide_top_toolbar": false,
      "hide_legend": false,
      "save_image": false,
      "container_id": "tvChartContainer"
    });
  }
  if (tvScriptLoaded) { draw(); return; }
  const s = document.createElement("script");
  s.src = "https://s3.tradingview.com/tv.js";
  s.onload = function() { tvScriptLoaded = true; draw(); };
  document.body.appendChild(s);
}

applyTheme(localStorage.getItem("theme") || "dark");

function timeAgo(iso) {
  return iso;
}

function renderStats() {
  const total = allSignals.length;
  const buys = allSignals.filter(s => s.signal === "BUY").length;
  const sells = allSignals.filter(s => s.signal === "SELL").length;
  document.getElementById("statsStrip").innerHTML = `
    <div class="stat-pill"><div class="num">${total}</div><div class="lbl">Total</div></div>
    <div class="stat-pill buy"><div class="num">${buys}</div><div class="lbl">Buy</div></div>
    <div class="stat-pill sell"><div class="num">${sells}</div><div class="lbl">Sell</div></div>
  `;
}

function renderFilters() {
  const opts = [["all","All"],["BUY","Buy"],["SELL","Sell"],["signal","New Setup"],["touch","Zone Touch"]];
  document.getElementById("filters").innerHTML = opts.map(([key,label]) =>
    `<div class="chip ${currentFilter===key?'active':''}" onclick="setFilter('${key}')">${label}</div>`
  ).join("");
}

function setFilter(key) {
  currentFilter = key;
  renderFilters();
  renderCards();
}

function renderCards() {
  const el = document.getElementById("content");
  let list = allSignals;
  if (currentFilter === "BUY" || currentFilter === "SELL") list = list.filter(s => s.signal === currentFilter);
  if (currentFilter === "signal" || currentFilter === "touch") list = list.filter(s => s.kind === currentFilter);

  if (list.length === 0) {
    el.innerHTML = '<div class="empty"><div class="emoji">\ud83d\udcc9</div>No signals match this filter yet.</div>';
    return;
  }
  let html = "";
  list.forEach((s, i) => {
    const badgeClass = s.signal === "BUY" ? "buy" : "sell";
    const arrow = s.signal === "BUY" ? "\u2191" : "\u2193";
    const kindLabel = s.kind === "touch" ? "Zone Re-Touch" : "New Setup";
    html += `
      <a class="card-link" href="https://www.tradingview.com/chart/?symbol=FOREXCOM:XAUUSD" target="_blank" rel="noopener">
      <div class="card" style="animation-delay:${Math.min(i,10)*0.04}s">
        <img src="${s.chart_url}" loading="lazy">
        <div class="card-body">
          <div class="badge-row">
            <span class="badge ${badgeClass}">${arrow} ${s.signal}</span>
            <span class="kind-tag">${kindLabel}</span>
          </div>
          <div class="rows">
            <div class="row entry"><span class="label">Entry</span><span class="value">${s.entry}</span></div>
            <div class="row sl"><span class="label">Stop Loss</span><span class="value">${s.sl}</span></div>
            <div class="row tp"><span class="label">TP1</span><span class="value">${s.tp1}</span></div>
            <div class="row tp"><span class="label">TP2</span><span class="value">${s.tp2}</span></div>
            <div class="row tp"><span class="label">TP3</span><span class="value">${s.tp3}</span></div>
          </div>
        </div>
        <div class="time">${s.symbol} \u2022 ${s.time}</div>
        <div class="tap-hint">\ud83d\udcc8 Tap to open on TradingView</div>
      </div>
      </a>`;
  });
  el.innerHTML = html;
}

async function load(manual) {
  const btn = document.getElementById("refreshBtn");
  if (manual) btn.classList.add("spinning");
  try {
    const res = await fetch("/latest");
    const data = await res.json();
    allSignals = data.signals || [];
    renderStats();
    renderFilters();
    renderCards();
  } catch (e) {
    document.getElementById("content").innerHTML = '<div class="empty"><div class="emoji">\u26a0\ufe0f</div>Could not load signals. Tap Refresh to try again.</div>';
  }
  if (manual) setTimeout(()=>btn.classList.remove("spinning"), 500);
}
load();
setInterval(load, 20000);
if ("serviceWorker" in navigator) {
  navigator.serviceWorker.register("/sw.js").catch(()=>{});
}
</script>
</body>
</html>"""
    return Response(html, mimetype="text/html")


@app.route("/manifest.json", methods=["GET"])
def manifest():
    m = {
        "name": "Gold CHoCH Signals",
        "short_name": "Gold Signals",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#0d1117",
        "theme_color": "#0d1117",
        "icons": [
            {"src": "/icon192.png", "sizes": "192x192", "type": "image/png"},
            {"src": "/icon512.png", "sizes": "512x512", "type": "image/png"}
        ]
    }
    return Response(json.dumps(m), mimetype="application/json")


@app.route("/sw.js", methods=["GET"])
def sw():
    js = "self.addEventListener('fetch', function(e){});"
    return Response(js, mimetype="application/javascript")


@app.route("/icon192.png", methods=["GET"])
def icon192():
    return Response(base64.b64decode(ICON_192_B64), mimetype="image/png")


@app.route("/icon512.png", methods=["GET"])
def icon512():
    return Response(base64.b64decode(ICON_512_B64), mimetype="image/png")


@app.route("/latest", methods=["GET"])
def latest():
    history, _ = gh_load_history()
    return Response(json.dumps({"signals": history}), mimetype="application/json")


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
    kind = payload.get("kind", "signal")
    entry = payload.get("entry", "")
    sl = payload.get("sl", "")
    tp1 = payload.get("tp1", "")
    tp2 = payload.get("tp2", "")
    tp3 = payload.get("tp3", "")

    caption = build_caption(symbol, signal, kind, entry, sl, tp1, tp2, tp3)

    chart_sent = False
    chart_url_for_app = ""
    if TWELVE_DATA_KEY:
        try:
            closes = fetch_closes()
            if closes and len(closes) > 10:
                chart_url_for_app = build_chart_url(closes, float(entry), float(sl), float(tp1), float(tp2), float(tp3), signal)
                r = send_photo_from_url(chart_url_for_app, caption)
                chart_sent = r.status_code == 200
        except Exception as e:
            print("Chart generation failed:", e)

    if not chart_sent:
        send_text(caption)

    new_entry = {
        "symbol": symbol, "signal": signal, "kind": kind,
        "entry": entry, "sl": sl, "tp1": tp1, "tp2": tp2, "tp3": tp3,
        "chart_url": chart_url_for_app,
        "time": datetime.utcnow().strftime("%d %b %Y, %H:%M UTC")
    }

    try:
        history, sha = gh_load_history()
        history.insert(0, new_entry)
        history = history[:MAX_HISTORY]
        gh_save_history(history, sha)
    except Exception as e:
        print("GitHub history save failed:", e)

    return "OK", 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
