from datetime import datetime, timezone
from pathlib import Path
import re

from garmin_fit_sdk import Encoder, Profile


OUTPUT_DIR = Path("/data/generated")


def _pace_to_speed_mps(pace: str) -> float:
    """
    '4:15' min/km -> m/s
    """
    match = re.fullmatch(r"(\d+):(\d{2})", pace.strip())

    if not match:
        raise ValueError(
            f"Niepoprawne tempo: {pace}. Użyj formatu MM:SS, np. 4:15"
        )

    minutes = int(match.group(1))
    seconds = int(match.group(2))

    total_seconds = minutes * 60 + seconds

    if total_seconds <= 0:
        raise ValueError("Tempo musi być większe od zera.")

    return 1000 / total_seconds


def generate_running_workout_fit(
    name: str,
    warmup_seconds: int,
    interval_seconds: int,
    recovery_seconds: int,
    repetitions: int,
    cooldown_seconds: int,
    pace_min: str | None = None,
    pace_max: str | None = None,
) -> dict:

    if repetitions < 1 or repetitions > 50:
        raise ValueError("repetitions musi być w zakresie 1-50.")

    for value in (
        warmup_seconds,
        interval_seconds,
        recovery_seconds,
        cooldown_seconds,
    ):
        if value < 0:
            raise ValueError("Czas kroku nie może być ujemny.")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    safe_name = re.sub(r"[^a-zA-Z0-9_-]+", "_", name).strip("_")
    filename = f"{safe_name}.fit"
    output_path = OUTPUT_DIR / filename

    encoder = Encoder()

    # FILE_ID
    encoder.write_mesg(
        {
            "mesg_num": Profile["mesg_num"]["FILE_ID"],
            "type": "workout",
            "manufacturer": "development",
            "product": 1,
            "time_created": datetime.now(timezone.utc),
        }
    )

    # Liczba logicznych kroków:
    # warmup + interval + recovery + repeat + cooldown
    num_steps = 5

    encoder.write_mesg(
        {
            "mesg_num": Profile["mesg_num"]["WORKOUT"],
            "sport": "running",
            "wkt_name": name,
            "num_valid_steps": num_steps,
        }
    )

    step_index = 0

    # WARMUP
    encoder.write_mesg(
        {
            "mesg_num": Profile["mesg_num"]["WORKOUT_STEP"],
            "message_index": step_index,
            "duration_type": "time",
            "duration_value": warmup_seconds * 1000,
            "target_type": "open",
            "target_value": 0,
            "intensity": "warmup",
        }
    )

    step_index += 1

    # INTERVAL
    interval_step = {
        "mesg_num": Profile["mesg_num"]["WORKOUT_STEP"],
        "message_index": step_index,
        "duration_type": "time",
        "duration_value": interval_seconds * 1000,
        "target_type": "open",
        "target_value": 0,
        "intensity": "active",
    }

    if pace_min and pace_max:
        speed_fast = _pace_to_speed_mps(pace_min)
        speed_slow = _pace_to_speed_mps(pace_max)

        interval_step["target_type"] = "speed"
        interval_step["target_value"] = 0

        # FIT speed: m/s * 1000
        interval_step["custom_target_value_low"] = int(speed_slow * 1000)
        interval_step["custom_target_value_high"] = int(speed_fast * 1000)

    encoder.write_mesg(interval_step)

    interval_index = step_index
    step_index += 1

    # RECOVERY
    encoder.write_mesg(
        {
            "mesg_num": Profile["mesg_num"]["WORKOUT_STEP"],
            "message_index": step_index,
            "duration_type": "time",
            "duration_value": recovery_seconds * 1000,
            "target_type": "open",
            "target_value": 0,
            "intensity": "rest",
        }
    )

    step_index += 1

    # REPEAT
    encoder.write_mesg(
        {
            "mesg_num": Profile["mesg_num"]["WORKOUT_STEP"],
            "message_index": step_index,
            "duration_type": "repeat_until_steps_cmplt",
            "duration_value": interval_index,
            "target_type": "open",
            "target_value": repetitions,
        }
    )

    step_index += 1

    # COOLDOWN
    encoder.write_mesg(
        {
            "mesg_num": Profile["mesg_num"]["WORKOUT_STEP"],
            "message_index": step_index,
            "duration_type": "time",
            "duration_value": cooldown_seconds * 1000,
            "target_type": "open",
            "target_value": 0,
            "intensity": "cooldown",
        }
    )

    fit_bytes = encoder.close()

    with open(output_path, "wb") as f:
        f.write(fit_bytes)

    return {
        "success": True,
        "filename": filename,
        "path": str(output_path),
        "workout": {
            "name": name,
            "warmup_seconds": warmup_seconds,
            "interval_seconds": interval_seconds,
            "recovery_seconds": recovery_seconds,
            "repetitions": repetitions,
            "cooldown_seconds": cooldown_seconds,
            "pace_min": pace_min,
            "pace_max": pace_max,
        },
    }
