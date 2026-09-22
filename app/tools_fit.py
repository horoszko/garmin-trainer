from pathlib import Path

from workout_json_to_fit_encoder import generate_running_workout_fit


GENERATED_DIR = Path("/data/generated").resolve()

def create_running_workout(
    name: str,
    warmup_seconds: int,
    interval_seconds: int,
    recovery_seconds: int,
    repetitions: int,
    cooldown_seconds: int,
    pace_min: str = "",
    pace_max: str = "",
) -> dict:
    """
    Tworzy plik FIT z treningiem biegowym.

    Obsługiwany schemat:
    - rozgrzewka
    - interwał
    - regeneracja
    - powtórzenia
    - schłodzenie

    pace_min i pace_max podawaj jako MM:SS min/km.

    Przykład:
    name="Prog 5x3min"
    warmup_seconds=600
    interval_seconds=180
    recovery_seconds=120
    repetitions=5
    cooldown_seconds=600
    pace_min="4:10"
    pace_max="4:20"
    """

    try:
        return generate_running_workout_fit(
            name=name,
            warmup_seconds=warmup_seconds,
            interval_seconds=interval_seconds,
            recovery_seconds=recovery_seconds,
            repetitions=repetitions,
            cooldown_seconds=cooldown_seconds,
            pace_min=pace_min or None,
            pace_max=pace_max or None,
        )

    except Exception as exc:
        return {
            "success": False,
            "error": str(exc),
        }

