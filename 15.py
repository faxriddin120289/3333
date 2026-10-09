import os
import time
import threading
import requests
from bs4 import BeautifulSoup
import telebot
from flask import Flask

# 1. Flask server (Render port talab qilgani uchun)
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot muvaffaqiyatli ishlamoqda!"

def run_flask():
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

# 2. Telegram Bot sozlamalari
TOKEN = "8886515862:AAEZdaCl7JSgTqa2m17xGfwzy4Ds8QxbYY8"  # BotFather'dan olingan tokenni yozing
bot = telebot.TeleBot(TOKEN)

# 3. etender.uzex.uz saytidan qidiruv funksiyasi
def search_etender(keyword: str):
    url = f"https://etender.uzex.uz/lots/1/0?search={keyword}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            # Lotlarni ajratib olish
            cards = soup.find_all('div', class_='lot-card') or soup.find_all('div', class_='card')
            
            results = []
            for card in cards:
                text = card.get_text(separator=" ", strip=True)
                if keyword.lower() in text.lower():
                    results.append(text)
            return results
        return []
    except Exception as e:
        print(f"Scraper xatosi: {e}")
        return []

# 4. Telegram Bot buyruqlari
@bot.message_handler(commands=['start'])
def start_cmd(message):
    bot.send_message(message.chat.id, "Salom! etender.uzex.uz botiga xush kelibsiz. Qidirilayotgan kalit so'zni yuboring (Masalan: water):")

@bot.message_handler(func=lambda msg: True)
def handle_search(message):
    keyword = message.text.strip()
    bot.send_message(message.chat.id, f"🔍 `{keyword}` bo'yicha etender.uzex.uz saytidan qidirilmoqda...", parse_mode="Markdown")
    
    lots = search_etender(keyword)
    
    if lots:
        bot.send_message(message.chat.id, f"✅ Topilgan e'lonlar soni: {len(lots)}")
        for lot in lots[:5]: # Birinchi 5 ta natijani yuborish
            bot.send_message(message.chat.id, lot[:4000])
    else:
        bot.send_message(message.chat.id, "❌ Kalit so'z bo'yicha e'lonlar topilmadi.")

# 5. Botni ishga tushirish (Polling va Web-server parallel)
if __name__ == "__main__":
    # Web serverni alohida oqimda (thread) ishga tushiramiz
    threading.Thread(target=run_flask, daemon=True).start()
    
    # Eski osilib qolgan sessiyalarni tozalaymiz
    try:
        bot.remove_webhook()
        time.sleep(1)
    except Exception as e:
        print(f"Webhook o'chirish xatosi: {e}")
        
    print("Bot va Web-server ishga tushdi...")
    
    # Doimiy polling
    bot.infinity_polling(timeout=10, long_polling_timeout=5)
