# bieganie.nocodework.pl — Przewodnik po bieganiu

## Opis
Personalny przewodnik po bieganiu dla partnerki Mikołaja. System VDOT Jacka Danielsa, szkoła amerykańska, strefy treningowe, plan treningowy 3x/tydzień. Dziennik treningowy z API (zapis na serwerze).

## Dane biegaczki
- Kobieta, 25 lat, 77 kg, 180 cm
- HRmax: 191 bpm (wzór Tanaki)
- VDOT: 27.9 (półmaraton 2:30:03, tempo 7:07/km)

## Tempa treningowe (VDOT 27.9)
| Strefa | Tempo (min/km) |
|--------|---------------|
| Easy (E) | 7:20 – 8:02 |
| Marathon (M) | 7:15 |
| Threshold (T) | 6:27 |
| Interval (I) | 5:40 |
| Repetition (R) | 5:25 |

## Strefy tętna (HRmax 191)
| Strefa | bpm |
|--------|-----|
| 1 Regeneracja | 95–114 |
| 2 Baza tlenowa | 115–143 |
| 3 Tempo | 144–156 |
| 4 Próg | 157–172 |
| 5 Maksymalna | 173–191 |

## Hosting
- **URL:** https://bieganie.nocodework.pl
- **Serwer:** serwer1 (204.168.178.238)
- **Kontener:** `bieganie-app` (ręczny docker run, NIE przez Coolify)
- **Technologia:** Python Flask (gunicorn) — serwuje HTML + API
- **Traefik labels:** automatyczny HTTPS via coolify-proxy
- **DNS:** wildcard `*.nocodework.pl` → serwer1 (automatycznie)
- **Coolify:** app `uldkyvseufswahkowrcut2a0` jest ZATRZYMANA (zastąpiona kontenerem ręcznym)

## Dane na serwerze
| Ścieżka | Opis |
|---------|------|
| `/data/bieganie/index.html` | Strona HTML |
| `/data/bieganie/server.py` | Flask API server |
| `/data/bieganie/Dockerfile` | Obraz Docker |
| `/data/bieganie/requirements.txt` | Zależności (flask, gunicorn) |
| `/data/bieganie/entries.json` | Baza danych treningów (JSON) |
| `/data/bieganie/uploads/` | Screenshoty z Garmina |

## API Endpoints
| Metoda | URL | Opis |
|--------|-----|------|
| GET | `/` | Strona HTML |
| GET | `/api/entries` | Lista treningów (JSON) |
| POST | `/api/entries` | Dodaj trening (FormData: date, distance, time, pace, type, notes, screenshot) |
| DELETE | `/api/entries/{id}` | Usuń trening |
| GET | `/uploads/{filename}` | Screenshot z Garmina |

## Deploy / Aktualizacja
```bash
# 1. Upload plików na serwer
scp -i ~/.ssh/Hetzner_ index.html server.py deploy@100.119.224.115:/data/bieganie/

# 2. Jeśli zmienił się tylko HTML — restart nie potrzebny (Flask serwuje z /data/bieganie/)
# 3. Jeśli zmienił się server.py lub Dockerfile — rebuild:
ssh -i ~/.ssh/Hetzner_ deploy@100.119.224.115 "cd /data/bieganie && \
  sudo docker build -t bieganie-app . && \
  sudo docker stop bieganie-app && sudo docker rm bieganie-app && \
  sudo docker run -d --name bieganie-app --restart unless-stopped \
    --network coolify -v /data/bieganie:/data/bieganie \
    -l 'traefik.enable=true' \
    -l 'traefik.http.routers.bieganie-https.rule=Host(\`bieganie.nocodework.pl\`)' \
    -l 'traefik.http.routers.bieganie-https.entrypoints=https' \
    -l 'traefik.http.routers.bieganie-https.tls=true' \
    -l 'traefik.http.routers.bieganie-http.rule=Host(\`bieganie.nocodework.pl\`)' \
    -l 'traefik.http.routers.bieganie-http.entrypoints=http' \
    -l 'traefik.http.services.bieganie.loadbalancer.server.port=5000' \
    bieganie-app"
```

## Pliki lokalne
| Plik | Opis |
|------|------|
| `index.html` | Strona — przewodnik + dziennik treningowy |
| `server.py` | Flask API (serwuje HTML + API + uploads) |
| `Dockerfile` | Python 3.12 alpine + Flask + gunicorn |
| `requirements.txt` | flask, gunicorn |
| `CLAUDE.md` | Ten plik |

## Zawartość strony
1. Porównanie szkół biegania (polska / amerykańska / norweska)
2. System VDOT — co to jest, jak działa
3. 5 stref treningowych z tempami i opisami
4. Plan treningowy 3 dni/tydzień (szkoła amerykańska)
5. Strefy tętna (spersonalizowane) + kalkulator Karvonena
6. Od zera do 5 km (10-tygodniowy plan marszobiegu)
7. Progresja i 10 typowych błędów
8. **Dziennik treningowy** — formularz + tabela + screenshoty (dane na serwerze, JSON + uploads)

## Funkcje interaktywne
- Kalkulator stref tętna (Karvonen)
- Dziennik treningowy: dodawanie, przeglądanie, usuwanie wpisów
- Upload screenshotów z Garmina (zapisywane na serwerze)
- Automatyczne obliczanie tempa (dystans + czas)
- Statystyki zbiorcze (łączne km, czas, średnie tempo)
- Lightbox na screenshoty
- Akordeon z opisami stref i błędów

## Do zrobienia
- [ ] Dodać więcej treści o rozciąganiu / warm-up
- [ ] Sekcja z dietą / nawodnieniem dla biegaczy
- [ ] Tracker postępu VDOT w czasie (wykres)
- [ ] Integracja z Garmin API (automatyczny import)
- [ ] Edycja istniejących wpisów
