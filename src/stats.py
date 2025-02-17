from datetime import datetime
from statistics import mean
from typing import Optional

from schema import Book


class BookStats:
    """
    Class to generate stats for books read, based on date_completed
    """

    def __init__(self, books: list[Book]):
        self.books = books
        self.ymd = [self._get_ymd(book) for book in books if self._get_ymd(book)[0]]

    def _get_ymd(self, book: Book) -> tuple[int, int, int]:
        if book.status == "COMPLETED" and book.date_completed:
            ymd = datetime.fromisoformat(book.date_completed)
            return (
                ymd.year,
                ymd.month,
                book.days_to_read,
            )
        return (0, 0, 0)

    def detailed_stats(self) -> list[dict]:
        yms = sorted({(ymd[0], ymd[1]) for ymd in self.ymd}, reverse=True)
        return [self.month_stats(*ym) for ym in yms]

    def month_stats(self, year: int, month: int) -> dict[str, int | Optional[float]]:
        books_read = [book for book in self.ymd if book[0] == year and book[1] == month]
        count = len(books_read)
        if count:
            avg_days_to_read = round(mean([book[2] for book in books_read]), 2)
        else:
            avg_days_to_read = None
        return {
            "year": year,
            "month": month,
            "count": count,
            "avg_days_to_read": avg_days_to_read,
        }

    def year_stats(self, year: int) -> dict[str, int | Optional[float]]:
        books_read = [book for book in self.ymd if book[0] == year]
        count = len(books_read)
        num_months = len({book[1] for book in self.ymd if book[0] == year})
        num_weeks = num_months * 4.33
        books_per_month = round(count / num_months, 2)
        books_per_week = round(count / num_weeks, 2)
        if count:
            avg_days_to_read = round(mean([book[2] for book in books_read]), 2)
        else:
            avg_days_to_read = None
        return {
            "year": year,
            "count": count,
            "books_per_month": books_per_month,
            "books_per_week": books_per_week,
            "avg_days_to_read": avg_days_to_read,
        }
