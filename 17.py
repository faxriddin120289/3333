import os
import time
import threading
import telebot
from flask import Flask
from playwright.sync_api import sync_playwright

# 1. Render uchun Flask web-server (Port xatoligi bermasligi uchun)
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

# 3. Playwright orqali real brauzerda qidirish funksiyasi
def search_etender_playwright(keyword: str):
    found_lots = []
    
    with sync_playwright() as p:
        # Chromium brauzerini fonda (headless) ishga tushiramiz
        browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-setuid-sandbox"])
        page = browser.new_page()
        
        try:
            # Qidiruv URL manziliga o'tamiz
            url = f"https://etender.uzex.uz/lots/1/0?search={keyword}"
            page.goto(url, timeout=30000, wait_until="networkidle")
            
            # Dinamik ma'lumotlar yuklanishi uchun 3 soniya kutamiz
            page.wait_for_timeout(3000)
            
            # Sahifadagi lot kartochkalarini topamiz
            cards = page.query_selector_all(".lot-card, .card, .lot-item")
            
            for card in cards[:5]:  # Dastlabki 5 ta natija
                text = card.inner_text()
                if text.strip():
                    found_lots.append(text.strip())
                    
        except Exception as e:
            print(f"Playwright qidiruv xatosi: {e}")
        finally:
            browser.close()
            
    return found_lots

# 4. Telegram handlerlar
@bot.message_handler(commands=['start'])
def start_cmd(message):
    bot.send_message(
        message.chat.id, 
        "Salom! etender.uzex.uz saytidan qidirmoqchi bo'lgan kalit so'zni yuboring (Masalan: water yoki suv):"
    )

@bot.message_handler(func=lambda msg: True)
def handle_search(message):
    text = message.text.strip()
    
    # Menyudagi maxsus tugmalarni e'tiborsiz qoldirish[span_0](start_span)[span_0](end_span)
    if text.startswith('/') or text.startswith('🌐') or text.startswith('📋') or text.startswith('🚀') or text.startswith('✏️'):
        return

    bot.send_message(
        message.chat.id, 
        f"🔍 `{text}` bo'yicha etender.uzex.uz saytidan brauzer orqali qidirilmoqda (10-15 soniya vaqt olishi mumkin)...", 
        parse_mode="Markdown"
    )
    
    results = search_etender_playwright(text)
    
    if results:
        bot.send_message(message.chat.id, f"✅ Topilgan e'lonlar soni: {len(results)}")
        for lot in results:
            bot.send_message(message.chat.id, lot[:3500])
    else:
        bot.send_message(message.chat.id, "❌ Kalit so'z bo'yicha e'lonlar topilmadi.")

if __name__ == "__main__":
    # Flask serverni alohida oqimda ishga tushirish
    threading.Thread(target=run_flask, daemon=True).start()
    
    # Eski webhook sessiyasini tozalash
    try:
        bot.remove_webhook()
        time.sleep(1)
    except Exception:
        pass
        
    print("Bot va Server ishga tushdi...")
    bot.infinity_polling(timeout=10, long_polling_timeout=5)
