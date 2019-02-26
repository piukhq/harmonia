import logging
import os
import typing as t
from pathlib import Path

import inotify.adapters
import inotify.calls
import inotify.constants

from app.imports.agents.bases.base import BaseAgent

inotify.adapters._LOGGER.setLevel(logging.INFO)


class DirectoryWatchAgent(BaseAgent):
    file_open_mode = "r"

    def ensure_path(self, path: Path) -> None:
        if not path.exists():
            self.log.warning(
                f"Watch directory is set to {path} but it does not exist! Attempting to create…"
            )
            path.mkdir(parents=True)
            self.log.warning(f"Created watch directory {path} successfully.")

    def import_existing_files(
        self, watch_path: Path, *, once: bool = False
    ) -> None:
        for file_path in watch_path.iterdir():
            self.log.info(f"Found existing file at {file_path}, importing.")

            try:
                self.do_import(file_path)
            except Exception as ex:
                if self.debug is True:
                    raise
                self.log.error(f"Import failed: {repr(ex)}.")

    def create_inotify_adapter(
        self, watch_path: Path
    ) -> inotify.adapters.Inotify:
        adapter = inotify.adapters.Inotify()
        try:
            adapter.add_watch(str(watch_path))
        except inotify.calls.InotifyError as ex:
            self.log.critical(
                f"Failed to set watch on `{watch_path}`. "
                "Please check that the directory exists, "
                "and that we have read & execute permissions on it. "
                f"Error code: {ex.errno}."
            )
            return
        return adapter

    def inotify_write_event(
        self, adapter: inotify.adapters.Inotify, *, once: bool = False
    ) -> t.Iterable[Path]:
        for event in adapter.event_gen(yield_nones=False):
            event, _, path, filename = event

            if event.mask & inotify.constants.IN_CLOSE_WRITE:
                yield Path(path) / filename

    def run(self, *, debug: bool = False, once: bool = False):
        self.debug = debug
        watch_path = Path(self.Config.watch_directory)  # type: ignore

        self.ensure_path(watch_path)
        self.import_existing_files(watch_path, once=once)
        if once is True:
            self.log.info(
                "Quitting existing file loop because we were told to run once."
            )
            return

        adapter = self.create_inotify_adapter(watch_path)

        self.log.info(f'Awaiting events on "{watch_path}".')

        for file_path in self.inotify_write_event(adapter, once=once):
            self.log.debug(
                f"Write event detected at {file_path}! Invoking handler."
            )

            try:
                self.do_import(file_path)
            except Exception as ex:
                if self.debug is True:
                    raise
                self.log.error(f"Import failed: {repr(ex)}.")

            if once is True:
                self.log.info(
                    "Quitting event generator because we were told to run once."
                )
                break

    def yield_transactions_data(self, fd: t.IO) -> t.Iterable[dict]:
        raise NotImplementedError

    def do_import(self, file_path: Path):
        with file_path.open(self.file_open_mode) as fd:
            transactions_data = list(self.yield_transactions_data(fd))
        self._import_transactions(transactions_data, source=str(file_path))
        file_path.unlink()
