import sqlite3

from mcp.server.mcpserver import MCPServer
from config import GARMIN_ACTIVITIES_DB, GARMIN_DB
from sport_categories import SPORT_CATEGORIES, SPORT_SUBSPORT_CATEGORIES
from datetime import date, datetime, timedelta

mcp = MCPServer("Garmin AI")

@mcp.tool()
def get_activities(
    start_date: str,
    end_date: str,
    sport: str = ""
) -> list[dict]:
    """
    Pobiera aktywności z GarminDB w podanym zakresie dat.

    sport może być kategorią, np.:
    running, cycling, walking, hiking, swimming,
    fitness_cardio, strength
    """
   
    conn = sqlite3.connect(f"file:{GARMIN_ACTIVITIES_DB}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row

    query = """
        SELECT
            activity_id,
            name,
            sport,
            sub_sport,
            start_time,
            stop_time,
            distance,
            moving_time,
            avg_hr,
            max_hr,
            calories,
            training_load,
            training_effect
        FROM activities
        WHERE date(start_time) BETWEEN ? AND ?
    """

    params = [start_date, end_date]
#
    if sport:
        special_category = SPORT_SUBSPORT_CATEGORIES.get(sport)

        if special_category:
            query += " AND sport = ? AND sub_sport = ?"
            params.extend([
                special_category["sport"],
                special_category["sub_sport"]
            ])

        else:
            sports = SPORT_CATEGORIES.get(sport, [sport])
            placeholders = ",".join("?" * len(sports))

            query += f" AND sport IN ({placeholders})"
            params.extend(sports)

    query += " ORDER BY start_time DESC"

    rows = conn.execute(query, params).fetchall()
    conn.close()

    results = []

    for row in rows:
        activity = dict(row)

        if (
            activity["sport"] == "fitness_equipment"
            and activity["sub_sport"] == "cardio_training"
        ):
            activity["sport"] = "fitness_cardio"

        elif (
            activity["sport"] == "fitness_equipment"
            and activity["sub_sport"] == "strength_training"
        ):
            activity["sport"] = "strength"

        results.append(activity)

    return results

@mcp.tool()
def get_sport_types() -> list:
    """
    Zwraca wszystkie typy aktywności występujące w bazie GarminDB
    wraz z liczbą ich wystąpień.
    """

    conn = sqlite3.connect(f"file:{GARMIN_ACTIVITIES_DB}?mode=ro", uri=True)

    rows = conn.execute("""
        SELECT
            CASE
                WHEN sport = 'fitness_equipment'
                     AND sub_sport = 'cardio_training'
                    THEN 'fitness_cardio'

                WHEN sport = 'fitness_equipment'
                     AND sub_sport = 'strength_training'
                    THEN 'strength'

                ELSE sport
            END AS sport,

            sub_sport,
            COUNT(*) AS count

        FROM activities

        GROUP BY 1, 2
        ORDER BY 1, 2
    """).fetchall()

    conn.close()

    return [
        {
            "sport": row[0],
            "sub_sport": row[1],
            "count": row[2]
        }
        for row in rows
    ]

@mcp.tool()
def get_sport_summary(
    start_date: str,
    end_date: str,
    sport: str
) -> dict:
    """
    Zwraca podsumowanie wybranego sportu w podanym zakresie dat.

    sport: np. running, cycling, walking, hiking, swimming
    """

    conn = sqlite3.connect(f"file:{GARMIN_ACTIVITIES_DB}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row

    special_category = SPORT_SUBSPORT_CATEGORIES.get(sport)

    query = """
        SELECT
            distance,
            moving_time,
            avg_hr,
            calories,
            training_load
        FROM activities
        WHERE date(start_time) BETWEEN ? AND ?
    """

    params = [start_date, end_date]

    if special_category:
        query += " AND sport = ? AND sub_sport = ?"
        params.extend([
            special_category["sport"],
            special_category["sub_sport"]
        ])

    else:
        sports = SPORT_CATEGORIES.get(sport, [sport])
        placeholders = ",".join("?" * len(sports))

        query += f" AND sport IN ({placeholders})"
        params.extend(sports)

    rows = conn.execute(query, params).fetchall()
    conn.close()

    total_distance = sum(row["distance"] or 0 for row in rows)
    total_calories = sum(row["calories"] or 0 for row in rows)
    total_training_load = sum(row["training_load"] or 0 for row in rows)

    total_seconds = 0
    weighted_hr_sum = 0
    hr_time_sum = 0

    for row in rows:
        if row["moving_time"]:
            h, m, s = row["moving_time"].split(":")
            seconds = int(h) * 3600 + int(m) * 60 + float(s)
            total_seconds += seconds

            if row["avg_hr"]:
                weighted_hr_sum += row["avg_hr"] * seconds
                hr_time_sum += seconds

    average_hr = (
        round(weighted_hr_sum / hr_time_sum)
        if hr_time_sum > 0
        else None
    )

    average_pace = None
    average_pace_100m = None
    average_speed = None

    if total_distance > 0 and total_seconds > 0:
        if sport in ("running", "walking", "hiking"):
            pace_seconds = total_seconds / total_distance
            pace_minutes = int(pace_seconds // 60)
            pace_remainder = int(round(pace_seconds % 60))

            if pace_remainder == 60:
                pace_minutes += 1
                pace_remainder = 0

            average_pace = f"{pace_minutes}:{pace_remainder:02d}"

        elif sport == "swimming":
            pace_seconds = total_seconds / (total_distance * 10)
            pace_minutes = int(pace_seconds // 60)
            pace_remainder = int(round(pace_seconds % 60))

            if pace_remainder == 60:
                pace_minutes += 1
                pace_remainder = 0

            average_pace_100m = f"{pace_minutes}:{pace_remainder:02d}"

        elif sport == "cycling":
            average_speed = round(
                total_distance / (total_seconds / 3600),
                1
            )

    return {
        "sport": sport,
        "activities": len(rows),
        "distance_km": round(total_distance, 3),
        "moving_time_seconds": round(total_seconds),
        "average_pace_min_km": average_pace,
        "average_pace_min_100m": average_pace_100m,
        "average_speed_kmh": average_speed,
        "average_heart_rate_bpm": average_hr,
        "calories_kcal": round(total_calories),
        "training_load": round(total_training_load, 1)
    }

@mcp.tool()
def get_latest_activity(sport: str = "") -> dict:
    """
    Zwraca ostatnią aktywność użytkownika.

    sport jest opcjonalny.
    Przykłady:
    running, cycling, swimming, walking, hiking, climbing

    Jeśli sport nie zostanie podany, zwraca ostatnią aktywność dowolnego typu.
    """

    conn = sqlite3.connect(f"file:{GARMIN_ACTIVITIES_DB}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row

    query = """
        SELECT
            activity_id,
            name,
            sport,
            sub_sport,
            start_time,
            stop_time,
            distance,
            moving_time,
            avg_hr,
            max_hr,
            calories,
            training_load,
            training_effect
        FROM activities
    """

    params = []

    if sport:
        special_category = SPORT_SUBSPORT_CATEGORIES.get(sport)

        if special_category:
            query += " WHERE sport = ? AND sub_sport = ?"
            params.extend([
                special_category["sport"],
                special_category["sub_sport"]
            ])

        else:
            sports = SPORT_CATEGORIES.get(sport, [sport])
            placeholders = ",".join("?" * len(sports))

            query += f" WHERE sport IN ({placeholders})"
            params.extend(sports)

    query += """
        ORDER BY start_time DESC
        LIMIT 1
    """

    row = conn.execute(query, params).fetchone()
    conn.close()

    if row is None:
        return {}

    result = dict(row)

    if (
        result["sport"] == "fitness_equipment"
        and result["sub_sport"] == "cardio_training"
    ):
        result["sport"] = "fitness_cardio"

    elif (
        result["sport"] == "fitness_equipment"
        and result["sub_sport"] == "strength_training"
    ):
        result["sport"] = "strength"

    distance_km = result.pop("distance") or 0
    moving_time = result.get("moving_time")

    # Urządzenia użyte podczas aktywności

    conn = sqlite3.connect(
        f"file:{GARMIN_ACTIVITIES_DB}?mode=ro",
        uri=True
    )
    conn.row_factory = sqlite3.Row

    device_rows = conn.execute("""
        SELECT device_serial_number
        FROM activities_devices
        WHERE activity_id = ?
    """, [result["activity_id"]]).fetchall()

    conn.close()

    serial_numbers = [
        row["device_serial_number"]
        for row in device_rows
    ]

    heart_rate_source = "unknown"
    heart_rate_device = None

    if serial_numbers:
        placeholders = ",".join("?" * len(serial_numbers))

        conn = sqlite3.connect(
            f"file:{GARMIN_DB}?mode=ro",
            uri=True
        )
        conn.row_factory = sqlite3.Row

        devices = conn.execute(f"""
            SELECT
                serial_number,
                device_type,
                manufacturer,
                product,
                hardware_version
            FROM devices
            WHERE serial_number IN ({placeholders})
        """, serial_numbers).fetchall()

        conn.close()

        wrist_device = None

        for device in devices:
            device_type = (device["device_type"] or "").lower()
            product = (device["product"] or "").lower()

            if (
                device_type == "heart_rate"
                or "hrm" in product
            ):
                heart_rate_source = "external_chest_sensor"
                heart_rate_device = dict(device)
                break

            if device_type == "wrist_heart_rate":
                wrist_device = dict(device)

        if heart_rate_source == "unknown" and wrist_device:
            heart_rate_source = "wrist_sensor"
            heart_rate_device = wrist_device


    total_seconds = 0

    if moving_time:
        h, m, s = moving_time.split(":")
        total_seconds = (
            int(h) * 3600
            + int(m) * 60
            + float(s)
        )

    average_speed_kmh = None
    average_pace_min_km = None
    average_pace_min_100m = None

    if distance_km > 0 and total_seconds > 0:
        average_speed_kmh = round(
            distance_km / (total_seconds / 3600),
            2
        )

        if result["sport"] in ("running", "walking", "hiking"):
            pace_seconds = total_seconds / distance_km
            pace_minutes = int(pace_seconds // 60)
            pace_remainder = int(round(pace_seconds % 60))

            if pace_remainder == 60:
                pace_minutes += 1
                pace_remainder = 0

            average_pace_min_km = (
            f"{pace_minutes}:{pace_remainder:02d}"
            )

        elif result["sport"] == "swimming":
            pace_seconds = total_seconds / (distance_km * 10)
            pace_minutes = int(pace_seconds // 60)
            pace_remainder = int(round(pace_seconds % 60))

            if pace_remainder == 60:
                pace_minutes += 1
            pace_remainder = 0

            average_pace_min_100m = (
                f"{pace_minutes}:{pace_remainder:02d}"
            )

        return {
            "activity_id": result["activity_id"],
            "name": result["name"],
            "sport": result["sport"],
            "sub_sport": result["sub_sport"],
            "start_time": result["start_time"],
            "stop_time": result["stop_time"],

            "distance_km": round(distance_km, 3),

            "moving_time": moving_time,
            "moving_time_seconds": round(total_seconds),

            "average_pace_min_km": average_pace_min_km,
            "average_pace_min_100m": average_pace_min_100m,
            "average_speed_kmh": average_speed_kmh,

            "average_heart_rate_bpm": result["avg_hr"],
            "max_heart_rate_bpm": result["max_hr"],

            "heart_rate_source": heart_rate_source,
            "heart_rate_device": heart_rate_device,

            "calories_kcal": result["calories"],
            "training_load": result["training_load"],
            "training_effect": result["training_effect"],
        }

@mcp.tool()
def get_activity_details(activity_id: str) -> dict:
    """
    Zwraca szczegółowe dane jednej aktywności na podstawie activity_id.

    Uwzględnia:
    - pełny rekord aktywności,
    - lapy,
    - dostępne pola szczegółowych rekordów aktywności.

    Narzędzie przeznaczone jest do dokładniejszej analizy pojedynczego
    treningu, np. techniki biegu, tempa, kadencji lub pływania.

    Ważne:
    - pola GarminDB avg_rr, max_rr i rr oznaczają częstość oddechu,
      dlatego są zwracane pod jednoznacznymi nazwami,
    - dla biegania GarminDB cadence oznacza cykle/strides na minutę;
      dodatkowo zwracana jest kadencja w krokach/min (cadence * 2).

    Zwraca wyłącznie dane rzeczywiście obecne w GarminDB.
    """

    conn = sqlite3.connect(
        f"file:{GARMIN_ACTIVITIES_DB}?mode=ro",
        uri=True
    )
    conn.row_factory = sqlite3.Row

    # Podstawowe dane aktywności
    activity = conn.execute("""
        SELECT *
        FROM activities
        WHERE activity_id = ?
        LIMIT 1
    """, [activity_id]).fetchone()

    if activity is None:
        conn.close()
        return {}

    # Lapy
    laps = conn.execute("""
        SELECT *
        FROM activity_laps
        WHERE activity_id = ?
        ORDER BY lap
    """, [activity_id]).fetchall()

    # Szczegółowe rekordy mogą być bardzo liczne.
    # Nie wysyłamy całej aktywności do LLM.
    records = conn.execute("""
        SELECT *
        FROM activity_records
        WHERE activity_id = ?
        ORDER BY record
        LIMIT 200
    """, [activity_id]).fetchall()

    conn.close()

    activity_data = dict(activity)
    sport = activity_data.get("sport")

    # Respiration rate
    if "avg_rr" in activity_data:
        activity_data["average_respiration_rate_bpm"] = (
            activity_data.pop("avg_rr")
        )

    if "max_rr" in activity_data:
        activity_data["max_respiration_rate_bpm"] = (
            activity_data.pop("max_rr")
        )

    # Kadencja biegowa:
    # GarminDB/FIT cadence dla biegu jest w strides/cycles per minute.
    # Jeden pełny cykl biegu odpowiada dwóm krokom.
    if sport == "running":
        if activity_data.get("avg_cadence") is not None:
            activity_data["average_running_cadence_steps_per_min"] = (
                activity_data["avg_cadence"] * 2
            )

        if activity_data.get("max_cadence") is not None:
            activity_data["max_running_cadence_steps_per_min"] = (
                activity_data["max_cadence"] * 2
            )

    # Lapy
    lap_data = []

    for row in laps:
        item = dict(row)

        if "avg_rr" in item:
            item["average_respiration_rate_bpm"] = item.pop("avg_rr")

        if "max_rr" in item:
            item["max_respiration_rate_bpm"] = item.pop("max_rr")

        if sport == "running":
            if item.get("avg_cadence") is not None:
                item["average_running_cadence_steps_per_min"] = (
                    item["avg_cadence"] * 2
                )

            if item.get("max_cadence") is not None:
                item["max_running_cadence_steps_per_min"] = (
                    item["max_cadence"] * 2
                )

        lap_data.append(item)

    # Rekordy szczegółowe
    record_data = []

    for row in records:
        item = dict(row)

        if "rr" in item:
            item["respiration_rate_bpm"] = item.pop("rr")

        if (
            sport == "running"
            and item.get("cadence") is not None
        ):
            item["running_cadence_steps_per_min"] = (
                item["cadence"] * 2
            )

        record_data.append(item)

    # Informacja, jakie szczegółowe pola GarminDB posiada
    record_fields_available = (
        list(record_data[0].keys())
        if record_data
        else []
    )

    return {
        "activity": activity_data,

        "laps": lap_data,

        "records": {
            "returned_records": len(record_data),
            "limit": 200,
            "fields_available": record_fields_available,
            "data": record_data
        }
    }

#@mcp.tool() #odznaczamy aby nie było narzędziem MCP ale zostawiam funkcję
def get_activity_devices(activity_id: str) -> dict:
    """
    Zwraca urządzenia i sensory użyte podczas wskazanej aktywności.

    Dodatkowo określa prawdopodobne źródło pomiaru tętna:
    - external_chest_sensor
    - wrist_sensor
    - unknown
    """

    # Pobranie numerów seryjnych urządzeń przypisanych do aktywności
    conn = sqlite3.connect(
        f"file:{GARMIN_ACTIVITIES_DB}?mode=ro",
        uri=True
    )
    conn.row_factory = sqlite3.Row

    device_rows = conn.execute("""
        SELECT device_serial_number
        FROM activities_devices
        WHERE activity_id = ?
    """, [activity_id]).fetchall()

    conn.close()

    serial_numbers = [
        row["device_serial_number"]
        for row in device_rows
    ]

    if not serial_numbers:
        return {
            "activity_id": activity_id,
            "heart_rate_source": "unknown",
            "external_heart_rate_sensor_used": False,
            "devices": []
        }

    # Pobranie informacji o urządzeniach
    placeholders = ",".join("?" * len(serial_numbers))

    conn = sqlite3.connect(
        f"file:{GARMIN_DB}?mode=ro",
        uri=True
    )
    conn.row_factory = sqlite3.Row

    rows = conn.execute(f"""
        SELECT
            serial_number,
            device_type,
            manufacturer,
            product,
            hardware_version
        FROM devices
        WHERE serial_number IN ({placeholders})
    """, serial_numbers).fetchall()

    conn.close()

    devices = [dict(row) for row in rows]

    external_hr_device = None
    wrist_hr_device = None

    for device in devices:
        device_type = (device["device_type"] or "").lower()
        product = (device["product"] or "").lower()

        # Zewnętrzny czujnik HR / pas na klatkę
        if (
            device_type == "heart_rate"
            or "hrm" in product
        ):
            external_hr_device = device
            break

        # Optyczny czujnik HR w zegarku
        if device_type == "wrist_heart_rate":
            wrist_hr_device = device

    if external_hr_device:
        heart_rate_source = "external_chest_sensor"
        external_sensor_used = True
        heart_rate_device = external_hr_device

    elif wrist_hr_device:
        heart_rate_source = "wrist_sensor"
        external_sensor_used = False
        heart_rate_device = wrist_hr_device

    else:
        heart_rate_source = "unknown"
        external_sensor_used = False
        heart_rate_device = None

    return {
        "activity_id": activity_id,
        "heart_rate_source": heart_rate_source,
        "external_heart_rate_sensor_used": external_sensor_used,
        "heart_rate_device": heart_rate_device,
        "devices": devices
    }

@mcp.tool()
def get_daily_activity_summary(
    start_date: str,
    end_date: str,
    sport: str = ""
) -> dict:
    """
    Zwraca aktywności pogrupowane według konkretnych dni
    w podanym zakresie dat.

    Narzędzie jest przeznaczone do pytań typu:
    - co trenowałem dzisiaj,
    - jak wyglądał mój trening w tym tygodniu,
    - co trenowałem przez ostatnie 7 dni,
    - co robiłem w poszczególnych dniach.

    WAŻNE:
    - jeśli użytkownik nie wskazał konkretnego sportu,
      nie ustawiaj parametru sport,
    - "w tym tygodniu" oznacza okres od poniedziałku
      bieżącego tygodnia do dzisiaj,
    - "ostatnie 7 dni" oznacza dzisiaj oraz 6 poprzednich dni.

    sport może być kategorią, np.:
    running, cycling, walking, hiking, swimming.
    """

    conn = sqlite3.connect(
        f"file:{GARMIN_ACTIVITIES_DB}?mode=ro",
        uri=True
    )
    conn.row_factory = sqlite3.Row

    query = """
        SELECT
            activity_id,
            name,
            sport,
            sub_sport,
            start_time,
            distance,
            moving_time,
            avg_hr,
            max_hr,
            calories,
            training_load
        FROM activities
        WHERE date(start_time) BETWEEN ? AND ?
    """

    params = [start_date, end_date]

    if sport:
        special_category = SPORT_SUBSPORT_CATEGORIES.get(sport)

        if special_category:
            query += " AND sport = ? AND sub_sport = ?"
            params.extend([
                special_category["sport"],
                special_category["sub_sport"]
            ])

        else:
            sports = SPORT_CATEGORIES.get(sport, [sport])
            placeholders = ",".join("?" * len(sports))

            query += f" AND sport IN ({placeholders})"
            params.extend(sports)

    query += " ORDER BY start_time ASC"

    rows = conn.execute(query, params).fetchall()
    conn.close()

    weekday_names = [
        "poniedziałek",
        "wtorek",
        "środa",
        "czwartek",
        "piątek",
        "sobota",
        "niedziela"
    ]

    days = {}

    for row in rows:
        activity_datetime = datetime.fromisoformat(row["start_time"])
        activity_date = activity_datetime.date().isoformat()

        if activity_date not in days:
            days[activity_date] = {
                "date": activity_date,
                "day_of_week": weekday_names[activity_datetime.weekday()],
                "activities_count": 0,
                "moving_time_seconds": 0,
                "training_load": 0,
                "sports": {},
                "activities": []
            }

        total_seconds = 0

        if row["moving_time"]:
            h, m, s = row["moving_time"].split(":")
            total_seconds = (
                int(h) * 3600
                + int(m) * 60
                + float(s)
            )

        distance = row["distance"] or 0
        training_load = row["training_load"] or 0
               
        activity_sport = row["sport"] or "unknown"

        if (
            row["sport"] == "fitness_equipment"
            and row["sub_sport"] == "cardio_training"
        ):
            activity_sport = "fitness_cardio"

        elif (
            row["sport"] == "fitness_equipment"
            and row["sub_sport"] == "strength_training"
        ):
            activity_sport = "strength"

        average_pace_min_km = None
        average_speed_kmh = None

        if distance > 0 and total_seconds > 0:

            if activity_sport in ("running", "walking", "hiking"):
                pace_seconds = total_seconds / distance
                pace_minutes = int(pace_seconds // 60)
                pace_remainder = int(round(pace_seconds % 60))

                if pace_remainder == 60:
                    pace_minutes += 1
                    pace_remainder = 0

                average_pace_min_km = (
                    f"{pace_minutes}:{pace_remainder:02d}"
                )

            elif activity_sport == "cycling":
                average_speed_kmh = round(
                    distance / (total_seconds / 3600),
                    1
                )

        day = days[activity_date]

        day["activities_count"] += 1
        day["moving_time_seconds"] += total_seconds
        day["training_load"] += training_load

        if activity_sport not in day["sports"]:
            day["sports"][activity_sport] = {
                "activities": 0,
                "distance_km": 0,
                "moving_time_seconds": 0,
                "training_load": 0
            }

        sport_summary = day["sports"][activity_sport]

        sport_summary["activities"] += 1
        sport_summary["distance_km"] += distance
        sport_summary["moving_time_seconds"] += total_seconds
        sport_summary["training_load"] += training_load

        day["activities"].append({
            "activity_id": row["activity_id"],
            "name": row["name"],
            #"sport": row["sport"],
            "sport": activity_sport,
            "sub_sport": row["sub_sport"],
            "start_time": row["start_time"],
            "distance_km": round(distance, 3),
            "moving_time_seconds": round(total_seconds),
            "average_pace_min_km": average_pace_min_km,
            "average_speed_kmh": average_speed_kmh,
            "average_heart_rate_bpm": row["avg_hr"],
            "max_heart_rate_bpm": row["max_hr"],
            "calories_kcal": row["calories"],
            "training_load": (
                round(training_load, 1)
                if row["training_load"] is not None
                else None
            )
        })

    period_total_seconds = 0
    period_total_load = 0
    period_sports = {}

    result_days = []

    for day in days.values():
        day["moving_time_seconds"] = round(
            day["moving_time_seconds"]
        )

        day["moving_time_hours"] = round(
            day["moving_time_seconds"] / 3600,
            2
        )

        day["training_load"] = round(
            day["training_load"],
            1
        )

        for sport_summary in day["sports"].values():
            sport_summary["distance_km"] = round(
                sport_summary["distance_km"],
                3
            )

            sport_summary["moving_time_seconds"] = round(
                sport_summary["moving_time_seconds"]
            )

            sport_summary["training_load"] = round(
                sport_summary["training_load"],
                1
            )

        period_total_seconds += day["moving_time_seconds"]
        period_total_load += day["training_load"]

        for sport_name, sport_data in day["sports"].items():

            if sport_name not in period_sports:
                period_sports[sport_name] = {
                    "activities": 0,
                    "distance_km": 0,
                    "moving_time_seconds": 0,
                    "training_load": 0
                }

            period_sports[sport_name]["activities"] += (
                sport_data["activities"]
            )

            period_sports[sport_name]["distance_km"] += (
                sport_data["distance_km"]
            )

            period_sports[sport_name]["moving_time_seconds"] += (
                sport_data["moving_time_seconds"]
            )

            period_sports[sport_name]["training_load"] += (
                sport_data["training_load"]
            )

        result_days.append(day)

    for sport_data in period_sports.values():
        sport_data["distance_km"] = round(
            sport_data["distance_km"],
            3
        )

        sport_data["moving_time_seconds"] = round(
            sport_data["moving_time_seconds"]
        )

        sport_data["moving_time_hours"] = round(
            sport_data["moving_time_seconds"] / 3600,
            2
        )

        sport_data["training_load"] = round(
            sport_data["training_load"],
            1
        )

    return {
        "period": {
            "start_date": start_date,
            "end_date": end_date
        },

        "summary": {
            "days_with_activities": len(result_days),
            "activities": len(rows),
            "moving_time_seconds": round(period_total_seconds),
            "moving_time_hours": round(
                period_total_seconds / 3600,
                2
            ),
            "training_load": round(period_total_load, 1),
            "sports": period_sports
        },

        "days": result_days
    }

@mcp.tool()
def get_recovery_metrics(start_date: str, end_date: str) -> dict:
    """
    Zwraca podsumowanie regeneracji w podanym zakresie dat.

    Uwzględnia:
    - HRV
    - sen i Sleep Score
    - tętno spoczynkowe
    - stres

    Daty w formacie YYYY-MM-DD.

    Ważne:
    - Dla snu pola start i end określają rzeczywisty przedział snu.
      Pole date/day jest techniczną datą rekordu GarminDB i nie powinno być
      używane samodzielnie do określania, której nocy dotyczy sen.
    """

    conn = sqlite3.connect(f"file:{GARMIN_DB}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row

    # Body Battery
    daily_rows = conn.execute("""
        SELECT
            day,
            bb_charged,
            bb_max,
            bb_min,
            stress_avg
        FROM daily_summary
        WHERE date(day) BETWEEN ? AND ?
        ORDER BY day
    """, [start_date, end_date]).fetchall()

    # HRV
    hrv_rows = conn.execute("""
        SELECT
            day,
            weekly_avg,
            last_night_avg,
            last_night_5min_high,
            baseline_low,
            baseline_upper,
            status
        FROM hrv
        WHERE date(day) BETWEEN ? AND ?
        ORDER BY day
    """, [start_date, end_date]).fetchall()

    # Sen
    sleep_rows = conn.execute("""
        SELECT
            day,
            start,
            end,
            total_sleep,
            deep_sleep,
            light_sleep,
            rem_sleep,
            awake,
            avg_stress,
            score,
            qualifier
        FROM sleep
        WHERE date(day) BETWEEN ? AND ?
        ORDER BY day
    """, [start_date, end_date]).fetchall()

    # Tętno Spoczynkowe (Resting HR)
    rhr_rows = conn.execute("""
        SELECT day, resting_heart_rate
        FROM resting_hr
        WHERE date(day) BETWEEN ? AND ?
        ORDER BY day
    """, [start_date, end_date]).fetchall()

    # Stress
    stress_rows = conn.execute("""
        SELECT stress
        FROM stress
        WHERE date(timestamp) BETWEEN ? AND ?
          AND stress BETWEEN 0 AND 100
    """, [start_date, end_date]).fetchall()

    conn.close()

    def time_to_seconds(value):
        if not value:
            return 0

        h, m, s = value.split(":")
        return int(h) * 3600 + int(m) * 60 + float(s)

    # Body Battery
    bb_charged_values = [
        row["bb_charged"]
        for row in daily_rows
        if row["bb_charged"] is not None
    ]

    avg_bb_charged = (
        round(sum(bb_charged_values) / len(bb_charged_values), 1)
        if bb_charged_values else None
    )

    latest_body_battery = None

    if daily_rows:
        row = daily_rows[-1]

        latest_body_battery = {
            "date": row["day"],
            "recharged_points": row["bb_charged"],
            "max_body_battery_level": row["bb_max"],
            "min_body_battery_level": row["bb_min"],
            "average_daily_stress_0_100": row["stress_avg"]
        }        

    # HRV
    latest_hrv = dict(hrv_rows[-1]) if hrv_rows else None

    hrv_nightly_values = [
        row["last_night_avg"]
        for row in hrv_rows
        if row["last_night_avg"] is not None
    ]

    avg_nightly_hrv = (
        round(sum(hrv_nightly_values) / len(hrv_nightly_values), 1)
        if hrv_nightly_values else None
    )

    # Sen
    sleep_seconds = [
        time_to_seconds(row["total_sleep"])
        for row in sleep_rows
        if row["total_sleep"]
    ]

    avg_sleep_hours = (
        round(sum(sleep_seconds) / len(sleep_seconds) / 3600, 2)
        if sleep_seconds else None
    )

    sleep_scores = [
        row["score"]
        for row in sleep_rows
        if row["score"] is not None
    ]

    avg_sleep_score = (
        round(sum(sleep_scores) / len(sleep_scores), 1)
        if sleep_scores else None
    )

    latest_sleep = None

    if sleep_rows:
        row = sleep_rows[-1]

        latest_sleep = {
            "date": row["day"],
            "start": row["start"],
            "end": row["end"],
            "total_sleep_hours": round(
                time_to_seconds(row["total_sleep"]) / 3600, 2
           ),
            "deep_sleep_hours": round(
                time_to_seconds(row["deep_sleep"]) / 3600, 2
            ),
          "light_sleep_hours": round(
              time_to_seconds(row["light_sleep"]) / 3600, 2
           ),
          "rem_sleep_hours": round(
               time_to_seconds(row["rem_sleep"]) / 3600, 2
           ),
           "awake_hours": round(
               time_to_seconds(row["awake"]) / 3600, 2
           ),
           "sleep_score": row["score"],
           "sleep_qualifier": row["qualifier"],
           "average_sleep_stress": row["avg_stress"],
        }

    # Tętno Spoczynkowe (Resting HR)
    rhr_values = [
        row["resting_heart_rate"]
        for row in rhr_rows
        if row["resting_heart_rate"] is not None
    ]

    avg_resting_hr = (
        round(sum(rhr_values) / len(rhr_values), 1)
        if rhr_values else None
    )

    latest_resting_hr = (
        rhr_rows[-1]["resting_heart_rate"]
        if rhr_rows else None
    )

    # Stress
    stress_values = [
        row["stress"]
        for row in stress_rows
    ]

    avg_stress = (
        round(sum(stress_values) / len(stress_values), 1)
        if stress_values else None
    )

    return {
        "period": {
            "start_date": start_date,
            "end_date": end_date
        },

        "body_battery": {
            "average_recharged_points": avg_bb_charged,
            "latest": latest_body_battery
        },

        "hrv": {
            "average_nightly_hrv_ms": avg_nightly_hrv,
            "latest": latest_hrv
        },

        "sleep": {
            "average_sleep_hours": avg_sleep_hours,
            "average_sleep_score": avg_sleep_score,
            "latest": latest_sleep
        },

        "resting_heart_rate": {
            "average_bpm": avg_resting_hr,
            "latest_bpm": latest_resting_hr
        },

        "stress": {
            "average_level": avg_stress
        },

        "days_with_hrv": len(hrv_rows),
        "days_with_sleep": len(sleep_rows),
        "days_with_resting_hr": len(rhr_rows)
    }

@mcp.tool()
def get_training_load_summary(weeks: int = 4) -> dict:
    """
    Zwraca obciążenie treningowe z ostatnich N tygodni.

    Uwzględnia wszystkie aktywności:
    - liczbę treningów
    - łączny czas
    - training load
    - podział tydzień po tygodniu

    weeks: liczba analizowanych tygodni, domyślnie 4.
    """

    if weeks < 1:
        weeks = 1

    if weeks > 52:
        weeks = 52

    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=weeks * 7 - 1)

    conn = sqlite3.connect(
        f"file:{GARMIN_ACTIVITIES_DB}?mode=ro",
        uri=True
    )

    conn.row_factory = sqlite3.Row

    rows = conn.execute("""
        SELECT
            start_time,
            sport,
            sub_sport,
            distance,
            moving_time,
            training_load
        FROM activities
        WHERE date(start_time) BETWEEN ? AND ?
        ORDER BY start_time
    """, [
        start_date.isoformat(),
        end_date.isoformat()
    ]).fetchall()

    conn.close()

    def time_to_seconds(value):
        if not value:
            return 0

        h, m, s = value.split(":")

        return (
            int(h) * 3600
            + int(m) * 60
            + float(s)
        )

    weeks_data = {}

    total_seconds = 0
    total_load = 0

    for row in rows:

        activity_date = datetime.fromisoformat(
            row["start_time"]
        ).date()

        week_start = activity_date - timedelta(
            days=activity_date.weekday()
        )

        week_key = week_start.isoformat()

        if week_key not in weeks_data:
            weeks_data[week_key] = {
                "week_start": week_key,
                "activities": 0,
                "moving_time_seconds": 0,
                "training_load": 0,
                "sports": {}
            }

        seconds = time_to_seconds(row["moving_time"])
        distance = row["distance"] or 0
        load = row["training_load"] or 0
        sport = row["sport"] or "unknown"

        if (
            row["sport"] == "fitness_equipment"
            and row["sub_sport"] == "cardio_training"
        ):
            sport = "fitness_cardio"

        elif (
            row["sport"] == "fitness_equipment"
            and row["sub_sport"] == "strength_training"
        ):
            sport = "strength"        

        week = weeks_data[week_key]

        week["activities"] += 1
        week["moving_time_seconds"] += seconds
        week["training_load"] += load

        if sport not in week["sports"]:
            week["sports"][sport] = {
                "activities": 0,
                "distance_km": 0,
                "training_load": 0
            }

        week["sports"][sport]["activities"] += 1
        week["sports"][sport]["distance_km"] += distance
        week["sports"][sport]["training_load"] += load

        total_seconds += seconds
        total_load += load

    weekly = []

    for week in weeks_data.values():

        week["moving_time_hours"] = round(
            week.pop("moving_time_seconds") / 3600,
            2
        )

        week["training_load"] = round(
            week["training_load"], 1
        )

        for sport in week["sports"].values():
            sport["distance_km"] = round(
                sport["distance_km"], 2
            )

            sport["training_load"] = round(
                sport["training_load"], 1
            )

        weekly.append(week)

    return {
        "period": {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "weeks": weeks
        },

        "total": {
            "activities": len(rows),
            "moving_time_hours": round(
                total_seconds / 3600, 2
            ),
            "training_load": round(total_load, 1)
        },

        "weekly": weekly
    }

@mcp.tool()
def get_readiness_summary() -> dict:
    """
    Zwraca najnowsze dostępne dane potrzebne do oceny aktualnej
    gotowości treningowej użytkownika.

    Uwzględnia:
    - HRV ostatniej dostępnej nocy oraz jego baseline i status,
    - Tętno Spoczynkowe (Resting HR) oraz średnią z ostatnich 7 dni,
    - ostatni dostępny sen i Sleep Score,
    - Body Battery,
    - Obciążenie Treningowe (Training Load) z ostatnich 7 i 28 dni.

    Ważne:
    - Zwracane dane mogą nie obejmować bieżącego dnia ani ostatniej nocy.
      Zawsze sprawdź daty poszczególnych danych przed oceną aktualnej
      gotowości.
    - data_freshness pokazuje datę najnowszych dostępnych danych
      zdrowotnych oraz ostatniej aktywności. Użyj tego do oceny,
      czy dane są wystarczająco świeże względem current_date.
    - Dla snu pola start i end określają rzeczywisty przedział snu.
      Pole date/day jest techniczną datą rekordu GarminDB i nie powinno być
      używane samodzielnie do określania, której nocy dotyczy sen.
    - recharged_points oznacza liczbę punktów Body Battery odzyskanych
      podczas regeneracji. NIE oznacza aktualnego poziomu Body Battery.
    - max_body_battery_level oznacza najwyższy zarejestrowany poziom
      Body Battery danego dnia.
    - min_body_battery_level oznacza najniższy zarejestrowany poziom
      Body Battery danego dnia.
    - Funkcja zwraca fakty i porównania z GarminDB.
      Interpretację i rekomendację treningową wykonuje trener AI.
    """

    today = date.today()

    start_7d = today - timedelta(days=6)
    previous_7d_start = today - timedelta(days=13)
    previous_7d_end = today - timedelta(days=7)
    start_28d = today - timedelta(days=27)

    # Regeneracja
    conn = sqlite3.connect(
        f"file:{GARMIN_DB}?mode=ro",
        uri=True
    )
    conn.row_factory = sqlite3.Row

    hrv = conn.execute("""
        SELECT *
        FROM hrv
        WHERE date(day) <= ?
        ORDER BY day DESC
        LIMIT 1
    """, [today.isoformat()]).fetchone()

    sleep = conn.execute("""
        SELECT *
        FROM sleep
        WHERE date(day) <= ?
        ORDER BY day DESC
        LIMIT 1
    """, [today.isoformat()]).fetchone()

    body_battery = conn.execute("""
        SELECT
            day,
            bb_charged,
            bb_max,
            bb_min,
            stress_avg
        FROM daily_summary
        WHERE date(day) <= ?
        ORDER BY day DESC
        LIMIT 1
    """, [today.isoformat()]).fetchone()

    rhr_rows = conn.execute("""
        SELECT resting_heart_rate
        FROM resting_hr
        WHERE date(day) BETWEEN ? AND ?
          AND resting_heart_rate IS NOT NULL
    """, [
        start_7d.isoformat(),
        today.isoformat()
    ]).fetchall()

    latest_rhr = conn.execute("""
        SELECT day, resting_heart_rate
        FROM resting_hr
        WHERE date(day) <= ?
        ORDER BY day DESC
        LIMIT 1
    """, [today.isoformat()]).fetchone()

    conn.close()

    rhr_values = [
        row["resting_heart_rate"]
        for row in rhr_rows
    ]

    avg_rhr_7d = (
        round(sum(rhr_values) / len(rhr_values), 1)
        if rhr_values else None
    )

    # Obciążenie Treningowe (Training Load)
    conn = sqlite3.connect(
        f"file:{GARMIN_ACTIVITIES_DB}?mode=ro",
        uri=True
    )
    conn.row_factory = sqlite3.Row

    load_current = conn.execute("""
        SELECT SUM(training_load) AS load
        FROM activities
        WHERE date(start_time) BETWEEN ? AND ?
    """, [
        start_7d.isoformat(),
        today.isoformat()
    ]).fetchone()["load"] or 0

    load_previous = conn.execute("""
        SELECT SUM(training_load) AS load
        FROM activities
        WHERE date(start_time) BETWEEN ? AND ?
    """, [
        previous_7d_start.isoformat(),
        previous_7d_end.isoformat()
    ]).fetchone()["load"] or 0

    load_28d = conn.execute("""
        SELECT SUM(training_load) AS load
        FROM activities
        WHERE date(start_time) BETWEEN ? AND ?
    """, [
        start_28d.isoformat(),
        today.isoformat()
    ]).fetchone()["load"] or 0

    last_activity = conn.execute("""
        SELECT
            start_time,
            sport,
            name,
            training_load
        FROM activities
        ORDER BY start_time DESC
        LIMIT 1
    """).fetchone()

    conn.close()

    average_weekly_load_28d = round(load_28d / 4, 1)

    # Świeżość danych
    health_dates = [
        row["day"]
        for row in (hrv, sleep, body_battery, latest_rhr)
        if row is not None and row["day"] is not None
    ]

    latest_health_data_date = (
        max(health_dates)
        if health_dates
        else None
    )

    latest_activity_date = (
        last_activity["start_time"]
        if last_activity
        else None
    )

    # Wynik
    return {
        "current_date": today.isoformat(),

        "data_freshness": {
            "latest_health_data_date": latest_health_data_date,
            "latest_activity_date": latest_activity_date,
        },

        "hrv": {
            "date":
                hrv["day"] if hrv else None,

            "last_night_average_ms":
                hrv["last_night_avg"] if hrv else None,

            "weekly_average_ms":
                hrv["weekly_avg"] if hrv else None,

            "baseline_low_ms":
                hrv["baseline_low"] if hrv else None,

            "baseline_upper_ms":
                hrv["baseline_upper"] if hrv else None,

            "status":
                hrv["status"] if hrv else None,
        },

        "sleep": {
            "date":
                sleep["day"] if sleep else None,

            "start":
                sleep["start"] if sleep else None,

            "end":
                sleep["end"] if sleep else None,

            "total_sleep":
                sleep["total_sleep"] if sleep else None,

            "deep_sleep":
                sleep["deep_sleep"] if sleep else None,

            "light_sleep":
                sleep["light_sleep"] if sleep else None,

            "rem_sleep":
                sleep["rem_sleep"] if sleep else None,

            "awake":
                sleep["awake"] if sleep else None,

            "score":
                sleep["score"] if sleep else None,

            "qualifier":
                sleep["qualifier"] if sleep else None,

            "average_sleep_stress":
                sleep["avg_stress"] if sleep else None,
        },

        "resting_heart_rate": {
            "date":
                latest_rhr["day"] if latest_rhr else None,

            "latest_bpm":
                latest_rhr["resting_heart_rate"]
                if latest_rhr else None,

            "average_7d_bpm": avg_rhr_7d,
        },

        "body_battery": {
            "date":
                body_battery["day"]
                if body_battery else None,

            "recharged_points":
                body_battery["bb_charged"]
                if body_battery else None,

            "max_body_battery_level":
                body_battery["bb_max"]
                if body_battery else None,

            "min_body_battery_level":
                body_battery["bb_min"]
                if body_battery else None,
        },

        "training_load": {
            "last_7_days": round(load_current, 1),
            "previous_7_days": round(load_previous, 1),
            "last_28_days": round(load_28d, 1),
            "average_weekly_load_last_28_days": average_weekly_load_28d,
        },

        "last_activity": (
            dict(last_activity)
            if last_activity else None
        )
    }

if __name__ == "__main__":
    mcp.run(
        transport="streamable-http",
        host="0.0.0.0",
        port=8000
    )

    ###
