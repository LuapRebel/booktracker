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


class Book(BaseModel, extra="ignore"):
    id: Optional[int] = None
    title: str = ""
    author: str = ""
    status: Status = Status.TBR
    date_started: str = ""
    date_completed: str = ""

    @field_validator("date_started", "date_completed", mode="before")
    @classmethod
    def validate_date(cls, value: str) -> str:
        """Validate date inputs to verify they are formatted YYYY-MM-DD

        Args:
            value (str): Date in YYYY-MM-DD

        Raises:
            ValueError: raises an error if dates are not formatted YYYY-MM-DD

        Returns:
            str: Will return original date string if formatted properly or an empty
            string if no value is entered. If not formatted properly, a ValueError
            will be raised.
        """
        if value:
            if re.match("[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
                return value
            else:
                raise ValueError("dates must be formatted as 'YYYY-MM-DD'.")
        return ""

    @model_validator(mode="after")
    def validate_date_completed(self) -> Self:
        """Validate that if date_completed is entered, it is after date_started.

        Raises:
            ValueError: raised if date_completed is before date_started.
                They can be the same.

        Returns:
            Self: Returns original model instance if successful. If not,
                a ValueError is raised.
        """
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
        """Calculates number of days it took to complete a book.

        Returns:
            Optional[int]: Number of days to read a book. If a book has
                date_started and date_completed on the same day, 1 is returned.
        """
        if self.date_started and self.date_completed:
            ds = datetime.strptime(self.date_started, "%Y-%m-%d")
            dc = datetime.strptime(self.date_completed, "%Y-%m-%d")
            return (dc - ds).days + 1  # inclusive
        else:
            return None

    @classmethod
    async def load_books(self) -> list["Book"]:
        """Load Book data from database and create a Book object for each row.

        Returns:
            list[Book]: list of Book objects from the database.
        """
        cur = db.cursor()
        data = cur.execute("SELECT * FROM books ORDER BY id DESC").fetchall()
        return [Book(**book) for book in data]
