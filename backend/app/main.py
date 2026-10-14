import re
from pathlib import Path
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from fastapi import FastAPI, UploadFile, File, HTTPException
from app.services.chat_parser import parse_chat
from app.db.database import get_connection, initialize_database


app = FastAPI(
    title = "Whatsapp quick link search",
    description = "For self use only",
    version = "1.0"
)


FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"

app.mount(
    "/static",
    StaticFiles(directory=str(FRONTEND_DIR)),
    name="static",
)

@app.get("/", include_in_schema=False)
def serve_frontend():
    return FileResponse(str(FRONTEND_DIR / "index.html"))


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500",
        "http://127.0.0.1:3000",
        "http://localhost:3000",
        "null",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

URL_PATTERN = re.compile(r"https?://[^\s<>\"']+", re.IGNORECASE)

def detect_platform(url: str) -> str:
    from urllib.parse import urlparse

    host = (urlparse(url).hostname or "").lower()
    host = host.removeprefix("www.")

    if host.endswith("youtube.com") or host == "youtu.be":
        return "YouTube"
    if host.endswith("facebook.com") or host == "fb.watch":
        return "Facebook"
    if host.endswith("instagram.com"):
        return "Instagram"

    return "other"

@app.on_event("startup")
def startup():
    initialize_database()

@app.get("/api/health")
def health_check():
    return {"status": "ok"}


@app.get("/")
def home():
    return {"Status" : "Tanzeem"}


@app.post("/api/upload")
async def upload_chat(
    file: UploadFile = File(...),
    group_name: str = "",
):
    if not file.filename or not file.filename.lower().endswith(".txt"):
        raise HTTPException(
            status_code=400,
            detail="Please upload a WhatsApp .txt export.",
        )

    raw_content = await file.read()

    if len(raw_content) > 20 * 1024 * 1024:
        raise HTTPException(
            status_code=413,
            detail="File exceeds the 20 MB upload limit.",
        )

    content = raw_content.decode("utf-8-sig", errors="replace")
    messages = parse_chat(content)

    if not messages:
        raise HTTPException(
            status_code=422,
            detail="No messages recognized. Check the chat export format.",
        )

    inferred_name = group_name.strip() or Path(file.filename).stem

    with get_connection() as connection:
        # Avoid importing the same named chat again.
        existing = connection.execute(
            """
            SELECT id
            FROM chats
            WHERE filename = ? AND group_name = ?
            ORDER BY id
            LIMIT 1
            """,
            (file.filename, inferred_name),
        ).fetchone()

        if existing:
            existing_chat_id = existing["id"]

            existing_links = connection.execute(
                """
                SELECT COUNT(*) AS total
                FROM links
                JOIN messages ON links.message_id = messages.id
                WHERE messages.chat_id = ?
                """,
                (existing_chat_id,),
            ).fetchone()["total"]

            return {
                "chat_id": existing_chat_id,
                "group_name": inferred_name,
                "messages_parsed": len(messages),
                "links_found": existing_links,
                "already_imported": True,
            }

        cursor = connection.execute(
            "INSERT INTO chats (group_name, filename) VALUES (?, ?)",
            (inferred_name, file.filename),
        )
        chat_id = cursor.lastrowid
        link_count = 0

        for index, message in enumerate(messages):
            cursor = connection.execute(
                """
                INSERT INTO messages
                (chat_id, message_index, timestamp, sender, text)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    chat_id,
                    index,
                    message["timestamp"],
                    message["sender"],
                    message["text"],
                ),
            )
            message_id = cursor.lastrowid

            for url in message.get("links", []):
                connection.execute(
                    """
                    INSERT INTO links (message_id, url, platform)
                    VALUES (?, ?, ?)
                    """,
                    (message_id, url, detect_platform(url)),
                )
                link_count += 1

    return {
        "chat_id": chat_id,
        "group_name": inferred_name,
        "messages_parsed": len(messages),
        "links_found": link_count,
        "already_imported": False,
    }

@app.get("/api/search")
def search_chats(
    q: str,
    group_name: str = "",
    platform: str = "",
    limit: int = 50,
):
    query = q.strip()

    if not query:
        raise HTTPException(
            status_code=400,
            detail="Search query cannot be empty.",
        )

    limit = max(1, min(limit, 100))
    results = []

    with get_connection() as connection:
        matches = connection.execute(
            """
            SELECT
                m.id AS message_id,
                m.chat_id,
                m.message_index,
                m.timestamp,
                m.sender,
                m.text,
                c.group_name
            FROM messages m
            JOIN chats c ON c.id = m.chat_id
            WHERE m.text LIKE ? COLLATE NOCASE
              AND (? = '' OR c.group_name LIKE ? COLLATE NOCASE)
            ORDER BY m.timestamp DESC, m.id DESC
            LIMIT ?
            """,
            (
                f"%{query}%",
                group_name,
                f"%{group_name}%",
                limit,
            ),
        ).fetchall()

        for match in matches:
            nearby = connection.execute(
                """
                SELECT DISTINCT
                    l.url,
                    l.platform,
                    m.timestamp AS link_timestamp,
                    m.sender AS link_sender,
                    m.text AS link_message
                FROM messages m
                JOIN links l ON l.message_id = m.id
                WHERE m.chat_id = ?
                  AND m.message_index BETWEEN ? AND ?
                  AND (? = '' OR l.platform = ?)
                ORDER BY m.message_index
                """,
                (
                    match["chat_id"],
                    match["message_index"] - 3,
                    match["message_index"] + 3,
                    platform,
                    platform,
                ),
            ).fetchall()

            results.append({
                "group_name": match["group_name"],
                "timestamp": match["timestamp"],
                "sender": match["sender"],
                "matched_message": match["text"],
                "links": [dict(link) for link in nearby],
            })

    return {
        "query": query,
        "results_count": len(results),
        "results": results,
    }


@app.get("/api/chats")
def list_chats():
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                c.id,
                c.group_name,
                c.filename,
                c.imported_at,
                COUNT(DISTINCT m.id) AS message_count,
                COUNT(DISTINCT l.id) AS link_count
            FROM chats c
            LEFT JOIN messages m ON m.chat_id = c.id
            LEFT JOIN links l ON l.message_id = m.id
            GROUP BY c.id
            ORDER BY c.id DESC
            """
        ).fetchall()

    return [dict(row) for row in rows]
