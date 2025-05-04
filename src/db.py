import datetime
from pathlib import Path
import sqlite3
from sqlite3 import Cursor, Row
from typing import Any


DB_PATH = Path(__file__).parent.resolve() / "books.db"
CREATE_STATEMENTS = {
    "create_books": """
    CREATE TABLE IF NOT EXISTS books(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        author TEXT,
        status TEXT,
        date_started DATE,
        date_completed DATE,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """,
    "books_trigger": """
    CREATE TRIGGER update_test_updated_at
        AFTER UPDATE ON books
        WHEN old.updated_at <> current_timestamp
        BEGIN
            UPDATE books
            SET updated_at = CURRENT_TIMESTAMP
            WHERE id = OLD.id;
        END;
    """,
}


def dict_row_factory(cursor: Cursor, row: Row) -> dict[str, Any]:
    """Return database table rows as dictionaries

    Args:
        cursor (Cursor): sqlite3 Connection cursor
        row (Row): sqlite3 Row

    Returns:
        dict[str, Any]: dictionary containing database table row data
    """
    fields = [column[0] for column in cursor.description]
    return {k: v for k, v in zip(fields, row)}


## ADAPTERS
def adapt_date_iso(val):
    """Adapt datetime.date to ISO 8601 date."""
    return val.isoformat()


def adapt_datetime_iso(val):
    """Adapt datetime.datetime to timezone-naive ISO 8601 date."""
    return val.isoformat()


sqlite3.register_adapter(datetime.date, adapt_date_iso)
sqlite3.register_adapter(datetime.datetime, adapt_datetime_iso)


# ## CONVERTERS
def convert_date(val):
    """Convert ISO 8601 date to datetime.date object."""
    return datetime.date.fromisoformat(val.decode())


def convert_datetime(val):
    """Convert ISO 8601 datetime to datetime.datetime object."""
    return datetime.datetime.fromisoformat(val.decode())


sqlite3.register_converter("date", convert_date)
sqlite3.register_converter("datetime", convert_datetime)

if Path(DB_PATH).is_file():
    db = sqlite3.connect(DB_PATH, detect_types=sqlite3.PARSE_DECLTYPES)
    db.row_factory = dict_row_factory


if __name__ == "__main__":
    db = sqlite3.connect(DB_PATH)
    for stmt in CREATE_STATEMENTS.values():
        db.execute(stmt)
    db.close()
