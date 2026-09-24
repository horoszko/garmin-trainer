"""
title: GarminDB Tools
description: Garmin Trainer capabilities.
version: 0.1.0
"""

import asyncio
from concurrent.futures import TimeoutError as FutureTimeoutError
import sys
import time

sys.path.insert(0, "/opt/garmin-trainer/app")

import garmin_db as backend


class Tools:

    async def get_activities(
        self,
        start_date: str,
        end_date: str,
        sport: str = "",
    ):
        """
        Pobiera aktywności z GarminDB w podanym zakresie dat.

        sport może być kategorią, np.:
        running, cycling, walking, hiking, swimming,
        fitness_cardio, strength
        """
        return await asyncio.to_thread(
            backend.get_activities,
            start_date=start_date,
            end_date=end_date,
            sport=sport,
        )

    async def get_sport_types(self):
        """
        Zwraca wszystkie typy aktywności występujące w bazie GarminDB
        wraz z liczbą ich wystąpień.
        """
        return await asyncio.to_thread(
            backend.get_sport_types,
        )

    async def get_sport_summary(
        self,
        start_date: str,
        end_date: str,
        sport: str,
    ):
        """
        Zwraca podsumowanie wybranego sportu w podanym zakresie dat.

        sport: np. running, cycling, walking, hiking, swimming
        """
        return await asyncio.to_thread(
            backend.get_sport_summary,
            start_date=start_date,
            end_date=end_date,
            sport=sport,
        )

    async def get_latest_activity(
        self,
        sport: str = "",
    ):
        """
        Zwraca ostatnią aktywność użytkownika.

        sport jest opcjonalny.
        Przykłady:
        running, cycling, swimming, walking, hiking, climbing

        Jeśli sport nie zostanie podany, zwraca ostatnią aktywność
        dowolnego typu.
        """
        return await asyncio.to_thread(
            backend.get_latest_activity,
            sport=sport,
        )

    async def get_activity_details(
        self,
        activity_id: str,
    ):
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
        return await asyncio.to_thread(
            backend.get_activity_details,
            activity_id=activity_id,
        )

    async def get_daily_activity_summary(
        self,
        start_date: str,
        end_date: str,
        sport: str = "",
    ):
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
        return await asyncio.to_thread(
            backend.get_daily_activity_summary,
            start_date=start_date,
            end_date=end_date,
            sport=sport,
        )

    async def get_user_profile(self):
        """
        Zwraca podstawowy profil użytkownika zapisany w GarminDB.

        Dane pochodzą bezpośrednio z tabeli attributes.
        Nie zgaduje brakujących wartości.
        """
        return await asyncio.to_thread(
            backend.get_user_profile,
        )

    async def get_recovery_metrics(
        self,
        start_date: str,
        end_date: str,
    ):
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
          Pole date/day jest techniczną datą rekordu GarminDB i nie powinno
          być używane samodzielnie do określania, której nocy dotyczy sen.
        """
        return await asyncio.to_thread(
            backend.get_recovery_metrics,
            start_date=start_date,
            end_date=end_date,
        )

    async def get_training_load_summary(
        self,
        weeks: int = 4,
    ):
        """
        Zwraca obciążenie treningowe z ostatnich N tygodni.

        Uwzględnia wszystkie aktywności:
        - liczbę treningów
        - łączny czas
        - training load
        - podział tydzień po tygodniu

        weeks: liczba analizowanych tygodni, domyślnie 4.
        """
        return await asyncio.to_thread(
            backend.get_training_load_summary,
            weeks=weeks,
        )

    async def get_readiness_summary(self):
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
          Pole date/day jest techniczną datą rekordu GarminDB i nie powinno
          być używane samodzielnie do określania, której nocy dotyczy sen.
        - recharged_points oznacza liczbę punktów Body Battery odzyskanych
          podczas regeneracji. NIE oznacza aktualnego poziomu Body Battery.
        - max_body_battery_level oznacza najwyższy zarejestrowany poziom
          Body Battery danego dnia.
        - min_body_battery_level oznacza najniższy zarejestrowany poziom
          Body Battery danego dnia.
        - Funkcja zwraca fakty i porównania z GarminDB.
          Interpretację i rekomendację treningową wykonuje trener AI.
        """
        return await asyncio.to_thread(
            backend.get_readiness_summary,
        )

    async def get_vo2max_history(
        self,
        start_date: str,
        end_date: str,
        sport: str = "running",
    ):
        """
        Zwraca historię VO2max w podanym zakresie dat.

        Narzędzie służy do analizy aktualnej kondycji oraz zmian
        wydolności w czasie.

        Daty w formacie YYYY-MM-DD.

        Obsługiwane sporty:
        - running
        - cycling

        Ważne:
        - VO2max dla biegania i jazdy na rowerze są osobnymi
          wskaźnikami i nie należy ich bezpośrednio porównywać,
        - GarminDB zapisuje VO2max przy wybranych aktywnościach,
          dlatego nie każda aktywność musi posiadać pomiar,
        - interpretację trendu wykonuje trener AI.
        """
        return await asyncio.to_thread(
            backend.get_vo2max_history,
            start_date=start_date,
            end_date=end_date,
            sport=sport,
        )

    async def get_garmindb_status(self):
        """
        Zwraca stan lokalnego GarminDB bez wykonywania synchronizacji.
        """
        return await asyncio.to_thread(
            backend.get_garmindb_status,
        )

    async def sync_garmindb(
        self,
        mode: str = "auto",
        full_sync_after_days: int = 30,
        __event_emitter__=None,
    ):
        """
        Synchronizuje GarminDB i pokazuje główne etapy synchronizacji.

        `/sync` używa mode="auto", czyli latest. `/sync full` wymaga
        mode="full" i powinno być używane wyłącznie po wyraźnym żądaniu.
        Pełna synchronizacja może potrwać kilka godzin.

        Domyślnie oraz dla mode="auto" używa latest. Tryb mode="full"
        wykonuj wyłącznie po jednoznacznym żądaniu pełnej synchronizacji.
        Wynik success=false oznacza błąd i nie wolno przedstawiać go jako
        udanej synchronizacji.
        """
        loop = asyncio.get_running_loop()
        last_status_at = time.monotonic()
        last_status_description = "Synchronizacja GarminDB"

        async def emit_status(description: str, done: bool = False):
            nonlocal last_status_at, last_status_description

            last_status_at = time.monotonic()
            last_status_description = description

            if not __event_emitter__:
                return

            try:
                await __event_emitter__(
                    {
                        "type": "status",
                        "data": {
                            "description": description,
                            "done": done,
                        },
                    }
                )
            except Exception:
                # Status w GUI nie może przerwać synchronizacji GarminDB.
                return

        if mode.strip().lower() == "full":
            await emit_status(
                "Pełna synchronizacja może potrwać kilka godzin. Możesz ją "
                "przerwać używając polecenia \"/sync stop\", ale wówczas "
                "baza danych nie zostanie zaktualizowana."
            )
            # Daj GUI chwilę na pokazanie ostrzeżenia przed kolejnym statusem.
            await asyncio.sleep(5)
            await emit_status(
                "Uruchomiono pełną synchronizację GarminDB."
            )

        def progress(message: str):
            nonlocal last_status_at, last_status_description

            last_status_at = time.monotonic()
            last_status_description = message

            if __event_emitter__:
                future = asyncio.run_coroutine_threadsafe(
                    __event_emitter__(
                        {
                            "type": "status",
                            "data": {
                                "description": message,
                                "done": False,
                            },
                        }
                    ),
                    loop,
                )
                try:
                    future.result(timeout=2.0)
                except FutureTimeoutError:
                    future.cancel()
                except Exception:
                    future.cancel()

        async def emit_heartbeat():
            while True:
                await asyncio.sleep(15)
                if time.monotonic() - last_status_at >= 15:
                    await emit_status(
                        "Synchronizacja nadal trwa — "
                        f"{last_status_description.lower()}"
                    )

        heartbeat_task = (
            asyncio.create_task(emit_heartbeat())
            if __event_emitter__
            else None
        )

        try:
            result = await asyncio.to_thread(
                backend.sync_garmindb,
                mode,
                full_sync_after_days,
                progress,
            )
        finally:
            if heartbeat_task:
                heartbeat_task.cancel()
                try:
                    await heartbeat_task
                except asyncio.CancelledError:
                    pass

        if result.get("interrupted"):
            final_description = "Synchronizacja GarminDB przerwana."
        elif result.get("success"):
            final_description = "Synchronizacja GarminDB zakończona."
        else:
            final_description = "Synchronizacja GarminDB zakończona błędem."

        await emit_status(final_description, done=True)

        return result

    async def stop_garmindb_sync(self, __event_emitter__=None):
        """
        Zatrzymuje aktywną synchronizację GarminDB.

        Użyj przy prośbie `/sync stop`. Jeśli synchronizacja nie działa,
        zwracany jest status `not_running` bez błędu.
        """
        result = await asyncio.to_thread(
            backend.stop_garmindb_sync,
        )

        if __event_emitter__:
            await __event_emitter__(
                {
                    "type": "status",
                    "data": {
                        "description": result.get(
                            "message",
                            "Synchronizacja GarminDB została zatrzymana.",
                        ),
                        "done": True,
                    },
                }
            )

        return result
