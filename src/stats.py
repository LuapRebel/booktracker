from datetime import date
from itertools import product

from statistics import mean
from typing import Optional

from schema import Book


class BookStats:
    """Class to generate stats for books read, based on date_completed"""

    def __init__(self, books: list[Book]):
        self.books = books
        self.ymd = [self._get_ymd(book) for book in books if self._get_ymd(book)[0]]

    def _get_ymd(self, book: Book) -> tuple[int, int, int]:
        """Get year, month and days_to_read from all books

        Args:
            book (Book): Book

        Returns:
            tuple[int, int, int]: year, month, and days_to_read. year
                and month are taken from date_completed.
        """
        if book.status == "COMPLETED" and book.date_completed:
            return (
                book.date_completed.year,
                book.date_completed.month,
                book.days_to_read,
            )
        return (0, 0, 0)

    def detailed_stats(self) -> list[dict]:
        """Return monthly stats for every month and year in which a book
        was completed.

        Returns:
            list[dict]: list of returns from the `month_stats` method, corresponding
                to every month and year in which a book was completed.
        """
        yms = {(ymd[0], ymd[1]) for ymd in self.ymd}
        years = {i[0] for i in self.ymd}
        months = range(1, 13)
        all_years_months = set(product(years, months))
        missing = {
            i for i in all_years_months if min(yms) < i < max(yms) and i not in yms
        }
        monthly = [self.month_stats(*ym) for ym in yms]
        for m in missing:
            monthly.append({"year": m[0], "month": m[1], "count": 0, "avg_dtr": 0})
        return sorted(monthly, key=lambda x: (x["year"], x["month"]), reverse=True)

    def month_stats(self, year: int, month: int) -> dict[str, int | Optional[float]]:
        """Calculate monthly stats for books read during a particular month.

        Args:
            year (int): e.g. 2024
            month (int): e.g. 1 (Jan)

        Returns:
            dict[str, int | Optional[float]]: dictionary containing the following
                items:
                `year`, `month`, `count`, `avg_days_to_read` (all calculated by month)
        """
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
            "avg_dtr": avg_days_to_read,
        }

    def year_stats(self, year: int) -> dict[str, int | Optional[float]]:
        """Calculate yearly stats for books read during a particular year.

        Args:
            year (int): e.g. 2024

        Returns:
            dict[str, int | Optional[float]]: dictionary containing the following
                items:
                `year`, `count`, `books_per_month`, `books_per_week`, `avg_days_to_read`
                (all calculated by year)
        """
        books_read = [book for book in self.ymd if book[0] == year]
        count = len(books_read)
        num_months = len({book[1] for book in self.ymd if book[0] == year})
        num_weeks = num_months * 4.33
        # Calculate by day in current year to avoid undercounting incomplete months
        if year == date.today().year:
            days = (date.today() - date(year, 1, 1)).days
            books_per_month = round((count / days) * (364.25 / 12), 2)
            books_per_week = round(count / days, 2) * 7
        else:
            books_per_month = round(count / num_months, 2)
            books_per_week = round(count / num_weeks, 2)
        if count:
            avg_days_to_read = round(mean([book[2] for book in books_read]), 2)
        else:
            avg_days_to_read = None
        return {
            "year": year,
            "count": count,
            "per_month": books_per_month,
            "per_week": books_per_week,
            "avg_dtr": avg_days_to_read,
        }
