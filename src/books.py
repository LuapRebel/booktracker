from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import (
    DataTable,
    Footer,
    Header,
)

from db import db
from schema import Book


def load_books() -> list[Book]:
    cur = db.cursor()
    data = cur.execute("SELECT * FROM books ORDER BY id DESC").fetchall()
    return [Book(**d) for d in data]


class BookScreen(Screen):
    """Widget to manage book collection."""

    BINDINGS = [
        # ("f", "push_filter", "Filter"),
        # ("a", "push_add", "Add"),
        # ("e", "push_edit", "Edit"),
        # ("d", "push_delete", "Delete"),
        # ("s", "push_stats", "Stats"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        yield DataTable(id="books-table")
        yield Footer()

    def on_mount(self) -> None:
        books = load_books()
        rows = [book.model_dump().values() for book in books]
        table = self.query_one("#books-table", DataTable)
        table.clear(columns=True)
        columns = [*Book.model_fields.keys(), *Book.model_computed_fields.keys()]
        table.add_columns(*columns)
        table.add_rows(rows)
        table.zebra_stripes = True

    def _on_screen_resume(self) -> None:
        books = load_books()
        rows = [book.model_dump().values() for book in books]
        table = self.query_one("#books-table", DataTable)
        table.clear(columns=True)
        columns = [*Book.model_fields.keys(), *Book.model_computed_fields.keys()]
        table.add_columns(*columns)
        table.add_rows(rows)
        table.zebra_stripes = True

    def on_data_table_cell_highlighted(self, event: DataTable.CellHighlighted) -> None:
        self.cell_value = str(event.value) or ""
        self.cell_coordinate = event.coordinate
