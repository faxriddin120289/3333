import os
import requests
from bs4 import BeautifulSoup
import telebot
from telebot import types
from threading import Thread
from flask import Flask

TOKEN = "8886515862:AAF_OgNPap1iJUWuMv9lDMlbRbVLOqOZd8A"
bot = telebot.TeleBot(TOKEN)

app = Flask('')

@app.route('/')
def home():
    return "Bot muvaffaqiyatli ishlayapti!"

def run():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.start()

# Standart kalit so'zlar
default_keywords = ["burg'ulash", "skvajina", "nasos", "quduq"]
user_keywords = {}

def get_keywords(user_id):
    return user_keywords.get(user_id, default_keywords)

def get_main_keyboard():
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    btn_etender = types.KeyboardButton("🌐 etender.uzex.uz")
    btn_xarid = types.KeyboardButton("🌐 xarid.uzex.uz")
    btn_xt = types.KeyboardButton("🌐 xt-xarid.uz")
    btn_all = types.KeyboardButton("🚀 Barcha saytlarni tekshirish")
    btn_my_kw = types.KeyboardButton("📋 Mening kalit so'zlarim")
    btn_edit_kw = types.KeyboardButton("✏️ Kalit so'zlarni o'zgartirish")
    
    markup.add(btn_etender, btn_xarid)
    markup.add(btn_xt, btn_all)
    markup.add(btn_my_kw, btn_edit_kw)
    return markup

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.send_message(
        message.chat.id,
        "Assalomu alaykum! Tender va xaridlarni monitoring qiluvchi botga xush kelibsiz.\n\n"
        "Tugmalardan birini tanlang:",
        reply_markup=get_main_keyboard()
    )

def show_keywords(message):
    keywords = get_keywords(message.chat.id)
    kw_text = "\n".join([f"- {kw}" for kw in keywords])
    bot.send_message(
        message.chat.id,
        f"Sizning joriy kalit so'zlaringiz:\n\n{kw_text}"
    )

def ask_new_keywords(message):
    msg = bot.send_message(
        message.chat.id,
        "Yangi kalit so'zlarni vergul bilan ajratib yuboring.\n"
        "Masalan: burg'ulash, nasos, kabel, quvur"
    )
    bot.register_next_step_handler(msg, process_new_keywords)

def process_new_keywords(message):
    raw_text = message.text
    if raw_text:
        new_list = [item.strip() for item in raw_text.split(",") if item.strip()]
        if new_list:
            user_keywords[message.chat.id] = new_list
            kw_text = "\n".join([f"- {kw}" for kw in new_list])
            bot.send_message(
                message.chat.id,
                f"✅ Kalit so'zlar yangilandi:\n\n{kw_text}",
                reply_markup=get_main_keyboard()
            )
            return
    bot.send_message(
        message.chat.id,
        "❌ Noto'g'ri format. Kalit so'zlar o'zgartirilmadi.",
        reply_markup=get_main_keyboard()
    )

# Saytlardan lotlarni qidirish
def check_etender(chat_id):
    bot.send_message(chat_id, "🔍 etender.uzex.uz qidirilmoqda...")
    keywords = get_keywords(chat_id)
    headers = {"User-Agent": "Mozilla/5.0"}
    
    try:
        url = "https://etender.uzex.uz/lot-list"
        res = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        links = soup.find_all('a', href=True)
        results = []
        
        for link in links:
            text = link.get_text(strip=True)
            href = link['href']
            for kw in keywords:
                if kw.lower() in text.lower():
                    full_link = href if href.startswith("http") else f"https://etender.uzex.uz{href}"
                    results.append(f"📌 [{kw.upper()}] {text}\n🔗 {full_link}")
                    break
        
        if results:
            msg = "🌐 **etender.uzex.uz bo'yicha topilgan lotlar:**\n\n" + "\n\n".join(results[:5])
            bot.send_message(chat_id, msg, parse_mode="Markdown", disable_web_page_preview=True)
        else:
            bot.send_message(chat_id, "ℹ️ etender.uzex.uz: Kalit so'zlar bo'yicha yangi lotlar topilmadi.")
            
    except Exception as e:
        bot.send_message(chat_id, f"❌ etender.uzex.uz xatolik: {e}")

def check_xarid(chat_id):
    bot.send_message(chat_id, "🔍 xarid.uzex.uz qidirilmoqda...")
    keywords = get_keywords(chat_id)
    headers = {"User-Agent": "Mozilla/5.0"}
    
    try:
        url = "https://xarid.uzex.uz"
        res = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        links = soup.find_all('a', href=True)
        results = []
        
        for link in links:
            text = link.get_text(strip=True)
            href = link['href']
            for kw in keywords:
                if kw.lower() in text.lower():
                    full_link = href if href.startswith("http") else f"https://xarid.uzex.uz{href}"
                    results.append(f"📌 [{kw.upper()}] {text}\n🔗 {full_link}")
                    break
        
        if results:
            msg = "🌐 **xarid.uzex.uz bo'yicha topilgan lotlar:**\n\n" + "\n\n".join(results[:5])
            bot.send_message(chat_id, msg, parse_mode="Markdown", disable_web_page_preview=True)
        else:
            bot.send_message(chat_id, "ℹ️ xarid.uzex.uz: Kalit so'zlar bo'yicha yangi lotlar topilmadi.")
            
    except Exception as e:
        bot.send_message(chat_id, f"❌ xarid.uzex.uz xatolik: {e}")

def check_xt(chat_id):
    bot.send_message(chat_id, "🔍 xt-xarid.uz qidirilmoqda...")
    keywords = get_keywords(chat_id)
    headers = {"User-Agent": "Mozilla/5.0"}
    
    try:
        url = "https://xt-xarid.uz/lots"
        res = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        links = soup.find_all('a', href=True)
        results = []
        
        for link in links:
            text = link.get_text(strip=True)
            href = link['href']
            for kw in keywords:
                if kw.lower() in text.lower():
                    full_link = href if href.startswith("http") else f"https://xt-xarid.uz{href}"
                    results.append(f"📌 [{kw.upper()}] {text}\n🔗 {full_link}")
                    break
        
        if results:
            msg = "🌐 **xt-xarid.uz bo'yicha topilgan lotlar:**\n\n" + "\n\n".join(results[:5])
            bot.send_message(chat_id, msg, parse_mode="Markdown", disable_web_page_preview=True)
        else:
            bot.send_message(chat_id, "ℹ️ xt-xarid.uz: Kalit so'zlar bo'yicha yangi lotlar topilmadi.")
            
    except Exception as e:
        bot.send_message(chat_id, f"❌ xt-xarid.uz xatolik: {e}")

# Menyu va tugmalar bilan ishlash
@bot.message_handler(func=lambda message: True)
def handle_menu_clicks(message):
    text = message.text
    chat_id = message.chat.id
    
    if "etender.uzex.uz" in text:
        check_etender(chat_id)
    elif "xarid.uzex.uz" in text:
        check_xarid(chat_id)
    elif "xt-xarid.uz" in text:
        check_xt(chat_id)
    elif "Barcha saytlarni" in text:
        check_etender(chat_id)
        check_xarid(chat_id)
        check_xt(chat_id)
    elif "Mening kalit" in text:
        show_keywords(message)
    elif "o'zgartirish" in text or "o’zgartirish" in text:
        ask_new_keywords(message)

if __name__ == "__main__":
    keep_alive()
    bot.delete_webhook()
    print("Bot muvaffaqiyatli ishga tushdi...")
    bot.infinity_polling()
