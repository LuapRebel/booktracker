from datetime import datetime
from enum import StrEnum
import re
from typing import Optional, Self


from db import db
from pydantic import BaseModel, computed_field, field_validator, model_validator


class Status(StrEnum):
    TBR = "TBR"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"


class Book(BaseModel, extra="allow"):
    id: Optional[int] = None
    title: str = ""
    author: str = ""
    status: Status = Status.TBR
    date_started: str | None = None
    date_completed: str | None = None

    @field_validator("date_started", "date_completed", mode="before")
    @classmethod
    def validate_date(cls, value: str) -> str:
        if value:
            if re.match("[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
                return value
            else:
                raise ValueError("dates must be formatted as 'YYYY-MM-DD'.")
        return ""

    @model_validator(mode="after")
    def validate_date_completed(self) -> Self:
        if self.date_started and self.date_completed:
            if datetime.fromisoformat(self.date_completed) >= datetime.fromisoformat(
                self.date_started
            ):
                return self
            else:
                raise ValueError("date_completed must be after date_started.")
        return self

    @computed_field  # type: ignore[prop-decorator]
    @property
    def days_to_read(self) -> Optional[int]:
        if self.date_started and self.date_completed:
            ds = datetime.strptime(self.date_started, "%Y-%m-%d")
            dc = datetime.strptime(self.date_completed, "%Y-%m-%d")
            return (dc - ds).days + 1  # inclusive
        else:
            return None

    @classmethod
    def load_books(self) -> list["Book"]:
        cur = db.cursor()
        data = cur.execute("SELECT * FROM books ORDER BY id DESC").fetchall()
        return [Book(**book) for book in data]
