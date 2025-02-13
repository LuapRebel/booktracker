from datetime import datetime
from statistics import mean

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
        self.ymd = [self.get_ymd(book) for book in books]

    def get_ymd(self, book: Book) -> Book:
        if book.status == "COMPLETED" and book.date_completed:
            ymd = datetime.fromisoformat(book.date_completed)
            return (
                ymd.year,
                ymd.month,
                book.days_to_read,
            )

    def flatten(self, l: list) -> list:
        out = []
        for item in l:
            if isinstance(item, list):
                out.extend(self.flatten(item))
            else:
                out.append(item)
        return out

    def complete_stats(self) -> list[dict]:
        years = {book[0] for book in self.ymd if book}
        stats = [
            [self.month_stats(year, month) for month in range(1, 13)] for year in years
        ]
        return self.flatten(stats)

    def month_stats(self, year: int, month: int) -> list[dict]:
        books_read = [
            book for book in self.ymd if book and book[0] == year and book[1] == month
        ]
        count = len(books_read)
        if count:
            avg_days_to_read = round(mean([book[2] for book in books_read]), 2)
        else:
            avg_days_to_read = None
        return [
            {
                "year": year,
                "month": month,
                "count": count,
                "avg_days_to_read": avg_days_to_read,
            }
        ]

    def year_stats(self, year: int, complete: bool = False) -> list[dict]:
        books_read = [book for book in self.ymd if book and book[0] == year]
        count = len(books_read)
        if count:
            avg_days_to_read = round(mean([book[2] for book in books_read]), 2)
        else:
            avg_days_to_read = None
        if complete:
            month_stats = [self.month_stats(year, month) for month in range(1, 13)]
            return self.flatten(month_stats)
        return [
            {
                "year": year,
                "count": count,
                "avg_days_to_read": avg_days_to_read,
            }
        ]


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
        with Center(id="complete-stats"):
            yield Label("BookTracker Complete Stats", id="stats-table-complete-label")
            yield DataTable(id="stats-table-complete")
        yield Footer()

    def on_mount(self) -> None:
        # books = load_books()
        complete_stats = BookStats(self.books).complete_stats()
        years = {stat["year"] for stat in complete_stats}
        year_table = self.query_one("#stats-table-year", DataTable)
        year_table_stats = [BookStats(self.books).year_stats(year)[0] for year in years]
        year_table_columns = year_table_stats[0].keys()
        year_table_rows = [stat.values() for stat in year_table_stats]
        year_table.clear(columns=True)
        year_table.add_columns(*year_table_columns)
        year_table.add_rows(year_table_rows)
        year_table.zebra_stripes = True
        complete_columns = complete_stats[0].keys()
        complete_rows = [stat.values() for stat in complete_stats]
        complete_table = self.query_one("#stats-table-complete", DataTable)
        complete_table.clear(columns=True)
        complete_table.add_columns(*complete_columns)
        complete_table.add_rows(complete_rows)
        complete_table.zebra_stripes = True

    def action_push_books(self) -> None:
        self.app.push_screen("books")
