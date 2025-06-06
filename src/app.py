import json
import logging
import logging.config
import logging.handlers
from pathlib import Path


from textual.app import App, ComposeResult
from textual.widgets import Footer, Header

from books import BookScreen
from db import db

logger = logging.getLogger("booktracker")


def setup_logging():
    logs_path = Path("logs/booktracker.log")
    if not logs_path.is_file():
        Path("logs").mkdir()
        logs_path.touch()
    config_file = Path("src/config.json")
    with open(config_file) as f_in:
        config = json.load(f_in)
    logging.config.dictConfig(config)


class BookTracker(App):
    CSS_PATH = "app.tcss"

    SCREENS = {
        "books": BookScreen,
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
    setup_logging()
    app = BookTracker()
    app.run()
