# AGENTS.md — Garmin Trainer

## Cel projektu

Garmin Trainer ma być prosty, czytelny, audytowalny i łatwy do wdrożenia oraz
odtworzenia. Nie buduj infrastruktury „na zapas”.

## Zasada dokumentacji

`AGENTS.md` ma zawierać przede wszystkim informacje wpływające na zachowanie
Agenta, których nie można szybko i jednoznacznie wywnioskować z kodu.

Stosuj praktyczny **test 10 sekund**: jeżeli Agent może ustalić daną informację
w kilka–kilkanaście sekund z kodu, konfiguracji lub `README.md`, zwykle nie
trzeba jej tutaj powtarzać.

Dokumentuj przede wszystkim:

- dlaczego coś zostało zaprojektowane w dany sposób;
- źródła prawdy;
- ograniczenia i nietypowe pułapki;
- zasady bezpieczeństwa;
- decyzje, których przyszły Agent nie powinien samowolnie zmieniać.

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

### Założenia wdrożenia

- jedna instancja Garmin Trainer obsługuje jednego użytkownika GarminDB;
- obsługa kolejnego użytkownika wymaga osobnej instancji z oddzielnym katalogiem `data/`;
- bootstrap korzysta z oficjalnego API Open WebUI;
- stan Open WebUI jest trwały i przechowywany w wolumenie `openwebui-data`;
- dane Garmin Trainer są przechowywane w jawnych bind mountach w `data/`.

Aktualne wersje zależności i stan funkcji sprawdzaj w `README.md`, plikach
konfiguracyjnych i faktycznym kodzie zamiast utrzymywać ich kopię w `AGENTS.md`.

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

Procedura instalacji znajduje się w `README.md`.

Przy instalacji:

- korzystaj z commitowanych plików `.example`;
- pytaj użytkownika tylko o brakujące sekrety i prywatne dane;
- nie commituj lokalnej konfiguracji zawierającej dane logowania;
- zachowaj trwałość `data/garmindb/` i wolumenu Open WebUI;
- po wdrożeniu wykonaj walidację opisaną poniżej.

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

Należy potwierdzić status `healthy`, poprawne zakończenie bootstrapu, zgodność
wersji Open WebUI z projektem, obecność Tools i Custom Models oraz działające
provider connection. Minimalny test funkcjonalny obejmuje `/start`, zwykłe
`/sync`, odczyt Diary i generowanie FIT.

`/sync full` i `/sync stop` testuj tylko przy zmianach dotyczących pełnej
synchronizacji lub mechanizmu zatrzymywania. Pełny sync może trwać wiele godzin,
wykonać dużą liczbę zapytań do Garmin Connect i doprowadzić do błędów `503` lub
rate limiting. Nie uruchamiaj go jako zwykłego testu wdrożenia.

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
- konfiguracje JSON formatuj i utrzymuj w postaci edytowalnej dla człowieka;
- nazwy plików konfiguracyjnych utrzymuj jako samoopisujące i czytelne po sklonowaniu projektu.

## Zarządzanie zasobami AI

Używaj najmniejszego modelu, poziomu reasoning, liczby subagentów i ilości
kontekstu wystarczających do niezawodnego wykonania zadania.

- Proste edycje i operacje mechaniczne wykonuj lekkimi zasobami.
- Mocniejsze modele wykorzystuj do architektury, trudnej analizy i niejednoznacznych problemów.
- Po rozwiązaniu trudnego problemu wracaj do tańszych zasobów przy prostych czynnościach.
- Używaj subagentów tylko wtedy, gdy zadania są faktycznie niezależne lub równoległe.
- Nie uruchamiaj browser testu, jeśli zmianę można wiarygodnie sprawdzić testem, API lub logami.
- Nie analizuj całej bazy, repozytorium ani wszystkich logów, jeśli zadanie wymaga tylko ich fragmentu.
- Nie przywiązuj tej polityki do nazw modeli konkretnego dostawcy.

Optymalizuj koszt całego poprawnie wykonanego zadania, nie pojedynczego wywołania.

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

Sama opcja `-f` nie gwarantuje lokalizacji `HealthData`; GarminDB używa także
katalogu domowego procesu. Adapter wymusza `HOME=/data/garmindb` zarówno w
Compose, jak i w środowisku procesu synchronizacji. Po zakończeniu synchronizacji
adapter musi potwierdzić istnienie obu oczekiwanych baz. Kod wyjścia `0` bez baz
nie może być przedstawiony użytkownikowi jako udana synchronizacja.

Tryb `auto` ma oznaczać `latest`. Pełna synchronizacja jest dozwolona tylko po
wyraźnym żądaniu użytkownika i nie może być uruchamiana automatycznie ani
wykonywana wyłącznie w celu przetestowania kodu.

Adapter Open WebUI synchronizacji GarminDB powinien emitować czytelne statusy
dla trybów `latest` i `full`, w tym postęp pobierania oraz importowania
aktywności, dni i plików. Statusy GUI nie mogą wpływać na działanie
synchronizacji ani przerywać jej przy błędzie emisji komunikatu. Powtarzające
się statusy powinny być ograniczane.

W aktualnej wersji Open WebUI GUI może długo wyświetlać `0%` dla podetapu,
który przetwarza pojedynczy plik, mimo że GarminDB nadal pracuje. Stosujemy
obejście w adapterze Open WebUI: dla takiego etapu pokazujemy komunikat o
trwającym przetwarzaniu pliku, a po braku nowego statusu emitujemy okresowy
heartbeat. Jest to obejście prezentacji statusu w obecnej wersji Open WebUI,
a nie zmiana logiki synchronizacji GarminDB.

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
