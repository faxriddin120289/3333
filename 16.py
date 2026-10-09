import os
import time
import threading
import requests
import telebot
from flask import Flask

# 1. Render porti uchun Flask server
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot muvaffaqiyatli ishlamoqda!"

def run_flask():
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

# 2. Telegram Bot sozlamalari
TOKEN = "8886515862:AAEZdaCl7JSgTqa2m17xGfwzy4Ds8QxbYY8"
bot = telebot.TeleBot(TOKEN)

# 3. etender.uzex.uz saytidan real API orqali qidirish
def search_etender_api(keyword: str):
    session = requests.Session()
    
    # Sayt brauzerdagidek qabul qilishi uchun sarlavhalar
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json",
        "Origin": "https://etender.uzex.uz",
        "Referer": "https://etender.uzex.uz/lots/1/0"
    }
    
    # etender.uzex.uz filtri talab qiladigan to'liq so'rov strukturasi
    payload = {
        "Name": keyword,
        "Page": 1,
        "PageSize": 20,
        "SortType": 0,
        "Status": None
    }
    
    urls = [
        "https://etender.uzex.uz/api/lots/search",
        "https://etender.uzex.uz/api/lots/get-lots",
        "https://etender.uzex.uz/api/Lots/GetList"
    ]
    
    lots_found = []
    
    for url in urls:
        try:
            res = session.post(url, json=payload, headers=headers, timeout=10)
            if res.status_code == 200:
                data = res.json()
                # Javob strukturasi obyekt yoki massiv bo'lishi mumkin
                items = data.get("data", []) if isinstance(data, dict) else data
                if isinstance(items, dict):
                    items = items.get("items", []) or items.get("lots", [])
                
                for item in items:
                    title = item.get("name") or item.get("Name") or item.get("title") or ""
                    lot_number = item.get("lotNumber") or item.get("id") or ""
                    if keyword.lower() in title.lower():
                        lots_found.append(f"📦 **Lot № {lot_number}**\n{title}")
                
                if lots_found:
                    break
        except Exception:
            continue
            
    # Agar API POST orqali topilmasa, zaxira sifatida GET parametri bilan API'ni sinaymiz
    if not lots_found:
        try:
            fallback_url = f"https://etender.uzex.uz/api/lots?search={keyword}&page=1"
            res = session.get(fallback_url, headers=headers, timeout=10)
            if res.status_code == 200:
                data = res.json()
                items = data.get("data", []) if isinstance(data, dict) else data
                for item in items:
                    title = str(item)
                    if keyword.lower() in title.lower():
                        lots_found.append(f"📦 **E'lon:** {title[:300]}")
        except Exception:
            pass

    return lots_found

# 4. Telegram handlerlar
@bot.message_handler(commands=['start'])
def start_cmd(message):
    bot.send_message(message.chat.id, "Salom! Kalit so'zni kiriting (Masalan: water):")

@bot.message_handler(func=lambda msg: True)
def handle_search(message):
    keyword = message.text.strip()
    
    # Telegram tugmalari yoki ortiqcha komandalarni filter qilish
    if keyword.startswith('/') or keyword.startswith('📋') or keyword.startswith('🌐'):
        return

    bot.send_message(message.chat.id, f"🔍 `{keyword}` bo'yicha etender.uzex.uz saytidan qidirilmoqda...", parse_mode="Markdown")
    
    results = search_etender_api(keyword)
    
    if results:
        bot.send_message(message.chat.id, f"✅ Topilgan e'lonlar soni: {len(results)}")
        for lot in results[:5]:
            bot.send_message(message.chat.id, lot, parse_mode="Markdown")
    else:
        bot.send_message(message.chat.id, "❌ Kalit so'z bo'yicha e'lonlar topilmadi.")

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    
    try:
        bot.remove_webhook()
        time.sleep(1)
    except Exception:
        pass
        
    print("Bot va Server ishga tushdi...")
    bot.infinity_polling(timeout=10, long_polling_timeout=5)
