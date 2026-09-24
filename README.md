# Garmin Trainer

Garmin Trainer to osobisty trener AI oparty na danych z Garmin Connect. Łączy historię treningów z GarminDB, własny dziennik treningowy oraz opcjonalne źródła wiedzy trenerskiej i udostępnia je agentowi w Open WebUI.

Projekt działa w Dockerze i jest pomyślany tak, żeby dało się go łatwo uruchomić, przenieść na inny serwer i rozwijać bez wiązania logiki treningowej z jednym interfejsem AI.

UWAGA: Obecny model wdrożenia: jedna instancja Garmin Trainer = jeden użytkownik GarminDB.
Obsługa kolejnego użytkownika wymaga uruchomienia osobnej instancji kontenera z oddzielnym `data/`, lokalną konfiguracją i niekolidującym portem hosta. Nie współdziel danych GarminDB pomiędzy niezależnymi użytkownikami.

UWAGA: Agent celowo nie ma dostępu do wyszukiwarki internetowej. Korzysta wyłącznie z danych GarminDB, Training Diary oraz źródeł wiedzy umieszczonych w `data/knowledge/`.

> **Ostatnia weryfikacja dokumentacji:** 2026-09-24

## Co potrafi

Garmin Trainer może między innymi:

- analizować aktywności zapisane w Garmin Connect;
- korzystać z danych o obciążeniu, regeneracji, śnie, HRV, tętnie spoczynkowym, stresie, Body Battery i VO2max;
- pamiętać plan, wykonanie i ważne ustalenia w plikach Markdown Training Diary;
- oceniać trening w kontekście poprzednich tygodni;
- układać i aktualizować plan treningowy;
- generować treningi jako pliki FIT (gotowe do wgrania na zegarek) i załączać je bezpośrednio do rozmowy;
- korzystać z własnych źródeł wiedzy, np. książek lub opracowań treningowych;
- synchronizować lokalną bazę GarminDB z poziomu rozmowy chata.

## Jak to działa

Garmin Trainer łączy trzy główne źródła informacji:

1. **GarminDB** — faktyczne dane z Garmin Connect: wykonane aktywności, metryki, obciążenie i regeneracja.
2. **Training Diary** — pamięć robocza trenera: plan, kontekst tygodnia, wykonanie względem planu, ustalenia i wnioski.
3. **Knowledge** — opcjonalna wiedza metodologiczna używana do interpretacji danych i planowania treningu.

W uproszczeniu:

```text
Garmin Connect
      ↓
   GarminDB
      ↓
GarminDB Tools ──────────┐
                         │
Training Diary Tools ────┼── Garmin Trainer w Open WebUI
                         │
Knowledge ───────────────┘

FIT files Tools → data/generated/ → plik FIT w rozmowie
```

GarminDB pozostaje źródłem prawdy o tym, **co rzeczywiście się wydarzyło**. Training Diary przechowuje to, czego nie da się odczytać bezpośrednio z Garmina: plan, znaczenie treningu, decyzje, wykonanie względem planu i dalsze działania.

## API i integracje

Garmin Trainer może być wykorzystywany przez inne agenty i automatyzacje przez API Open WebUI. Obecnym interfejsem integracyjnym są Open WebUI oraz jego Workspace Tools.

Rdzeń aplikacji jest napisany w Pythonie i pozostaje niezależny od warstwy interfejsu, więc może zostać wykorzystany przez inny frontend, framework agentowy lub własny adapter bez przepisywania głównej logiki aplikacji. Osobne API Garmin Trainer i MCP nie są obecnie zaimplementowane.

## Wymagania

- Docker z Docker Compose;
- konto Garmin Connect;
- model LLM obsługujący `tool/function calling`;
- dostęp do zewnętrznego API modelu albo lokalnego providera;
- wolny port `3000` albo odpowiednia zmiana mapowania portu w konfiguracji.

## Szybki start

### 1. Sklonuj repozytorium

```bash
git clone https://github.com/horoszko/garmin-trainer
cd garmin-trainer
cp .env.example .env
```

### 2. Uzupełnij `.env`

Minimalnie ustaw konto administratora Open WebUI:

```text
WEBUI_ADMIN_EMAIL="admin@example.com"
WEBUI_ADMIN_PASSWORD="CHANGE_ME"
WEBUI_ADMIN_NAME="Administrator"
```

Nie zapisuj w repozytorium haseł, tokenów, plików sesji ani prywatnych danych treningowych.

### 3. Skonfiguruj GarminDB

Umieść lokalny plik konfiguracji GarminDB i wprowadź dane logowania Garmin Connect oraz zakresy pobierania danych :

```text
cp data/garmindb/GarminConnectConfig.json.example data/garmindb/GarminConnectConfig.json && nano data/garmindb/GarminConnectConfig.json
```

Format konfiguracji opisuje projekt [GarminDB](https://github.com/elbart/garmindb).

GarminDB przechowuje dane użytkownika w katalogu projektu:

```text
/opt/garmin-trainer/data/garmindb/
```

W kontenerze ten sam katalog jest dostępny jako `/data/garmindb`. Zmienna
`HOME` kontenera jest ustawiona na `/data/garmindb`, ponieważ GarminDB tworzy
`HealthData/` względem katalogu domowego procesu. Oczekiwana lokalizacja baz to:

```text
data/garmindb/HealthData/DBs/garmin.db
data/garmindb/HealthData/DBs/garmin_activities.db
```

Nie używaj `/root/HealthData` ani `data/garmindb/garmin_data/`. Dane w
`data/garmindb/` są lokalnymi danymi użytkownika, pozostają poza repozytorium i
mogą być ręcznie kopiowane oraz przenoszone razem z instalacją.

### 4. Uruchom projekt

```bash
docker compose up -d --build
```

Open WebUI będzie dostępne pod adresem:

```text
http://<IP_SERWERA>:3000
```

Aktualnie używana i przetestowana wersja Open WebUI: `v0.11.4`.

## Pierwsze uruchomienie

Po zalogowaniu do Open WebUI skonfiguruj dostawcę modelu LLM:

```text
Avatar → Ustawienia → Administrator → AI → Połączenia
```

Garmin Trainer nie dostarcza własnego modelu językowego. Możesz użyć zewnętrznego API albo lokalnego modelu, o ile obsługuje wywoływanie narzędzi (`tool/function calling`).

Następnie wybierz jeden z przygotowanych Custom Models i przypisz mu działający model bazowy.

Podczas startu projektu bootstrap automatycznie synchronizuje przez oficjalne API Open WebUI:

- `garmin_db_tools`;
- `training_diary_tools`;
- `fit_files_tools`;
- przygotowane Custom Models;
- źródła Knowledge z `data/knowledge/`.

Bootstrap jest idempotentny: aktualizuje zasoby zarządzane przez projekt, nie powinien tworzyć duplikatów i nie modyfikuje bezpośrednio bazy SQLite Open WebUI. Jeśli bootstrap się nie powiedzie, kontener kończy pracę zamiast uruchamiać niekompletną instalację.

## Pierwsze użycie

Najprościej zacząć od:

```text
/start
```

Jeśli profil startowy W00 jeszcze nie istnieje, trener pokaże dane, które już zna z GarminDB, a następnie zapyta o najważniejsze informacje, których nie da się wiarygodnie wywnioskować automatycznie — np. cel, termin, liczbę głównych jednostek tygodniowo czy preferowane dni treningowe.

Nie trzeba znać wszystkich parametrów. Brakujące dane mogą pozostać puste i zostać uzupełnione później.

Profil startowy jest zapisywany jako plik:

```text
data/training_diary/<ROK>-W00_training_diary.md
```

Referencyjny wzorzec jego struktury znajduje się w:

```text
docs/training_diary/2000-W00_training_diary.md
```

`2000-W00` jest wyłącznie dokumentem referencyjnym. Nie jest aktywnym profilem użytkownika i nie należy kopiować go do `data/training_diary/`.

## Synchronizacja GarminDB

Do codziennej synchronizacji użyj w chacie OpenWebUI z trenerem:

```text
/sync
```

Domyślny tryb pobiera najnowsze dane (`latest`) i nie uruchamia pełnej synchronizacji historii.

Pełną synchronizację uruchamiaj tylko świadomie:

```text
/sync full
```

Może ona potrwać nawet kilka godzin.

Aktywną synchronizację można przerwać:

```text
/sync stop
```

Po przerwaniu część danych może być już zaktualizowana. Jeśli przerwany został pełny sync, później warto uruchomić go ponownie.

## Training Diary

Training Diary to zwykłe pliki Markdown przechowywane w:

```text
data/training_diary/
```

Dziennik może zawierać między innymi:

- profil startowy W00;
- aktualny plan tygodnia;
- wykonanie względem planu;
- ocenę jednostek;
- ważne ustalenia i ograniczenia;
- kontekst potrzebny przy kolejnych rozmowach;
- wnioski trenera.

W tygodniowym Diary sekcje mają stały podział odpowiedzialności:

- `Profil zawodnika` — imię, data urodzenia, masa ciała i płeć; brakujące dane pozostają `null`;
- `Context` — krótki aktualny obraz tygodnia dla LLM;
- `Stan tygodnia` — status, liczniki jednostek i bieżąca decyzja;
- `Ustalenia` — trwałe cele, ograniczenia, preferencje i limity;
- `Plan tygodnia` — planowane jednostki;
- `Ocena jednostek` — szczegóły wykonania;
- `Trend` — porównania i trendy;
- `Notatki trenera` — bieżące obserwacje, samopoczucie, uzasadnienia i następne kontrole.

Nie powtarzaj pełnych list treningów w `Context` ani `Notatki trenera`. Plan i ocena jednostek mają tam swoje główne, jednoznaczne miejsce.
Planowane jednostki zapisuj tylko w `Plan tygodnia`; `Ocena jednostek` uzupełniaj dopiero po wykonaniu, modyfikacji, opuszczeniu albo odwołaniu treningu.

Najważniejsze narzędzia:

- `start_training` — onboarding i obsługa profilu startowego;
- `get_training_context` — odczyt W00 oraz sąsiednich tygodni;
- `get_training_diary` — odczyt i załączenie istniejącej notatki;
- `create_training_diary` — utworzenie nowego Diary;
- `update_training_diary` — aktualizacja wybranej sekcji istniejącego pliku.

Po zapisaniu lub odczytaniu notatki agent może załączyć aktualny `.md` do rozmowy. Open WebUI pozwala wtedy podejrzeć treść Markdown i pobrać plik.

Przykład:

```text
Załącz mi aktualną notatkę Training Diary.
```

## Generowanie plików FIT

Garmin Trainer może przygotować trening i wygenerować plik `.fit` gotowy do dalszego użycia z Garminem.

Przykład:

```text
Utwórz trening FIT: 10 minut rozgrzewki, 3 powtórzenia
1 minuty biegu i 1 minuty regeneracji, 5 minut schłodzenia.
Bez celu tempa.
```

Generator zapisuje plik w:

```text
data/generated/
```

a adapter Open WebUI dodaje go jako załącznik do rozmowy.

## Knowledge

Knowledge jest opcjonalne. Garmin Trainer może działać bez niego, korzystając tylko z GarminDB, Training Diary i system promptu, ale własne źródła wiedzy pozwalają oprzeć sposób planowania na wybranej metodologii.

Każdy bezpośredni podfolder w:

```text
data/knowledge/
```

jest osobnym źródłem Knowledge i powinien zawierać plik `_source.md` z opisem źródła.
Przygotowanie źródła knowledge wg odrębnego opracowania.

Przykładowo:

```text
data/knowledge/
└── training-for-the-uphill-athlete/
    ├── _source.md
    ├── block-01.md
    ├── block-02.md
    └── ...
```

Bootstrap synchronizuje wyłącznie źródła zarządzane przez projekt w `data/knowledge/`. Własne Knowledge można również dodawać bezpośrednio w Open WebUI przez GUI.

## Przykładowe pytania

```text
Jaki był mój ostatni trening?
```

```text
Jak wygląda mój trening w tym tygodniu i co powinienem zrobić dalej?
```

```text
Oceń mój dzisiejszy trening i porównaj go z planem.
```

```text
Jak wygląda moja regeneracja i czy dziś powinienem trenować?
```

```text
Rozpisz mi plan treningowy na przyszły tydzień.
```

```text
Przygotuj mi plik FIT do następnego zaplanowanego treningu. Następnie przełóż planowany trening z środy na czwartek i zapisz tę zmianę w notatce.
```

## Dostępne narzędzia GarminDB

GarminDB Tools udostępniają agentowi między innymi:

- `get_activities` — aktywności z wybranego okresu;
- `get_sport_types` — typy sportów zapisane w bazie;
- `get_sport_summary` — podsumowanie wybranego sportu;
- `get_latest_activity` — ostatnia aktywność;
- `get_activity_details` — szczegóły aktywności, lapy i rekordy;
- `get_daily_activity_summary` — aktywności pogrupowane według dni;
- `get_user_profile` — podstawowe dane profilu;
- `get_recovery_metrics` — dane o regeneracji, m.in. HRV, sen, tętno spoczynkowe i stres;
- `get_training_load_summary` — obciążenie treningowe w kolejnych tygodniach;
- `get_readiness_summary` — dane potrzebne do oceny gotowości;
- `get_vo2max_history` — historia VO2max;
- `get_garmindb_status` — stan lokalnej bazy GarminDB;
- `sync_garmindb` — synchronizacja danych;
- `stop_garmindb_sync` — zatrzymanie aktywnej synchronizacji.

## Architektura projektu

Kod jest rozdzielony na logikę aplikacji i adaptery Open WebUI:

```text
app/
├── garmin_db.py
├── training_diary.py
├── tools_fit.py
├── workspace_tools_garmin_db.py
├── workspace_tools_training_diary.py
└── workspace_tools_fit.py
```

Logika GarminDB, Training Diary i generowania FIT nie powinna zależeć bezpośrednio od Open WebUI. Pliki `workspace_tools_*` pełnią rolę adapterów między rdzeniem projektu a interfejsem Open WebUI.

Dzięki temu te same moduły można w przyszłości wykorzystać z innym frontendem lub systemem agentowym bez przepisywania całej aplikacji.

Pełna struktura:

```text
garmin-trainer/
├── Dockerfile
├── docker-compose.yml
├── README.md
├── AGENTS.md
├── app/
│   ├── garmin_db.py
│   ├── training_diary.py
│   ├── tools_fit.py
│   ├── workspace_tools_garmin_db.py
│   ├── workspace_tools_training_diary.py
│   └── workspace_tools_fit.py
├── config/
│   ├── tools/
│   └── custom_models/
├── data/
│   ├── garmindb/
│   ├── training_diary/
│   ├── generated/
│   └── knowledge/
└── docs/
    └── training_diary/
```

Zestawy Tools są niezależne i mogą być przypisywane do Custom Modeli osobno, np. GarminDB + Training Diary + FIT albo tylko GarminDB.

## Dane i trwałość

Stan Open WebUI jest przechowywany w wolumenie:

```text
openwebui-data
```

Obejmuje on m.in.:

- konfigurację dostawców modeli;
- historię rozmów;
- ustawienia użytkowników;
- bazę Open WebUI.

Restart lub ponowne zbudowanie kontenera nie powinny usuwać tych danych.

Dane Garmin Trainer są przechowywane w jawnych katalogach `data/`:

```text
data/garmindb/         # GarminDB i log synchronizacji
data/training_diary/  # rzeczywiste pliki Training Diary
data/generated/       # wygenerowane pliki FIT
data/knowledge/       # źródła Knowledge zarządzane przez projekt
```

Przy tworzeniu kopii zapasowej warto zabezpieczyć zarówno `data/`, jak i wolumen Open WebUI.

Minimalna kopia danych Garmin Trainer powinna obejmować cały katalog
`data/garmindb/`, w szczególności `HealthData/`, obie bazy SQLite, pliki FIT,
sesję GarminDB oraz `GarminConnectConfig.json`. Plik konfiguracyjny zawiera
sekrety i powinien być przechowywany z ograniczonymi uprawnieniami; nie wolno
go commitować.

## Bootstrap i konfiguracja Open WebUI

Konfiguracje Tools i Custom Models są zapisane w repozytorium jako czytelne pliki:

```text
config/tools/
config/custom_models/
```

Po uruchomieniu kontenera bootstrap synchronizuje je z Open WebUI przez oficjalne API. Dzięki temu nie trzeba ręcznie importować narzędzi po każdej instalacji, a konfiguracja pozostaje możliwa do przejrzenia i wersjonowania.

Bootstrap zarządza tylko zasobami należącymi do Garmin Trainer. Nie powinien usuwać połączeń z dostawcami modeli, historii rozmów ani innych ustawień użytkownika.

## Szybki test po instalacji

Po świeżej instalacji warto sprawdzić:

1. czy Open WebUI uruchamia się poprawnie;
2. czy połączenie z dostawcą LLM działa i przetrwa restart kontenera;
3. czy `/start` tworzy profil W00;
4. czy `/sync` pobiera najnowsze dane;
5. czy agent potrafi odczytać i zaktualizować Training Diary;
6. czy wygenerowany plik FIT pojawia się jako załącznik w rozmowie;
7. czy `/sync full` można zatrzymać przez `/sync stop`.

Pełnej synchronizacji GarminDB nie uruchamiaj wyłącznie po to, żeby sprawdzić, czy przycisk działa — może potrwać kilka godzin.

Synchronizacja jest uznana za udaną dopiero wtedy, gdy GarminDB zakończy się
kodem `0` oraz utworzone są obie oczekiwane bazy w
`data/garmindb/HealthData/DBs/`. Sam kod wyjścia procesu nie wystarcza.

## Możliwe, przykładowe kierunki rozwoju aplikacji
- obsługa wielu użytkowników i niezależnych profili GarminDB w jednej instancji aplikacji
- zweryfikowanie działania z różnymi dyscyplinami sportowymi
- obsługa/edycja plików np .md przez UI
