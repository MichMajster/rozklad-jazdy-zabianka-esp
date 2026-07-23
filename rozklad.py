import os
import re
import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime, timedelta

def pobierz_odjazdy():
    dzisiaj_dt = datetime.now()
    jutro_dt = dzisiaj_dt + timedelta(days=1)
    
    data_dzis_str = dzisiaj_dt.strftime("%Y-%m-%d")
    data_jutro_str = jutro_dt.strftime("%Y-%m-%d")

    data_dzis_koleo = dzisiaj_dt.strftime("%d-%m-%Y")
    data_jutro_koleo = jutro_dt.strftime("%d-%m-%Y")

    baza_url = "https://koleo.pl/dworzec-pkp/gdansk-zabianka-awfis/odjazdy"
    urle = [
        (baza_url, data_dzis_koleo, "dzis"),
        (f"{baza_url}/{data_jutro_str}", data_jutro_koleo, "jutro")
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
    katalog_wyjsciowy = os.path.join(katalog_programu, "rozklady_godzinowe")
    os.makedirs(katalog_wyjsciowy, exist_ok=True)

    wzorzec_linku = re.compile(
        r"/rozklad-pkp/[^/]+/(?P<slug>[^/]+)/(?P<data>\d{2}-\d{2}-\d{4})_(?P<godzina>\d{2}:\d{2})"
    )
    wzorzec_pociagu = re.compile(r"^(?P<pociag>.*?)(?P<peron>Peron.*)?$")

    pliki_odjazdow = {f"{h:02d}": [] for h in range(24)}
    pliki_odjazdow["00_jut"] = []
    pliki_odjazdow["01_jut"] = []

    unikalne_klucze = set()

    for url, oczekiwana_data, typ_dnia in urle:
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

                if data != oczekiwana_data:
                    continue

                hh = godzina.split(":")[0]

                if typ_dnia == "jutro":
                    if hh not in ("00", "01"):
                        continue
                    klucz_pliku = f"{hh}_jut"
                else:
                    klucz_pliku = hh

                tekst_linku = element.get_text(strip=True)
                if tekst_linku.startswith(godzina):
                    reszta = tekst_linku[len(godzina):]
                else:
                    reszta = tekst_linku

                dopasowanie_pociagu = wzorzec_pociagu.match(reszta)
                numer_pociagu = dopasowanie_pociagu.group("pociag").strip() if dopasowanie_pociagu else reszta
                peron = dopasowanie_pociagu.group("peron").strip() if dopasowanie_pociagu and dopasowanie_pociagu.group("peron") else ""

                klucz = (data, godzina, numer_pociagu, aktualna_stacja_docelowa)
                if klucz in unikalne_klucze:
                    continue
                unikalne_klucze.add(klucz)

                pliki_odjazdow[klucz_pliku].append({
                    "time": godzina,
                    "destination": aktualna_stacja_docelowa,
                    #"train": numer_pociagu,
                    #"platform": peron,
                    "date": data
                })

        except Exception as e:
            print(f"Wystąpił błąd przy pobieraniu z {url}: {e}")

    # Zapis z wcześniejszym SORTOWANIEM CHRONOLOGICZNYM
    zapisane_pliki = 0
    for nazwa_pliku, odjazdy_godzina in pliki_odjazdow.items():
        # SORTOWANIE PO CZASIE ODJAZDU (HH:MM)
        odjazdy_godzina.sort(key=lambda x: x["time"])

        sciezka = os.path.join(katalog_wyjsciowy, f"{nazwa_pliku}.json")
        try:
            with open(sciezka, "w", encoding="utf-8") as f:
                json.dump({"departures": odjazdy_godzina}, f, indent=2, ensure_ascii=False)
            zapisane_pliki += 1
        except Exception as e:
            print(f"Błąd zapisu pliku {nazwa_pliku}.json: {e}")

    print(f"\n[SUKCES] Zapisano i posortowano {zapisane_pliki} plików JSON w folderze: {katalog_wyjsciowy}")

if __name__ == "__main__":
    pobierz_odjazdy()