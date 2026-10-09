import os
import time
import threading
import telebot
from flask import Flask
from curl_cffi import requests

# 1. Render port xatosi bermasligi uchun Flask server
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot muvaffaqiyatli ishlamoqda!"

def run_flask():
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

# 2. Telegram Bot sozlamalari
TOKEN = "8886515862:AAEZdaCl7JSgTqa2m17xGfwzy4Ds8QxbYY8"  # BotFather tokenini qo'ying
bot = telebot.TeleBot(TOKEN)

# 3. Chrome TLS Barmoq izini taqlid qilib etender.uzex.uz API'sidan qidirish
def search_etender(keyword: str):
    # curl_cffi orqali Chrome 120 brauzerini imitatsiya qiluvchi sessiya
    session = requests.Session(impersonate="chrome120")
    
    url = "https://etender.uzex.uz/api/lots/get-lots"
    
    headers = {
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "uz,ru;q=0.9,en;q=0.8",
        "Content-Type": "application/json",
        "Origin": "https://etender.uzex.uz",
        "Referer": "https://etender.uzex.uz/lots/1/0",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin"
    }
    
    payload = {
        "name": keyword,
        "page": 1,
        "pageSize": 10,
        "status": None
    }
    
    found_lots = []
    
    try:
        response = session.post(url, json=payload, headers=headers, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            items = []
            
            if isinstance(data, dict):
                items = data.get("items") or data.get("data") or data.get("lots") or []
            elif isinstance(data, list):
                items = data

            for item in items:
                if isinstance(item, dict):
                    lot_id = item.get("id") or item.get("lotNumber") or item.get("code") or "—"
                    title = item.get("name") or item.get("title") or item.get("lotName") or ""
                    cost = item.get("startCost") or item.get("cost") or item.get("price") or "—"
                    
                    if keyword.lower() in str(title).lower():
                        lot_msg = (
                            f"📦 **Lot № {lot_id}**\n"
                            f"📝 {title}\n"
                            f"💰 **Boshlang'ich narxi:** {cost}\n"
                            f"🔗 https://etender.uzex.uz/lot/{lot_id}"
                        )
                        found_lots.append(lot_msg)

    except Exception as e:
        print(f"Xatolik yuz berdi: {e}")

    # Agar POST ishlamasa, fallback sifatida GET parametri bilan sinaymiz
    if not found_lots:
        try:
            get_url = f"https://etender.uzex.uz/api/lots?search={keyword}"
            res = session.get(get_url, headers=headers, timeout=12)
            if res.status_code == 200:
                data = res.json()
                items = data.get("items", []) if isinstance(data, dict) else data
                for item in items[:5]:
                    if isinstance(item, dict):
                        title = item.get("name") or str(item)
                        found_lots.append(f"📦 **E'lon:** {title}")
        except Exception as e:
            print(f"GET Fallback xatosi: {e}")

    return found_lots

# 4. Telegram handlerlar
@bot.message_handler(commands=['start'])
def start_cmd(message):
    bot.send_message(
        message.chat.id, 
        "Salom! etender.uzex.uz saytidan qidirmoqchi bo'lgan kalit so'zingizni yuboring (Masalan: water, suv yoki bur):"
    )

@bot.message_handler(func=lambda msg: True)
def handle_search(message):
    text = message.text.strip()
    
    # Menyudagi maxsus tugmalarni e'tiborsiz qoldirish
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
        for lot in results[:5]:
            bot.send_message(message.chat.id, lot, parse_mode="Markdown", disable_web_page_preview=True)
    else:
        bot.send_message(message.chat.id, "❌ Kalit so'z bo'yicha e'lonlar topilmadi.")

if __name__ == "__main__":
    # Render port talabi uchun Flask thread
    threading.Thread(target=run_flask, daemon=True).start()
    
    try:
        bot.remove_webhook()
        time.sleep(1)
    except Exception:
        pass
        
    print("Bot va Server ishga tushdi...")
    bot.infinity_polling(timeout=10, long_polling_timeout=5)
