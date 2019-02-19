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

    def run(self, *, debug: bool = False, once: bool = False):
        self.debug = debug
        watch_path = Path(self.Config.watch_directory)  # type: ignore

        if not watch_path.exists():
            self.log.warning(
                f"Watch directory is set to {watch_path} but it does not exist! Attempting to create…"
            )
            watch_path.mkdir(parents=True)
            self.log.warning(
                f"Created watch directory {watch_path} successfully."
            )

        for file_path in watch_path.iterdir():
            self.log.info(f"Found existing file at {file_path}, importing.")

            try:
                self.do_import(file_path)
            except Exception as ex:
                if self.debug is True:
                    raise
                self.log.error(f"Import failed: {repr(ex)}.")

            if once is True:
                self.log.info(
                    "Quitting existing file loop because we were told to run once."
                )
                return

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

        self.log.info(f'Awaiting events on "{watch_path}".')

        for event in adapter.event_gen(yield_nones=False):
            event, _, path, filename = event

            if event.mask & inotify.constants.IN_CLOSE_WRITE:
                file_path = Path(os.path.join(path, filename))
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
                    return

    def yield_transactions_data(self, fd: t.IO) -> t.Iterable[dict]:
        raise NotImplementedError

    def do_import(self, file_path: Path):
        with file_path.open(self.file_open_mode) as fd:
            transactions_data = list(self.yield_transactions_data(fd))
        self._import_transactions(transactions_data, source=str(file_path))
        file_path.unlink()
