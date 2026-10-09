import requests
import json

def get_etender_lots(keyword: str):
    # eTender API uchi
    url = "https://etender.uzex.uz/api/lots"
    
    # Sayt brauzer deb o'ylashi uchun to'liq Header
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json",
        "Referer": "https://etender.uzex.uz/lots/1/0",
        "Origin": "https://etender.uzex.uz"
    }
    
    payload = {
        "name": keyword,
        "page": 1,
        "limit": 20
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=15)
        
        # Server JSON qaytarmasa ham skript o'lib qolmasligi uchun xavfsiz o'qish:
        if response.status_code == 200:
            try:
                data = response.json()
                return data
            except json.JSONDecodeError:
                print("Server JSON emas, boshqa formatda javob qaytardi (masalan HTML).")
                return []
        else:
            print(f"Server xatolik qaytardi: Status {response.status_code}")
            return []

    except Exception as e:
        print(f"So'rov yuborishda xatolik yuz berdi: {e}")
        return []

# Bot ichida chaqirish usuli:
if __name__ == "__main__":
    keyword = "water"
    lots = get_etender_lots(keyword)
    print(f"Topilgan lotlar: {lots}")
