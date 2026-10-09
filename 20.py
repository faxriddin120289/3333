import os
import time
import threading
import requests
from bs4 import BeautifulSoup
import telebot
from flask import Flask

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot status: Active"

def run_flask():
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

TOKEN = "8886515862:AAEZdaCl7JSgTqa2m17xGfwzy4Ds8QxbYY8"  # BotFather'dan olingan token
bot = telebot.TeleBot(TOKEN)

def search_etender_all_methods(keyword: str):
    found_lots = []
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "uz,ru,en"
    }

    # USUL 1: etender/uzex ochiq API xizmatlari
    api_urls = [
        f"https://etender.uzex.uz/api/lots?search={keyword}&page=1&pageSize=10",
        f"https://etender.uzex.uz/api/lots/search?name={keyword}",
        f"https://xarid.uzex.uz/api/deals/get-list?search={keyword}"
    ]

    for url in api_urls:
        try:
            res = requests.get(url, headers=headers, timeout=10)
            if res.status_code == 200:
                data = res.json()
                items = data.get("items") or data.get("data") or (data if isinstance(data, list) else [])
                
                for item in items:
                    if isinstance(item, dict):
                        lot_id = item.get("id") or item.get("lotNumber") or item.get("code") or "—"
                        title = item.get("name") or item.get("title") or item.get("displayValue") or ""
                        cost = item.get("startCost") or item.get("cost") or item.get("price") or "—"
                        
                        if keyword.lower() in str(title).lower():
                            found_lots.append(
                                f"📦 **Lot № {lot_id}**\n"
                                f"📝 {title}\n"
                                f"💰 **Narxi:** {cost}\n"
                                f"🔗 https://etender.uzex.uz/lot/{lot_id}"
                            )
                if found_lots:
                    return found_lots
        except Exception as e:
            print(f"API Error ({url}): {e}")

    # USUL 2: Uzex RSS va Mobile/Web HTML Fallback
    try:
        html_url = f"https://etender.uzex.uz/lots/1/0?search={keyword}"
        res = requests.get(html_url, headers=headers, timeout=10)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            # SSR yoki SEO meta kartalarini qidirish
            cards = soup.find_all(['div', 'tr', 'a'], class_=lambda c: c and any(x in str(c).lower() for x in ['lot', 'card', 'item', 'row']))
            
            for card in cards[:5]:
                text = card.get_text(separator=" ", strip=True)
                if keyword.lower() in text.lower() and len(text) > 15:
                    found_lots.append(f"📦 **E'lon ma'lumoti:**\n{text[:300]}")
    except Exception as e:
        print(f"HTML Error: {e}")

    return found_lots

@bot.message_handler(commands=['start'])
def start_cmd(message):
    bot.send_message(
        message.chat.id, 
        "Salom! etender.uzex.uz saytidan qidiruv uchun kalit so'zni kiriting (Masalan: water, bur, suv):"
    )

@bot.message_handler(func=lambda msg: True)
def handle_search(message):
    text = message.text.strip()
    
    if text.startswith('/') or text.startswith('🌐') or text.startswith('📋') or text.startswith('🚀') or text.startswith('✏️'):
        return

    bot.send_message(
        message.chat.id, 
        f"🔍 `{text}` bo'yicha etender.uzex.uz saytidan qidirilmoqda...", 
        parse_mode="Markdown"
    )
    
    results = search_etender_all_methods(text)
    
    if results:
        bot.send_message(message.chat.id, f"✅ Topilgan e'lonlar soni: {len(results)}")
        for lot in results[:5]:
            bot.send_message(message.chat.id, lot, parse_mode="Markdown", disable_web_page_preview=True)
    else:
        bot.send_message(
            message.chat.id, 
            "❌ Kalit so'z bo'yicha e'lon topilmadi yoki ushbu so'z bo'yicha etender.uzex.uz platformasida hozirda aktiv lotlar mavjud emas."
        )

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    
    try:
        bot.remove_webhook()
        time.sleep(1)
    except Exception:
        pass
        
    print("Bot muvaffaqiyatli ishga tushirildi...")
    bot.infinity_polling(timeout=10, long_polling_timeout=5)
