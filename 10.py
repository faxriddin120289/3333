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
    return "Tender Monitoring Bot is Active!"

def run():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.start()

default_keywords = ["burg", "бур", "tanlash", "скважин", "bvr", "бвр", "burg‘ilash", "буровой", "взрыв", "отбор"]
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

def ask_new_keywords(message):
    msg = bot.send_message(
        message.chat.id,
        "✏️ **Yangi kalit so'zlarni vergul bilan ajratib yuboring:**\n\n"
        "Masalan: `burg, бур, bvr, бвр, nasos, skvajina`",
        parse_mode="Markdown"
    )
    bot.register_next_step_handler(msg, process_new_keywords)

def process_new_keywords(message):
    raw_text = message.text
    if not raw_text or any(raw_text.startswith(prefix) for prefix in ["🌐", "🚀", "📋", "✏️", "/"]):
        bot.send_message(message.chat.id, "❌ Amal bekor qilindi.", reply_markup=get_main_keyboard())
        return

    new_list = [item.strip() for item in raw_text.split(",") if item.strip()]
    if new_list:
        user_keywords[message.chat.id] = new_list
        kw_text = "\n".join([f"• {kw}" for kw in new_list])
        bot.send_message(
            message.chat.id,
            f"✅ **Kalit so'zlaringiz muvaffaqiyatli saqlandi:**\n\n{kw_text}",
            parse_mode="Markdown",
            reply_markup=get_main_keyboard()
        )
    else:
        bot.send_message(message.chat.id, "❌ Kalit so'zlar kiritilmadi.", reply_markup=get_main_keyboard())

# 1. ETENDER.UZEX.UZ PARSER
def check_etender(chat_id):
    bot.send_message(chat_id, "🔍 **etender.uzex.uz** bo'yicha qidirilmoqda...", parse_mode="Markdown")
    keywords = get_keywords(chat_id)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    results = []
    api_url = "https://etender.uzex.uz/api/common/GetLots"
    for kw in keywords:
        try:
            payload = {"Name": kw, "PageSize": 15, "PageIndex": 1}
            res = requests.post(api_url, json=payload, headers=headers, timeout=10)
            if res.status_code == 200:
                data = res.json()
                lots = data.get("data") or data.get("List") or data.get("items") or []
                if isinstance(data, list):
                    lots = data
                
                for lot in lots:
                    title = lot.get("Name") or lot.get("lotName") or lot.get("Description") or ""
                    lot_id = lot.get("Id") or lot.get("lotId") or lot.get("Number") or ""
                    if title and lot_id:
                        link = f"https://etender.uzex.uz/lot/{lot_id}"
                        results.append(f"📌 **[{kw.upper()}]** {title.strip()}\n🔗 {link}")
        except Exception:
            continue

    if not results:
        try:
            web_url = "https://etender.uzex.uz/lots/1/0"
            res = requests.get(web_url, headers=headers, timeout=12)
            if res.status_code == 200:
                soup = BeautifulSoup(res.text, 'html.parser')
                for a in soup.find_all('a', href=True):
                    text = a.get_text(" ", strip=True)
                    href = a['href']
                    for kw in keywords:
                        if kw.lower() in text.lower():
                            full_link = href if href.startswith("http") else f"https://etender.uzex.uz{href}"
                            results.append(f"📌 **[{kw.upper()}]** {text[:130]}...\n🔗 {full_link}")
                            break
        except Exception:
            pass

    unique_results = list(dict.fromkeys(results))

    if unique_results:
        msg = "🌐 **etender.uzex.uz bo'yicha topilgan lotlar:**\n\n" + "\n\n---\n\n".join(unique_results[:7])
        bot.send_message(chat_id, msg, parse_mode="Markdown", disable_web_page_preview=True)
    else:
        bot.send_message(
            chat_id, 
            f"ℹ️ **etender.uzex.uz:** Kalit so'zlar bo'yicha e'lonlar topilmadi.\n"
            f"💡 *Maslahat:* Qidiruv uchun so'z ildizlaridan foydalaning (Masalan: `burg, бур`).",
            parse_mode="Markdown"
        )

# 2. XARID.UZEX.UZ PARSER
def check_xarid(chat_id):
    bot.send_message(chat_id, "🔍 **xarid.uzex.uz** bo'yicha qidirilmoqda...", parse_mode="Markdown")
    keywords = get_keywords(chat_id)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    results = []
    urls = ["https://xarid.uzex.uz", "https://xarid.uzex.uz/e-shop"]
    
    for url in urls:
        try:
            res = requests.get(url, headers=headers, timeout=12)
            if res.status_code == 200:
                soup = BeautifulSoup(res.text, 'html.parser')
                for link in soup.find_all('a', href=True):
                    text = link.get_text(" ", strip=True)
                    href = link['href']
                    for kw in keywords:
                        if kw.lower() in text.lower() and len(text) > 10:
                            full_link = href if href.startswith("http") else f"https://xarid.uzex.uz{href}"
                            results.append(f"📌 **[{kw.upper()}]** {text[:130]}\n🔗 {full_link}")
                            break
        except Exception:
            continue

    unique_results = list(dict.fromkeys(results))

    if unique_results:
        msg = "🌐 **xarid.uzex.uz bo'yicha topilgan lotlar:**\n\n" + "\n\n---\n\n".join(unique_results[:7])
        bot.send_message(chat_id, msg, parse_mode="Markdown", disable_web_page_preview=True)
    else:
        bot.send_message(chat_id, "ℹ️ **xarid.uzex.uz:** Berilgan kalit so'zlar bo'yicha lotlar topilmadi.", parse_mode="Markdown")

# 3. XT-XARID.UZ PARSER
def check_xt(chat_id):
    bot.send_message(chat_id, "🔍 **xt-xarid.uz** bo'yicha qidirilmoqda...", parse_mode="Markdown")
    keywords = get_keywords(chat_id)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    results = []
    try:
        url = "https://xt-xarid.uz/lots"
        res = requests.get(url, headers=headers, timeout=12)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            for link in soup.find_all('a', href=True):
                text = link.get_text(" ", strip=True)
                href = link['href']
                for kw in keywords:
                    if kw.lower() in text.lower() and len(text) > 10:
                        full_link = href if href.startswith("http") else f"https://xt-xarid.uz{href}"
                        results.append(f"📌 **[{kw.upper()}]** {text[:130]}\n🔗 {full_link}")
                        break
    except Exception as e:
        bot.send_message(chat_id, f"❌ **xt-xarid.uz** ulanishda xatolik: {e}", parse_mode="Markdown")
        return

    unique_results = list(dict.fromkeys(results))

    if unique_results:
        msg = "🌐 **xt-xarid.uz bo'yicha topilgan lotlar:**\n\n" + "\n\n---\n\n".join(unique_results[:7])
        bot.send_message(chat_id, msg, parse_mode="Markdown", disable_web_page_preview=True)
    else:
        bot.send_message(chat_id, "ℹ️ **xt-xarid.uz:** Berilgan kalit so'zlar bo'yicha lotlar topilmadi.", parse_mode="Markdown")

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
        keywords = get_keywords(chat_id)
        kw_text = "\n".join([f"• {kw}" for kw in keywords])
        bot.send_message(chat_id, f"📋 **Sizning joriy kalit so'zlaringiz:**\n\n{kw_text}", parse_mode="Markdown")
    elif "zgartirish" in text:
        ask_new_keywords(message)

if __name__ == "__main__":
    keep_alive()
    bot.delete_webhook()
    print("Bot muvaffaqiyatli ishga tushdi...")
    bot.infinity_polling()
