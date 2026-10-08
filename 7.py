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

# Standart kalit so'zlar (So'z ildizlari va ruscha so'zlar qo'shildi)
default_keywords = ["burg", "бур", "skvajina", "скважин", "nasos", "насос", "quduq", "колодец"]
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
        "✏️ Yangi kalit so'zlarni vergul bilan ajratib yuboring:\n\n"
        "Masalan: *burg, бур, nasos, skvajina*",
        parse_mode="Markdown"
    )
    bot.register_next_step_handler(msg, process_new_keywords)

def process_new_keywords(message):
    raw_text = message.text
    if not raw_text or raw_text.startswith("🌐") or raw_text.startswith("🚀") or raw_text.startswith("📋") or raw_text.startswith("✏️"):
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

# ETENDER.UZEX.UZ PARSER (Yangi to'g'rilangan algoritm)
def check_etender(chat_id):
    bot.send_message(chat_id, "🔍 etender.uzex.uz qidirilmoqda...")
    keywords = get_keywords(chat_id)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*"
    }
    
    results = []
    
    # 1-usul: etender API orqali qidirish
    try:
        api_url = "https://etender.uzex.uz/api/common/GetLots"
        for kw in keywords[:3]:  # Asosiy so'zlar bo'yicha API ga so'rov
            payload = {"Name": kw, "PageSize": 10, "PageIndex": 1}
            res = requests.post(api_url, json=payload, headers=headers, timeout=10)
            if res.status_code == 200:
                data = res.json()
                lots = data.get("data", []) or data.get("List", []) or []
                for lot in lots:
                    title = lot.get("Name") or lot.get("lotName") or lot.get("Description", "")
                    lot_id = lot.get("Id") or lot.get("lotId") or lot.get("Number", "")
                    if title and lot_id:
                        link = f"https://etender.uzex.uz/lot/{lot_id}"
                        results.append(f"📌 **[{kw.upper()}]** {title}\n🔗 {link}")
    except Exception:
        pass

    # 2-usul: Agar API javob bermasa, /lots/1/0 sahifasidan scraping qilish
    if not results:
        try:
            web_url = "https://etender.uzex.uz/lots/1/0"
            res = requests.get(web_url, headers=headers, timeout=15)
            soup = BeautifulSoup(res.text, 'html.parser')
            
            # Lot bloklarini izlash
            items = soup.find_all(['div', 'a'], class_=lambda c: c and ('lot' in c.lower() or 'card' in c.lower() or 'item' in c.lower()))
            if not items:
                items = soup.find_all('a', href=True)
                
            for item in items:
                text = item.get_text(" ", strip=True)
                href = item.get('href', '')
                for kw in keywords:
                    if kw.lower() in text.lower():
                        full_link = href if href.startswith("http") else f"https://etender.uzex.uz{href}"
                        results.append(f"📌 **[{kw.upper()}]** {text[:150]}...\n🔗 {full_link}")
                        break
        except Exception as e:
            bot.send_message(chat_id, f"❌ etender.uzex.uz ulanish xatosi: {e}")
            return

    # Natijalarni tozalash va takrorlanishlarni olib tashlash
    unique_results = list(dict.fromkeys(results))

    if unique_results:
        msg = "🌐 **etender.uzex.uz bo'yicha topilgan lotlar:**\n\n" + "\n\n---\n\n".join(unique_results[:5])
        bot.send_message(chat_id, msg, parse_mode="Markdown", disable_web_page_preview=True)
    else:
        bot.send_message(
            chat_id, 
            f"ℹ️ **etender.uzex.uz:** Kalit so'zlar ({', '.join(keywords)}) bo'yicha yangi lotlar topilmadi.\n\n"
            "💡 *Maslahat:* Qidiruv kalit so'zlariga so'z ildizlarini yuborib ko'ring (Masalan: `burg, бур`).", 
            parse_mode="Markdown"
        )

# XARID.UZEX.UZ PARSER
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
                    results.append(f"📌 **[{kw.upper()}]** {text}\n🔗 {full_link}")
                    break
        
        unique_results = list(dict.fromkeys(results))
        if unique_results:
            msg = "🌐 **xarid.uzex.uz bo'yicha topilgan lotlar:**\n\n" + "\n\n".join(unique_results[:5])
            bot.send_message(chat_id, msg, parse_mode="Markdown", disable_web_page_preview=True)
        else:
            bot.send_message(chat_id, f"ℹ️ xarid.uzex.uz: ({', '.join(keywords)}) bo'yicha lotlar topilmadi.")
            
    except Exception as e:
        bot.send_message(chat_id, f"❌ xarid.uzex.uz xatolik: {e}")

# XT-XARID.UZ PARSER
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
                    results.append(f"📌 **[{kw.upper()}]** {text}\n🔗 {full_link}")
                    break
        
        unique_results = list(dict.fromkeys(results))
        if unique_results:
            msg = "🌐 **xt-xarid.uz bo'yicha topilgan lotlar:**\n\n" + "\n\n".join(unique_results[:5])
            bot.send_message(chat_id, msg, parse_mode="Markdown", disable_web_page_preview=True)
        else:
            bot.send_message(chat_id, f"ℹ️ xt-xarid.uz: ({', '.join(keywords)}) bo'yicha lotlar topilmadi.")
            
    except Exception as e:
        bot.send_message(chat_id, f"❌ xt-xarid.uz xatolik: {e}")

# BARCHA TUGMALARNI QABUL QILISH
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
