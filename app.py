import os
import asyncio
import requests
from datetime import datetime
import pytz
from flask import Flask
from telegram.ext import ApplicationBuilder
import json

# -----------------------------
# Variabili ambiente
# -----------------------------
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
API_KEY = os.getenv("RAPIDAPI_KEY")  # RapidAPI ForexFactory

TIMEZONE = pytz.timezone("Europe/Rome")
notified_events = set()

# -----------------------------
# Bot Telegram
# -----------------------------
application = ApplicationBuilder().token(BOT_TOKEN).build()

# -----------------------------
# Flask keep-alive
# -----------------------------
app = Flask("bot")

@app.route("/")
def home():
    return "🤖 Bot economico attivo!"

import threading
threading.Thread(
    target=lambda: app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000))),
    daemon=True
).start()

# -----------------------------
# Fetch eventi USD/EUR high impact
# -----------------------------
def fetch_events():
    url = "https://forexfactory1.p.rapidapi.com/api?function=get_list"
    headers = {
        "X-RapidAPI-Key": API_KEY,
        "X-RapidAPI-Host": "forexfactory1.p.rapidapi.com",
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(url, headers=headers, json={}, timeout=10)
        data = response.json()
        # Debug: primi 5 eventi
        print("DEBUG API RESPONSE:", json.dumps(data.get("events", [])[:5], indent=2))
    except Exception as e:
        print("Errore API:", e)
        return []

    events = []
    for item in data.get("events", []):
        currency = item.get("currency")
        impact_value = str(item.get("impact", "")).lower()

        if currency not in ["USD", "EUR"]:
            continue
        if impact_value != "high":
            continue

        # Genera ID univoco per evitare duplicati
        event_id = item.get("id") or f"{item.get('name', '')}_{item.get('date', '')}"

        events.append({
            "id": event_id,
            "currency": currency,
            "headline": item.get("name"),
            "actual": item.get("actual"),
            "forecast": item.get("forecast"),
            "previous": item.get("previous"),
            "datetime": item.get("date")  # stringa o timestamp
        })

    return events

# -----------------------------
# Messaggio giornaliero leggibile
# -----------------------------
async def send_daily():
    events = fetch_events()
    if not events:
        await application.bot.send_message(chat_id=CHAT_ID, text="📅 Oggi non ci sono news High Impact USD/EUR.")
        return

    msg = "📅 *High Impact USD & EUR - Oggi*\n\n"
    for e in events:
        dt_str = e["datetime"] or ""
        try:
            # prova a parsare come timestamp, altrimenti mostra così
            dt_obj = datetime.fromisoformat(dt_str)
            date_str = dt_obj.astimezone(TIMEZONE).strftime("%H:%M")
        except:
            date_str = dt_str

        actual = e["actual"] or "N/D"
        forecast = e["forecast"] or "N/D"
        previous = e["previous"] or "N/D"

        msg += f"*{e['headline']}* ({e['currency']})\n"
        msg += f"🕒 {date_str} | Forecast: {forecast} | Previous: {previous} | Actual: {actual}\n\n"

    await application.bot.send_message(chat_id=CHAT_ID, text=msg, parse_mode="Markdown")

# -----------------------------
# Scheduler
# -----------------------------
async def scheduler_loop():
    print("🚀 Bot avviato correttamente")
    await application.bot.send_message(chat_id=CHAT_ID, text="✅ Bot avviato correttamente")

    await send_daily()

    while True:
        # ripete ogni 5 minuti per nuove news
        await asyncio.sleep(300)
        await send_daily()

# -----------------------------
# Avvio
# -----------------------------
if __name__ == "__main__":
    asyncio.run(scheduler_loop())
