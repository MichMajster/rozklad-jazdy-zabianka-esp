import os
import requests
from bs4 import BeautifulSoup
import json

def pobierz_odjazdy():
    url = "https://jakdojade.pl/rozklady-pkp/dworzec/gdansk-zabianka-awfis"
    
    # Rozbudowane nagłówki HTTP imitujące realnego użytkownika systemu Windows
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "pl-PL,pl;q=0.9,en-US;q=0.8,en;q=0.7",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "Sec-Ch-Ua": '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"Windows"',
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1"
    }

    # Dynamiczne ustalenie folderu, w którym znajduje się uruchomiony skrypt
    katalog_programu = os.path.dirname(os.path.abspath(__file__))
    sciezka_zapisu = os.path.join(katalog_programu, "rozklad.json")

    try:
        print("Rozpoczynanie pobierania danych z internetu...")
        response = requests.get(url, headers=headers, timeout=15)
        
        # Sprawdzenie, czy serwer nie zablokował zapytania automatycznego
        if response.status_code == 403 or "cloudflare" in response.text.lower():
            print("\n[BŁĄD] Serwer Jakdojade zablokował automatyczne zapytanie (zabezpieczenie Cloudflare/403).")
            print("Plik 'rozklad.json' NIE mógł zostać zaktualizowany świeżymi danymi.")
            return

        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Lokalizacja nagłówka sekcji odjazdów na podstawie przesłanej struktury HTML
        naglowek_odjazdow = soup.find(lambda tag: tag.name == "h2" and "Odjazdy pociągów" in tag.text)
        
        if not naglowek_odjazdow:
            print("\n[BŁĄD] Nie znaleziono sekcji 'Odjazdy pociągów' w pobranym kodzie strony.")
            return

        # Znalezienie tabeli powiązanej z odjazdami
        tabela = naglowek_odjazdow.find_next("table", class_="train-table")
        if not tabela:
            print("\n[BŁĄD] Nie znaleziono tabeli danych pod nagłówkiem odjazdów.")
            return

        odjazdy = []
        wiersze = tabela.find_all("tr")
        
        for wiersz in wiersze:
            komorki = wiersz.find_all("td")
            # Upewniamy się, że wiersz zawiera wymagane komórki (Godzina, Pociąg, Do)
            if komorki and len(komorki) >= 3:
                # Komórka 0: Godzina odjazdu
                tekst_godziny = komorki[0].get_text(strip=True)
                
                # Komórka 2: Stacja docelowa (oczyszczamy tekst z listy stacji pośrednich po słowie 'przez:')
                pelny_tekst_stacji = komorki[2].get_text(strip=True)
                stacja_docelowa = pelny_tekst_stacji.split("przez:")[0].strip()
                
                # Walidacja poprawności formatu godziny (HH:MM)
                if len(tekst_godziny) == 5 and tekst_godziny[2] == ':':
                    odjazdy.append({
                        "time": tekst_godziny,
                        "destination": stacja_docelowa
                    })

        if not odjazdy:
            print("\n[BŁĄD] Tabela odjazdów została znaleziona, ale nie udało się wyodrębnić wierszy.")
            return

        # Przygotowanie struktury wyjściowej JSON
        wynik = {"departures": odjazdy}
        
        # Zapis do pliku z wyłączeniem konwersji ASCII, aby zachować polskie znaki (Ł, Ó, Ń itp.)
        with open(sciezka_zapisu, "w", encoding="utf-8") as f:
            json.dump(wynik, f, indent=2, ensure_ascii=False)

        print(f"\n[SUKCES] Pobrano poprawnie {len(odjazdy)} odjazdów wraz z kierunkami docelowymi.")
        print(f"Plik został zapisany w katalogu roboczym: {sciezka_zapisu}")

    except Exception as e:
        print(f"\nWystąpił nieoczekiwany błąd aplikacji: {e}")

if __name__ == "__main__":
    pobierz_odjazdy()