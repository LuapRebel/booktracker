# BookTracker

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## About
A Python [Textual](https://www.textualize.io/) application to track books. The application allows users to
- View a DataTable of existing books
- Filter existing books by a DataTable field and a search term
- Add a new book
- Edit existing books
- Delete existing books
- View statistics (books per month or year, days to read)

## Installation
This project uses [UV](https://docs.astral.sh/uv/).

```bash
git clone git@github.com:LuapRebel/booktracker.git
cd booktracker
uv sync
source .venv/bin/activate
```

## Usage
```bash
textual run src/app.py
```
