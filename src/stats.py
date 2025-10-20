from collections import Counter
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

    def _get_ymd(self, book: Book) -> tuple[int, int, int | None]:
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

    def monthly_stats(self) -> list[dict]:
        """Report monthly stats by year and month. Months where no books were
         read will have a count and averages of 0.

        Returns:
            list[dict]: list of returns from the `month_stats` method, corresponding
                to every month and year.
        """
        yms = {(ymd[0], ymd[1]) for ymd in self.ymd}
        years = {i[0] for i in self.ymd}
        monthly = [self.month_stats(*ym) for ym in yms]
        # Add row for months where no books were completed
        months = range(1, 13)
        all_years_months = set(product(years, months))
        missing = {
            i for i in all_years_months if min(yms) < i < max(yms) and i not in yms
        }
        for m in missing:
            monthly.append(
                {
                    "year": m[0],
                    "month": m[1],
                    "per_week": 0,
                    "count": 0,
                    "avg_dtr": "",
                }
            )
        return sorted(monthly, key=lambda x: (x["year"], x["month"]), reverse=True)

    def month_stats(
        self, year: int, month: int
    ) -> dict[str, int | Optional[float] | str]:
        """Calculate monthly stats for books read during a particular month.

        Args:
            year (int): e.g. 2024
            month (int): e.g. 1 (Jan)

        Returns:
            dict[str, int | Optional[float]]: dictionary containing the following
                items:
                `year`, `month`, `count`, per_week`, `avg_days_to_read` (all calculated by month)
        """
        books_read = [book for book in self.ymd if book[0] == year and book[1] == month]
        if books_read:
            books_w_avg_days_to_read = [book[2] for book in books_read]
            if all(books_w_avg_days_to_read):
                avg_days_to_read = round(mean(books_w_avg_days_to_read), 2)
            else:
                avg_days_to_read = ""
        else:
            avg_days_to_read = ""
        count = len(books_read)
        return {
            "year": year,
            "month": month,
            "count": count,
            "per_week": round(count / 4.3363, 2),
            "avg_days_to_read": avg_days_to_read,
        }

    def yearly_stats(self) -> list[dict[str, int | Optional[float]]]:
        """Report stats by year. Years where no books were
         read will have a count and averages of 0.

        Returns:
            list[dict]: list of returns from the `year_stats` method, corresponding
                to every month and year.
        """
        years = {i[0] for i in self.ymd}
        return sorted(
            [self.year_stats(year) for year in years],
            key=lambda x: x["year"],  # type: ignore
            reverse=True,
        )

    def year_stats(self, year: int) -> dict[str, int | Optional[float] | str]:
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
        if books_read:
            count = len(books_read)
            # Calculate by day in current year to avoid undercounting incomplete months
            if year == date.today().year:
                days = (date.today() - date(year, 1, 1)).days
                books_per_month = round((count / days) * (364.25 / 12), 2)
                books_per_week = round((count / days) * 7, 2)
            else:
                months = len({book[1] for book in self.ymd if book[0] == year})
                weeks = months * 4.33
                books_per_month = round(count / months, 2)
                books_per_week = round(count / weeks, 2)
            if count:
                avgs = [book[2] for book in books_read if book[2]]
                if avgs:
                    avg_days_to_read = round(mean(avgs), 2)
                else:
                    avg_days_to_read = ""
            else:
                avg_days_to_read = ""
        else:
            count, books_per_month, books_per_week, avg_days_to_read = "", "", "", ""
        return {
            "year": year,
            "count": count,
            "per_month": books_per_month,
            "per_week": books_per_week,
            "avg_days_to_read": avg_days_to_read,
        }

    def _get_total_books(self) -> int:
        return len([book for book in self.books if book.status == "COMPLETED"])

    def _get_max_year(self) -> tuple[int, ...]:
        stats_available = any([all(s) for s in self.yearly_stats()])
        if stats_available:
            max_year = sorted(
                self.yearly_stats(), key=lambda x: x["count"], reverse=True  # type: ignore
            )[0]
            return max_year["year"], max_year["count"]  # type: ignore
        else:
            return 0, 0

    def _get_max_year_month(self) -> tuple[int, int, int]:
        stats_available = any([all(s) for s in self.monthly_stats()])
        if stats_available:
            max_year_month = sorted(
                self.monthly_stats(), key=lambda x: x["count"], reverse=True
            )[0]
            return (
                max_year_month["year"],
                max_year_month["month"],
                max_year_month["count"],
            )
        else:
            return 0, 0, 0

    def _get_top_authors(self) -> list[tuple[str, int]]:
        """Returns Top 20 Authors by count."""
        authors = [book.author for book in self.books if book.author]
        author_count = Counter(authors)
        return author_count.most_common(20)
