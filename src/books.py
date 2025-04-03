import logging
import re

from pydantic import ValidationError
from rich.text import Text
from textual import on
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, HorizontalGroup
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


logger = logging.getLogger("booktracker")


class BookAddScreen(ModalScreen):
    """Screen to provide inputs to create a new Book"""

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
            logger.info(f"Added book: {validation_dict}")
            self.app.push_screen(BookScreen())

    def action_push_books(self) -> None:
        self.app.push_screen(BookScreen())


class EditableDeletableScreen(Screen):
    """Class containing methods used to take an ID from a DataTable cell
    and use it to get a Book to pass onto an Edit or Delete screen.

    Screens inheriting this class must define a `self.books` attribute before calling
        the `_get_book_from_cell_value` method. BookScreen does this on startup,
        BookFilterScreen does this after searching for books meeting the search
        criteria.
    """

    async def on_data_table_row_highlighted(
        self, event: DataTable.RowHighlighted
    ) -> None:
        row = event.data_table._data[event.row_key]
        self.row_id = tuple(row.values())[0]
        book = await self._get_book_from_row_id()
        if book:
            return book

    async def _get_book_from_row_id(self) -> Book:
        book = [book for book in self.books if book.id == self.row_id][0]
        return book

    async def action_push_edit(self) -> None:
        book: Book = await self._get_book_from_row_id()
        if book:
            self.app.push_screen(BookEditScreen(book))

    async def action_push_delete(self) -> None:
        book: Book = await self._get_book_from_row_id()
        if book:
            self.app.push_screen(BookDeleteScreen(book))


class BookDeleteScreen(ModalScreen):
    """Screen to delete a Book"""

    BINDINGS = [("escape", "push_books", "Books")]

    def __init__(self, book: Book) -> None:
        super().__init__()
        self.book: Book = book

    def compose(self) -> ComposeResult:
        with Container(classes="delete-container", id="book-delete-container"):
            yield Static(self.book.id, id="id-delete")
            yield Button("Delete", id="delete-submit")
            yield Footer()

    def on_mount(self) -> None:
        self.add_class("delete-screen")
        if self.book:
            input = self.query_one("#id-delete", Static)
            input.update(f"Delete {self.book.title}?")
        else:
            self.app.push_screen(self.app.screen_stack[-2])

    @on(Button.Pressed, "#delete-submit")
    def delete_book_pressed(self) -> None:
        def check_delete(delete: bool | None) -> None:
            if delete:
                cur = db.cursor()
                cur.execute("DELETE FROM books WHERE id=?", (self.book.id,))
                db.commit()
                logger.info(f"Deleted book: {self.book.model_dump()}")

        self.app.push_screen(BookDeleteConfirmationScreen(), check_delete)

    def action_push_books(self) -> None:
        self.app.push_screen(BookScreen())


class BookDeleteConfirmationScreen(ModalScreen[bool]):
    """Widget dialog box to query users to delete a book or not"""

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
        if event.button.id == "delete-book-yes":
            self.dismiss(True)
        else:
            self.dismiss(False)
        self.app.push_screen(BookScreen())


class BookEditScreen(EditableDeletableScreen):
    """Screen providing inputs to edit an existing book
    Input fields are automatically filled with data from the Book chosen.
    """

    BINDINGS = [
        ("escape", "app.pop_screen", "Cancel"),
    ]

    def __init__(self, book: Book) -> None:
        super().__init__()
        self.book = book

    def compose(self) -> ComposeResult:
        with Container(
            classes="edit-screen-container", id="book-edit-screen-container"
        ):
            yield Input(placeholder="Title", id="title")
            yield Input(placeholder="Author (Lastname, First)", id="author")
            yield Input(placeholder="Status (TBR, IN_PROGRESS, COMPLETED)", id="status")
            yield Input(
                placeholder="Date Started (YYYY-MM-DD)", id="date-started", value=None
            )
            yield Input(
                placeholder="Date Completed (YYYY-MM-DD)",
                id="date-completed",
                value=None,
            )
            yield Button("Submit", id="edit-submit")
            yield Footer()

    def on_mount(self) -> None:
        self.add_class("edit-screen")
        if self.book:
            inputs = self.query(Input)
            for i in inputs:
                if i.id:
                    key = i.id.replace("-", "_")
                    value = self.book.model_dump().get(key, "")
                    if value:
                        i.value = str(value)
        else:
            self.app.push_screen(BookScreen())

    def clear_inputs(self) -> None:
        inputs = self.query(Input)
        for i in inputs:
            i.clear()

    @on(Button.Pressed, "#edit-submit")
    def edit_submit_pressed(self):
        inputs = self.query(Input)
        validation_dict = {"id": self.book.id}
        for input in inputs:
            if input.id:
                key = input.id.replace("-", "_")
                validation_dict[key] = input.value
        try:
            Book(**validation_dict)
        except ValidationError as e:
            for error in e.errors():
                self.notify(f"{error['loc'][0]}: {error['msg']}")
        else:
            sql_prefix = "UPDATE books SET"
            sql_keys = ", ".join([f"{k} = ?" for k in validation_dict.keys()])
            sql_suffix = f"WHERE id = {self.book.id}"
            full_sql = f"{sql_prefix} {sql_keys} {sql_suffix}"
            sql_values = tuple(validation_dict.values())
            cursor = db.cursor()
            cursor.execute(full_sql, sql_values)
            db.commit()
            logger.info(f"Edited book: {self.book.model_dump()} -> {validation_dict}")
            self.clear_inputs()
        finally:
            self.app.push_screen(BookScreen())

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
        with Container(classes="stats-container"):
            yield Header()
            with Horizontal(id="stats-yearly-container"):
                yield DataTable(classes="stats-table", id="stats-yearly-table")
            with Horizontal(id="stats-detailed-container"):
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


class BookScreen(EditableDeletableScreen):
    """Widget to manage book collection."""

    BINDINGS = [
        ("a", "push_add", "Add"),
        ("e", "push_edit", "Edit"),
        ("d", "push_delete", "Delete"),
        ("s", "push_stats", "Stats"),
    ]

    def compose(self) -> ComposeResult:
        with Container(id="books-container"):
            yield Header()
            with Container(id="books-filter-input-group-container"):
                with HorizontalGroup(
                    classes="filter-input-group", id="books-filter-input-group"
                ):
                    for field in [
                        "title",
                        "author",
                        "status",
                        "date_started",
                        "date_completed",
                    ]:
                        yield Input(
                            placeholder=field.replace("_", " ").title(),
                            classes="filter-search",
                            id=f"filter-{field}-search",
                        )
            with Container(id="books-table-container"):
                yield DataTable(id="books-table")
            yield Footer()

    async def on_mount(self) -> None:
        self.books = await Book.load_books()
        self.add_class("class-screen")
        self._create_books_table(self.books)
        self.set_focus(self.query_one("#books-table", DataTable))

    def _create_books_table(self, books: list[Book]) -> None:
        table = self.query_one("#books-table", DataTable)
        table.cursor_type = "row"
        table.clear(columns=True)
        columns = [*Book.model_fields.keys(), *Book.model_computed_fields.keys()]
        table.add_columns(*columns)
        rows = [book.model_dump().values() for book in books]
        table.add_rows(rows)
        table.zebra_stripes = True

    async def filter_books(self, field: str, search_term: str) -> list[Book]:
        if field and search_term:
            read_sql = f"SELECT * FROM books WHERE {field} LIKE ?"
            binding = (f"%{search_term}%",)
            cur = db.cursor()
            data = cur.execute(read_sql, binding).fetchall()
            if data is not None:
                return [Book(**d) for d in data]
        return self.books

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id is not None:
            field = re.sub("^filter-|-search$", "", event.input.id).replace("-", "_")
            search_term = event.input.value
            filtered_data = await self.filter_books(field, search_term)
            self._create_books_table(filtered_data)

    def action_push_add(self) -> None:
        self.app.push_screen(BookAddScreen())

    def action_push_stats(self) -> None:
        self.app.push_screen(BookStatsScreen(self.books))
