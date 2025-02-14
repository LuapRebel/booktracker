from datetime import datetime
from itertools import product
from statistics import mean
from typing import Optional

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Center
from textual.screen import Screen
from textual.widgets import DataTable, Footer, Header, Label, Rule

from schema import Book


class BookStats:
    """
    Class to generate stats for books read, based on date_completed
    """

    def __init__(self, books: list[Book]):
        self.books = books
        self.ymd = [
            self.get_ymd(book) for book in books if self.get_ymd(book) is not None
        ]

    def get_ymd(self, book: Book) -> Book:
        if book.status == "COMPLETED" and book.date_completed:
            ymd = datetime.fromisoformat(book.date_completed)
            return (
                ymd.year,
                ymd.month,
                book.days_to_read,
            )

    def detailed_stats(self) -> list[dict]:
        years = {book[0] for book in self.ymd}
        months = {book[1] for book in self.ymd}
        return [self.month_stats(*item) for item in product(years, months)]

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


class BookStatsScreen(Screen):
    """Screen to display stats about books read"""

    BINDINGS = [("escape", "push_books", "Books")]

    def __init__(self, books: list[Book]) -> None:
        super().__init__()
        self.books = books

    def compose(self) -> ComposeResult:
        yield Header()
        with Center(id="yearly-stats"):
            yield Label("BookTracker Yearly Stats", id="stats-table-year-label")
            yield DataTable(id="stats-table-year")
        yield Rule(line_style="heavy")
        with Center(id="detailed-stats"):
            yield Label("BookTracker Detailed Stats", id="stats-table-detailed-label")
            yield DataTable(id="stats-table-detailed")
        yield Footer()

    def on_mount(self) -> None:
        detailed_stats = BookStats(self.books).detailed_stats()
        detailed_table = self.query_one("#stats-table-detailed", DataTable)
        detailed_table.clear(columns=True)
        detailed_columns = [
            self._style_table_column(key) for key in detailed_stats[0].keys()
        ]
        detailed_table.add_columns(*detailed_columns)
        detailed_rows = [stat.values() for stat in detailed_stats]
        for row in detailed_rows:
            styled_row = [Text(str(cell), justify="center") for cell in row]
            detailed_table.add_row(*styled_row)
        detailed_table.zebra_stripes = True
        years = {stat["year"] for stat in detailed_stats}
        year_table = self.query_one("#stats-table-year", DataTable)
        year_table.clear(columns=True)
        year_table_stats = [BookStats(self.books).year_stats(year) for year in years]
        year_table_columns = [
            self._style_table_column(key) for key in year_table_stats[0].keys()
        ]
        year_table.add_columns(*year_table_columns)
        year_table_rows = [stat.values() for stat in year_table_stats]
        for row in year_table_rows:
            styled_row = [Text(str(cell), justify="center") for cell in row]
            year_table.add_row(*styled_row)
        year_table.zebra_stripes = True

    def _style_table_column(self, column: str) -> Text:
        padded_title = column.replace("_", " ").title().center(len(column) + 2)
        return Text(padded_title, justify="center")

    def action_push_books(self) -> None:
        self.app.push_screen("books")
