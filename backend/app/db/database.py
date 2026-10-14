import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[2] / "smart_search.db"


def get_connection():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection

def initialize_database():
    with get_connection() as connection:
        connection.execute("""
        CREATE TABLE IF NOT EXISTS chats (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        group_name TEXT NOT NULL,
        filename TEXT NOT NULL,
        imported_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """)

        connection.execute("""
           CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER NOT NULL,
                message_index INTEGER NOT NULL,
                timestamp TEXT,
                sender TEXT,
                text TEXT NOT NULL,
                FOREIGN KEY(chat_id) REFERENCES chats(id)
                ON DELETE CASCADE
            )
        """)

        connection.execute("""
            CREATE TABLE IF NOT EXISTS links (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message_id INTEGER NOT NULL,
                url TEXT NOT NULL,
                platform TEXT,
                FOREIGN KEY(message_id) REFERENCES messages(id)
                ON DELETE CASCADE
            )
        """)

        connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_messages_chat
            ON messages(chat_id, message_index)
        """)

        connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_links_message
            ON links(message_id)
        """)
