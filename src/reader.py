from collections.abc import Iterator
from typing import Any, Optional
import json


class JsonlReader:
    def __init__(self, filepath: str):
        self.filepath: str = filepath
        self.file: Optional[Any] = None

    def __enter__(self) -> "JsonlReader":
        self.file = open(self.filepath, "r")
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ):
        if self.file:
            self.file.close()

    def __iter__(self) -> "JsonlReader":
        return self

    def __next__(self) -> dict[str, Any]:
        line = self.file.readline()

        if not line:
            raise StopIteration

        return json.loads(line)