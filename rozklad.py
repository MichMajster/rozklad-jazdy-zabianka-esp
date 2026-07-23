import os
import re
import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime, timedelta

def pobierz_odjazdy():
    # Pobieramy dzisiejszą i jutrzejszą datę w formacie YYYY-MM-DD dla URL
    dzisiaj_dt = datetime.now()
    jutro_dt = dzisiaj_dt + timedelta(days=1)
    
    data_dzis_str = dzisiaj_dt.strftime("%Y-%m-%d")
    data_jutro_str = jutro_dt.strftime("%Y-%m-%d")

    # Lista URL-i do odpytania (dzisiaj oraz jutro)
    baza_url = "https://koleo.pl/dworzec-pkp/gdansk-zabianka-awfis/odjazdy"
    urle = [
        baza_url,
        f"{baza_url}/{data_jutro_str}"
    ]

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

    katalog_programu = os.path.dirname(os.path.abspath(__file__))
    sciezka_zapisu = os.path.join(katalog_programu, "rozklad.json")

    wzorzec_linku = re.compile(
        r"/rozklad-pkp/[^/]+/(?P<slug>[^/]+)/(?P<data>\d{2}-\d{2}-\d{4})_(?P<godzina>\d{2}:\d{2})"
    )
    wzorzec_pociagu = re.compile(r"^(?P<pociag>.*?)(?P<peron>Peron.*)?$")

    odjazdy = []
    unikalne_klucze = set()

    for url in urle:
        try:
            print(f"Pobieranie danych z: {url}...")
            response = requests.get(url, headers=headers, timeout=15)

            if response.status_code == 403 or "cloudflare" in response.text.lower():
                print(f"[BŁĄD] Serwer Koleo zablokował zapytanie do {url}.")
                continue

            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')

            elementy = soup.find_all(["h2", "a"])
            aktualna_stacja_docelowa = None

            for element in elementy:
                if element.name == "h2":
                    tekst = element.get_text(strip=True)
                    if tekst and tekst.lower() != "odjazdy":
                        aktualna_stacja_docelowa = tekst
                    continue

                href = element.get("href", "")
                dopasowanie = wzorzec_linku.search(href)
                if not dopasowanie or not aktualna_stacja_docelowa:
                    continue

                godzina = dopasowanie.group("godzina")
                data = dopasowanie.group("data")

                tekst_linku = element.get_text(strip=True)
                if tekst_linku.startswith(godzina):
                    reszta = tekst_linku[len(godzina):]
                else:
                    reszta = tekst_linku

                dopasowanie_pociagu = wzorzec_pociagu.match(reszta)
                numer_pociagu = dopasowanie_pociagu.group("pociag").strip() if dopasowanie_pociagu else reszta
                peron = dopasowanie_pociagu.group("peron").strip() if dopasowanie_pociagu and dopasowanie_pociagu.group("peron") else ""

                # Unikalny klucz zapobiegający dublowaniu kursów (np. tuż po północy)
                klucz = (data, godzina, numer_pociagu, aktualna_stacja_docelowa)
                if klucz in unikalne_klucze:
                    continue
                unikalne_klucze.add(klucz)

                odjazdy.append({
                    "time": godzina,
                    "destination": aktualna_stacja_docelowa,
                    "train": numer_pociagu,
                    "platform": peron,
                    "date": data
                })

        except Exception as e:
            print(f"Wystąpił błąd przy pobieraniu z {url}: {e}")

    if not odjazdy:
        print("\n[BŁĄD] Nie udało się wyodrębnić żadnych odjazdów.")
        return

    # Zapis do pliku JSON
    try:
        wynik = {"departures": odjazdy}
        with open(sciezka_zapisu, "w", encoding="utf-8") as f:
            json.dump(wynik, f, indent=2, ensure_ascii=False)

        print(f"\n[SUKCES] Pobrano łącznie {len(odjazdy)} odjazdów (dzisiaj i jutro).")
        print(f"Plik został zapisany w katalogu roboczym: {sciezka_zapisu}")

    except Exception as e:
        print(f"\nWystąpił błąd podczas zapisu pliku: {e}")

if __name__ == "__main__":
    pobierz_odjazdy()