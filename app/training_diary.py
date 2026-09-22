import re
from datetime import date, timedelta
from pathlib import Path


TRAINING_DIARY_DIR = Path("/data/training_diary").resolve()
DIARY_SCHEMA = "training_diary_v1"

VALID_DIARY_SECTIONS = {
    "Podsumowanie",
    "Profil zawodnika",
    "Poprzedni tydzień",
    "Plan tygodnia",
    "Ocena jednostek",
    "Stan tygodnia",
    "Trend",
    "Context",
    "Ustalenia",
    "Notatki trenera",
}
VALID_DIARY_STATUS = {"PLANNED", "IN_PROGRESS", "CLOSED"}
VALID_SESSION_STATUS = {"PLANNED", "COMPLETED", "MODIFIED", "MISSED", "CANCELLED"}
VALID_STIMULI = {
    "NONE",
    "REST",
    "RECOVERY",
    "BASE",
    "LONG",
    "THRESHOLD",
    "VO2MAX",
    "ANAEROBIC",
    "STRENGTH",
    "OTHER",
    "UNKNOWN",
}
VALID_GOAL_ACHIEVED = {"YES", "PARTIAL", "NO", "UNKNOWN"}
VALID_TRAINING_VALUE = {"POSITIVE", "NEUTRAL", "NEGATIVE", "UNKNOWN"}

def _iso_week_id(day: date) -> str:
    iso = day.isocalendar()
    return f"{iso.year}-W{iso.week:02d}"


def _week_period(week_id: str) -> tuple[date, date]:
    match = re.fullmatch(r"(\d{4})-W(\d{2})", week_id)
    if not match:
        raise ValueError("week must use format YYYY-WXX")

    year = int(match.group(1))
    week = int(match.group(2))

    if week == 0:
        raise ValueError("W00 is the initial profile and has no calendar period")

    try:
        monday = date.fromisocalendar(year, week, 1)
    except ValueError as exc:
        raise ValueError("invalid ISO week") from exc

    return monday, monday + timedelta(days=6)


def _diary_path(week_id: str) -> Path:
    if not re.fullmatch(r"\d{4}-W\d{2}", week_id):
        raise ValueError("week must use format YYYY-WXX")

    return TRAINING_DIARY_DIR / f"{week_id}_training_diary.md"


def _read_text(path: Path) -> str | None:
    if not path.is_file():
        return None
    return path.read_text(encoding="utf-8")


def _find_initial_profile_path() -> Path | None:
    if not TRAINING_DIARY_DIR.is_dir():
        return None

    files = sorted(TRAINING_DIARY_DIR.glob("????-W00_training_diary.md"))
    return files[-1] if files else None


def _frontmatter_value(content: str | None, key: str) -> str | None:
    if not content:
        return None

    match = re.search(
        rf"(?m)^{re.escape(key)}:\s*(.+?)\s*$",
        content,
    )
    return match.group(1).strip() if match else None


def _replace_frontmatter_value(content: str, key: str, value: str) -> str:
    pattern = rf"(?m)^({re.escape(key)}:\s*).*$"
    if re.search(pattern, content):
        return re.sub(pattern, rf"\g<1>{value}", content, count=1)
    return content


def _replace_markdown_section(content: str, section: str, new_body: str) -> str:
    heading = f"## {section}"
    pattern = re.compile(
        rf"(?ms)^{re.escape(heading)}\s*\n.*?(?=^##\s|\Z)"
    )

    replacement = heading + "\n\n" + new_body.strip() + "\n\n"

    if pattern.search(content):
        return pattern.sub(replacement, content, count=1)

    return content.rstrip() + "\n\n" + replacement


def _preview_markdown_section(
    content: str,
    section: str | None = None,
    max_chars: int = 1200,
) -> str:
    """Returns a short Markdown preview without Open WebUI dependencies."""
    preview = content.strip()
    if section:
        heading = f"## {section}"
        pattern = re.compile(
            rf"(?ms)^{re.escape(heading)}\s*\n.*?(?=^##\s|\Z)"
        )
        match = pattern.search(content)
        preview = match.group(0).strip() if match else ""

    if len(preview) <= max_chars:
        return preview
    return preview[:max_chars].rstrip() + "…"


def _parse_diary_field(block: str, label: str) -> str | None:
    match = re.search(
        rf"(?mi)^\s*(?:[-*]\s*)?{re.escape(label)}:\s*(.*?)\s*$",
        block,
    )
    return match.group(1).strip() if match else None


def _is_nullish(value: str | None) -> bool:
    if value is None:
        return True
    return value.strip().lower() in {"", "null", "none", "n/a"}


def _validate_session_assessment_section(content: str) -> tuple[bool, str | None]:
    """
    Waliduje bloki w sekcji 'Ocena jednostek'.

    Dla COMPLETED / MODIFIED wymusza świadomą ocenę wykonanego treningu:
    - rzeczywisty bodziec,
    - wartość treningową,
    - ocenę celu.

    Planowany bodziec może być null, jeśli jednostka nie była wcześniej planowana.
    """
    blocks = re.split(r"(?m)^###\s+", content)
    blocks = [block.strip() for block in blocks[1:] if block.strip()]

    for block in blocks:
        heading, _, body = block.partition("\n")
        status = (
            _parse_diary_field(body, "Status")
            or _parse_diary_field(body, "Status wykonania")
        )

        if not status:
            return False, f"Brak pola 'Status' w jednostce: {heading}"

        status = status.upper()
        if status not in VALID_SESSION_STATUS:
            return (
                False,
                f"Nieobsługiwany Status '{status}' w jednostce: {heading}. "
                f"Dozwolone: {', '.join(sorted(VALID_SESSION_STATUS))}",
            )

        planned = _parse_diary_field(body, "Planowany bodziec")
        if not _is_nullish(planned):
            planned_upper = planned.upper()
            if planned_upper not in VALID_STIMULI:
                return (
                    False,
                    f"Nieobsługiwany planowany bodziec '{planned}' "
                    f"w jednostce: {heading}.",
                )

        actual = _parse_diary_field(body, "Rzeczywisty bodziec")
        if not _is_nullish(actual):
            actual_upper = actual.upper()
            if actual_upper not in VALID_STIMULI:
                return (
                    False,
                    f"Nieobsługiwany rzeczywisty bodziec '{actual}' "
                    f"w jednostce: {heading}.",
                )

        goal = _parse_diary_field(body, "Cel osiągnięty")
        if not _is_nullish(goal):
            goal_upper = goal.upper()
            if goal_upper not in VALID_GOAL_ACHIEVED:
                return (
                    False,
                    f"Nieobsługiwane 'Cel osiągnięty: {goal}' "
                    f"w jednostce: {heading}.",
                )

        training_value = _parse_diary_field(body, "Wartość treningowa")
        if not _is_nullish(training_value):
            value_upper = training_value.upper()
            if value_upper not in VALID_TRAINING_VALUE:
                return (
                    False,
                    f"Nieobsługiwana wartość treningowa '{training_value}' "
                    f"w jednostce: {heading}.",
                )

        if status in {"COMPLETED", "MODIFIED"}:
            if _is_nullish(actual):
                return (
                    False,
                    f"Jednostka {heading} ma status {status}, więc pole "
                    "'Rzeczywisty bodziec' jest wymagane. Użyj UNKNOWN, "
                    "jeśli dane nie pozwalają na wiarygodną klasyfikację.",
                )

            if _is_nullish(training_value):
                return (
                    False,
                    f"Jednostka {heading} ma status {status}, więc pole "
                    "'Wartość treningowa' jest wymagane. Użyj UNKNOWN, "
                    "jeśli nie da się jej wiarygodnie ocenić.",
                )

            if _is_nullish(goal):
                return (
                    False,
                    f"Jednostka {heading} ma status {status}, więc pole "
                    "'Cel osiągnięty' jest wymagane. Jeśli nie było planu, "
                    "użyj UNKNOWN.",
                )

    return True, None


def start_training() -> dict:
    """Sprawdza stan profilu W00 i rozpoczyna onboarding konwersacyjny.

    Funkcja nie tworzy, nie nadpisuje i nie pokazuje formularza. Przy braku
    profilu model powinien pobrać wiarygodne dane z GarminDB, a następnie
    własnymi słowami zapytać użytkownika o informacje potrzebne do onboardingu.
    Przy istniejącym profilu nie uruchamiaj onboardingu ponownie.
    """
    profile_path = _find_initial_profile_path()

    if profile_path:
        return {
            "success": True,
            "status": "profile_exists",
            "message": (
                "Już trochę się znamy. Jeśli chcesz, napisz mi coś nowego o "
                "sobie — zmianę celu, ograniczeń, preferencji albo inne "
                "ważne informacje. Uwzględnię je przy kolejnych decyzjach i "
                "zapisach w bieżących Training Diary."
            ),
        }

    return {
        "success": True,
        "status": "onboarding_required",
        "message": (
            "Rozpocznij onboarding rozmową. Najpierw użyj get_user_profile, "
            "aby pokazać wyłącznie wiarygodne dane znane z GarminDB. Następnie "
            "własnymi słowami zapytaj użytkownika o główny cel, termin celu, "
            "preferowaną lub maksymalną liczbę głównych jednostek tygodniowo, "
            "preferencje dni treningowych oraz inne ważne informacje. Nie "
            "pokazuj formularza ani code blocka. Nie pytaj o dane dostępne "
            "później z GarminDB. Braki pozostaw jako null. Jeśli czegoś nie "
            "wiesz albo nie masz zdania, zostaw to puste — ustalimy później. "
            "Gdy zbierzesz wystarczające informacje, utwórz profil przez "
            "create_training_diary() z week w formacie YYYY-W00, np. "
            "2026-W00."
        ),
    }


def get_training_context() -> dict:
    """
    Zwraca kontekst dziennika treningowego potrzebny trenerowi AI.

    Zwraca jednocześnie:
    - profil startowy W00,
    - dziennik bieżącego tygodnia,
    - dziennik poprzedniego tygodnia,
    - informację czy poprzedni tydzień wymaga zamknięcia,
    - informację czy bieżący tydzień już istnieje.

    Narzędzie nie interpretuje treningu. Dostarcza tylko stan dokumentów.
    """
    today = date.today()
    current_week = _iso_week_id(today)

    current_monday = today - timedelta(days=today.weekday())
    previous_week = _iso_week_id(current_monday - timedelta(days=7))
    next_week = _iso_week_id(current_monday + timedelta(days=7))

    profile_path = _find_initial_profile_path()
    current_path = _diary_path(current_week)
    previous_path = _diary_path(previous_week)
    next_path = _diary_path(next_week)

    profile_content = _read_text(profile_path) if profile_path else None
    current_content = _read_text(current_path)
    previous_content = _read_text(previous_path)
    next_content = _read_text(next_path)

    previous_status = _frontmatter_value(previous_content, "status")

    current_start, current_end = _week_period(current_week)
    previous_start, previous_end = _week_period(previous_week)
    next_start, next_end = _week_period(next_week)

    return {
        "current_date": today.isoformat(),
        "training_diary_directory": str(TRAINING_DIARY_DIR),
        "initial_profile": {
            "exists": profile_content is not None,
            "filename": profile_path.name if profile_path else None,
            "content": profile_content,
        },
        "current_week": {
            "week": current_week,
            "period_start": current_start.isoformat(),
            "period_end": current_end.isoformat(),
            "exists": current_content is not None,
            "filename": current_path.name,
            "content": current_content,
        },
        "previous_week": {
            "week": previous_week,
            "period_start": previous_start.isoformat(),
            "period_end": previous_end.isoformat(),
            "exists": previous_content is not None,
            "filename": previous_path.name,
            "status": previous_status,
            "needs_closure": (
                previous_content is not None
                and previous_status != "CLOSED"
            ),
            "content": previous_content,
        },
        "next_week": {
            "week": next_week,
            "period_start": next_start.isoformat(),
            "period_end": next_end.isoformat(),
            "exists": next_content is not None,
            "filename": next_path.name,
            "status": _frontmatter_value(next_content, "status"),
            "content": next_content,
        },
    }


def get_training_diary(week: str | None = None) -> dict:
    """Returns the requested or current Markdown diary for attachment."""
    week = (week or _iso_week_id(date.today())).strip().upper()

    try:
        path = _diary_path(week)
    except ValueError as exc:
        return {"success": False, "error": str(exc)}

    content = _read_text(path)
    if content is None:
        return {
            "success": False,
            "error": "training diary does not exist",
            "filename": path.name,
        }

    return {
        "success": True,
        "week": week,
        "filename": path.name,
        "path": str(path),
        "preview": _preview_markdown_section(content),
    }


def create_training_diary(week: str, content: str) -> dict:
    """
    Tworzy nowy plik dziennika treningowego Markdown.

    week:
    - YYYY-W00 dla profilu startowego,
    - YYYY-W01..W53 dla tygodnia kalendarzowego ISO.

    Nie nadpisuje istniejącego pliku.
    Treść powinna używać schema training_diary_v1.

    Dla profilu W00:
    - argument week musi mieć format YYYY-W00, np. 2026-W00;
    - nie używaj samego W00;
    - treść powinna zaczynać się od frontmatter:

      ---
      week: 2026-W00
      schema: training_diary_v1
      type: INITIAL_PROFILE
      ---

    Wartość week w treści musi być identyczna z argumentem week. Nie zgaduj
    brakujących danych — pozostaw je jako null. Obecny walidator wymaga pól
    week i schema; type: INITIAL_PROFILE opisuje właściwy profil W00.
    """
    week = week.strip().upper()

    if not re.fullmatch(r"\d{4}-W\d{2}", week):
        return {"success": False, "error": "week must use format YYYY-WXX"}

    week_number = int(week[-2:])
    if week_number != 0:
        try:
            _week_period(week)
        except ValueError as exc:
            return {"success": False, "error": str(exc)}

    if not content or not content.strip():
        return {"success": False, "error": "content cannot be empty"}

    if f"week: {week}" not in content:
        return {
            "success": False,
            "error": f"content must contain 'week: {week}'",
        }

    if f"schema: {DIARY_SCHEMA}" not in content:
        return {
            "success": False,
            "error": f"content must contain 'schema: {DIARY_SCHEMA}'",
        }
    
    diary_status = _frontmatter_value(content, "status")

    if week_number != 0 and diary_status not in VALID_DIARY_STATUS:
        return {
            "success": False,
            "error": "weekly diary must contain valid status",
            "allowed_statuses": sorted(VALID_DIARY_STATUS),
        }

    assessment_match = re.search(
        r"(?ms)^## Ocena jednostek\s*\n(.*?)(?=^##\s|\Z)",
        content,
    )

    if assessment_match:
        assessment_content = assessment_match.group(1).strip()

        if assessment_content:
            valid, error = _validate_session_assessment_section(
                assessment_content
            )

            if not valid:
                return {
                    "success": False,
                    "error": error,
                    "allowed_stimuli": sorted(VALID_STIMULI),
                    "allowed_goal_achieved": sorted(VALID_GOAL_ACHIEVED),
                    "allowed_training_value": sorted(VALID_TRAINING_VALUE),
                }

    path = _diary_path(week)
    TRAINING_DIARY_DIR.mkdir(parents=True, exist_ok=True)

    if path.exists():
        return {
            "success": False,
            "error": "training diary already exists",
            "filename": path.name,
        }

    path.write_text(content.rstrip() + "\n", encoding="utf-8")

    return {
        "success": True,
        "week": week,
        "filename": path.name,
        "path": str(path),
        "preview": _preview_markdown_section(content),
    }


def update_training_diary(
    week: str,
    section: str,
    content: str,
    diary_status: str = "",
) -> dict:
    """
    Aktualizuje jedną sekcję istniejącego dziennika treningowego.

    section musi być jedną z sekcji training_diary_v1, np.:
    Podsumowanie, Profil zawodnika, Poprzedni tydzień, Plan tygodnia,
    Ocena jednostek, Stan tygodnia, Trend, Notatki trenera.

    Opcjonalny diary_status może być IN_PROGRESS albo CLOSED.
    Narzędzie aktualizuje też Stan na na bieżącą datę.
    """
    week = week.strip().upper()
    section = section.strip()
    diary_status = diary_status.strip().upper()

    if section not in VALID_DIARY_SECTIONS:
        return {
            "success": False,
            "error": "unsupported section",
            "allowed_sections": sorted(VALID_DIARY_SECTIONS),
        }

    if diary_status and diary_status not in VALID_DIARY_STATUS:
        return {
            "success": False,
            "error": "unsupported diary_status",
            "allowed_statuses": sorted(VALID_DIARY_STATUS),
        }

    try:
        path = _diary_path(week)
    except ValueError as exc:
        return {"success": False, "error": str(exc)}

    if not path.is_file():
        return {
            "success": False,
            "error": "training diary does not exist",
            "filename": path.name,
        }

    if section == "Ocena jednostek":
        valid, error = _validate_session_assessment_section(content)
        if not valid:
            return {
                "success": False,
                "error": error,
                "allowed_stimuli": sorted(VALID_STIMULI),
                "allowed_goal_achieved": sorted(VALID_GOAL_ACHIEVED),
                "allowed_training_value": sorted(VALID_TRAINING_VALUE),
            }

    document = path.read_text(encoding="utf-8")
    document = _replace_markdown_section(document, section, content)

    today = date.today().isoformat()
    document = re.sub(
        r"(?m)^(Stan na:\s*).*$",
        rf"\g<1>{today}",
        document,
        count=1,
    )

    if diary_status:
        document = _replace_frontmatter_value(
            document,
            "status",
            diary_status,
        )

    path.write_text(document.rstrip() + "\n", encoding="utf-8")

    return {
        "success": True,
        "week": week,
        "filename": path.name,
        "path": str(path),
        "updated_section": section,
        "status": _frontmatter_value(document, "status"),
        "preview": _preview_markdown_section(document, section),
    }
