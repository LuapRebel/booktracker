from pydantic import ValidationError
import pytest

from src.schema import Book


def test_valid_book():
    book = Book(
        title="TITLE",
        author="AUTHOR",
        status="TBR",
        date_started="2025-01-01",
        date_completed="2025-01-02",
    )
    assert book.title == "TITLE"
    assert book.author == "AUTHOR"
    assert book.status == "TBR"
    assert book.date_started.isoformat() == "2025-01-01"
    assert book.date_completed.isoformat() == "2025-01-02"
    assert book.days_to_read == 2


def test_book_invalid_status():
    with pytest.raises(ValidationError) as e:
        Book(title="TITLE", author="AUTHOR", status="TB")
        error = e.errors()[0]
        assert error["loc"][0] == "status"
        assert error["msg"] == "Input should be 'TBR', 'IN_PROGRESS' or 'COMPLETED'"


def test_book_invalid_date_started():
    with pytest.raises(ValidationError) as e:
        Book(title="TITLE", author="AUTHOR", status="TBR", date_started="INVALID_DATE")
        error = e.errors()[0]
        assert error["loc"][0] == "date_started"
        assert error["msg"] == "Value error, dates must be formatted as 'YYYY-MM-DD'."


def test_book_invalid_date_completed():
    with pytest.raises(ValidationError) as e:
        Book(
            title="TITLE",
            author="AUTHOR",
            status="TBR",
            date_started="2024-01-01",
            date_completed="INVALID_DATE",
        )
        error = e.errors()[0]
        assert error["loc"][0] == "date_completed"
        assert error["msg"] == "Value error, dates must be formatted as 'YYYY-MM-DD'."


def test_book_date_started_before_date_completed_error():
    with pytest.raises(ValidationError) as e:
        Book(
            title="TITLE",
            author="AUTHOR",
            status="TBR",
            date_started="2024-01-01",
            date_completed="2023-01-01",
        )
        error = e.errors()[0]
        assert error["msg"] == "Value error, date_completed must be after date_started."
