import io
import re
from pathlib import Path

from open_webui.models.files import Files
from open_webui.models.users import Users
from open_webui.routers.files import upload_file_handler
from starlette.datastructures import Headers, UploadFile


async def attach_workspace_file(
    file_path: Path,
    allowed_root: Path,
    user_context: dict | None,
    request,
    event_emitter,
    content_type: str,
) -> dict:
    """Uploads one generated project file and attaches it to the chat."""
    if not user_context or request is None or event_emitter is None:
        raise ValueError(
            "Załącznik wymaga zalogowanego użytkownika i aktywnej rozmowy "
            "Open WebUI."
        )

    user = await Users.get_user_by_id(user_context["id"])
    if user is None:
        raise ValueError("Nie znaleziono użytkownika Open WebUI.")

    root = allowed_root.resolve()
    path = file_path.resolve()
    if path == root or root not in path.parents:
        raise ValueError("Niepoprawna ścieżka załączanego pliku.")

    if not path.is_file():
        raise ValueError("Nie znaleziono załączanego pliku.")

    filename = path.name
    if not re.fullmatch(r"[a-zA-Z0-9_.-]+", filename):
        raise ValueError("Niepoprawna nazwa załączanego pliku.")

    upload = UploadFile(
        file=io.BytesIO(path.read_bytes()),
        filename=filename,
        headers=Headers({"content-type": content_type}),
    )

    try:
        saved = await upload_file_handler(
            request=request,
            file=upload,
            metadata={},
            process=False,
            process_in_background=False,
            user=user,
        )
    finally:
        await upload.close()

    file_id = saved["id"] if isinstance(saved, dict) else saved.id

    if content_type == "text/markdown" or path.suffix.lower() == ".md":
        updated = await Files.update_file_data_by_id(
            file_id,
            {
                "content": path.read_text(encoding="utf-8"),
                "status": "completed",
            },
        )
        if updated is None:
            raise RuntimeError("Nie udało się zapisać treści pliku Markdown.")

    url = f"/api/v1/files/{file_id}/content?attachment=true"
    await event_emitter(
        {
            "type": "files",
            "data": {
                "files": [
                    {
                        "type": "file",
                        "id": file_id,
                        "name": filename,
                        "url": url,
                    }
                ]
            },
        }
    )

    return {
        "file_id": file_id,
        "filename": filename,
        "url": url,
    }
