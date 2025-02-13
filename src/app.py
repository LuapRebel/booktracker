from textual.app import App, ComposeResult
from textual.widgets import Footer, Header

from books import BookFilterScreen, BookScreen
from db import db


class BookTracker(App):
    CSS_PATH = "app.tcss"

    SCREENS = {
        "books": BookScreen,
        "filter": BookFilterScreen,
    }

    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()

    def on_mount(self) -> None:
        self.theme = "dracula"
        self.push_screen(BookScreen())

    def _on_screen_resume(self) -> None:
        self.push_screen(BookScreen())

    def on_close(self) -> None:
        db.close()


if __name__ == "__main__":
    app = BookTracker()
    app.run()
