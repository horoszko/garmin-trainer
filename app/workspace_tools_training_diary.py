"""
title: Training Diary Tools
description: Training Diary Markdown capabilities.
version: 0.1.0
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, "/opt/garmin-trainer/app")

import training_diary as backend
from workspace_tools_files import attach_workspace_file


class Tools:
    async def start_training(self):
        """
        Rozpoczyna konwersacyjny onboarding Garmin Trainer.

        Użyj przy prośbie typu `/start`. Funkcja nie tworzy, nie nadpisuje
        pliku i nie pokazuje formularza ani code blocka. Przy braku profilu
        użyj najpierw `get_user_profile`, a potem zapytaj użytkownika własnymi
        słowami o informacje potrzebne do onboardingu. Przy istniejącym W00
        nie uruchamiaj onboardingu ponownie i nie modyfikuj go automatycznie.
        """
        return await asyncio.to_thread(
            backend.start_training,
        )

    async def get_training_context(self):
        """
        Zwraca kontekst dziennika treningowego potrzebny trenerowi AI.
        """
        return await asyncio.to_thread(
            backend.get_training_context,
        )

    async def get_training_diary(
        self,
        week: str | None = None,
        __user__: dict = None,
        __request__=None,
        __event_emitter__=None,
    ):
        """
        Otwiera istniejący Training Diary i dołącza jego plik Markdown.

        Użyj tej funkcji, gdy użytkownik chce pokazać, załączyć, pobrać lub
        otworzyć istniejącą notatkę Training Diary. Jeśli `week` nie jest
        podany, użyj bieżącego tygodnia.
        """
        result = await asyncio.to_thread(
            backend.get_training_diary,
            week=week,
        )

        if not result.get("success"):
            return result

        attachment = await attach_workspace_file(
            file_path=Path(result["path"]),
            allowed_root=backend.TRAINING_DIARY_DIR,
            user_context=__user__,
            request=__request__,
            event_emitter=__event_emitter__,
            content_type="text/markdown",
        )

        return {
            **result,
            "attached": True,
            "attachment": attachment,
        }

    async def create_training_diary(
        self,
        week: str,
        content: str,
        __user__: dict = None,
        __request__=None,
        __event_emitter__=None,
    ):
        """
        Tworzy dziennik Markdown, pokazuje preview i dołącza plik.

        Dla profilu W00 użyj week w formacie YYYY-W00, np. 2026-W00, nigdy
        samego W00. Treść musi zawierać frontmatter:

        ---
        week: 2026-W00
        schema: training_diary_v1
        type: INITIAL_PROFILE
        ---

        Wartość week w treści musi być identyczna z argumentem week.

        Dla tygodni YYYY-W01–YYYY-W53 dodaj do frontmatter status:
        CLOSED, IN_PROGRESS albo PLANNED. Pole `Status:` w treści dokumentu
        nie zastępuje pola `status:` w frontmatter.
        """
        result = await asyncio.to_thread(
            backend.create_training_diary,
            week=week,
            content=content,
        )

        if not result.get("success"):
            return result

        attachment = await attach_workspace_file(
            file_path=Path(result["path"]),
            allowed_root=backend.TRAINING_DIARY_DIR,
            user_context=__user__,
            request=__request__,
            event_emitter=__event_emitter__,
            content_type="text/markdown",
        )

        return {
            **result,
            "attached": True,
            "attachment": attachment,
        }

    async def update_training_diary(
        self,
        week: str,
        section: str,
        content: str,
        diary_status: str = "",
        __user__: dict = None,
        __request__=None,
        __event_emitter__=None,
    ):
        """
        Aktualizuje sekcję Diary, pokazuje preview i dołącza plik.
        """
        result = await asyncio.to_thread(
            backend.update_training_diary,
            week=week,
            section=section,
            content=content,
            diary_status=diary_status,
        )

        if not result.get("success"):
            return result

        attachment = await attach_workspace_file(
            file_path=Path(result["path"]),
            allowed_root=backend.TRAINING_DIARY_DIR,
            user_context=__user__,
            request=__request__,
            event_emitter=__event_emitter__,
            content_type="text/markdown",
        )

        return {
            **result,
            "attached": True,
            "attachment": attachment,
        }
