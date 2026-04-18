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

## Hosting — ZAWSZE PRZEZ COOLIFY + GITHUB
- **URL:** https://bieganie.nocodework.pl
- **Serwer:** serwer1 (204.168.178.238)
- **Coolify UUID:** `kh79yxgsf0pq5uq0s5xeai3q`
- **Projekt:** Strony statyczne (`lpwjdtu7bn336kszd63ma52y`)
- **Build pack:** Dockerfile (z GitHub)
- **GitHub repo:** https://github.com/Brunodev/bieganie (publiczne)
- **Branch:** main
- **Deploy:** Coolify buduje obraz z Dockerfile i deployuje automatycznie
- **Webhook:** GitHub → Coolify (secret: `coolify-bieganie-2026`) — auto-build po `git push`
- **DNS:** wildcard `*.nocodework.pl` → serwer1 (automatycznie)

**WAŻNE: NIGDY nie deployuj ręcznym docker run. Zawsze przez GitHub + Coolify.**

## Dane w kontenerze
| Ścieżka | Opis |
|---------|------|
| `/app/index.html` | Strona HTML (z GitHub, w obrazie Docker) |
| `/app/server.py` | Flask API (z GitHub, w obrazie) |
| `/app/data/bieganie.db` | SQLite baza (persistent w kontenerze) |
| `/app/data/uploads/` | Screenshoty z Garmina |
| `/app/data/.garmin_tokens/` | Tokeny Garmin Connect |

## API Endpoints
| Metoda | URL | Opis |
|--------|-----|------|
| GET | `/` | Strona HTML |
| GET | `/api/entries` | Lista treningów (JSON) |
| POST | `/api/entries` | Dodaj trening (FormData: date, distance, time, pace, type, notes, screenshot) |
| DELETE | `/api/entries/{id}` | Usuń trening |
| GET | `/uploads/{filename}` | Screenshot z Garmina |

## Deploy / Aktualizacja — ZAWSZE PRZEZ GITHUB
```bash
# 1. Edytuj pliki lokalnie (Hetzner/bieganie/)
# 2. Commit + push na GitHub
cd /Users/mikolajbrunka/Pliki/Asystent/Hetzner/bieganie
git add -A && git commit -m "opis zmiany" && git push

# 3. Redeploy w Coolify (API lub UI)
source /Users/mikolajbrunka/Pliki/Asystent/Hetzner/.env
curl -s -X GET "${COOLIFY_URL}/api/v1/applications/kh79yxgsf0pq5uq0s5xeai3q/restart" \
  -H "Authorization: Bearer ${COOLIFY_TOKEN}"
```

**NIGDY** nie rób ręcznego `docker run` ani `docker cp`. Kod idzie z GitHub → Coolify buduje → Coolify deployuje.

## Pliki (Git repo: Brunodev/bieganie)
| Plik | Opis |
|------|------|
| `index.html` | Strona — przewodnik + dziennik treningowy |
| `server.py` | Flask API (serwuje HTML + API + uploads + auto-sync co 3h) |
| `database.py` | SQLite baza (aktywności, manual entries, sync log) |
| `garmin_sync.py` | Sync z Garmin Connect (python-garminconnect) |
| `vdot.py` | Obliczanie VDOT ze wzoru Danielsa-Gilberta |
| `Dockerfile` | Python 3.12-slim + Flask + gunicorn + garminconnect |
| `requirements.txt` | flask, gunicorn, garminconnect, curl_cffi |
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
