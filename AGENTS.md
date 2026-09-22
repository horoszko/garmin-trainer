# AGENTS.md — Garmin Trainer

## Cel projektu

Garmin Trainer ma być prosty, czytelny, audytowalny i łatwy do wdrożenia oraz
odtworzenia. Nie buduj infrastruktury „na zapas”.

## Architektura

```text
Open WebUI
    ↓
app/workspace_tools_*.py
    ↓
app/garmin_db.py / app/training_diary.py / app/tools_fit.py
    ↓
GarminDB / Training Diary / FIT
```

- Open WebUI jest warstwą interfejsu i integracji z użytkownikiem.
- `app/workspace_tools_*.py` są cienkimi, niezależnie podłączanymi adapterami
  capabilities Open WebUI.
- `app/garmin_db.py`, `app/training_diary.py` i `app/tools_fit.py` zawierają
  logikę biznesową i nie mogą
  zależeć od modułów Open WebUI.
- Rdzeń powinien pozostać możliwy do użycia przez inny adapter w przyszłości.
- Nie dodawaj nowych warstw komunikacyjnych bez realnego wymagania i wyraźnej
  decyzji użytkownika.

## Kontekst kontynuowania pracy i odtworzenie projektu

Oficjalne repozytorium projektu:

```text
https://github.com/horoszko/garmin-trainer
```

### Aktualny stan projektu

- Open WebUI: `v0.11.4`;
- GarminDB: `3.7.0`;
- Garmin FIT SDK: `21.214.0`;
- wdrożenie: jeden kontener Docker;
- jedna instancja: jeden użytkownik GarminDB;
- bootstrap: oficjalne API Open WebUI;
- stan Open WebUI: trwały wolumen `openwebui-data`;
- dane Garmin Trainer: bind mounty w `data/`.

Za zakończone i działające obszary należy obecnie uznawać:

- niezależne GarminDB Tools, Training Diary Tools i FIT Tools;
- natywne załączanie plików `.fit`;
- natywne załączanie, podgląd i pobieranie Markdown Diary;
- konwersacyjny onboarding `/start`;
- `/sync`, `/sync full` i `/sync stop`;
- zatrzymywanie synchronizacji przez grupę procesu;
- trwałość provider connections, historii rozmów i ustawień Open WebUI;
- wzorzec `docs/training_diary/2000-W00_training_diary.md`;
- przypięte wersje bezpośrednich zależności.

Jedna instancja Garmin Trainer obsługuje obecnie jednego użytkownika GarminDB.
Obsługa kolejnego użytkownika wymaga osobnej instancji kontenera z oddzielnym
katalogiem `data/`.

### Core i adaptery

Rdzeń aplikacji jest napisany w Pythonie i nie zależy od Open WebUI. Obejmuje
między innymi:

- `app/garmin_db.py`;
- `app/training_diary.py`;
- `app/tools_fit.py`;
- `app/workout_json_to_fit_encoder.py`.

Obecnym adapterem interfejsu są:

- `app/workspace_tools_garmin_db.py`;
- `app/workspace_tools_training_diary.py`;
- `app/workspace_tools_fit.py`;
- konfiguracje `config/tools/*.json`.

Adapter może tłumaczyć wywołania Tools, emitować statusy do GUI i załączać pliki
w sposób właściwy dla Open WebUI. Logika domenowa ma pozostać w core.

Projekt wykorzystuje obecnie oficjalne API Open WebUI do synchronizacji Tools,
Custom Models i Knowledge. `bootstrap_openwebui.py` jest adapterem wdrożeniowym,
a nie częścią core treningowego.

Core można w przyszłości wykorzystać przez inny adapter Python, własne API,
MCP, CLI albo inny framework agentowy. MCP i osobne API Garmin Trainer nie są
obecnie zaimplementowane. Nie dodawaj ich bez konkretnego wymagania użytkownika.

Plik `app/garmin_trainer.py` nie jest częścią aktualnej architektury i nie należy
przywracać go jako fasady wyłącznie dla historycznej kompatybilności.

### Źródła prawdy i ważne rozróżnienia

- GarminDB — faktycznie wykonane aktywności i metryki;
- Training Diary — plan, interpretacja, ustalenia i decyzje;
- Knowledge — opcjonalna wiedza metodologiczna;
- wolumen Open WebUI — provider connections, historia rozmów, użytkownicy i ustawienia.

Nie myl następujących katalogów:

- `data/` — dane runtime i dane użytkownika;
- `config/` — zasoby projektu synchronizowane przez bootstrap;
- `docs/` — dokumentacja i wzorce commitowane do repozytorium;
- `app/` — Pythonowy core i adaptery;
- `config/tools/` — opisy i implementacje Tools uruchamiane przez Open WebUI.

Tool Open WebUI jest adapterem oraz opisem funkcji. Nie jest właściwą logiką
domenową, która powinna pozostać w Pythonowym core.

Do repozytorium nie wolno commitować:

- `.env`;
- `data/garmindb/GarminConnectConfig.json`;
- sesji Garmin Connect;
- baz i logów GarminDB;
- rzeczywistych plików `data/training_diary/`;
- wygenerowanych plików FIT;
- runtime i bazy Open WebUI.

### Świeża instalacja

Minimalny scenariusz odtworzenia projektu:

```bash
git clone https://github.com/horoszko/garmin-trainer
cd garmin-trainer

cp .env.example .env
cp data/garmindb/GarminConnectConfig.json.example \
  data/garmindb/GarminConnectConfig.json
chmod 600 data/garmindb/GarminConnectConfig.json

docker compose up -d --build
```

Przed uruchomieniem uzupełnij w `.env`:

- `WEBUI_ADMIN_EMAIL`;
- `WEBUI_ADMIN_PASSWORD`;
- `WEBUI_ADMIN_NAME`.

Uzupełnij również dane Garmin Connect w:

```text
data/garmindb/GarminConnectConfig.json
```

Ten plik zawiera sekrety i nigdy nie może trafić do repozytorium. Commitowany
jest wyłącznie `data/garmindb/GarminConnectConfig.json.example`.

GarminDB korzysta z katalogu `data/garmindb/`. Nie twórz ani nie używaj
`data/garmindb/garmin_data/` jako katalogu konfiguracyjnego projektu.

Po uruchomieniu Open WebUI jest dostępne pod portem `3000`. Bootstrap musi
zakończyć się sukcesem; w przeciwnym razie entrypoint zatrzymuje kontener.

### Zasoby zarządzane przez bootstrap

Bootstrap synchronizuje wyłącznie zasoby projektu:

- `config/tools/*.json` — Workspace Tools;
- `config/custom_models/*.json` — Custom Models;
- `data/knowledge/<source>/` — źródła Knowledge.

Bootstrap jest idempotentny, aktualizuje istniejące zasoby i może usuwać z
zarządzanego Knowledge pliki, których nie ma już w lokalnym źródle. Nie resetuje
provider connections, historii rozmów, użytkowników ani innych ustawień Open
WebUI.

### Polecenia użytkownika

- `/start` — konwersacyjny onboarding bez formularza i code blocka;
- `/sync` — synchronizacja najnowszych danych (`auto/latest`);
- `/sync full` — pełna synchronizacja wyłącznie na wyraźne żądanie;
- `/sync stop` — zatrzymanie aktywnej synchronizacji;
- prośba o istniejący Diary — użyj `get_training_diary()`;
- prośba o plik FIT — użyj odpowiedniego Toola FIT.

Pełna synchronizacja może potrwać kilka godzin. Nie uruchamiaj jej automatycznie
ani wyłącznie jako testu. Po jej przerwaniu dane mogą być częściowo zaktualizowane
i pełną synchronizację warto później świadomie powtórzyć.

### Training Diary i W00

Referencyjny wzorzec znajduje się w:

```text
docs/training_diary/2000-W00_training_diary.md
```

`2000-W00` nie jest profilem użytkownika i nie należy kopiować go do
`data/training_diary/`. Rzeczywisty profil ma nazwę:

```text
data/training_diary/<CURRENT_YEAR>-W00_training_diary.md
```

Brakujące dane pozostają `null`; agent nie może zgadywać parametrów treningowych.
Ponowne `/start` nie może automatycznie nadpisywać istniejącego W00.

### Trwałość i bezpieczeństwo

Wolumen `openwebui-data` przechowuje między innymi provider connections, historię
rozmów, użytkowników, ustawienia i bazę Open WebUI. Rebuild lub restart nie
powinien usuwać tych danych.

Nie używaj bez wyraźnej zgody użytkownika:

```bash
docker compose down -v
```

Ta komenda może usunąć trwały stan Open WebUI. Backup powinien obejmować
`openwebui-data`, `data/garmindb`, `data/training_diary` oraz — jeśli nie istnieje
osobna kopia — `data/knowledge`.

### Weryfikacja po instalacji

Po wdrożeniu sprawdź:

```bash
docker compose ps
docker compose logs --tail=200 open-webui
curl http://localhost:3000/health
curl http://localhost:3000/api/version
```

Należy potwierdzić status `healthy`, poprawne zakończenie bootstrapu, wersję
Open WebUI `v0.11.4`, obecność Tools i Custom Models oraz działające provider
connection. Minimalny test funkcjonalny obejmuje `/start`, `/sync`, odczyt Diary,
generowanie FIT oraz `/sync full` → `/sync stop`.

### Rozpoczęcie pracy przez kolejnego agenta

Agent rozpoczynający pracę powinien przeczytać `AGENTS.md` i `README.md`, a
następnie sprawdzić faktyczny kod, konfigurację i `git status`. Dokumentacja nie
zastępuje kontroli stanu projektu. Agent nie powinien zakładać, że zna historię
wcześniejszych rozmów ani traktować `ROADMAP.md` jako aktualnej specyfikacji.
`ROADMAP.md` jest lokalnym, roboczym plikiem i nie jest źródłem kontekstu
projektu.

Przed modyfikacją agent powinien:

1. ustalić faktyczny stan implementacji;
2. sprawdzić zakres zadania i pliki, których dotyczy;
3. uwzględnić trwałość danych Open WebUI i danych użytkownika;
4. zaproponować zakres zmiany, jeśli zadanie wymaga decyzji architektonicznej;
5. nie wykonywać większego refaktoru bez akceptacji użytkownika.

## KISS i rozwój projektu

- Rozwijaj istniejący kod i architekturę zamiast przepisywać je od nowa.
- Większy refaktor lub zmiana architektury wymaga wyraźnej decyzji użytkownika.
- Nie twórz abstrakcji, konfiguracji ani usług „na zapas”.
- Preferuj prosty, jawny kod nad sprytnym lub nadmiernie generycznym.
- Nie zmieniaj zachowania aplikacji przy okazji porządkowania kodu.

## Czytelność kodu

Kod ma być łatwy do audytu przez człowieka w VS Code:

- stosuj normalne wieloliniowe formatowanie i czytelne nazwy;
- używaj krótkich docstringów tam, gdzie funkcja nie jest oczywista;
- unikaj skompresowanych one-linerów i zbędnych warstw pośrednich;
- komentarze mają wyjaśniać „dlaczego”, a nie przepisywać kod;
- konfiguracje JSON formatuj i utrzymuj w postaci edytowalnej dla człowieka.

## Struktura projektu

```text
config/
├── custom_models/
└── tools/

data/
├── garmindb/
├── training_diary/
├── generated/
└── knowledge/
```

- `config/custom_models/` zawiera konfiguracje custom modeli i person.
- `config/tools/` zawiera konfiguracje Workspace Tools.
- `data/garmindb/` zawiera dane GarminDB.
- `data/training_diary/` zawiera dziennik treningowy w Markdown.
- `data/generated/` zawiera wygenerowane pliki FIT.
- `data/knowledge/` zawiera przenośne źródła wiedzy.

Nazwy plików konfiguracyjnych mają być samoopisujące. Użytkownik powinien móc
je bezpiecznie odczytać i ręcznie edytować po sklonowaniu projektu.

## Główne zależności

Projekt opiera się na następujących bezpośrednich komponentach:

- [Open WebUI](https://github.com/open-webui/open-webui);
- [GarminDB](https://github.com/elbart/garmindb);
- [Garmin FIT Python SDK](https://github.com/garmin/fit-python-sdk).

Aktualnie używana i przetestowana wersja Open WebUI: `v0.11.4`.
Przypięte wersje bezpośrednich pakietów Python:

- `GarminDb==3.7.0`;
- `garmin-fit-sdk==21.214.0`.

Nie dokumentuj tutaj pełnego drzewa zależności tranzytywnych instalowanych
przez `pip`.

## Standard Knowledge

Każdy bezpośredni podfolder `data/knowledge/` reprezentuje jedno niezależne
Knowledge w Open WebUI.

```text
data/knowledge/
└── training-for-the-uphill-athlete/
    ├── _source.md
    ├── 01-....md
    └── ...
```

- Nazwa folderu jest krótkim, czytelnym `source-slugiem`.
- Każdy folder musi zawierać `_source.md`.
- Pozostałe pliki `.md` są właściwą treścią wiedzy.
- `_source.md` zawiera metadane i opis dla człowieka; nie jest importowany jako
  dokument Knowledge.
- Nie stosuj w `_source.md` flag `enabled` ani `disabled`. Wybór Knowledge
  używanego przez model odbywa się w Open WebUI.
- Bootstrap nie może zawierać hardcodowanych nazw konkretnych książek ani
  źródeł.

Minimalny standard `_source.md`:

```yaml
---
name: Training for the Uphill Athlete
title: Training for the Uphill Athlete
author: Steve House, Scott Johnston, Kilian Jornet
source: książka
description: Wiedza o treningu wytrzymałościowym i przygotowaniu do sportów górskich.
---

Dłuższy opis źródła przeznaczony dla człowieka.
```

Znaczenie pól:

- `name` — nazwa Knowledge widoczna w Open WebUI;
- `title` — tytuł materiału;
- `author` — autor lub autorzy;
- `source` — typ albo pochodzenie materiału;
- `description` — krótki opis przeznaczony do GUI;
- treść poniżej frontmatter — pełniejszy opis dla człowieka.

## Bootstrap Open WebUI

Bootstrap:

- korzysta wyłącznie z oficjalnego API Open WebUI;
- jest idempotentny i nie tworzy duplikatów;
- synchronizuje Tools, Custom Models i Knowledge;
- czyta konfigurację i źródła z plików projektu;
- nie modyfikuje bezpośrednio bazy SQLite Open WebUI;
- pozostaje prosty i możliwy do ręcznej kontroli.
- jest wymaganym elementem startu aplikacji; jeśli się nie powiedzie, entrypoint
  zatrzymuje Open WebUI i kończy kontener błędem.

Konfiguracje obiektów tworzonych przez bootstrap mają być czytelne, formatowane
i możliwe do ręcznej edycji. Zmiana pliku konfiguracyjnego nie powinna wymagać
przepisywania kodu bootstrapu.

## Dane, Docker i bezpieczeństwo

- Dane użytkownika przechowuj w jawnych bind mountach `data/`.
- Stan Open WebUI przechowuj w jego dedykowanym wolumenie.
- Wersję Open WebUI przypinaj do konkretnego, przetestowanego tagu. Aktualizuj
  ją świadomie razem z testami projektu; nie używaj domyślnie `main` ani `latest`.
- Preferuj najnowsze stabilne wersje zależności, ale każdą aktualizację najpierw
  sprawdź pod kątem kompatybilności z projektem. Dotyczy to w szczególności
  Open WebUI i GarminDB.
- Przy każdej pracy nad kodem sprawdź dostępność nowszych wersji używanych
  narzędzi i oceń, czy aktualizacja jest kompatybilna oraz warta wykonania.
- Nie wymagaj ręcznego ustawiania `WEBUI_SECRET_KEY` w `.env`. Używaj
  `WEBUI_SECRET_KEY_FILE=/app/backend/data/.webui_secret_key`, aby Open WebUI
  mogło wygenerować sekret i zachować go w persistent volume.
- Nie hardcoduj sekretów, tokenów, haseł, IP hosta ani domen zależnych od
  instalacji.
- Konfigurację zależną od instalacji pobieraj z `.env` lub zmiennych środowiska.
- Nie pokazuj sekretów w logach i nie commituj ich.
- Nie modyfikuj ani nie usuwaj danych GarminDB, Training Diary, Knowledge lub
  wygenerowanych plików bez wyraźnej potrzeby zadania.
- Nie modyfikuj repozytoriów referencyjnych używanych wyłącznie do odczytu.
- Przed usunięciem kodu upewnij się, że jest nieużywany; przy niepewności
  pozostaw go i zgłoś do decyzji.

Wygenerowanie FIT powinno:

1. zapisać poprawny plik w `data/generated/`;
2. zwrócić neutralny wynik w rdzeniu;
3. załączyć plik do rozmowy dopiero w adapterze Open WebUI.

`app/workout_json_to_fit_encoder.py` jest używany przez rdzeń do zapisania pliku
FIT. Adapter odpowiada za jego natywne załączenie w rozmowie.

## Odpowiedzialność danych treningowych

- GarminDB jest źródłem prawdy o tym, co faktycznie się wydarzyło.
- Training Diary przechowuje plan, interpretację, kontekst, realizację względem
  planu, ocenę jednostek i dalsze decyzje.
- Nie przedstawiaj estymacji jako faktów.
- Markdown preferuj ze względu na czytelność i migrację danych.

## GarminDB

`-f` w GarminDB CLI wskazuje katalog konfiguracji, a nie plik JSON:

```bash
garmindb_cli.py -f /data/garmindb --all --download --import --analyze
```

Tryb `auto` ma oznaczać `latest`. Pełna synchronizacja jest dozwolona tylko po
wyraźnym żądaniu użytkownika i nie może być uruchamiana automatycznie ani
wykonywana wyłącznie w celu przetestowania kodu.

## Workflow zmian

Pracuj etapami:

1. sprawdź faktyczny stan projektu i istniejące zmiany;
2. określ zakres oraz pliki, których dotyczy zadanie;
3. zmodyfikuj tylko to, co jest potrzebne;
4. uruchom testy adekwatne do zmiany i nie maskuj błędów;
5. pokaż zmienione pliki, wyniki testów i najważniejsze obserwacje;
6. zatrzymaj się przed kolejnym logicznym etapem i czekaj na akceptację.

Nie wykonuj szerokich zmian przy okazji. Nie commituj ani nie pushuj bez wyraźnej
zgody użytkownika.

Przy zmianach destrukcyjnych najpierw potwierdź dokładny zakres i sprawdź, czy
element nie jest używany. Nie stosuj `git reset --hard` ani blanket restore.

## Testowanie

Dobieraj testy do zmiany. Przy kodzie Python sprawdź co najmniej składnię
zmodyfikowanych plików. Przy zmianach Dockera sprawdź konfigurację Compose. Przy
zmianach bootstrapu sprawdź zachowanie oficjalnego API Open WebUI i idempotencję.

Nie uruchamiaj pełnej synchronizacji GarminDB jako testu.

# Możliwe kierunki rozwoju

- obsługa wielu użytkowników i niezależnych profili GarminDB w jednej instancji aplikacji;
- zweryfikowanie działania z innymi dyscyplinami sportowymi.
