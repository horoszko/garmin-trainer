# Garmin Trainer

Garmin Trainer udostępnia dane z Garmin Connect agentowi AI poprzez GarminDB i serwer MCP.

Projekt składa się z trzech elementów:

- **GarminDB** – pobieranie i przechowywanie danych Garmin Connect,
- **GarminDB MCP** – udostępnianie danych GarminDB przez MCP,
- **Open WebUI** – interfejs dla agenta Garmin Trainer.

## Struktura

```text
garmin-trainer/
├── docker-compose.yml
├── README.md
├── garmindb/
├── garmindb-mcp/
└── openwebui/
```

## Instalacja

```bash
git clone https://github.com/horoszko/garmin-trainer.git && cd garmin-trainer
```

### Konfiguracja Garmin Connect

Utwórz katalog konfiguracji:
```bash
mkdir -p garmindb/garmin_data
```

Skopiuj przykładowy plik:
```bash
cp garmindb/GarminConnectConfig.json.example garmindb/garmin_data/GarminConnectConfig.json
```

Edytuj:
```bash
nano garmindb/garmin_data/GarminConnectConfig.json
```

Wpisz dane logowania do Garmin Connect oraz ustaw daty, od których GarminDB ma pobrać historię.

Domyślnie pobieranych jest 25 ostatnich aktywności. Zakres historii oraz pozostałe opcje pobierania można zmienić w `garmindb/garmin_data/GarminConnectConfig.json` zgodnie z [dokumentacją GarminDB](https://github.com/tcgoetz/GarminDB).

Pełny przykład konfiguracji GarminDB:

https://github.com/tcgoetz/GarminDB/blob/master/garmindb/GarminConnectConfig.json.example

## Pierwsze uruchomienie

Zbuduj i uruchom projekt:
```bash
docker compose up -d --build && docker compose logs -f garmindb
```

Przy pierwszym uruchomieniu GarminDB może przez kilka - kilkadziesiat minut pobierać i analizować dane z Garmin Connect (w zależności od liczby dni i aktywności, które pobieramy oraz szybkości łącza).

Poprawne zakończenie wygląda tak:
```text
exited with code 0
```

Open WebUI:
```text
http://<IP_SERWERA>:3000
```

GarminDB MCP:
```text
http://<IP_SERWERA>:8000/mcp
```

## Open WebUI

Przy pierwszym uruchomieniu skonfiguruj używany połączenie API :
```text
Ikona Avatar > Ustawienia > Administrator | AI | Połączenia
```

Dodaj Serwer MCP :
```text
Ikona Avatar > Ustawienia > Administrator | Narzędzia | Integracje
Typ : MCP Streamable HTTP
Name: garmindb-mcp
URL: http://garmindb-mcp:8000/mcp
```

Gotową konfigurację Tool Server można również zaimportować z: `openwebui/garmindb-mcp-tool-server-100.json`

Konfiguracja Agenta Garmin Trainer :
```text
Ikona Avatar > Obszar roboczy > (Utwórz) V - Importuj
openwebui/garmin-trainer.json
```

Po imporcie sprawdź, czy Agent ma przypisany serwer MCP w sekcji :
```text
Narzędzia | Wybierz narzędzie : garmindb-mcp
```
UWAGA : Narzędzia MCP wymagają modelu LLM obsługującego wywoływanie narzędzi (tool/function calling). Dobrze sprawdzają się m.in. modele GPT oraz Qwen z obsługą narzędzi.

UWAGA : Dla modeli lokalnych Ollama warto dostosować num_ctx do dostępnej pamięci VRAM. Przy korzystaniu z zewnętrznych dostawców modeli zalecane jest pozostawienie domyślnych ustawień kontekstu - ręczne wymuszanie `num_ctx` może być nieobsługiwane przez API i powodować błędy.

Zapisz i zrób prosty test zapytaj Agenta :

```text
Jaki był mój ostatni trening?
```

## Synchronizacja bazy danych z Garmin Connect

Ręczne pobranie najnowszych danych:
```bash
docker compose run --rm garmindb
```

Synchronizacja działa w terminalu i po zakończeniu zwraca kontrolę użytkownikowi.

Serwer MCP i Open WebUI działają niezależnie od procesu synchronizacji.

## GarminDB

Projekt korzysta obecnie z **GarminDB 3.9.0**.

Podczas budowania obrazu oficjalne repozytorium GarminDB jest klonowane automatycznie.

Projekt stosuje lokalny patch:
```text
garmindb/patches/garmindb-today.patch
```

Patch bazuje na GarminDB PR #318 i naprawia zakres `--latest`, tak aby pobierany był również bieżący dzień.

Jest to istotne m.in. dla aktualnych danych snu, HRV i regeneracji.

Jeżeli poprawka zostanie w przyszłości włączona do GarminDB, patch oraz krok jego aplikowania można usunąć z:

```text
garmindb/Dockerfile
```

Oficjalne repozytorium: https://github.com/tcgoetz/GarminDB

## Narzędzia MCP

Garmin Trainer udostępnia modelowi AI następujące narzędzia:

- `get_activities` – pobiera listę aktywności z wybranego okresu, opcjonalnie ograniczoną do konkretnego sportu. Pozwala analizować historię treningów i porównywać aktywności.
- `get_sport_types` – zwraca rodzaje aktywności dostępne w GarminDB i pomaga modelowi dobrać właściwy filtr sportu.
- `get_sport_summary` – tworzy podsumowanie wybranego sportu w zadanym okresie, m.in. liczbę aktywności, dystans, czas i podstawowe statystyki.
- `get_latest_activity` – zwraca ostatnią aktywność użytkownika lub ostatnią aktywność konkretnego typu wraz z jej podstawowymi parametrami.
- `get_activity_details` – pobiera szczegółowe dane pojedynczego treningu, m.in. lapy, tempo, tętno, kadencję oraz dostępne dane szczegółowe aktywności.
- `get_daily_activity_summary` – grupuje aktywności dzień po dniu w wybranym okresie, ułatwiając analizę regularności i struktury treningów.
- `get_recovery_metrics` – pobiera dane dotyczące regeneracji, m.in. HRV, sen, tętno spoczynkowe, stres i Body Battery.
- `get_training_load_summary` – analizuje obciążenie treningowe tydzień po tygodniu, umożliwiając ocenę zmian objętości i intensywności treningów.
- `get_readiness_summary` – łączy najważniejsze dane treningowe i regeneracyjne potrzebne do oceny aktualnej gotowości do treningu.