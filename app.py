from flask import Flask, request, Response
import requests
import os
import json
import base64
from datetime import datetime, timezone
from pywebpush import webpush, WebPushException

app = Flask(__name__)

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
TWELVE_DATA_KEY = os.environ.get("TWELVE_DATA_KEY", "")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
GITHUB_REPO = os.environ.get("GITHUB_REPO", "")  # format: username/gold-webhook-server
HISTORY_PATH = "data/history.json"
SUBS_PATH = "data/subscriptions.json"
MAX_HISTORY = 100

VAPID_PRIVATE_KEY = os.environ.get("VAPID_PRIVATE_KEY", "")
VAPID_PUBLIC_KEY = os.environ.get("VAPID_PUBLIC_KEY", "")
VAPID_CLAIMS_EMAIL = os.environ.get("VAPID_CLAIMS_EMAIL", "mailto:admin@bakalestrading.app")

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


def gh_load_json(path):
    if not GITHUB_TOKEN or not GITHUB_REPO:
        return [], None
    url = "https://api.github.com/repos/" + GITHUB_REPO + "/contents/" + path
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


def gh_save_json(path, data_list, sha):
    if not GITHUB_TOKEN or not GITHUB_REPO:
        return False
    url = "https://api.github.com/repos/" + GITHUB_REPO + "/contents/" + path
    content_str = json.dumps(data_list, indent=2)
    content_b64 = base64.b64encode(content_str.encode("utf-8")).decode("utf-8")
    body = {"message": "Update " + path, "content": content_b64, "branch": "main"}
    if sha:
        body["sha"] = sha
    r = requests.put(url, headers=gh_headers(), json=body, timeout=15)
    return r.status_code in (200, 201)


def send_push_to_all(title, body_text, url_path="/"):
    subs, sha = gh_load_json(SUBS_PATH)
    if not subs or not VAPID_PRIVATE_KEY:
        return
    payload = json.dumps({"title": title, "body": body_text, "url": url_path})
    still_valid = []
    changed = False
    for sub in subs:
        try:
            webpush(
                subscription_info=sub,
                data=payload,
                vapid_private_key=VAPID_PRIVATE_KEY,
                vapid_claims={"sub": VAPID_CLAIMS_EMAIL}
            )
            still_valid.append(sub)
        except WebPushException as e:
            status = e.response.status_code if e.response is not None else None
            if status in (404, 410):
                changed = True  # expired subscription, drop it
            else:
                still_valid.append(sub)
                print("Push send failed (kept):", e)
        except Exception as e:
            still_valid.append(sub)
            print("Push send error (kept):", e)
    if changed:
        gh_save_json(SUBS_PATH, still_valid, sha)


def fetch_closes(symbol="XAU/USD", interval="15min", outputsize=200):
    if not TWELVE_DATA_KEY:
        return None
    url = "https://api.twelvedata.com/time_series"
    params = {"symbol": symbol, "interval": interval, "outputsize": outputsize, "apikey": TWELVE_DATA_KEY, "format": "JSON"}
    try:
        r = requests.get(url, params=params, timeout=20)
        data = r.json()
    except Exception as e:
        print("Twelve Data request failed (fetch_closes):", e)
        return None
    if "values" not in data:
        print("Twelve Data error:", data)
        return None
    values = list(reversed(data["values"]))
    try:
        closes = [float(v["close"]) for v in values]
    except Exception as e:
        print("Failed parsing closes:", e)
        return None
    return closes


def fetch_ohlc(symbol="XAU/USD", interval="15min", outputsize=700):
    import time as _time
    if not TWELVE_DATA_KEY:
        return None
    url = "https://api.twelvedata.com/time_series"
    params = {"symbol": symbol, "interval": interval, "outputsize": outputsize, "apikey": TWELVE_DATA_KEY, "format": "JSON"}
    try:
        r = requests.get(url, params=params, timeout=25)
        data = r.json()
    except Exception as e:
        print("Twelve Data request failed:", e)
        return None
    if "values" not in data:
        print("Twelve Data error:", data)
        return None
    values = list(reversed(data["values"]))
    raw_bars = []
    for v in values:
        try:
            t = int(_time.mktime(_time.strptime(v["datetime"], "%Y-%m-%d %H:%M:%S")))
            raw_bars.append({"time": t, "open": float(v["open"]), "high": float(v["high"]), "low": float(v["low"]), "close": float(v["close"])})
        except Exception:
            continue

    # Drop stale/placeholder bars from closed-market periods (e.g. weekends):
    # a real trading bar for gold almost always has some intrabar range.
    # Only strip RUNS of 3+ consecutive zero-range bars with the same close,
    # so genuine brief quiet moments in live trading are kept.
    bars = []
    i = 0
    n = len(raw_bars)
    while i < n:
        b = raw_bars[i]
        is_flat = b["open"] == b["high"] == b["low"] == b["close"]
        if is_flat:
            j = i
            while j < n and raw_bars[j]["open"] == raw_bars[j]["high"] == raw_bars[j]["low"] == raw_bars[j]["close"] == b["close"]:
                j += 1
            run_len = j - i
            if run_len >= 3:
                i = j
                continue
        bars.append(b)
        i += 1

    return bars


def build_chart_config(closes, entry, sl, tp1, tp2, tp3, signal):
    n = len(closes)
    labels = [str(i) for i in range(n)]
    flat_entry = [entry] * n
    flat_sl = [sl] * n
    flat_tp1 = [tp1] * n
    flat_tp2 = [tp2] * n
    flat_tp3 = [tp3] * n

    return {
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


def render_chart_png_bytes(config):
    """POST to QuickChart instead of a giant GET URL - avoids the ~19,000+ character
    URL that a 200-point, 6-line chart produces, which was silently rejected before."""
    body = {"chart": config, "width": 900, "height": 500, "backgroundColor": "#131722",
             "devicePixelRatio": 2, "format": "png"}
    r = requests.post("https://quickchart.io/chart", json=body, timeout=25)
    r.raise_for_status()
    return r.content


def send_photo_bytes(photo_bytes, caption):
    files = {"photo": ("setup.png", photo_bytes)}
    data = {"chat_id": CHAT_ID, "caption": caption, "parse_mode": "HTML"}
    return requests.post(TELEGRAM_SEND_PHOTO_URL, data=data, files=files, timeout=25)


def build_caption(symbol, signal, kind, entry, sl, tp1, tp2, tp3):
    dot = "🟢" if signal == "BUY" else "🔴"
    title = (signal + " SETUP") if kind == "signal" else (signal + " ZONE TOUCHED AGAIN")
    caption = dot + " <b>" + symbol + " / GOLD</b>\n\n<b>" + title + "</b>\n\nEntry: " + entry + "\nSL: " + sl + "\n\nTP1: " + tp1 + "\nTP2: " + tp2 + "\nTP3: " + tp3
    return caption


def compute_outcome_and_excursion(sig, bars):
    # Returns {"outcome": "SL"/"TP"/"OPEN", "mfe_r": float, "mae_r": float} or None.
    # mfe_r = best price move in the trade's favor before exit, in R-multiples (risk units).
    # mae_r = worst price move against the trade before exit, in R-multiples.
    # Walks candles chronologically from the signal's own timestamp; if a bar's range
    # touches both SL and TP1, SL is assumed first (conservative, matches prior behavior).
    if "time_unix" not in sig:
        return None
    try:
        entry_t = int(sig["time_unix"])
        entry_v = float(sig["entry"])
        sl_v = float(sig["sl"])
        tp1_v = float(sig["tp1"])
        direction = sig["signal"]
        risk = abs(entry_v - sl_v)
        if risk == 0:
            return None
    except Exception:
        return None

    relevant = [b for b in bars if b["time"] >= entry_t]
    outcome = "OPEN"
    mfe_r = 0.0
    mae_r = 0.0
    for b in relevant:
        if direction == "BUY":
            favorable = (b["high"] - entry_v) / risk
            adverse = (entry_v - b["low"]) / risk
            hit_sl = b["low"] <= sl_v
            hit_tp = b["high"] >= tp1_v
        else:
            favorable = (entry_v - b["low"]) / risk
            adverse = (b["high"] - entry_v) / risk
            hit_sl = b["high"] >= sl_v
            hit_tp = b["low"] <= tp1_v
        mfe_r = max(mfe_r, favorable)
        mae_r = max(mae_r, adverse)
        if hit_sl:
            outcome = "SL"
            break
        if hit_tp:
            outcome = "TP"
            break

    return {"outcome": outcome, "mfe_r": round(mfe_r, 2), "mae_r": round(mae_r, 2)}


_stats_cache = {"data": None, "ts": 0}
STATS_CACHE_TTL = 300  # seconds


def get_7day_stats():
    import time as _time
    now = _time.time()
    if _stats_cache["data"] is not None and (now - _stats_cache["ts"]) < STATS_CACHE_TTL:
        return _stats_cache["data"]

    history, _ = gh_load_history()
    cutoff = now - 7 * 24 * 3600
    week_signals = [s for s in history if s.get("kind") == "signal" and s.get("time_unix", 0) >= cutoff]

    result = {"total": len(week_signals), "sl_hit": 0, "tp_hit": 0, "open": 0, "untracked": 0}
    mfe_values, mae_values, mfe_on_losses = [], [], []

    if week_signals and TWELVE_DATA_KEY:
        bars = fetch_ohlc(outputsize=700)
        if not bars:
            # Full 7-day window failed - likely a Twelve Data quota/credit ceiling tied
            # to request size (Market Context's smaller 300-bar request keeps working).
            # Fall back to a smaller, cheaper request rather than showing nothing.
            print("7-day stats: 700-bar fetch failed, falling back to 300-bar request")
            bars = fetch_ohlc(outputsize=300)
        if bars:
            for s in week_signals:
                r = compute_outcome_and_excursion(s, bars)
                if r is None:
                    result["untracked"] += 1
                    continue
                outcome = r["outcome"]
                mfe_values.append(r["mfe_r"])
                mae_values.append(r["mae_r"])
                if outcome == "SL":
                    result["sl_hit"] += 1
                    mfe_on_losses.append(r["mfe_r"])
                elif outcome == "TP":
                    result["tp_hit"] += 1
                elif outcome == "OPEN":
                    result["open"] += 1
        else:
            result["untracked"] = len(week_signals)
    else:
        result["untracked"] = len(week_signals)

    resolved = result["sl_hit"] + result["tp_hit"]
    result["win_rate"] = round(100.0 * result["tp_hit"] / resolved, 1) if resolved > 0 else None
    result["avg_mfe_r"] = round(sum(mfe_values) / len(mfe_values), 2) if mfe_values else None
    result["avg_mae_r"] = round(sum(mae_values) / len(mae_values), 2) if mae_values else None
    result["avg_mfe_r_on_losses"] = round(sum(mfe_on_losses) / len(mfe_on_losses), 2) if mfe_on_losses else None

    _stats_cache["data"] = result
    _stats_cache["ts"] = now
    return result


@app.route("/", methods=["GET"])
def home():
    html = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no">
<title>Bakale's Trading</title>
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
.brand { display:flex; align-items:center; gap:8px; }
.brand .logo {
  width:28px; height:28px; border-radius:50%; background:linear-gradient(135deg,#f2c94c,#b8860b);
  display:flex; align-items:center; justify-content:center; font-weight:800; color:#161b22; font-size:13px;
}
.brand h1 { font-size:14px; margin:0; font-weight:700; letter-spacing:0.2px; }
.brand .sub { font-size:11px; color:var(--muted); margin-top:1px; }
.header-actions { display:flex; align-items:center; gap:6px; }
.theme-toggle {
  width:36px; height:21px; border-radius:20px; background:var(--card2); border:1px solid var(--border);
  position:relative; cursor:pointer; transition:background 0.3s;
}
.theme-toggle .knob {
  position:absolute; top:2px; left:2px; width:15px; height:15px; border-radius:50%;
  background:var(--accent); transition: transform 0.3s ease; display:flex; align-items:center; justify-content:center; font-size:9px;
}
html[data-theme="light"] .theme-toggle .knob { transform: translateX(15px); }
.switch-btn {
  background:var(--card2); border:1px solid var(--border); border-radius:9px; width:29px; height:29px;
  font-size:13px; cursor:pointer; display:flex; align-items:center; justify-content:center;
}
.ticker-strip {
  overflow:hidden; background:var(--card2); border-bottom:1px solid var(--border);
  white-space:nowrap; position:relative; padding:8px 0;
}
.ticker-track {
  display:inline-flex; align-items:center; animation: ticker-scroll 55s linear infinite;
}
.ticker-strip:hover .ticker-track { animation-play-state: paused; }
@keyframes ticker-scroll {
  from { transform: translateX(0); }
  to { transform: translateX(-50%); }
}
.ticker-item {
  display:inline-flex; align-items:center; gap:6px; padding:0 18px; font-size:13px; flex-shrink:0;
}
.ticker-item .tsym { font-weight:800; color:#39ff14; text-shadow: 0 0 6px rgba(57,255,20,0.95), 0 0 14px rgba(57,255,20,0.6); }
.ticker-item .tprice { color:#39ff14; text-shadow: 0 0 5px rgba(57,255,20,0.8); font-weight:600; }
.ticker-item .tchange.up { color:#26a69a; font-weight:600; }
.ticker-item .tchange.down { color:#ef5350; font-weight:600; }
.ticker-item .tgainer-tag {
  font-size:10px; background:#f4c43022; color:#f4c430; border-radius:5px; padding:1px 5px; font-weight:700;
}
.ticker-loading { padding:0 18px; font-size:13px; color:var(--text-dim); }
.chooser-overlay {
  display:none; position:fixed; inset:0; background:rgba(0,0,0,0.6); z-index:100;
  align-items:center; justify-content:center; padding:20px;
}
.chooser-overlay.show { display:flex; }
.chooser-box {
  background:var(--card); border:1px solid var(--border); border-radius:18px; padding:24px;
  max-width:400px; width:100%; box-shadow: var(--shadow);
}
.chooser-box h2 { margin:0 0 6px; font-size:19px; }
.chooser-box p { margin:0 0 18px; color:var(--muted); font-size:13px; }
.chooser-option {
  display:flex; gap:14px; align-items:center; padding:14px; border-radius:14px; background:var(--card2);
  border:1px solid var(--border); margin-bottom:10px; cursor:pointer; transition: transform 0.15s, border-color 0.2s;
}
.chooser-option:active { transform: scale(0.97); }
.chooser-option:hover { border-color: var(--accent); }
.chooser-icon { font-size:26px; }
.chooser-title { font-weight:700; font-size:14px; margin-bottom:3px; }
.chooser-desc { font-size:12px; color:var(--muted); line-height:1.4; }
.setups-hint { font-size:11px; color:var(--muted); text-align:center; padding:8px 16px 12px; }
.setups-tooltip {
  position:absolute; background:var(--card2); border:1px solid var(--accent); border-radius:10px;
  padding:10px 12px; font-size:12px; box-shadow: var(--shadow); z-index:5; pointer-events:none;
  min-width:150px;
}
.setups-tooltip .t-row { display:flex; justify-content:space-between; gap:10px; padding:2px 0; }
.setups-tooltip .t-label { color:var(--muted); }
.setups-tooltip .t-title { font-weight:700; margin-bottom:4px; }
.refresh-btn:active { transform: scale(0.94); }
.refresh-btn.spinning svg { animation: spin 0.8s linear infinite; }
@keyframes spin { from{transform:rotate(0deg);} to{transform:rotate(360deg);} }

.stats-strip { display:flex; gap:10px; padding:14px 16px 4px; overflow-x:auto; }
.week-panel {
  margin:14px 16px 0; background:var(--card); border:1px solid var(--border); border-radius:16px;
  padding:16px; box-shadow: var(--shadow);
}
.week-panel h2 { font-size:14px; margin:0 0 12px; font-weight:700; display:flex; align-items:center; gap:6px; }
.week-grid { display:grid; grid-template-columns: repeat(4, 1fr); gap:8px; }
.week-cell { text-align:center; padding:10px 4px; border-radius:10px; background:var(--card2); }
.week-cell .num { font-size:19px; font-weight:800; }
.week-cell .lbl { font-size:10.5px; color:var(--muted); margin-top:3px; }
.week-cell.sl .num { color:var(--sell); }
.week-cell.tp .num { color:var(--buy); }
.week-note { font-size:11px; color:var(--muted); margin-top:10px; text-align:center; line-height:1.6; }
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
      <h1>Bakale's Trading</h1>
    </div>
  </div>
  <div class="header-actions">
    <div class="theme-toggle" id="themeToggle" onclick="toggleTheme()"><div class="knob" id="themeKnob">🌙</div></div>
    <button class="switch-btn" id="switchBtn" onclick="openChooser()">📊</button>
    <button class="switch-btn" id="notifyBtn" onclick="enablePush()">🔔</button>
    <button class="switch-btn" id="settingsBtn" onclick="openSettings()">⚙️</button>
    <button class="switch-btn" onclick="window.location.href='/history'">🕘</button>
    <button class="switch-btn" onclick="window.location.href='/news'">📰</button>
  </div>
</div>

<div class="ticker-strip" id="tickerStrip">
  <div class="ticker-track" id="tickerTrack">
    <span class="ticker-loading">Loading market data…</span>
  </div>
</div>

<div class="chooser-overlay" id="chooserOverlay">
  <div class="chooser-box">
    <h2>Choose Your Chart</h2>
    <p>Pick which chart view you'd like to see</p>
    <div class="chooser-option" onclick="selectChart('tv')">
      <div class="chooser-icon">📊</div>
      <div>
        <div class="chooser-title">Live TradingView Chart</div>
        <div class="chooser-desc">Full-featured live chart with indicators and drawing tools</div>
      </div>
    </div>
    <div class="chooser-option" onclick="selectChart('setups')">
      <div class="chooser-icon">📈</div>
      <div>
        <div class="chooser-title">My Setups Chart</div>
        <div class="chooser-desc">Candles with every past BUY/SELL setup marked - tap a marker for details</div>
      </div>
    </div>
  </div>
</div>

<div class="chooser-overlay" id="settingsOverlay">
  <div class="chooser-box">
    <h2>Settings</h2>
    <p>Notification preferences</p>
    <div class="chooser-option" onclick="return false;" style="cursor:default;">
      <div class="chooser-icon" id="settingsPushIcon">🔕</div>
      <div>
        <div class="chooser-title" id="settingsPushStatus">Notifications off</div>
        <div class="chooser-desc" id="settingsPushDesc">Tap below to enable phone alerts for new setups</div>
      </div>
    </div>
    <div class="chooser-option" onclick="enablePush()">
      <div class="chooser-icon">🔔</div>
      <div>
        <div class="chooser-title">Enable Notifications</div>
        <div class="chooser-desc">Get alerted even when your phone is locked</div>
      </div>
    </div>
    <div class="chooser-option" onclick="toggleSound()">
      <div class="chooser-icon" id="settingsSoundIcon">🔊</div>
      <div>
        <div class="chooser-title" id="settingsSoundTitle">Sound: On</div>
        <div class="chooser-desc">Play a sound when a new setup card appears in-app</div>
      </div>
    </div>
    <div class="chooser-option" onclick="closeSettings()" style="justify-content:center;">
      <div class="chooser-title">Close</div>
    </div>
  </div>
</div>

<div class="chart-embed-card" id="tvCard">
  <div class="chart-embed-header">
    <h2><span class="live-dot"></span>XAUUSD Live Chart</h2>
  </div>
  <div id="tvChartContainer"></div>
</div>

<div class="chart-embed-card" id="setupsCard" style="display:none;">
  <div class="chart-embed-header">
    <h2><span class="live-dot"></span>My Setups Chart</h2>
  </div>
  <div id="setupsChartContainer" style="height:340px; position:relative;"></div>
  <div class="setups-hint">Tap near a marker to see its Entry / SL / TP details</div>
  <div id="setupsTooltip" class="setups-tooltip" style="display:none;"></div>
</div>

<div class="week-panel" id="weekPanel">
  <h2>📅 Last 7 Days</h2>
  <div class="week-grid" id="weekGrid">
    <div class="week-cell"><div class="num">...</div><div class="lbl">Trades</div></div>
    <div class="week-cell sl"><div class="num">...</div><div class="lbl">Hit SL</div></div>
    <div class="week-cell tp"><div class="num">...</div><div class="lbl">Hit TP</div></div>
    <div class="week-cell"><div class="num">...</div><div class="lbl">Still Open</div></div>
  </div>
  <div class="week-note" id="weekNote"></div>
</div>

<div class="stats-strip" id="statsStrip"></div>
<div class="filters" id="filters"></div>
<div id="content"><div class="empty"><div class="emoji">⏳</div>Loading signals...</div></div>

<script>
let allSignals = [];
let currentFilter = "all";

function applyTheme(t) {
  document.documentElement.setAttribute("data-theme", t);
  document.getElementById("themeKnob").textContent = t === "light" ? "\u2600\ufe0f" : "\ud83c\udf19";
  localStorage.setItem("theme", t);
  const choice = localStorage.getItem("chartChoice");
  if (choice === "tv" && tvScriptLoaded !== undefined) {
    if (document.getElementById("tvCard").style.display !== "none") initTVWidget(t);
  } else if (choice === "setups" && window._lwChart) {
    const isLight = t === "light";
    window._lwChart.applyOptions({
      layout: { background: { color: isLight ? "#ffffff" : "#131722" }, textColor: isLight ? "#16181d" : "#d1d4dc" },
      grid: { vertLines: { color: isLight ? "#e2e6ea" : "#242832" }, horzLines: { color: isLight ? "#e2e6ea" : "#242832" } }
    });
  }
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

// ============= CHART CHOOSER =============
function openChooser() {
  document.getElementById("chooserOverlay").classList.add("show");
}
function closeChooser() {
  document.getElementById("chooserOverlay").classList.remove("show");
}

function openSettings() {
  document.getElementById("settingsOverlay").classList.add("show");
  refreshSettingsPanel();
}
function closeSettings() {
  document.getElementById("settingsOverlay").classList.remove("show");
}
function refreshSettingsPanel() {
  const icon = document.getElementById("settingsPushIcon");
  const status = document.getElementById("settingsPushStatus");
  const desc = document.getElementById("settingsPushDesc");
  if ("Notification" in window && Notification.permission === "granted") {
    icon.textContent = "🔔";
    status.textContent = "Notifications on";
    desc.textContent = "You'll be alerted even when your phone is locked";
  } else {
    icon.textContent = "🔕";
    status.textContent = "Notifications off";
    desc.textContent = "Tap below to enable phone alerts for new setups";
  }
  const soundOn = localStorage.getItem("soundEnabled") !== "off";
  document.getElementById("settingsSoundIcon").textContent = soundOn ? "🔊" : "🔇";
  document.getElementById("settingsSoundTitle").textContent = "Sound: " + (soundOn ? "On" : "Off");
}
function toggleSound() {
  const soundOn = localStorage.getItem("soundEnabled") !== "off";
  localStorage.setItem("soundEnabled", soundOn ? "off" : "on");
  refreshSettingsPanel();
}
let lwScriptLoaded = false;
let setupsChartBuilt = false;

function selectChart(which) {
  localStorage.setItem("chartChoice", which);
  closeChooser();
  if (which === "tv") {
    document.getElementById("tvCard").style.display = "";
    document.getElementById("setupsCard").style.display = "none";
    initTVWidget(document.documentElement.getAttribute("data-theme") || "dark");
  } else {
    document.getElementById("tvCard").style.display = "none";
    document.getElementById("setupsCard").style.display = "";
    initSetupsChart();
  }
}

function initSetupsChart() {
  function build() {
    if (setupsChartBuilt) { loadSetupsData(); return; }
    setupsChartBuilt = true;
    const theme = document.documentElement.getAttribute("data-theme") || "dark";
    const isLight = theme === "light";
    window._lwChart = LightweightCharts.createChart(document.getElementById("setupsChartContainer"), {
      layout: { background: { color: isLight ? "#ffffff" : "#131722" }, textColor: isLight ? "#16181d" : "#d1d4dc" },
      grid: { vertLines: { color: isLight ? "#e2e6ea" : "#242832" }, horzLines: { color: isLight ? "#e2e6ea" : "#242832" } },
      timeScale: { timeVisible: true, secondsVisible: false },
      autoSize: true
    });
    window._lwSeries = window._lwChart.addCandlestickSeries({
      upColor: "#26a69a", downColor: "#ef5350", borderVisible: false,
      wickUpColor: "#26a69a", wickDownColor: "#ef5350"
    });
    window._lwChart.subscribeClick(function(param) {
      showSetupTooltip(param);
    });
    loadSetupsData();
  }
  if (lwScriptLoaded) { build(); return; }
  const s = document.createElement("script");
  s.src = "https://unpkg.com/lightweight-charts@4.1.3/dist/lightweight-charts.standalone.production.js";
  s.onload = function() { lwScriptLoaded = true; build(); };
  document.body.appendChild(s);
}

async function loadSetupsData() {
  try {
    const res = await fetch("/candles");
    const data = await res.json();
    const bars = data.bars || [];
    if (bars.length === 0) return;
    window._lwSeries.setData(bars);

    const withTime = allSignals.filter(s => s.kind === "signal" && s.time_unix);
    const markers = withTime.map(s => ({
      time: s.time_unix,
      position: s.signal === "BUY" ? "belowBar" : "aboveBar",
      color: s.signal === "BUY" ? "#3fb950" : "#f85149",
      shape: s.signal === "BUY" ? "arrowUp" : "arrowDown",
      text: s.signal
    })).sort((a, b) => a.time - b.time);
    window._lwSeries.setMarkers(markers);
    window._lwSignals = withTime;

    window._lwSeries.priceLines?.forEach(pl => window._lwSeries.removePriceLine(pl));
    window._lwSeries.priceLines = [];
    if (withTime.length > 0) {
      const latest = withTime[withTime.length - 1];
      const lines = [
        [parseFloat(latest.entry), "#2962ff", "Entry"],
        [parseFloat(latest.sl), "#f85149", "SL"],
        [parseFloat(latest.tp1), "#3fb950", "TP1"],
        [parseFloat(latest.tp2), "#3fb950", "TP2"],
        [parseFloat(latest.tp3), "#3fb950", "TP3"]
      ];
      lines.forEach(([price, color, title]) => {
        const pl = window._lwSeries.createPriceLine({ price, color, lineWidth: 1, lineStyle: 2, title });
        window._lwSeries.priceLines.push(pl);
      });
    }
    window._lwChart.timeScale().fitContent();
  } catch (e) {
    console.log("Setups chart load failed", e);
  }
}

function showSetupTooltip(param) {
  const tip = document.getElementById("setupsTooltip");
  if (!param.time || !window._lwSignals || window._lwSignals.length === 0) {
    tip.style.display = "none";
    return;
  }
  let closest = null, closestDiff = Infinity;
  window._lwSignals.forEach(s => {
    const diff = Math.abs(s.time_unix - param.time);
    if (diff < closestDiff) { closestDiff = diff; closest = s; }
  });
  if (!closest || closestDiff > 3600 * 6) {
    tip.style.display = "none";
    return;
  }
  tip.innerHTML = `
    <div class="t-title">${closest.signal} - ${closest.time}</div>
    <div class="t-row"><span class="t-label">Entry</span><span>${closest.entry}</span></div>
    <div class="t-row"><span class="t-label">SL</span><span>${closest.sl}</span></div>
    <div class="t-row"><span class="t-label">TP1</span><span>${closest.tp1}</span></div>
    <div class="t-row"><span class="t-label">TP2</span><span>${closest.tp2}</span></div>
    <div class="t-row"><span class="t-label">TP3</span><span>${closest.tp3}</span></div>
  `;
  tip.style.left = Math.min(param.point.x, 160) + "px";
  tip.style.top = "10px";
  tip.style.display = "block";
}

function urlBase64ToUint8Array(base64String) {
  const padding = "=".repeat((4 - base64String.length % 4) % 4);
  const base64 = (base64String + padding).replace(/-/g, "+").replace(/_/g, "/");
  const rawData = atob(base64);
  const outputArray = new Uint8Array(rawData.length);
  for (let i = 0; i < rawData.length; i++) outputArray[i] = rawData.charCodeAt(i);
  return outputArray;
}

function updateNotifyBtn() {
  const btn = document.getElementById("notifyBtn");
  if (!("Notification" in window)) { btn.style.display = "none"; return; }
  if (Notification.permission === "granted") {
    btn.textContent = "🔔";
    btn.title = "Notifications enabled";
  } else {
    btn.textContent = "🔕";
    btn.title = "Tap to enable notifications";
  }
}

async function enablePush() {
  if (!("serviceWorker" in navigator) || !("PushManager" in window)) {
    alert("Push notifications aren't supported in this browser.");
    return;
  }
  if (Notification.permission === "denied") {
    alert("Notifications were previously blocked for this site. Your browser won't ask again automatically.\n\nTo fix: tap the lock/info icon next to the address bar → Site settings → Notifications → set to Allow, then reload this page and tap the bell again.");
    return;
  }
  try {
    const permission = await Notification.requestPermission();
    if (permission !== "granted") {
      alert("Notification permission was not granted, so alerts can't be enabled right now.");
      updateNotifyBtn();
      return;
    }
    const reg = await navigator.serviceWorker.ready;
    const keyRes = await fetch("/vapid-public-key");
    const keyData = await keyRes.json();
    let sub = await reg.pushManager.getSubscription();
    if (!sub) {
      sub = await reg.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: urlBase64ToUint8Array(keyData.key)
      });
    }
    await fetch("/subscribe", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(sub)
    });
    updateNotifyBtn();
  } catch (e) {
    console.log("Push subscribe failed", e);
    alert("Could not enable notifications: " + (e && e.message ? e.message : e));
  }
  updateNotifyBtn();
  refreshSettingsPanel();
}

const savedChoice = localStorage.getItem("chartChoice");
if (savedChoice) {
  selectChart(savedChoice);
} else {
  openChooser();
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

async function loadWeekStats() {
  try {
    const res = await fetch("/stats7d");
    const s = await res.json();
    const grid = document.getElementById("weekGrid");
    const cells = grid.querySelectorAll(".week-cell .num");
    cells[0].textContent = s.total;
    cells[1].textContent = s.sl_hit;
    cells[2].textContent = s.tp_hit;
    cells[3].textContent = s.open;
    const note = document.getElementById("weekNote");
    if (s.total === 0) {
      note.innerHTML = "No setups yet in the last 7 days - this fills in automatically once your indicator fires a signal.";
    } else {
      let parts = [];
      if (s.win_rate !== null && s.win_rate !== undefined) parts.push(`Win rate: <b>${s.win_rate}%</b>`);
      if (s.avg_mfe_r !== null && s.avg_mfe_r !== undefined) parts.push(`Avg best move: <b>${s.avg_mfe_r}R</b>`);
      if (s.avg_mae_r !== null && s.avg_mae_r !== undefined) parts.push(`Avg worst move: <b>${s.avg_mae_r}R</b>`);
      if (s.avg_mfe_r_on_losses !== null && s.avg_mfe_r_on_losses !== undefined) {
        parts.push(`Losers moved <b>${s.avg_mfe_r_on_losses}R</b> in your favor before reversing`);
      }
      if (s.untracked > 0) parts.push(`${s.untracked} not counted (no price history)`);
      note.innerHTML = parts.join(" · ") || "";
    }
  } catch (e) {
    document.getElementById("weekNote").textContent = "Could not load weekly results.";
  }
}

let lastSeenSignalKey = null;
function playAlertSound() {
  if (localStorage.getItem("soundEnabled") === "off") return;
  try {
    const ctx = new (window.AudioContext || window.webkitAudioContext)();
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.frequency.value = 880;
    gain.gain.setValueAtTime(0.15, ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.4);
    osc.start();
    osc.stop(ctx.currentTime + 0.4);
  } catch (e) {}
}

async function load(manual) {
  try {
    const res = await fetch("/latest");
    const data = await res.json();
    allSignals = data.signals || [];
    if (allSignals.length > 0) {
      const topKey = allSignals[0].time + allSignals[0].signal + allSignals[0].kind;
      if (lastSeenSignalKey !== null && topKey !== lastSeenSignalKey) {
        playAlertSound();
      }
      lastSeenSignalKey = topKey;
    }
    renderStats();
    renderFilters();
    renderCards();
  } catch (e) {
    document.getElementById("content").innerHTML = '<div class="empty"><div class="emoji">\u26a0\ufe0f</div>Could not load signals. It will retry automatically.</div>';
  }
}

async function loadTicker() {
  try {
    const res = await fetch("/crypto-ticker");
    const data = await res.json();
    const coins = data.coins || [];
    if (coins.length === 0) return;
    const itemHtml = (c) => {
      const dir = c.change_pct >= 0 ? "up" : "down";
      const arrow = c.change_pct >= 0 ? "▲" : "▼";
      const priceStr = c.price >= 1 ? c.price.toLocaleString(undefined, {maximumFractionDigits: 2}) : c.price.toPrecision(4);
      const tag = c.type === "gainer" ? '<span class="tgainer-tag">TOP GAINER</span>' : "";
      const name = c.symbol;
      return `<span class="ticker-item">${tag}<span class="tsym">${name}</span><span class="tprice">$${priceStr}</span><span class="tchange ${dir}">${arrow} ${Math.abs(c.change_pct).toFixed(2)}%</span></span>`;
    };
    // Render the list twice back-to-back so the CSS animation (translateX -50%) loops seamlessly
    const html = coins.map(itemHtml).join("") + coins.map(itemHtml).join("");
    document.getElementById("tickerTrack").innerHTML = html;
  } catch (e) {
    // leave existing ticker content in place on a transient failure
  }
}

load();
loadTicker();
loadWeekStats();
setInterval(load, 20000);
setInterval(loadTicker, 120000);
if ("serviceWorker" in navigator) {
  navigator.serviceWorker.register("/sw.js").catch(()=>{});
}
updateNotifyBtn();
</script>
</body>
</html>"""
    return Response(html, mimetype="text/html")


@app.route("/manifest.json", methods=["GET"])
def manifest():
    m = {
        "name": "Bakale's Trading",
        "short_name": "Bakale's Trading",
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
    js = """
self.addEventListener('fetch', function(e){});

self.addEventListener('push', function(event) {
  let data = { title: 'Bakale\\'s Trading', body: 'New signal available', url: '/' };
  try { data = event.data.json(); } catch (e) {}
  const options = {
    body: data.body,
    icon: '/icon192.png',
    badge: '/icon192.png',
    vibrate: [200, 100, 200],
    data: { url: data.url || '/' }
  };
  event.waitUntil(self.registration.showNotification(data.title, options));
});

self.addEventListener('notificationclick', function(event) {
  event.notification.close();
  const url = event.notification.data && event.notification.data.url ? event.notification.data.url : '/';
  event.waitUntil(
    clients.matchAll({ type: 'window' }).then(function(clientList) {
      for (const client of clientList) {
        if (client.url.includes(self.location.origin) && 'focus' in client) return client.focus();
      }
      if (clients.openWindow) return clients.openWindow(url);
    })
  );
});
"""
    return Response(js, mimetype="application/javascript")


@app.route("/icon192.png", methods=["GET"])
def icon192():
    return Response(base64.b64decode(ICON_192_B64), mimetype="image/png")


@app.route("/icon512.png", methods=["GET"])
def icon512():
    return Response(base64.b64decode(ICON_512_B64), mimetype="image/png")


FOREX_CURRENCIES = {"EUR", "USD", "JPY", "GBP", "CHF", "AUD", "CAD", "NZD"}
FF_NOTIFIED_PATH = "data/ff_notified.json"
FF_SETTINGS_PATH = "data/ff_settings.json"
FF_ALERT_WINDOW_SECONDS = 15 * 60  # matches the ~15-min external check interval

_ff_cache = {"data": None, "ts": 0}
FF_CACHE_TTL = 1800  # 30 min - Forex Factory limits their feed to 2 requests/5min


def fetch_forex_calendar():
    import time as _time
    now = _time.time()
    if _ff_cache["data"] is not None and (now - _ff_cache["ts"]) < FF_CACHE_TTL:
        return _ff_cache["data"]
    try:
        r = requests.get("https://nfs.faireconomy.media/ff_calendar_thisweek.json", timeout=20)
        r.raise_for_status()
        raw = r.json()
    except Exception as e:
        print("Forex Factory calendar fetch failed:", repr(e))
        return _ff_cache["data"] if _ff_cache["data"] is not None else []

    events = []
    for e in raw:
        if e.get("country") not in FOREX_CURRENCIES:
            continue
        try:
            dt = datetime.fromisoformat(e["date"])
        except Exception:
            continue
        events.append({
            "title": e.get("title", ""), "country": e["country"], "impact": e.get("impact", ""),
            "forecast": e.get("forecast", ""), "previous": e.get("previous", ""),
            "date_iso": dt.isoformat(), "time_unix": int(dt.timestamp()),
        })
    events.sort(key=lambda x: x["time_unix"])
    _ff_cache["data"] = events
    _ff_cache["ts"] = now
    return events


@app.route("/forex-news", methods=["GET"])
def forex_news():
    events = fetch_forex_calendar()
    now_unix = int(datetime.now(timezone.utc).timestamp())
    upcoming = [e for e in events if e["time_unix"] >= now_unix - 3600]
    return Response(json.dumps({"events": upcoming}), mimetype="application/json")


@app.route("/forex-alerts-setting", methods=["GET", "POST"])
def forex_alerts_setting():
    settings, sha = gh_load_json(FF_SETTINGS_PATH)
    current = settings[0] if isinstance(settings, list) and settings else {"enabled": True}
    if request.method == "GET":
        return Response(json.dumps(current), mimetype="application/json")
    body = request.get_json(silent=True) or {}
    current = {"enabled": bool(body.get("enabled", True))}
    gh_save_json(FF_SETTINGS_PATH, [current], sha)
    return Response(json.dumps(current), mimetype="application/json")


@app.route("/check-forex-news", methods=["GET"])
def check_forex_news():
    settings, _ = gh_load_json(FF_SETTINGS_PATH)
    enabled = True
    if isinstance(settings, list) and settings:
        enabled = bool(settings[0].get("enabled", True))
    if not enabled:
        return json.dumps({"skipped": "alerts disabled"}), 200

    events = fetch_forex_calendar()
    now_unix = int(datetime.now(timezone.utc).timestamp())
    imminent = [
        e for e in events
        if e["impact"] == "High" and now_unix <= e["time_unix"] <= now_unix + FF_ALERT_WINDOW_SECONDS
    ]
    if not imminent:
        return json.dumps({"checked": len(events), "notified": 0}), 200

    notified_list, sha = gh_load_json(FF_NOTIFIED_PATH)
    if not isinstance(notified_list, list):
        notified_list = []
    notified_keys = set(notified_list)
    cutoff = now_unix - 7 * 24 * 3600
    notified_list = [k for k in notified_list if int(k.split("|")[-1]) >= cutoff]

    sent = 0
    for e in imminent:
        key = f"{e['country']}|{e['title']}|{e['time_unix']}"
        if key in notified_keys:
            continue
        try:
            send_push_to_all(
                f"📰 {e['country']} High Impact: {e['title']}",
                f"Forecast {e['forecast'] or 'N/A'} | Previous {e['previous'] or 'N/A'}",
                "/news"
            )
            notified_list.append(key)
            sent += 1
        except Exception as ex:
            print("Forex news push failed for", key, ":", repr(ex))

    gh_save_json(FF_NOTIFIED_PATH, notified_list, sha)
    return json.dumps({"checked": len(events), "notified": sent}), 200


@app.route("/news", methods=["GET"])
def forex_news_page():
    html = r"""<!DOCTYPE html>
<html><head><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Forex News</title>
<style>
body { background:#0f1115; color:#eee; font-family:-apple-system,sans-serif; padding:16px; margin:0; }
h2 { margin:0 0 4px; font-size:20px; }
.sub { color:#888; font-size:12px; margin-bottom:14px; }
.toggle-row { display:flex; justify-content:space-between; align-items:center; background:#1a1d24; border:1px solid #2a2e39; border-radius:12px; padding:12px 14px; margin-bottom:16px; }
.toggle { width:44px; height:26px; border-radius:20px; background:#333; position:relative; cursor:pointer; transition:background 0.2s; }
.toggle.on { background:#2ea043; }
.toggle .knob { position:absolute; top:2px; left:2px; width:22px; height:22px; border-radius:50%; background:white; transition:transform 0.2s; }
.toggle.on .knob { transform:translateX(18px); }
.item { background:#1a1d24; border:1px solid #2a2e39; border-radius:12px; padding:12px 14px; margin-bottom:8px; }
.item .top { display:flex; justify-content:space-between; align-items:center; margin-bottom:4px; }
.badge { font-size:11px; font-weight:700; padding:3px 8px; border-radius:6px; }
.badge.High { background:#3a1a1a; color:#ef5350; }
.badge.Medium { background:#3a2f1a; color:#f4c430; }
.badge.Low { background:#1a2a1a; color:#8fbf8f; }
.ccy { font-weight:700; font-size:12px; color:#aaa; }
.time { font-size:11px; color:#888; }
.title { font-size:13.5px; margin-top:4px; }
.fc { font-size:11.5px; color:#888; margin-top:3px; }
.empty { text-align:center; color:#888; padding:40px 0; font-size:13px; }
</style></head>
<body>
<h2>📰 Forex News</h2>
<div class="sub">High-impact economic events for EUR, USD, JPY, GBP, CHF, AUD, CAD, NZD</div>
<div class="toggle-row">
  <span>Push alerts for high-impact events</span>
  <div class="toggle" id="ffToggle" onclick="toggleAlerts()"><div class="knob"></div></div>
</div>
<div id="list"><div class="empty">Loading…</div></div>
<script>
async function loadToggle() {
  try {
    const res = await fetch("/forex-alerts-setting");
    const s = await res.json();
    document.getElementById("ffToggle").classList.toggle("on", s.enabled !== false);
  } catch (e) {}
}
async function toggleAlerts() {
  const el = document.getElementById("ffToggle");
  const newState = !el.classList.contains("on");
  el.classList.toggle("on", newState);
  await fetch("/forex-alerts-setting", {
    method: "POST", headers: {"Content-Type": "application/json"},
    body: JSON.stringify({enabled: newState})
  });
}
async function loadNews() {
  const list = document.getElementById("list");
  try {
    const res = await fetch("/forex-news");
    const data = await res.json();
    const events = data.events || [];
    if (events.length === 0) {
      list.innerHTML = '<div class="empty">No upcoming events found.</div>';
      return;
    }
    list.innerHTML = events.map(e => {
      const d = new Date(e.time_unix * 1000);
      const timeStr = d.toLocaleString(undefined, {weekday:"short", hour:"2-digit", minute:"2-digit", month:"short", day:"numeric"});
      return `<div class="item">
        <div class="top"><span class="ccy">${e.country}</span><span class="badge ${e.impact}">${e.impact || "?"}</span></div>
        <div class="title">${e.title}</div>
        <div class="fc">Forecast: ${e.forecast || "-"} · Previous: ${e.previous || "-"}</div>
        <div class="time">${timeStr}</div>
      </div>`;
    }).join("");
  } catch (e) {
    list.innerHTML = '<div class="empty">Could not load news.</div>';
  }
}
loadToggle();
loadNews();
</script>
</body></html>"""
    return Response(html, mimetype="text/html")


@app.route("/history", methods=["GET"])
def notification_history_page():
    html = r"""<!DOCTYPE html>
<html><head><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Notification History</title>
<style>
body { background:#0f1115; color:#eee; font-family:-apple-system,sans-serif; padding:16px; margin:0; }
h2 { margin:0 0 4px; font-size:20px; }
.sub { color:#888; font-size:12px; margin-bottom:16px; }
.item {
  background:#1a1d24; border:1px solid #2a2e39; border-radius:12px; padding:12px 14px; margin-bottom:10px;
}
.item .top { display:flex; justify-content:space-between; align-items:center; margin-bottom:4px; }
.badge { font-size:11px; font-weight:700; padding:3px 8px; border-radius:6px; }
.badge.buy { background:#1a3a2e; color:#26a69a; }
.badge.sell { background:#3a1a1a; color:#ef5350; }
.badge.touch { background:#3a2f1a; color:#f4c430; }
.time { font-size:11px; color:#888; }
.detail { font-size:12.5px; color:#bbb; margin-top:4px; }
.empty { text-align:center; color:#888; padding:40px 0; font-size:13px; }
</style></head>
<body>
<h2>🔔 Notification History</h2>
<div class="sub">Every setup and zone-touch alert ever sent - useful if you missed push notifications while offline.</div>
<div id="list"><div class="empty">Loading…</div></div>
<script>
async function load() {
  const list = document.getElementById("list");
  try {
    const res = await fetch("/latest");
    const data = await res.json();
    const signals = data.signals || [];
    if (signals.length === 0) {
      list.innerHTML = '<div class="empty">No notifications yet.</div>';
      return;
    }
    list.innerHTML = signals.map(s => {
      const isTouch = s.kind === "touch";
      const badgeClass = isTouch ? "touch" : (s.signal === "BUY" ? "buy" : "sell");
      const label = isTouch ? "ZONE TOUCH" : s.signal;
      return `<div class="item">
        <div class="top"><span class="badge ${badgeClass}">${label}</span><span class="time">${s.time || ""}</span></div>
        <div class="detail">${s.symbol || "XAUUSD"} · Entry ${s.entry || "-"} · SL ${s.sl || "-"} · TP1 ${s.tp1 || "-"}</div>
      </div>`;
    }).join("");
  } catch (e) {
    list.innerHTML = '<div class="empty">Could not load history.</div>';
  }
}
load();
</script>
</body></html>"""
    return Response(html, mimetype="text/html")


@app.route("/add", methods=["GET"])
def add_form():
    html = r"""<!DOCTYPE html>
<html><head><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Add Past Setup</title>
<style>
body { background:#0f1115; color:#eee; font-family:-apple-system,sans-serif; padding:20px; }
h2 { margin-top:0; }
label { display:block; margin-top:14px; font-size:14px; color:#aaa; }
input, select { width:100%; box-sizing:border-box; padding:10px; margin-top:4px; border-radius:8px; border:1px solid #333; background:#1a1d24; color:#fff; font-size:16px; }
button { margin-top:20px; width:100%; padding:14px; border:none; border-radius:10px; background:#f4c430; color:#000; font-weight:700; font-size:16px; }
.msg { margin-top:14px; padding:10px; border-radius:8px; }
.ok { background:#1a3a1a; color:#8f8; }
.err { background:#3a1a1a; color:#f88; }
</style></head>
<body>
<h2>Add a Past Setup</h2>
<p style="color:#888;font-size:13px">Enter values exactly as shown on your TradingView chart/log for a setup that already fired.</p>
<form id="f">
  <label>Symbol</label>
  <input name="symbol" value="XAUUSD" required>
  <label>Signal</label>
  <select name="signal"><option>BUY</option><option>SELL</option></select>
  <label>Entry</label>
  <input name="entry" type="number" step="any" required>
  <label>Stop Loss</label>
  <input name="sl" type="number" step="any" required>
  <label>TP1</label>
  <input name="tp1" type="number" step="any" required>
  <label>TP2</label>
  <input name="tp2" type="number" step="any">
  <label>TP3</label>
  <input name="tp3" type="number" step="any">
  <label>Date &amp; Time it fired</label>
  <input name="datetime" type="datetime-local" required>
  <button type="submit">Add Setup</button>
</form>
<div id="result"></div>
<script>
document.getElementById("f").addEventListener("submit", async function(e){
  e.preventDefault();
  const fd = new FormData(e.target);
  const body = Object.fromEntries(fd.entries());
  const res = document.getElementById("result");
  res.innerHTML = "";
  try {
    const r = await fetch("/add-manual-signal", {
      method: "POST",
      headers: {"Content-Type":"application/json"},
      body: JSON.stringify(body)
    });
    const j = await r.json();
    if (r.ok) {
      res.innerHTML = '<div class="msg ok">Added. <a href="/" style="color:#8f8">Go to app</a> or add another below.</div>';
      e.target.reset();
      document.querySelector('input[name="symbol"]').value = "XAUUSD";
    } else {
      res.innerHTML = '<div class="msg err">' + (j.error || "Failed to add") + '</div>';
    }
  } catch (err) {
    res.innerHTML = '<div class="msg err">Network error: ' + err + '</div>';
  }
});
</script>
</body></html>"""
    return Response(html, mimetype="text/html")


SWING_LEN = 5
ATR_LEN = 14
SL_BUFFER_MULT = 0.25
RR = [1.0, 2.0, 3.0]


def compute_atr(bars, length):
    atr = [None] * len(bars)
    trs = []
    for i in range(len(bars)):
        if i == 0:
            tr = bars[i]["high"] - bars[i]["low"]
        else:
            pc = bars[i - 1]["close"]
            tr = max(bars[i]["high"] - bars[i]["low"], abs(bars[i]["high"] - pc), abs(bars[i]["low"] - pc))
        trs.append(tr)
        if i + 1 >= length:
            if atr[i - 1] is None:
                atr[i] = sum(trs[i - length + 1:i + 1]) / length
            else:
                atr[i] = (atr[i - 1] * (length - 1) + tr) / length
    return atr


def find_pivots_15m(bars15, length):
    """Returns confirmed pivot events (onset_time, pivot_high_or_None, pivot_low_or_None).
    onset_time is 'length' bars after the pivot bar itself, matching request.security(lookahead_off)
    non-repainting behavior - the structure level isn't knowable until confirmed."""
    n = len(bars15)
    confirmed = []
    for i in range(length, n - length):
        window = bars15[i - length:i + length + 1]
        h = bars15[i]["high"]
        l = bars15[i]["low"]
        ph = h if h == max(b["high"] for b in window) else None
        pl = l if l == min(b["low"] for b in window) else None
        if ph is not None or pl is not None:
            onset_index = i + length
            if onset_index < n:
                confirmed.append((bars15[onset_index]["time"], ph, pl))
    confirmed.sort(key=lambda x: x[0])
    return confirmed


def detect_choch_signals_dual_tf(bars15, bars1):
    """Structure from 15M pivots, CHoCH break checked on 1-minute closes -
    matches the live indicator's 'CONFIRMATION (1M)' mode exactly."""
    if len(bars15) < (SWING_LEN * 2 + 2) or len(bars1) < ATR_LEN + 2:
        return []

    pivot_events = find_pivots_15m(bars15, SWING_LEN)
    atr1 = compute_atr(bars1, ATR_LEN)

    struct_high = None
    struct_low = None
    trend = 0
    signals = []
    pivot_idx = 0
    n_pivots = len(pivot_events)

    for i in range(1, len(bars1)):
        t = bars1[i]["time"]
        while pivot_idx < n_pivots and pivot_events[pivot_idx][0] <= t:
            _, ph, pl = pivot_events[pivot_idx]
            if ph is not None:
                struct_high = ph
            if pl is not None:
                struct_low = pl
            pivot_idx += 1

        if atr1[i] is None or struct_high is None or struct_low is None:
            continue

        close = bars1[i]["close"]
        prev_close = bars1[i - 1]["close"]

        bullish_choch = (trend != 1) and (prev_close <= struct_high) and (close > struct_high)
        bearish_choch = (trend != -1) and (prev_close >= struct_low) and (close < struct_low)

        if bullish_choch:
            trend = 1
            entry = close
            sl = struct_low - atr1[i] * SL_BUFFER_MULT
            risk = abs(entry - sl)
            signals.append({"time_unix": t, "signal": "BUY", "entry": entry, "sl": sl,
                             "tp1": entry + risk * RR[0], "tp2": entry + risk * RR[1], "tp3": entry + risk * RR[2]})
        elif bearish_choch:
            trend = -1
            entry = close
            sl = struct_high + atr1[i] * SL_BUFFER_MULT
            risk = abs(entry - sl)
            signals.append({"time_unix": t, "signal": "SELL", "entry": entry, "sl": sl,
                             "tp1": entry - risk * RR[0], "tp2": entry - risk * RR[1], "tp3": entry - risk * RR[2]})

    return signals


@app.route("/backfill-historical", methods=["GET"])
def backfill_historical():
    bars15 = fetch_ohlc(interval="15min", outputsize=700)
    bars1 = fetch_ohlc(interval="1min", outputsize=5000)
    if not bars15 or not bars1:
        return json.dumps({"error": "Could not fetch price history (check TWELVE_DATA_KEY)"}), 500

    detected = detect_choch_signals_dual_tf(bars15, bars1)
    if not detected:
        return json.dumps({"detected": 0, "added": 0, "message": "No CHoCH setups found in the fetched history window"})

    history, sha = gh_load_history()
    existing_times = set(h.get("time_unix") for h in history if h.get("time_unix"))

    added = 0
    for s in detected:
        if s["time_unix"] in existing_times:
            continue
        dt_str = datetime.utcfromtimestamp(s["time_unix"]).strftime("%d %b %Y, %H:%M UTC")
        history.append({
            "symbol": "XAUUSD", "signal": s["signal"], "kind": "signal",
            "entry": f'{s["entry"]:.2f}', "sl": f'{s["sl"]:.2f}',
            "tp1": f'{s["tp1"]:.2f}', "tp2": f'{s["tp2"]:.2f}', "tp3": f'{s["tp3"]:.2f}',
            "chart_url": "", "time": dt_str, "time_unix": s["time_unix"]
        })
        added += 1

    history.sort(key=lambda x: x.get("time_unix", 0), reverse=True)
    history = history[:MAX_HISTORY]
    ok = gh_save_history(history, sha)
    if not ok:
        return json.dumps({"error": "Detected signals but GitHub save failed - check /debug-github"}), 500

    return json.dumps({
        "detected": len(detected), "added": added, "already_present": len(detected) - added,
        "bars_used": {"15min": len(bars15), "1min": len(bars1)}
    })


@app.route("/add-manual-signal", methods=["POST"])
def add_manual_signal():
    data = request.get_json(silent=True)
    if not data:
        return json.dumps({"error": "No data received"}), 400
    required = ["symbol", "signal", "entry", "sl", "tp1", "datetime"]
    for f in required:
        if not data.get(f):
            return json.dumps({"error": "Missing field: " + f}), 400
    try:
        import time as _time
        dt = datetime.strptime(data["datetime"], "%Y-%m-%dT%H:%M")
        time_unix = int(dt.timestamp())
        time_str = dt.strftime("%d %b %Y, %H:%M")
    except Exception as e:
        return json.dumps({"error": "Bad date/time: " + str(e)}), 400

    new_entry = {
        "symbol": data["symbol"], "signal": data["signal"], "kind": "signal",
        "entry": str(data["entry"]), "sl": str(data["sl"]),
        "tp1": str(data["tp1"]), "tp2": str(data.get("tp2") or ""), "tp3": str(data.get("tp3") or ""),
        "chart_url": "", "time": time_str, "time_unix": time_unix
    }
    try:
        history, sha = gh_load_history()
        history.insert(0, new_entry)
        history.sort(key=lambda x: x.get("time_unix", 0), reverse=True)
        history = history[:MAX_HISTORY]
        ok = gh_save_history(history, sha)
        if not ok:
            return json.dumps({"error": "GitHub save failed - check /debug-github"}), 500
    except Exception as e:
        return json.dumps({"error": "Save error: " + str(e)}), 500

    return json.dumps({"success": True}), 200


@app.route("/debug-github", methods=["GET"])
def debug_github():
    result = {
        "github_token_present": bool(GITHUB_TOKEN),
        "github_repo_value": GITHUB_REPO,
    }
    if not GITHUB_TOKEN or not GITHUB_REPO:
        result["problem"] = "GITHUB_TOKEN or GITHUB_REPO is missing/empty on the server."
        return Response(json.dumps(result, indent=2), mimetype="application/json")

    url = "https://api.github.com/repos/" + GITHUB_REPO + "/contents/" + HISTORY_PATH
    try:
        r = requests.get(url, headers=gh_headers(), timeout=15)
        result["get_status_code"] = r.status_code
        if r.status_code == 200:
            j = r.json()
            result["file_found"] = True
            result["sha"] = j.get("sha")
            try:
                content = base64.b64decode(j["content"]).decode("utf-8")
                parsed = json.loads(content)
                result["current_entry_count"] = len(parsed)
            except Exception as e:
                result["content_parse_error"] = str(e)
        else:
            result["file_found"] = False
            result["github_api_response"] = r.text[:500]
    except Exception as e:
        result["request_exception"] = str(e)

    return Response(json.dumps(result, indent=2), mimetype="application/json")


TWELVE_DATA_CRYPTO_MAP = {
    "BTC/USD": "BTC", "ETH/USD": "ETH", "BNB/USD": "BNB", "XRP/USD": "XRP", "SOL/USD": "SOL",
    "TRX/USD": "TRX", "DOGE/USD": "DOGE", "ADA/USD": "ADA", "DOT/USD": "DOT", "LINK/USD": "LINK",
    "AVAX/USD": "AVAX", "LTC/USD": "LTC", "ATOM/USD": "ATOM", "NEAR/USD": "NEAR", "SUI/USD": "SUI",
}
COINGECKO_ID_MAP = {
    "BTCUSDT": ("bitcoin", "BTC"), "ETHUSDT": ("ethereum", "ETH"), "BNBUSDT": ("binancecoin", "BNB"),
    "XRPUSDT": ("ripple", "XRP"), "SOLUSDT": ("solana", "SOL"), "TRXUSDT": ("tron", "TRX"),
    "HYPEUSDT": ("hyperliquid", "HYPE"), "DOGEUSDT": ("dogecoin", "DOGE"), "ZECUSDT": ("zcash", "ZEC"),
}
TOP_GAINERS_COUNT = 8
MIN_MARKET_CAP_USD = 20_000_000  # filters out illiquid/low-cap noise from top gainers

_crypto_cache = {"data": None, "ts": 0}
CRYPTO_CACHE_TTL = 600  # seconds - crypto is a bonus feature; gold price reliability takes priority


def fetch_main_coins_via_twelvedata():
    # Per-symbol calls, each isolated - one bad/unsupported symbol can't silently take
    # down the others. Cached for 10 min, and spaced slightly, so this burst of calls
    # never competes hard with the gold price fetching that shares the same API key/quota.
    import time as _time
    if not TWELVE_DATA_KEY:
        return []
    results = []
    for i, (td_symbol, label) in enumerate(TWELVE_DATA_CRYPTO_MAP.items()):
        if i > 0:
            _time.sleep(0.12)
        try:
            r = requests.get("https://api.twelvedata.com/quote",
                              params={"symbol": td_symbol, "apikey": TWELVE_DATA_KEY}, timeout=15)
            d = r.json()
            if "close" not in d or "percent_change" not in d:
                print("Twelve Data crypto quote missing fields for", td_symbol, ":", d)
                continue
            results.append({
                "symbol": label, "price": float(d["close"]),
                "change_pct": float(d["percent_change"]), "type": "main"
            })
        except Exception as e:
            print("Twelve Data crypto quote failed for", td_symbol, ":", repr(e))
            continue
    return results


def _fetch_coingecko_markets(**params):
    base = {"vs_currency": "usd", "price_change_percentage": "24h"}
    base.update(params)
    r = requests.get("https://api.coingecko.com/api/v3/coins/markets", params=base, timeout=15)
    r.raise_for_status()
    return r.json()


@app.route("/debug-crypto", methods=["GET"])
def debug_crypto():
    result = {}
    try:
        main_coins = fetch_main_coins_via_twelvedata()
        result["twelvedata_main_coins_success"] = len(main_coins) > 0
        result["twelvedata_coins_returned"] = [c["symbol"] for c in main_coins]
        result["twelvedata_coins_missing"] = [
            label for td_symbol, label in TWELVE_DATA_CRYPTO_MAP.items()
            if label not in [c["symbol"] for c in main_coins]
        ]
        result["twelvedata_sample"] = main_coins[0] if main_coins else None
    except Exception as e:
        result["twelvedata_main_coins_success"] = False
        result["twelvedata_error"] = repr(e)
    try:
        top_data = _fetch_coingecko_markets(order="market_cap_desc", per_page=10, page=1)
        result["coingecko_gainers_success"] = True
        result["coingecko_sample_count"] = len(top_data)
    except Exception as e:
        result["coingecko_gainers_success"] = False
        result["coingecko_error"] = repr(e)
    return Response(json.dumps(result, indent=2, default=str), mimetype="application/json")


@app.route("/crypto-ticker", methods=["GET"])
def crypto_ticker():
    import time as _time
    now = _time.time()
    if _crypto_cache["data"] is not None and (now - _crypto_cache["ts"]) < CRYPTO_CACHE_TTL:
        return Response(json.dumps({"coins": _crypto_cache["data"]}), mimetype="application/json")

    results = []
    try:
        results.extend(fetch_main_coins_via_twelvedata())
    except Exception as e:
        print("Crypto ticker main-coins (Twelve Data) fetch failed:", repr(e))

    try:
        top_data = _fetch_coingecko_markets(order="market_cap_desc", per_page=250, page=1)
        main_gecko_ids = set(v[0] for v in COINGECKO_ID_MAP.values())
        gainer_candidates = [
            d for d in top_data
            if d["id"] not in main_gecko_ids
            and d.get("price_change_percentage_24h") is not None
            and d.get("market_cap") and d["market_cap"] >= MIN_MARKET_CAP_USD
            and d["price_change_percentage_24h"] > 0
        ]
        gainer_candidates.sort(key=lambda d: d["price_change_percentage_24h"], reverse=True)
        for d in gainer_candidates[:TOP_GAINERS_COUNT]:
            results.append({
                "symbol": d["symbol"].upper(), "price": float(d["current_price"]),
                "change_pct": float(d["price_change_percentage_24h"]), "type": "gainer"
            })
    except Exception as e:
        # Gainers are a bonus feature - main coins (Twelve Data) still work even if this fails
        print("Crypto ticker gainers (CoinGecko) fetch failed:", repr(e))

    if results:
        _crypto_cache["data"] = results
        _crypto_cache["ts"] = now
        return Response(json.dumps({"coins": results}), mimetype="application/json")

    # Any failure (rate limit, network issue, etc.) - serve the last successful
    # result regardless of how stale it is, rather than showing nothing.
    if _crypto_cache["data"] is not None:
        return Response(json.dumps({"coins": _crypto_cache["data"], "stale": True}), mimetype="application/json")
    return Response(json.dumps({"coins": []}), mimetype="application/json")



@app.route("/ping", methods=["GET"])
def ping():
    return "pong", 200


@app.route("/vapid-public-key", methods=["GET"])
def vapid_public_key():
    return Response(json.dumps({"key": VAPID_PUBLIC_KEY}), mimetype="application/json")


@app.route("/subscribe", methods=["POST"])
def subscribe():
    sub = request.get_json(silent=True)
    if not sub or "endpoint" not in sub:
        return "Invalid subscription", 400
    subs, sha = gh_load_json(SUBS_PATH)
    if not any(s.get("endpoint") == sub.get("endpoint") for s in subs):
        subs.append(sub)
        gh_save_json(SUBS_PATH, subs, sha)
    return "OK", 200


@app.route("/debug-chart", methods=["GET"])
def debug_chart():
    result = {"twelve_data_key_present": bool(TWELVE_DATA_KEY)}
    if not TWELVE_DATA_KEY:
        result["problem"] = "TWELVE_DATA_KEY missing on the server."
        return Response(json.dumps(result, indent=2), mimetype="application/json")
    try:
        closes = fetch_closes()
        result["closes_fetched"] = len(closes) if closes else 0
        if not closes or len(closes) <= 10:
            result["problem"] = "Not enough price data returned from Twelve Data"
            return Response(json.dumps(result, indent=2), mimetype="application/json")
        config = build_chart_config(closes, 4655.07, 4681.79, 4626.35, 4601.64, 4574.92, "SELL")
        png_bytes = render_chart_png_bytes(config)
        result["chart_render_success"] = True
        result["chart_bytes"] = len(png_bytes)
    except Exception as e:
        result["chart_render_success"] = False
        result["error"] = repr(e)
    return Response(json.dumps(result, indent=2), mimetype="application/json")


@app.route("/chart-image", methods=["GET"])
def chart_image():
    try:
        entry = float(request.args.get("entry"))
        sl = float(request.args.get("sl"))
        tp1 = float(request.args.get("tp1"))
        tp2 = float(request.args.get("tp2", tp1))
        tp3 = float(request.args.get("tp3", tp1))
        signal = request.args.get("signal", "BUY")
    except (TypeError, ValueError):
        return "Bad or missing parameters", 400

    closes = fetch_closes()
    if not closes or len(closes) <= 10:
        return "Could not fetch price data", 502
    try:
        config = build_chart_config(closes, entry, sl, tp1, tp2, tp3, signal)
        png_bytes = render_chart_png_bytes(config)
    except Exception as e:
        return "Chart render failed: " + str(e), 502
    return Response(png_bytes, mimetype="image/png")


@app.route("/candles", methods=["GET"])
def candles():
    bars = fetch_ohlc(outputsize=300)
    if bars is None:
        return Response(json.dumps({"bars": []}), mimetype="application/json")
    return Response(json.dumps({"bars": bars}), mimetype="application/json")


@app.route("/stats7d", methods=["GET"])
def stats7d():
    return Response(json.dumps(get_7day_stats()), mimetype="application/json")


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
                config = build_chart_config(closes, float(entry), float(sl), float(tp1), float(tp2), float(tp3), signal)
                png_bytes = render_chart_png_bytes(config)
                r = send_photo_bytes(png_bytes, caption)
                chart_sent = r.status_code == 200
                if not chart_sent:
                    print("Telegram photo send failed:", r.status_code, r.text[:300])
                chart_url_for_app = ("/chart-image?signal=" + signal + "&entry=" + str(entry) +
                                      "&sl=" + str(sl) + "&tp1=" + str(tp1) + "&tp2=" + str(tp2) + "&tp3=" + str(tp3))
        except Exception as e:
            print("Chart generation/send failed:", repr(e))

    if not chart_sent:
        send_text(caption)

    new_entry = {
        "symbol": symbol, "signal": signal, "kind": kind,
        "entry": entry, "sl": sl, "tp1": tp1, "tp2": tp2, "tp3": tp3,
        "chart_url": chart_url_for_app,
        "time": datetime.utcnow().strftime("%d %b %Y, %H:%M UTC"),
        "time_unix": int(datetime.utcnow().timestamp())
    }

    try:
        history, sha = gh_load_history()
        history.insert(0, new_entry)
        history = history[:MAX_HISTORY]
        gh_save_history(history, sha)
    except Exception as e:
        print("GitHub history save failed:", e)

    try:
        push_dot = "🟢" if signal == "BUY" else "🔴"
        push_title = push_dot + " " + signal + (" Setup" if kind == "signal" else " Zone Touched Again")
        push_body = "Entry " + entry + " | SL " + sl + " | TP1 " + tp1
        send_push_to_all(push_title, push_body, "/")
    except Exception as e:
        print("Push notification failed:", e)

    return "OK", 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
