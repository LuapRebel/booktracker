from pathlib import Path
import sqlite3


DB_PATH = Path(__file__).parent.resolve() / "books.db"
CREATE_DB = """
CREATE TABLE IF NOT EXISTS books(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT,
    author TEXT,
    status TEXT,
    date_started TEXT,
    date_completed TEXT
)
"""


def dict_factory(cursor, row):
    fields = [column[0] for column in cursor.description]
    return {k: v for k, v in zip(fields, row)}


if not Path(DB_PATH).is_file():
    db = sqlite3.connect(DB_PATH)
    db.execute(CREATE_DB)
    db.close()

db = sqlite3.connect(DB_PATH)
db.row_factory = dict_factory
