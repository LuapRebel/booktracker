import calendar
import csv
from datetime import date, timedelta
import json
import logging
import os
from pathlib import Path
import re
from typing import Iterable

from pydantic import ValidationError
from rich.text import Text
from textual import on
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, HorizontalGroup, Vertical
from textual.screen import ModalScreen, Screen
from textual.widgets import (
    Button,
    DataTable,
    DirectoryTree,
    Footer,
    Header,
    Input,
    Label,
    Markdown,
    RadioButton,
    RadioSet,
    RichLog,
    Select,
    Static,
)

from db import db
from schema import Book, Status
from stats import BookStats


logger = logging.getLogger("booktracker")


class MonthlyBookScreen(ModalScreen):
    """Screen to display books read during a particular month chosen
    from the Monthly Stats table.
    """

    BINDINGS = [("escape", "app.pop_screen", "Cancel")]

    def __init__(self, year: str, month: str, books: list[Book]) -> None:
        super().__init__()
        self.year = year
        self.month = calendar.month_name[int(month)]
        self.books = books

    def compose(self) -> ComposeResult:
        yield DataTable(id="monthly-books")
        yield Footer()

    def on_mount(self) -> None:
        self._create_table()

    def _create_table(self) -> None:
        table = self.query_one("#monthly-books", DataTable)
        table.border_title = f"{self.month} {self.year}: {len(self.books)} Books Read"
        table.clear(columns=True)
        column_info = {"Author": 30, "Title": 50, "Days to Read": 12}
        for column, width in column_info.items():
            table.add_column(label=column, width=width, key=column)
        rows = [dict(book.model_dump().items()) for book in self.books]
        for row in rows:
            r = (row["author"], row["title"], row["days_to_read"])
            table.add_row(*r)
        table.cursor_type = "none"


class BookAddScreen(ModalScreen):
    """Screen to provide inputs to create a new Book"""

    BINDINGS = [
        ("escape", "push_books", "Books"),
    ]

    def compose(self) -> ComposeResult:
        add_screen_container = Container(
            classes="add-screen-container", id="add-screen-container"
        )
        add_screen_container.border_title = "Add A Book"
        with add_screen_container:
            yield Input(placeholder="Title", id="title")
            yield Input(placeholder="Author (Lastname, First)", id="author")
            yield Select.from_values(
                values=Status._member_names_,
                prompt="Status",
                allow_blank=False,
                value=Status.TBR,
                id="status",
            )
            yield Input(placeholder="Date Started (YYYY-MM-DD)", id="date-started")
            yield Input(placeholder="Date Completed (YYYY-MM-DD)", id="date-completed")
            yield Button("Submit", id="add")
            yield Footer()

    @on(Button.Pressed, "#add")
    def book_submit_pressed(self):
        inputs = self.query(Input)
        status = self.query_one(Select)
        validation_dict = {i.id.replace("-", "_"): i.value for i in inputs}
        validation_dict[status.id] = status.value
        try:
            Book(**validation_dict)
        except ValidationError as e:
            for err in e.errors():
                self.notify(f"{err['loc'][0]}: {err['msg']}")
        else:
            cur = db.cursor()
            newbook = cur.execute(
                f"INSERT INTO books({", ".join(validation_dict.keys())}) VALUES (?, ?, ?, ?, ?) RETURNING *",
                tuple(validation_dict.values()),
            ).fetchone()
            db.commit()
            for i in inputs:
                i.clear()
            logger.info(f"Added: {newbook}")
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

    async def on_mount(self) -> None:
        self.books = await Book.load_books()
        self.stats = BookStats(self.books)

    async def on_data_table_row_highlighted(
        self, event: DataTable.RowHighlighted
    ) -> None:
        if event.data_table.id == "books-table":
            row = event.data_table._data[event.row_key]
            self.row_id = tuple(row.values())[-1]
            book = await self._get_book_from_row_id()
            if book:
                return book

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        if event.data_table.id == "stats-monthly-table":
            row = event.data_table._data[event.row_key]
            year, month = tuple(row.values())[0:2]
            books = [
                book
                for book in self.books
                if book.date_completed
                and book.date_completed.year == int(year.plain)
                and book.date_completed.month == int(month.plain)
            ]
            if books:
                self.app.push_screen(MonthlyBookScreen(year.plain, month.plain, books))

    async def _get_book_from_row_id(self) -> Book:
        book = [book for book in self.books if book.id == self.row_id]
        if book:
            return book[0]

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
                deletedbook = cur.execute(
                    "DELETE FROM books WHERE id=? RETURNING *", (self.book.id,)
                ).fetchone()
                db.commit()
                logger.info(f"Deleted: {deletedbook}")

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
        edit_screen_container = Container(
            classes="edit-screen-container", id="book-edit-screen-container"
        )
        edit_screen_container.border_title = "Edit Book"
        with edit_screen_container:
            yield Input(placeholder="Title", id="title")
            yield Input(placeholder="Author (Lastname, First)", id="author")
            yield Select.from_values(
                values=Status._member_names_,
                prompt="Status",
                allow_blank=False,
                value=Status.TBR,
                id="status",
            )
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

    def on_mount(self):
        if self.book:
            inputs = self.query(Input)
            for i in inputs:
                if i.id:
                    key = i.id.replace("-", "_")
                    value = self.book.model_dump().get(key, "")
                    if value:
                        i.value = str(value)
            status = self.query_one(Select)
            status.value = str(self.book.model_dump().get(status.id, ""))
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
        status = self.query_one(Select)
        validation_dict[status.id] = str(status.value)
        try:
            Book(**validation_dict)
        except ValidationError as e:
            for error in e.errors():
                self.notify(f"{error['loc'][0]}: {error['msg']}")
        else:
            sql_prefix = "UPDATE books SET"
            sql_keys = ", ".join([f"{k} = ?" for k in validation_dict.keys()])
            sql_suffix = f"WHERE id = {self.book.id}"
            full_sql = f"{sql_prefix} {sql_keys} {sql_suffix} RETURNING *"
            sql_values = tuple(validation_dict.values())
            cursor = db.cursor()
            editedbook = cursor.execute(full_sql, sql_values).fetchone()
            db.commit()
            logger.info(f"Edited: {self.book.model_dump()} -> {editedbook}")
            self.clear_inputs()
        finally:
            self.app.push_screen(BookScreen())

    def action_push_books(self) -> None:
        self.clear_inputs()
        self.app.push_screen(BookScreen())


class BookScreen(EditableDeletableScreen):
    """Widget to manage book collection."""

    BINDINGS = [
        ("a", "push_add", "Add"),
        ("e", "push_edit", "Edit"),
        ("d", "push_delete", "Delete"),
        ("x", "export_data", "Export Book Data"),
        ("l", "push_logs", "Logs"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            with Vertical(id="books-container"):
                yield Static("Books", id="books-container-header")
                with Vertical(id="books-filter-input-group-container"):
                    filter_group = HorizontalGroup(
                        classes="filter-input-group", id="books-filter-input-group"
                    )
                    filter_group.border_title = "Filter Books"
                    with filter_group:
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
            with Vertical(id="stats-container"):
                yield Static("Stats", id="stats-container-header")
                with Container(id="stats-table-container"):
                    with Container(id="stats-max-container"):
                        with HorizontalGroup(id="stats-max-horizontal-group"):
                            max_year = Static("", id="stats-max-year")
                            max_year.border_title = "Max Yearly Count"
                            max_year_month = Static("", id="stats-max-year-month")
                            max_year_month.border_title = "Max Monthly Count"
                            yield max_year
                            yield max_year_month
                    with Container(id="stats-yearly-table-container"):
                        yield DataTable(classes="stats-table", id="stats-yearly-table")
                    with Container(id="stats-monthly-table-container"):
                        yield DataTable(classes="stats-table", id="stats-monthly-table")
        yield Footer()

    async def on_mount(self) -> None:
        await super().on_mount()
        if not self.books:
            self.notify("To Add a Book, Press 'a'", severity="warning", timeout=20)
        self._create_books_table(self.books)
        self._create_stats_table("#stats-monthly-table", self.stats.monthly_stats())
        self._create_stats_table("#stats-yearly-table", self.stats.yearly_stats())
        self._create_max_data()
        self.set_focus(self.query_one("#books-table", DataTable))

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
            self.set_focus(self.query_one("#books-table", DataTable))

    def action_push_add(self) -> None:
        self.app.push_screen(BookAddScreen())

    def action_export_data(self) -> None:
        self.app.push_screen(ExportScreen())

    def action_push_logs(self) -> None:
        self.app.push_screen(LogScreen())

    def _create_books_table(self, books: list[Book]) -> None:
        def datesort(row_data):
            future_date = date.today() + timedelta(365)
            dates = tuple(d if d else future_date for d in row_data[-2:])
            return dates

        table = self.query_one("#books-table", DataTable)
        table.clear(columns=True)
        columns = [*Book.model_fields.keys(), *Book.model_computed_fields.keys()]
        columns = columns[1:] + [columns[0]]  # move id to the end
        widths = {"title": 35, "author": 25}
        for column in columns:
            if column in widths:
                width = widths[column]
            else:
                width = None
            label = column.replace("_", " ").title()
            table.add_column(label=label, width=width, key=column)
        if self.books:
            rows = [list(book.model_dump().values()) for book in books]
            for row in rows:
                r = row[1:] + [row[0]]  # move id to the end
                table.add_row(*r)
            table.sort("date_started", "date_completed", key=datesort, reverse=True)
        table.cursor_type = "row"
        table.zebra_stripes = True

    def _create_max_data(self) -> None:
        max_year = self.query_one("#stats-max-year", Static)
        max_year_year, max_year_count = self.stats._get_max_year()
        max_year.update(f"{max_year_year}: {max_year_count}")
        max_year_month = self.query_one("#stats-max-year-month", Static)
        max_year_month_year, max_year_month_month, max_year_month_count = (
            self.stats._get_max_year_month()
        )
        max_year_month.update(
            f"{calendar.month_name[int(max_year_month_month)]} {max_year_month_year}: {max_year_month_count}"
        )

    def _create_stats_table(self, id: str, data: list[dict]) -> None:
        border_titles = {
            "#stats-monthly-table": "Monthly Stats",
            "#stats-yearly-table": "Yearly Stats",
        }
        table_columns = {
            "#stats-monthly-table": [
                "Year",
                "Month",
                "Count",
                "Per Week",
                "Avg Days to Read",
            ],
            "#stats-yearly-table": [
                "Year",
                "Count",
                "Per Month",
                "Per Week",
                "Avg Days to Read",
            ],
        }
        table = self.query_one(id, DataTable)
        table.clear(columns=True)
        columns = table_columns[id]
        table.add_columns(*columns)
        if data:
            rows = [stat.values() for stat in data]
            for row in rows:
                styled_row = [Text(str(cell), justify="center") for cell in row]
                table.add_row(*styled_row)
        table.border_title = border_titles[id]
        table.cursor_type = "row"
        table.zebra_stripes = True


class LogScreen(ModalScreen):
    """Screen to display logs file in RichLog"""

    BINDINGS = [("escape", "app.pop_screen", "Cancel")]

    def __init__(self) -> None:
        super().__init__()
        self.logs = self._read_logs()

    def compose(self) -> ComposeResult:
        yield Markdown("# Logs")
        yield RichLog(wrap=True, highlight=True, markup=True, id="log-screen")
        yield Footer()

    def on_mount(self) -> None:
        if self.logs:
            richlog = self.query_one(RichLog)
            for log in self.logs:
                richlog.write(log)

    def _read_logs(self) -> list[str]:
        with open("logs/booktracker.log") as f:
            logs = f.readlines()
        return logs


class FilteredDirectoryTree(DirectoryTree):
    def filter_paths(self, paths: Iterable[Path]) -> Iterable[Path]:
        return [path for path in paths if not path.name.startswith(".")]


class ExportScreen(ModalScreen):
    """Screen providing interface for users to export book data in csv or json"""

    BINDINGS = [("escape", "app.pop_screen", "Cancel")]

    def __init__(
        self,
        root=f"/home/{os.environ.get("USER")}",
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(name, id, classes)
        self.title = "Save File"
        self.root = root
        self.folder = root

    def compose(self) -> ComposeResult:
        """
        Create the widgets for the SaveFileDialog's user interface
        """
        yield Container(
            Header(),
            Label(f"Folder name: {self.root}", id="folder"),
            FilteredDirectoryTree(self.root, id="directory"),
            Input(placeholder="Filename", id="filename"),
            RadioSet(
                RadioButton(".csv", value=True, id="csv"),
                RadioButton(".json", id="json"),
                id="export-radio-set",
            ),
            Horizontal(
                Button("Save File", variant="primary", id="save-file"),
                Button("Cancel", variant="error", id="cancel-file"),
                id="button-container",
            ),
            id="save-dialog",
        )

    def on_mount(self) -> None:
        """
        Focus the input widget so the user can name the file
        """
        self.query_one("#directory").focus()

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """
        Event handler for when the load file button is pressed
        """
        event.stop()
        if event.button.id == "save-file":
            filename = self.query_one("#filename", Input).value
            full_path = Path(self.folder) / filename
            extension = self.query_one("#export-radio-set", RadioSet).pressed_button.id  # type: ignore
            if full_path and extension:
                filename = f"{full_path}.{extension}"
                if extension == "csv":
                    await self._csv_data(filename=filename)
                elif extension == "json":
                    await self._json_data(filename=filename)
            else:
                self.notify("You must provide a Filename")
        elif event.button.id == "cancel-file":
            self.app.pop_screen()

    @on(DirectoryTree.DirectorySelected)
    def on_directory_selection(self, event: DirectoryTree.DirectorySelected) -> None:
        """
        Called when the DirectorySelected message is emitted from the DirectoryTree
        """
        self.folder = event.path
        self.query_one("#folder", Label).update(f"Folder name: {self.folder}")

    async def _csv_data(self, filename: str) -> None:
        with open(filename, mode="w") as f:
            writer = csv.writer(f)
            writer.writerow(
                [*Book.model_fields.keys(), *Book.model_computed_fields.keys()]
            )
            books = await Book.load_books()
            rows = [list(book.model_dump().values()) for book in books]
            writer.writerows(rows)
        self.app.pop_screen()
        self.notify(f"Data saved as {filename}")

    async def _json_data(self, filename: str) -> None:
        with open(filename, mode="w") as f:
            books = await Book.load_books()
            rows = [book.model_dump() for book in books]
            json.dump(rows, f, indent=2, default=str)
        self.app.pop_screen()
        self.notify(f"Data saved as {filename}")
