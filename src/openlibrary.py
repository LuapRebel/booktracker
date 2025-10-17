import io
from pathlib import Path
from PIL import Image
import requests


class OpenLibrarySearch:
    """
    Query the OpenLibrary Search API

    Download/View Covers
    Filter response data
    """

    def __init__(self, **kwargs):
        self.search(**kwargs)
        self.cover_id: int = 0
        self.cover: bytes = bytes()

    def search(self, **kwargs) -> None:
        """Return a Response object from the Open Library search API."""
        base_url = "https://openlibrary.org/search.json?"
        fields = ["language=eng"]
        for k, v in kwargs.items():
            text = str(v).replace(" ", "+")
            fields.append(f"{k}={text}")
        joined_fields = "&".join(fields)
        self.search_url = base_url + joined_fields
        self.kwargs = kwargs
        self.response = self._make_request(self.search_url)

    def update_cover(self, id: int, size: str = "L"):
        """
        Download a jpg of a cover using it's cover_id
        If cover is available attributes `cover_id` (int) and `cover` (bytes)
        are updated.
        """
        url = f"https://covers.openlibrary.org/b/id/{id}-{size}.jpg"
        res = self._make_request(url)
        if isinstance(res, requests.Response):
            self.cover_id = id
            self.cover = res.content

    def show_cover(self) -> None:
        """Open cover in default image viewing program."""
        if self.cover:
            image = Image.open(io.BytesIO(self.cover))
            image.show()

    def save_cover(self, directory: Path = Path("."), size: str = "L") -> None:
        """
        Save cover as jpg to the present working directory if alternative not provided.
        """
        if all([directory.is_dir(), directory.exists()]):
            if self.cover_id:
                with open(f"{directory}/{self.cover_id}-{size}.jpg", "wb") as f:
                    f.write(self.cover)

    def filter_docs(self, **kwargs) -> list[dict | None]:
        """Filter all results by providing keyword arguments. Must be exact."""
        if self.docs:
            return [doc for doc in self.docs if kwargs.items() <= doc.items()]
        return []

    def _make_request(self, url: str) -> requests.Response | str:
        try:
            res = requests.get(url)
            res.raise_for_status()
        except requests.exceptions.HTTPError as e:
            return f"HTTP error occurred: {e}"
        except requests.exceptions.RequestException as e:
            return f"A request error occurred: {e}"
        else:
            return res

    @property
    def num_found(self) -> int | None:
        """Number of matching search results."""
        if isinstance(self.response, requests.Response):
            return self.response.json()["numFound"]

    @property
    def docs(self) -> list[dict] | None:
        """Matching search results."""
        if isinstance(self.response, requests.Response):
            return self.response.json()["docs"]

    # @property
    # def search_url(self) -> str:
    #     """Original query URL"""
    #     if isinstance(self.response, requests.Response):
    #         return self.response.url

    @property
    def cover_ids(self, **kwargs) -> list[int | None]:
        """Return the cover ids for a book or None if one not available."""
        if isinstance(self.response, requests.Response):
            if self.response.json().get("numFound", None):
                if self.docs:
                    return [doc["cover_i"] for doc in self.docs if "cover_i" in doc]
        return []

    @property
    def search_keys(self) -> set[str] | None:
        """Available search keys given the data in the response"""
        if self.docs:
            return {k for d in self.docs for k in d}

    def __repr__(self) -> str:
        return f"{self.__class__!s}({self.kwargs!r})"

    def __str__(self) -> str:
        return f"{self.__class__.__name__}({", ".join([f"{k}={v}" for k,v in self.kwargs.items()])})"
