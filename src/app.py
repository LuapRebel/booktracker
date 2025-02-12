from textual.app import App, ComposeResult
from textual.widgets import Footer, Header

from db import db


class BookTracker(App):
    CSS_PATH = "app.tcss"

    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()

    def on_mount(self) -> None:
        self.theme = "dracula"

    def on_close(self) -> None:
        db.close()


if __name__ == "__main__":
    app = BookTracker()
    app.run()
