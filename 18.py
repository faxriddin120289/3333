import os
import time
import threading
import requests
import telebot
from flask import Flask

# 1. Render port talabi uchun Flask web-server
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot muvaffaqiyatli ishlamoqda!"

def run_flask():
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

# 2. Telegram Bot sozlamalari
TOKEN = "8886515862:AAEZdaCl7JSgTqa2m17xGfwzy4Ds8QxbYY8"  # O'zingizning tokeningizni qo'ying
bot = telebot.TeleBot(TOKEN)

# 3. etender.uzex.uz backend qidiruvi
def search_etender(keyword: str):
    session = requests.Session()
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json",
        "Origin": "https://etender.uzex.uz",
        "Referer": "https://etender.uzex.uz/lots/1/0"
    }
    
    # etender.uzex.uz real so'rov tanasi (payload)
    payload = {
        "name": keyword,
        "page": 1,
        "pageSize": 20,
        "status": 1
    }
    
    # Saytning 3 ta mumkin bo'lgan API manzili
    endpoints = [
        "https://etender.uzex.uz/api/lots/get-lots",
        "https://etender.uzex.uz/api/lots/search",
        "https://etender.uzex.uz/api/Lots/GetList"
    ]
    
    found_lots = []

    for url in endpoints:
        try:
            response = session.post(url, json=payload, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                
                # Massiv yoki Obyekt shaklidagi javobni ajratish
                items = []
                if isinstance(data, list):
                    items = data
                elif isinstance(data, dict):
                    items = data.get("items") or data.get("data") or data.get("lots") or []
                    if isinstance(items, dict):
                        items = items.get("items") or []

                for item in items:
                    if isinstance(item, dict):
                        lot_id = item.get("id") or item.get("lotNumber") or item.get("code") or "—"
                        title = item.get("name") or item.get("title") or item.get("lotName") or ""
                        cost = item.get("startCost") or item.get("cost") or item.get("price") or "—"
                        
                        if keyword.lower() in str(title).lower():
                            lot_msg = (
                                f"📦 **Lot № {lot_id}**\n"
                                f"📝 {title}\n"
                                f"💰 Narxi: {cost}\n"
                                f"🔗 https://etender.uzex.uz/lot/{lot_id}"
                            )
                            found_lots.append(lot_msg)
                
                if found_lots:
                    break
        except Exception as e:
            print(f"API so'rov xatosi ({url}): {e}")
            continue

    return found_lots

# 4. Telegram handlerlar
@bot.message_handler(commands=['start'])
def start_cmd(message):
    bot.send_message(
        message.chat.id, 
        "Salom! etender.uzex.uz saytidan qidirmoqchi bo'lgan kalit so'zingizni yuboring (Masalan: water):"
    )

@bot.message_handler(func=lambda msg: True)
def handle_search(message):
    text = message.text.strip()
    
    # Tugmalar va menyularni filtrlash[span_2](start_span)[span_2](end_span)
    if text.startswith('/') or text.startswith('🌐') or text.startswith('📋') or text.startswith('🚀') or text.startswith('✏️'):
        return

    bot.send_message(
        message.chat.id, 
        f"🔍 `{text}` bo'yicha etender.uzex.uz saytidan qidirilmoqda...", 
        parse_mode="Markdown"
    )
    
    results = search_etender(text)
    
    if results:
        bot.send_message(message.chat.id, f"✅ Topilgan e'lonlar soni: {len(results)}")
        for lot in results[:5]:  # Birinchi 5 tasini chiqarish
            bot.send_message(message.chat.id, lot, parse_mode="Markdown", disable_web_page_preview=True)
    else:
        bot.send_message(message.chat.id, "❌ Kalit so'z bo'yicha e'lonlar topilmadi.")

if __name__ == "__main__":
    # Render port xatosini oldini olish uchun Flask parallel yuritiladi
    threading.Thread(target=run_flask, daemon=True).start()
    
    try:
        bot.remove_webhook()
        time.sleep(1)
    except Exception:
        pass
        
    print("Bot va Server ishga tushdi...")
    bot.infinity_polling(timeout=10, long_polling_timeout=5)
