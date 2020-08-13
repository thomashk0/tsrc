""" Entry point for tsrc status """

from typing import Dict, List, Union, Optional, Tuple

import collections
import shutil

import cli_ui as ui
from path import Path

import tsrc
import tsrc.errors
import tsrc.git

from tsrc.cli import (
    with_workspace,
    with_groups,
    with_all_cloned,
    get_workspace,
    resolve_repos,
)


class ManifestStatus:
    def __init__(self, repo: tsrc.Repo, *, manifest: tsrc.Manifest):
        self.repo = repo
        self.manifest = manifest
        self.incorrect_branch = None  # type: Optional[Tuple[str,str]]

    def update(self, git_status: tsrc.git.Status) -> None:
        expected_branch = self.repo.branch
        actual_branch = git_status.branch
        if actual_branch and actual_branch != expected_branch:
            self.incorrect_branch = (actual_branch, expected_branch)

    def describe(self) -> List[ui.Token]:
        res = []  # type: List[ui.Token]
        incorrect_branch = self.incorrect_branch
        if incorrect_branch:
            actual, expected = incorrect_branch
            res += [ui.red, "(expected: " + expected + ")"]
        return res


class Status:
    def __init__(self, *, git: tsrc.git.Status, manifest: ManifestStatus):
        self.git = git
        self.manifest = manifest


StatusOrError = Union[Status, Exception]
CollectedStatuses = Dict[str, StatusOrError]


def describe_status(status: StatusOrError) -> List[ui.Token]:
    """ Returns a list of tokens suitable for ui.info() """
    if isinstance(status, tsrc.errors.MissingRepo):
        return [ui.red, "error: missing repo"]
    if isinstance(status, Exception):
        return [ui.red, "error: ", status]
    git_status = status.git.describe()
    manifest_status = status.manifest.describe()
    return git_status + manifest_status


def erase_last_line() -> None:
    terminal_size = shutil.get_terminal_size()
    ui.info(" " * terminal_size.columns, end="\r")


class StatusCollector(tsrc.Task[tsrc.Repo]):
    def __init__(self, workspace: tsrc.Workspace) -> None:
        self.workspace = workspace
        self.manifest = workspace.get_manifest()
        self.statuses = collections.OrderedDict()  # type: CollectedStatuses
        self.num_repos = 0

    def display_item(self, repo: tsrc.Repo) -> str:
        return repo.dest

    def process(self, index: int, total: int, repo: tsrc.Repo) -> None:
        ui.info_count(index, total, repo.dest, end="\r")
        full_path = self.workspace.root_path / repo.dest

        if not full_path.exists():
            self.statuses[repo.dest] = tsrc.errors.MissingRepo(repo.dest)
            return

        try:
            git_status = tsrc.git.get_status(full_path)
            manifest_status = ManifestStatus(repo, manifest=self.manifest)
            manifest_status.update(git_status)
            status = Status(git=git_status, manifest=manifest_status)
            self.statuses[repo.dest] = status
        except Exception as e:
            self.statuses[repo.dest] = e
        erase_last_line()

    def on_start(self, num_items: int) -> None:
        ui.info_1(f"Collecting statuses of {num_items} repo(s)")
        self.num_repos = num_items

    def on_success(self) -> None:
        erase_last_line()
        if not self.statuses:
            ui.info_2("Workspace is empty")
            return
        ui.info_2("Workspace status:")
        max_dest = max(len(x) for x in self.statuses.keys())
        for dest, status in self.statuses.items():
            message = [ui.green, "*", ui.reset, dest.ljust(max_dest)]
            message += describe_status(status)
            ui.info(*message)


@with_workspace  # type: ignore
@with_groups  # type: ignore
@with_all_cloned  # type: ignore
def status(
    workspace_path: Optional[Path] = None,
    groups: Optional[List[str]] = None,
    all_cloned: bool = False,
) -> None:
    """ display workspace status summary """
    workspace = get_workspace(workspace_path)
    workspace.repos = resolve_repos(workspace, groups=groups, all_cloned=all_cloned)
    status_collector = StatusCollector(workspace)
    tsrc.run_sequence(workspace.repos, status_collector)
