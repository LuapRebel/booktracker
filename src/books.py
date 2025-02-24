from pydantic import ValidationError
from rich.text import Text
from textual import on
from textual.app import ComposeResult
from textual.containers import Container, HorizontalGroup
from textual.screen import ModalScreen, Screen
from textual.widgets import (
    Button,
    DataTable,
    Footer,
    Header,
    Input,
    Select,
    Static,
)

from db import db
from schema import Book
from stats import BookStats


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
        with Container(classes="add-screen-container", id="add-screen-container"):
            yield Input(placeholder="Title", id="title")
            yield Input(placeholder="Author (Lastname, First)", id="author")
            yield Input(placeholder="Status (TBR, IN_PROGRESS, COMPLETED)", id="status")
            yield Input(placeholder="Date Started (YYYY-MM-DD)", id="date-started")
            yield Input(placeholder="Date Completed (YYYY-MM-DD)", id="date-completed")
            yield Button("Submit", id="add")
            yield Footer()

    def on_mount(self) -> None:
        self.add_class("add-screen")

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


class BookDeleteScreen(ModalScreen):
    """Screen to delete a Book given an ID"""

    BINDINGS = [("escape", "push_books", "Books")]

    def __init__(self, cell_value: str) -> None:
        super().__init__()
        self.cell_value = cell_value

    def compose(self) -> ComposeResult:
        with Container(classes="delete-container", id="book-delete-container"):
            yield Input(placeholder="ID", id="id-delete")
            yield Button("Delete", id="delete-submit")
            yield Footer()

    def on_mount(self) -> None:
        self.add_class("delete-screen")
        if self.cell_value:
            cur = db.cursor()
            book = cur.execute(
                "SELECT * FROM books WHERE id=?", (self.cell_value,)
            ).fetchone()
            input = self.query_one("#id-delete", Input)
            input.value = str(book.get("id", ""))
        else:
            self.app.push_screen(BookScreen())

    @on(Button.Pressed, "#delete-submit")
    def delete_book_pressed(self) -> None:
        def check_delete(delete: bool | None) -> None:
            if delete:
                cur.execute("DELETE FROM books WHERE id=?", (id.value,))
                db.commit()
            id.clear()

        id = self.query_one("#id-delete", Input)
        value = id.value
        cur = db.cursor()
        book = cur.execute("SELECT * FROM books WHERE id=?", (value,)).fetchone()
        if not book:
            self.notify(f"There is no book with ID = {value}")
            id.clear()
            self.app.push_screen(BookDeleteScreen(value))
        else:
            self.app.push_screen(BookDeleteConfirmationScreen(), check_delete)

    def action_push_books(self) -> None:
        self.app.push_screen(BookScreen())


class BookDeleteConfirmationScreen(ModalScreen[bool]):
    """Widget providing dialog box to allow users to delete a book or cancel"""

    BINDINGS = [("escape", "app.pop_screen", "Cancel")]

    def compose(self) -> ComposeResult:
        with Container(
            classes="delete-confirmation-container",
            id="book-delete-confirmation-container",
        ):
            yield Static("Are you sure you want to delete?")
            with HorizontalGroup(id="book-delete-confirmation-button"):
                yield Button("Yes", id="delete-book-yes")
                yield Button("No", id="delete-book-no")
            yield Footer()

    def on_mount(self) -> None:
        self.add_class("delete-confirmation-screen")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "delete-book":
            self.dismiss(True)
        else:
            self.dismiss(False)
        self.app.push_screen(BookScreen())


class BookEditScreen(Screen):
    """Modal Screen to provide inputs to edit an existing book"""

    BINDINGS = [
        ("escape", "push_books", "Books"),
    ]

    def __init__(self, cell_value: str) -> None:
        super().__init__()
        self.cell_value = cell_value

    def compose(self) -> ComposeResult:
        with Container(
            classes="edit-screen-container", id="book-edit-screen-container"
        ):
            yield Input(placeholder="Title", id="title")
            yield Input(placeholder="Author (Lastname, First)", id="author")
            yield Input(placeholder="Status (TBR, IN_PROGRESS, COMPLETED)", id="status")
            yield Input(placeholder="Date Started (YYYY-MM-DD)", id="date-started")
            yield Input(placeholder="Date Completed (YYYY-MM-DD)", id="date-completed")
            yield Button("Submit", id="edit-submit")
        yield Footer()

    def on_mount(self) -> None:
        self.add_class("edit-screen")
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
        with HorizontalGroup(
            classes="filter-input-group", id="book-filter-input-group-container"
        ):
            yield Select.from_values(
                values=Book.model_fields.keys(),
                prompt="Column",
                id="book-filter-field",
                classes="filter-field",
            )
            yield Input(
                placeholder="Search term",
                classes="filter-value",
                id="book-filter-value",
            )
            yield Button("Submit", id="book-filter-submit")
        with Container(
            classes="filter-table-container", id="book-filter-table-container"
        ):
            yield DataTable(classes="filter-table", id="book-filter-table")
        yield Footer()

    def on_mount(self) -> None:
        self.add_class("filter-screen")

    @on(Button.Pressed, "#book-filter-submit")
    def filter_submit_pressed(self) -> None:
        field = self.query_one("#book-filter-field", Select).value
        value = self.query_one("#book-filter-value", Input).value
        if field and value:
            read_sql = f"SELECT * FROM books WHERE {field} LIKE ?"
            binding = (f"%{value}%",)
            cur = db.cursor()
            data = cur.execute(read_sql, binding).fetchall()
            books = [Book(**d) for d in data]
            table = self.query_one("#book-filter-table", DataTable)
            table.clear(columns=True)
            columns = [*Book.model_fields.keys(), *Book.model_computed_fields.keys()]
            rows = [book.model_dump().values() for book in books]
            table.add_columns(*columns)
            table.add_rows(rows)
            table.zebra_stripes = True
            self.focus_next("#book-filter-table")
            self.clear_inputs()

    def clear_inputs(self) -> None:
        inputs = self.query(Input)
        for i in inputs:
            i.clear()

    def _on_screen_resume(self) -> None:
        table = self.query_one("#book-filter-table", DataTable)
        table.clear(columns=True)

    def on_data_table_cell_highlighted(self, event: DataTable.CellHighlighted) -> None:
        self.cell_value = str(event.value)
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


class BookStatsScreen(Screen):
    """Screen to display stats about books read"""

    BINDINGS = [("escape", "push_books", "Books")]

    def __init__(self, books: list[Book]) -> None:
        super().__init__()
        self.books = books
        self.stats = BookStats(self.books)

    def compose(self) -> ComposeResult:
        with Container(classes="stats-table-container"):
            yield Header()
            yield DataTable(classes="stats-table", id="stats-yearly-table")
            yield DataTable(classes="stats-table", id="stats-detailed-table")
            yield Footer()

    def on_mount(self) -> None:
        self.add_class("stats-screen")
        self._create_yearly_stats_table()
        self._create_detailed_stats_table()

    def _style_table_column(self, column: str) -> Text:
        padded_title = column.replace("_", " ").title().center(len(column) + 2)
        return Text(padded_title, justify="center")

    def _generate_formatted_table(self, table: DataTable, stats: list[dict]) -> None:
        table.clear(columns=True)
        columns = [self._style_table_column(key) for key in stats[0].keys()]
        table.add_columns(*columns)
        rows = [stat.values() for stat in stats]
        for row in rows:
            styled_row = [Text(str(cell), justify="center") for cell in row]
            table.add_row(*styled_row)
        table.zebra_stripes = True

    def _create_detailed_stats_table(self) -> None:
        table = self.query_one("#stats-detailed-table", DataTable)
        table.border_title = "BookTracker Yearly Stats"
        stats = self.stats.detailed_stats()
        self._generate_formatted_table(table, stats)

    def _create_yearly_stats_table(self) -> None:
        table = self.query_one("#stats-yearly-table", DataTable)
        table.border_title = "BookTracker Detailed Stats"
        years = sorted(
            {stat["year"] for stat in self.stats.detailed_stats()}, reverse=True
        )
        stats = [self.stats.year_stats(year) for year in years]
        self._generate_formatted_table(table, stats)

    def action_push_books(self) -> None:
        self.app.push_screen(BookScreen())


class BookScreen(Screen):
    """Widget to manage book collection."""

    BINDINGS = [
        ("f", "push_filter", "Filter"),
        ("a", "push_add", "Add"),
        ("e", "push_edit", "Edit"),
        ("d", "push_delete", "Delete"),
        ("s", "push_stats", "Stats"),
    ]

    def compose(self) -> ComposeResult:
        with Container(id="books-container"):
            yield Header()
            with Container(id="books-table-container"):
                yield DataTable(classes="class-table", id="books-table")
            yield Footer()

    def on_mount(self) -> None:
        self.books = load_books()
        self.add_class("class-screen")
        self._create_books_table()

    def _on_screen_resume(self) -> None:
        self._create_books_table()

    def _create_books_table(self) -> None:
        table = self.query_one("#books-table", DataTable)
        table.clear(columns=True)
        columns = [*Book.model_fields.keys(), *Book.model_computed_fields.keys()]
        table.add_columns(*columns)
        rows = [book.model_dump().values() for book in self.books]
        table.add_rows(rows)
        table.zebra_stripes = True

    def on_data_table_cell_highlighted(self, event: DataTable.CellHighlighted) -> None:
        self.cell_value = str(event.value)
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

    def action_push_delete(self) -> None:
        try:
            int(self.cell_value)
        except ValueError:
            pass
        else:
            if self.cell_coordinate.column == 0:
                self.app.push_screen(BookDeleteScreen(self.cell_value))

    def action_push_stats(self) -> None:
        self.app.push_screen(BookStatsScreen(self.books))
