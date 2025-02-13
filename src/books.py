from pydantic import ValidationError
from textual import on
from textual.app import ComposeResult
from textual.containers import Container, Horizontal
from textual.screen import ModalScreen, Screen
from textual.widget import Widget
from textual.widgets import (
    Button,
    DataTable,
    Footer,
    Header,
    Input,
)

from db import db
from schema import Book


def load_books() -> list[Book]:
    cur = db.cursor()
    data = cur.execute("SELECT * FROM books ORDER BY id DESC").fetchall()
    return [Book(**d) for d in data]


class BookAddScreen(ModalScreen):
    """Modal screen to provide inputs to create a new Book"""

    BINDINGS = [
        ("escape", "push_books", "Books"),
    ]

    def compose(self) -> ComposeResult:
        with Container(id="add-screen"):
            yield BookEditWidget()
            yield Button("Submit", id="add")
            yield Footer()

    @on(Button.Pressed, "#add")
    def book_submit_pressed(self):
        inputs = self.query(Input)
        validation_dict = {i.id.replace("-", "_"): i.value for i in inputs}
        try:
            Book(**validation_dict)
        except ValidationError as e:
            for err in e.errors():
                self.notify(f"{err['loc'][0]}: {err['msg']}")
        else:
            cur = db.cursor()
            cur.execute(
                f"INSERT INTO books({", ".join(validation_dict.keys())}) VALUES (?, ?, ?, ?, ?)",
                tuple(validation_dict.values()),
            )
            db.commit()
            for i in inputs:
                i.clear()
            self.app.push_screen("books")

    def action_push_books(self) -> None:
        self.app.push_screen(BookScreen())


class BookEditWidget(Widget):
    """Widget to edit book information. Used in both Add and Edit scenarios."""

    def compose(self) -> ComposeResult:
        with Container(id="book-edit-widget"):
            yield Input(placeholder="Title", id="title")
            yield Input(placeholder="Author (Lastname, First)", id="author")
            yield Input(placeholder="Status (TBR, IN_PROGRESS, COMPLETED)", id="status")
            yield Input(placeholder="Date Started (YYYY-MM-DD)", id="date-started")
            yield Input(placeholder="Date Completed (YYYY-MM-DD)", id="date-completed")


class BookEditScreen(Screen):
    """Modal Screen to provide inputs to edit an existing book"""

    BINDINGS = [
        ("escape", "push_books", "Books"),
    ]

    def __init__(self, cell_value: str) -> None:
        super().__init__()
        self.cell_value = cell_value

    def compose(self) -> ComposeResult:
        yield BookEditWidget()
        yield Button("Submit", id="edit-submit")
        yield Footer()

    def on_mount(self) -> None:
        if self.cell_value:
            cur = db.cursor()
            book = cur.execute(
                "SELECT * FROM books WHERE id=?", (self.cell_value,)
            ).fetchone()
            inputs = self.query(Input)
            for i in inputs:
                if i.id:
                    key = i.id.replace("-", "_")
                    i.value = book.get(key, "")
        else:
            self.app.push_screen(BookScreen())

    def clear_inputs(self) -> None:
        inputs = self.query(Input)
        for i in inputs:
            i.clear()

    @on(Button.Pressed, "#edit-submit")
    def edit_submit_pressed(self):
        inputs = self.query(Input)
        validation_dict = {i.id.replace("-", "_"): i.value for i in inputs}
        try:
            Book(**validation_dict)
            update_values = []
            update_sql = "SET "
            for k, v in validation_dict.items():
                update_sql += f"{k} = ?, "
                update_values.append(v)
            full_sql = f"""
            UPDATE books
            {update_sql[0:-2]}
            WHERE id = {self.cell_value}
            """
            cursor = db.cursor()
            cursor.execute(full_sql, update_values)
            db.commit()
            self.clear_inputs()
        except ValidationError as e:
            self.notify(str(e))
        self.app.push_screen(BookScreen())

    def action_push_books(self) -> None:
        self.clear_inputs()
        self.app.push_screen(BookScreen())


class BookFilterScreen(Screen):
    """Widget to filter books by field and search term"""

    BINDINGS = [
        ("escape", "push_books", "Books"),
        ("e", "push_edit", "Edit"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        yield Horizontal(
            Input(
                placeholder="id, title, author, status, date_started, date_completed",
                id="filter-field",
                classes="column",
            ),
            Input(placeholder="Search term", id="filter-value", classes="column"),
            Button("Submit", id="filter-submit", classes="column"),
            id="filter-container",
        )
        yield DataTable(id="filter-table")
        yield Footer()

    @on(Button.Pressed, "#filter-submit")
    def filter_submit_pressed(self) -> None:
        field = self.query_one("#filter-field", Input).value
        value = self.query_one("#filter-value", Input).value
        if field and value:
            read_sql = f"SELECT * FROM books WHERE {field} LIKE ?"
            binding = (f"%{value}%",)
            cur = db.cursor()
            data = cur.execute(read_sql, binding).fetchall()
            books = [Book(**d) for d in data]
            table = self.query_one("#filter-table", DataTable)
            table.clear(columns=True)
            columns = [*Book.model_fields.keys(), *Book.model_computed_fields.keys()]
            rows = [book.model_dump().values() for book in books]
            table.add_columns(*columns)
            table.add_rows(rows)
            table.zebra_stripes = True
            self.focus_next("#filter-table")
            self.clear_inputs()

    def clear_inputs(self) -> None:
        inputs = self.query(Input)
        for i in inputs:
            i.clear()

    def _on_screen_resume(self) -> None:
        table = self.query_one("#filter-table", DataTable)
        table.clear(columns=True)

    def on_data_table_cell_highlighted(self, event: DataTable.CellHighlighted) -> None:
        self.cell_value = str(event.value) or ""
        self.cell_coordinate = event.coordinate

    def action_push_edit(self) -> None:
        try:
            int(self.cell_value)
        except ValueError:
            pass
        else:
            if self.cell_coordinate.column == 0:
                self.app.push_screen(BookEditScreen(self.cell_value))

    def action_push_books(self) -> None:
        self.clear_inputs()
        self.app.push_screen(BookScreen())


class BookScreen(Screen):
    """Widget to manage book collection."""

    BINDINGS = [
        ("f", "push_filter", "Filter"),
        ("a", "push_add", "Add"),
        ("e", "push_edit", "Edit"),
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

    def action_push_filter(self) -> None:
        self.app.push_screen(BookFilterScreen())

    def action_push_add(self) -> None:
        self.app.push_screen(BookAddScreen())

    def action_push_edit(self) -> None:
        try:
            int(self.cell_value)
        except ValueError:
            pass
        else:
            if self.cell_coordinate.column == 0:
                self.app.push_screen(BookEditScreen(self.cell_value))
