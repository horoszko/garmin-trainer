"""Idempotentny bootstrap Toola, modeli i źródeł Knowledge."""

from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


OPEN_WEBUI_URL = os.environ.get(
    "OPEN_WEBUI_URL",
    "http://127.0.0.1:8080",
).rstrip("/")
CONFIG_DIR = Path(
    os.environ.get(
        "GARMIN_TRAINER_CONFIG_DIR",
        "/opt/garmin-trainer/config",
    )
)
KNOWLEDGE_DIR = Path(
    os.environ.get("GARMIN_TRAINER_KNOWLEDGE_DIR", "/data/knowledge")
)
WEBUI_ADMIN_EMAIL = os.environ.get("WEBUI_ADMIN_EMAIL", "").strip()
WEBUI_ADMIN_PASSWORD = os.environ.get("WEBUI_ADMIN_PASSWORD", "")


def request_json(method: str, path: str, payload=None, token: str = ""):
    body = None
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if payload is not None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = Request(
        f"{OPEN_WEBUI_URL}{path}", data=body, headers=headers, method=method
    )
    with urlopen(request, timeout=60) as response:
        raw = response.read()
        return json.loads(raw) if raw else None


def multipart_upload(path: str, file_path: Path, token: str) -> dict:
    boundary_hash = hashlib.sha256(file_path.name.encode()).hexdigest()[:16]
    boundary = f"----GarminTrainer{boundary_hash}"
    content = file_path.read_bytes()
    header = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{file_path.name}"\r\n'
        "Content-Type: text/markdown\r\n\r\n"
    ).encode("utf-8")
    body = header + content + f"\r\n--{boundary}--\r\n".encode("ascii")
    request = Request(
        f"{OPEN_WEBUI_URL}{path}",
        data=body,
        headers={
            "Accept": "application/json",
            "Authorization": f"Bearer {token}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
        method="POST",
    )
    with urlopen(request, timeout=120) as response:
        raw = response.read()
        return json.loads(raw) if raw else {}


def wait_for_open_webui() -> None:
    for _ in range(60):
        try:
            request = Request(f"{OPEN_WEBUI_URL}/health", method="GET")
            with urlopen(request, timeout=2) as response:
                if response.status == 200:
                    return
        except (HTTPError, URLError, OSError):
            pass
        time.sleep(2)
    raise RuntimeError("Open WebUI nie odpowiada na /health.")


def load_json(path: Path) -> dict:
    if not path.is_file():
        raise RuntimeError(f"Brak pliku konfiguracji: {path}")
    with path.open(encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise RuntimeError(f"Konfiguracja musi być obiektem JSON: {path}")
    return value


def sign_in() -> str:
    if not WEBUI_ADMIN_EMAIL or not WEBUI_ADMIN_PASSWORD:
        raise RuntimeError("Ustaw WEBUI_ADMIN_EMAIL i WEBUI_ADMIN_PASSWORD w .env.")
    response = request_json(
        "POST",
        "/api/v1/auths/signin",
        {"email": WEBUI_ADMIN_EMAIL, "password": WEBUI_ADMIN_PASSWORD},
    )
    token = response.get("token") if isinstance(response, dict) else None
    if not token:
        raise RuntimeError("Logowanie administratora nie zwróciło tokenu.")
    return token


def sync_tools(token: str) -> list[str]:
    tool_ids = []
    tool_paths = sorted((CONFIG_DIR / "tools").glob("*.json"))

    if not tool_paths:
        raise RuntimeError(f"Brak konfiguracji Tools w {CONFIG_DIR / 'tools'}")

    for path in tool_paths:
        config = load_json(path)
        tool_id = config["id"]
        tool_ids.append(tool_id)
        try:
            request_json("GET", f"/api/v1/tools/id/{tool_id}", token=token)
        except HTTPError as exc:
            if exc.code != 404:
                raise
            request_json("POST", "/api/v1/tools/create", config, token=token)
            print(f"Utworzono Tool: {tool_id}")
            continue
        request_json(
            "POST",
            f"/api/v1/tools/id/{tool_id}/update",
            config,
            token=token,
        )
        print(f"Zaktualizowano Tool: {tool_id}")

    return tool_ids


def read_source_metadata(source_path: Path) -> tuple[dict, str]:
    text = source_path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise RuntimeError(f"Brak frontmatter YAML w {source_path}")
    try:
        _, frontmatter, description = text.split("---\n", 2)
    except ValueError as exc:
        raise RuntimeError(f"Niepoprawny frontmatter YAML w {source_path}") from exc

    metadata = {}
    for line in frontmatter.splitlines():
        if not line.strip():
            continue
        key, separator, value = line.partition(":")
        if not separator or not key.strip() or not value.strip():
            raise RuntimeError(f"Niepoprawna linia metadanych w {source_path}: {line}")
        metadata[key.strip()] = value.strip()
    required_fields = ("name", "title", "author", "source", "description")
    missing_fields = [field for field in required_fields if not metadata.get(field)]
    if missing_fields:
        raise RuntimeError(
            f"Brak pól {', '.join(missing_fields)} w {source_path}"
        )
    return metadata, description.strip()


def sync_knowledge_source(
    source_dir: Path,
    source_metadata: dict,
    existing_items: list[dict],
    token: str,
) -> dict:
    knowledge_name = source_metadata["name"]
    knowledge = next(
        (item for item in existing_items if item.get("name") == knowledge_name),
        None,
    )
    if knowledge is None and len(existing_items) == 1:
        knowledge = existing_items[0]
    payload = {
        "name": knowledge_name,
        "description": source_metadata["description"],
        "access_grants": [],
    }
    if knowledge is None:
        knowledge = request_json(
            "POST",
            "/api/v1/knowledge/create",
            payload,
            token=token,
        )
        print(f"Utworzono Knowledge: {knowledge_name}")
    else:
        request_json(
            "POST",
            f"/api/v1/knowledge/{knowledge['id']}/update",
            payload,
            token=token,
        )
        print(f"Zaktualizowano Knowledge: {knowledge_name}")
    knowledge_id = knowledge.get("id")
    if not knowledge_id:
        raise RuntimeError(f"Brak identyfikatora Knowledge: {knowledge_name}")
    details = request_json(
        "GET", f"/api/v1/knowledge/{knowledge_id}/files?page=1", token=token
    ) or {}
    known_files = {
        item.get("filename"): item
        for item in (details.get("items") or [])
        if item.get("filename")
    }
    source_files = {
        path.name for path in source_dir.glob("*.md") if path.name != "_source.md"
    }
    for filename, existing_file in known_files.items():
        if filename not in source_files:
            request_json(
                "DELETE",
                f"/api/v1/files/{existing_file['id']}",
                token=token,
            )
            print(f"Usunięto nieaktualny plik Knowledge: {filename}")
    for file_path in sorted(source_dir.glob("*.md")):
        if file_path.name == "_source.md":
            continue
        local_hash = hashlib.sha256(file_path.read_bytes()).hexdigest()
        existing_file = known_files.get(file_path.name)
        remote_hash = (existing_file or {}).get("meta", {}).get("file_hash")
        if existing_file and remote_hash == local_hash:
            continue
        if existing_file:
            request_json(
                "DELETE",
                f"/api/v1/files/{existing_file['id']}",
                token=token,
            )
        uploaded = multipart_upload(
            "/api/v1/files/?process=true&process_in_background=false",
            file_path,
            token,
        )
        file_id = uploaded.get("id")
        if not file_id:
            raise RuntimeError(f"Upload Knowledge nie zwrócił ID: {file_path.name}")
        wait_for_file(file_id, token)
        request_json(
            "POST",
            f"/api/v1/knowledge/{knowledge_id}/file/add",
            {"file_id": file_id},
            token=token,
        )
        print(f"Zsynchronizowano plik Knowledge: {file_path.name}")
    return {"id": knowledge_id, "name": knowledge_name}


def sync_knowledge_sources(token: str) -> list[dict]:
    if not KNOWLEDGE_DIR.is_dir():
        raise RuntimeError(f"Brak katalogu Knowledge: {KNOWLEDGE_DIR}")
    source_dirs = sorted(path for path in KNOWLEDGE_DIR.iterdir() if path.is_dir())
    if not source_dirs:
        print(
            "Ostrzeżenie: brak źródeł Knowledge w "
            f"{KNOWLEDGE_DIR}; można je dodać później przez GUI Open WebUI.",
            file=sys.stderr,
        )
        return []

    response = request_json("GET", "/api/v1/knowledge/?page=1", token=token) or {}
    items = response.get("items", []) if isinstance(response, dict) else []
    knowledges = []
    for source_dir in source_dirs:
        source_path = source_dir / "_source.md"
        if not source_path.is_file():
            raise RuntimeError(f"Brak _source.md w {source_dir}")
        metadata, _ = read_source_metadata(source_path)
        knowledges.append(
            sync_knowledge_source(
                source_dir,
                metadata,
                items,
                token,
            )
        )
    return knowledges


def wait_for_file(file_id: str, token: str) -> None:
    for _ in range(90):
        status = request_json(
            "GET", f"/api/v1/files/{file_id}/process/status", token=token
        ) or {}
        state = status.get("status")
        if state == "completed":
            return
        if state in ("failed", "error"):
            raise RuntimeError(
                "Przetwarzanie pliku Knowledge nie powiodło się: "
                f"{file_id}"
            )
        time.sleep(2)
    raise RuntimeError(f"Timeout przetwarzania pliku Knowledge: {file_id}")


def sync_models(
    token: str,
    knowledges: list[dict],
    available_tool_ids: list[str],
) -> None:
    models = []
    for path in sorted((CONFIG_DIR / "custom_models").glob("*.json")):
        config = load_json(path)
        meta = dict(config.get("meta") or {})
        configured_tool_ids = meta.get("toolIds")
        meta["toolIds"] = (
            configured_tool_ids
            if isinstance(configured_tool_ids, list)
            else available_tool_ids
        )
        meta["knowledge"] = knowledges
        config["meta"] = meta
        models.append(config)
    if not models:
        raise RuntimeError(
            "Brak konfiguracji custom modeli w "
            f"{CONFIG_DIR / 'custom_models'}"
        )
    try:
        request_json("POST", "/api/v1/models/import", {"models": models}, token=token)
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:1000]
        raise RuntimeError(
            f"Import modeli HTTP {exc.code}: {detail}"
        ) from exc
    for model in models:
        print(f"Zsynchronizowano custom model: {model['name']}")


def main() -> int:
    wait_for_open_webui()
    token = sign_in()
    available_tool_ids = sync_tools(token)
    knowledges = sync_knowledge_sources(token)
    sync_models(token, knowledges, available_tool_ids)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (HTTPError, URLError, OSError, RuntimeError, KeyError, json.JSONDecodeError) as exc:
        print(f"Bootstrap Open WebUI nie powiódł się: {exc}", file=sys.stderr)
        raise SystemExit(1)
