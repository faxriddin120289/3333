import time
import requests
from bs4 import BeautifulSoup
import telebot

# Telegram botingiz tokeni
TOKEN = "8886515862:AAEZdaCl7JSgTqa2m17xGfwzy4Ds8QxbYY8"
bot = telebot.TeleBot(TOKEN)

def search_etender_html(keyword: str):
    """
    etender.uzex.uz saytidan berilgan kalit so'z bo'yicha lotlarni scraping qiladi.
    """
    # Saytdagi qidiruv parametri bilan URL
    url = f"https://etender.uzex.uz/lots/1/0?search={keyword}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "uz,ru,en;q=0.9",
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        print(f"Sayt javob kodi: {response.status_code}")
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Lot bloklarini topish
            lot_cards = soup.find_all('div', class_='lot-card') or soup.find_all('div', class_='card')
            
            found_lots = []
            for card in lot_cards:
                text = card.get_text(separator=" ", strip=True)
                # Kalit so'z matn ichida bormi?
                if keyword.lower() in text.lower():
                    found_lots.append(text)
            
            return found_lots
        else:
            print(f"Sayt xatolik qaytardi: Status {response.status_code}")
            return []

    except Exception as e:
        print(f"Xatolik yuz berdi: {e}")
        return []

# Botni uzliksiz ushlab turish uchun (Render'da 'Application exited early' bo'lmasligi uchun)
if __name__ == "__main__":
    print("Bot ishga tushdi...")
    
    # Test qidiruv
    keyword = "water"
    results = search_etender_html(keyword)
    print(f"Topilgan lotlar soni: {len(results)}")
    
    # Bot serverda doimiy ishlashi uchun polling
    while True:
        try:
            bot.polling(none_stop=True, interval=2, timeout=20)
        except Exception as e:
            print(f"Polling xatosi: {e}")
            time.sleep(5)
