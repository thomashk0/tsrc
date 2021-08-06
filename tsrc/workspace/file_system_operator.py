from pathlib import Path
from typing import List

import cli_ui as ui

from tsrc.errors import Error
from tsrc.executor import Outcome, Task
from tsrc.file_system import FileSystemOperation
from tsrc.repo import Repo


class FileSystemOperator(Task[FileSystemOperation]):
    """Implement file system operations to be run once every missing
    repo has been cloned, like copying files or creating symlinks.

    """

    def __init__(self, workspace_path: Path, repos: List[Repo]) -> None:
        self.workspace_path = workspace_path
        self.repos = repos

    def describe_item(self, item: FileSystemOperation) -> str:
        return str(item)

    def describe_process_start(self, item: FileSystemOperation) -> List[ui.Token]:
        return []

    def describe_process_end(self, item: FileSystemOperation) -> List[ui.Token]:
        return []

    def process(self, index: int, count: int, item: FileSystemOperation) -> Outcome:
        self.info_count(index, count, str(item))
        try:
            item.perform(self.workspace_path)
        except OSError as e:
            raise Error(str(e))
        return Outcome.from_summary(str(item))
