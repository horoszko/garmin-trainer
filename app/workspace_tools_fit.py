"""
title: FIT Files Tools
description: Garmin Trainer workout FIT generation.
version: 0.1.0
"""

import asyncio
import sys

sys.path.insert(0, "/opt/garmin-trainer/app")

import tools_fit as backend
from workspace_tools_files import attach_workspace_file


class Tools:
    async def create_running_workout(
        self,
        name: str,
        warmup_seconds: int,
        interval_seconds: int,
        recovery_seconds: int,
        repetitions: int,
        cooldown_seconds: int,
        pace_min: str = "",
        pace_max: str = "",
        __user__: dict = None,
        __request__=None,
        __event_emitter__=None,
    ):
        """
        Tworzy plik FIT z treningiem biegowym i dołącza go do rozmowy.

        Obsługiwany schemat:
        - rozgrzewka
        - interwał
        - regeneracja
        - powtórzenia
        - schłodzenie

        pace_min i pace_max podawaj jako MM:SS min/km.
        """
        result = await asyncio.to_thread(
            backend.create_running_workout,
            name=name,
            warmup_seconds=warmup_seconds,
            interval_seconds=interval_seconds,
            recovery_seconds=recovery_seconds,
            repetitions=repetitions,
            cooldown_seconds=cooldown_seconds,
            pace_min=pace_min,
            pace_max=pace_max,
        )

        if not result.get("success"):
            return result

        attachment = await attach_workspace_file(
            file_path=backend.GENERATED_DIR / result["filename"],
            allowed_root=backend.GENERATED_DIR,
            user_context=__user__,
            request=__request__,
            event_emitter=__event_emitter__,
            content_type="application/octet-stream",
        )

        return {
            **result,
            "attached": True,
            "attachment": attachment,
        }

