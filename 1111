import os
import requests
from bs4 import BeautifulSoup
import telebot
from telebot import types
from threading import Thread
from flask import Flask

# Telegram bot tokeni (To'g'rilandi)
TOKEN = "8886515862:AAF_OgNPap1iJUWuMv9lDMlbRbVLOqOZd8A"
bot = telebot.TeleBot(TOKEN)

# Veb-server sozlamalari (Render'da bepul ishlashi uchun)
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

@bot.message_handler(func=lambda message: message.text == "📋 Mening kalit so'zlarim")
def show_keywords(message):
    keywords = get_keywords(message.chat.id)
    kw_text = "\n".join([f"- {kw}" for kw in keywords])
    bot.send_message(
        message.chat.id,
        f"Sizning joriy kalit so'zlaringiz:\n\n{kw_text}"
    )

@bot.message_handler(func=lambda message: message.text == "✏️ Kalit so'zlarni o'zgartirish")
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

# Tekshirish funksiyalari
def check_etender(chat_id):
    bot.send_message(chat_id, "🔍 etender.uzex.uz tekshirilmoqda...")
    try:
        url = "https://etender.uzex.uz/lot-list"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            bot.send_message(chat_id, "✅ etender.uzex.uz: Sayt bilan aloqa bor, ma'lumotlar olindi!")
        else:
            bot.send_message(chat_id, f"⚠️ etender.uzex.uz status kodi: {response.status_code}")
    except Exception as e:
        bot.send_message(chat_id, f"❌ etender.uzex.uz tekshirishda xatolik: {e}")

def check_xarid(chat_id):
    bot.send_message(chat_id, "🔍 xarid.uzex.uz tekshirilmoqda...")
    try:
        url = "https://xarid.uzex.uz"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            bot.send_message(chat_id, "✅ xarid.uzex.uz: Sayt bilan aloqa bor!")
        else:
            bot.send_message(chat_id, f"⚠️ xarid.uzex.uz status kodi: {response.status_code}")
    except Exception as e:
        bot.send_message(chat_id, f"❌ xarid.uzex.uz tekshirishda xatolik: {e}")

def check_xt(chat_id):
    bot.send_message(chat_id, "🔍 xt-xarid.uz tekshirilmoqda...")
    try:
        url = "https://xt-xarid.uz/lots"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            bot.send_message(chat_id, "✅ xt-xarid.uz: Sayt bilan aloqa bor!")
        else:
            bot.send_message(chat_id, f"⚠️ xt-xarid.uz status kodi: {response.status_code}")
    except Exception as e:
        bot.send_message(chat_id, f"❌ xt-xarid.uz tekshirishda xatolik: {e}")

@bot.message_handler(func=lambda message: True)
def handle_menu_clicks(message):
    text = message.text
    chat_id = message.chat.id
    
    if text == "🌐 etender.uzex.uz":
        check_etender(chat_id)
    elif text == "🌐 xarid.uzex.uz":
        check_xarid(chat_id)
    elif text == "🌐 xt-xarid.uz":
        check_xt(chat_id)
    elif text == "🚀 Barcha saytlarni tekshirish":
        check_etender(chat_id)
        check_xarid(chat_id)
        check_xt(chat_id)

if __name__ == "__main__":
    keep_alive()
    print("Bot menyu va veb-server rejimi bilan ishga tushdi...")
    bot.infinity_polling()