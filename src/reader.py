import json
from collections.abc import Iterator
from typing import Any, Optional


class JsonlReader:
    def __init__(self, filepath: str):
        self.filepath: str = filepath
        self.isjsonl: bool = filepath.endswith(
            ".jsonl"
        )  # json otherwise, we dont support any other types
        self.file: Optional[Any] = None

    def __enter__(self) -> "JsonlReader":
        self.file = open(self.filepath, "r")
        if not self.isjsonl:
            self.candidates = json.load(self.file)
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
        if self.isjsonl:
            return self
        else:
            return iter(self.candidates)

    def __next__(self) -> dict[str, Any]:
        line = self.file.readline()

        if not line:
            raise StopIteration

        return json.loads(line)
