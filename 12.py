import requests

def search_etender(keyword: str):
    """
    etender.uzex.uz saytidan berilgan kalit so'z bo'yicha lotlarni qidiradi.
    """
    url = "https://etender.uzex.uz/api/lots"  # Saytning ichki API uchi
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json"
    }
    
    # Qidiruv parametrlari (Saytdagi 'Tovar nomi yoki lot raqami' maydoni)
    payload = {
        "name": keyword,
        "page": 1,
        "limit": 20
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        
        # Agar POST ishlamasa, fallback sifatida GET parametr bilan urinib ko'rish
        if response.status_code != 200:
            response = requests.get(f"https://etender.uzex.uz/lots/1/0?search={keyword}", headers=headers, timeout=10)
            
        return response.json() if response.status_code == 200 else None

    except Exception as e:
        print(f"Xatolik yuz berdi: {e}")
        return None

# Tekshirib ko'rish
if __name__ == "__main__":
    keyword = "water"
    results = search_etender(keyword)
    print(results)
