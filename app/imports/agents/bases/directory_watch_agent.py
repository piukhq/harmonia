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
    def run(self, *, once: bool = False):
        watch_path = Path(self.Config.watch_directory)  # type: ignore

        if not watch_path.exists():
            self.log.warning(
                f"Watch directory is set to {watch_path} but it does not exist! Attempting to create…"
            )
            watch_path.mkdir(parents=True)
            self.log.warning(f"Created watch directory {watch_path} successfully.")

        for file_path in watch_path.iterdir():
            self.log.info(f"Found existing file at {file_path}, importing.")
            self.do_import(file_path)
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
                file_path = os.path.join(path, filename)
                self.log.debug(
                    f"Write event detected at {file_path}! Invoking handler."
                )
                self.do_import(Path(file_path))

                if once is True:
                    self.log.info(
                        "Quitting event generator because we were told to run once."
                    )
                    return

    def yield_transactions_data(self, fd: t.IO) -> t.Iterable[dict]:
        raise NotImplementedError

    def do_import(self, file_path: Path):
        with file_path.open("r") as fd:
            transactions_data = list(self.yield_transactions_data(fd))
        transactions_data = self.get_schema().load(transactions_data, many=True)
        self._import_transactions(transactions_data, source=str(file_path))
        self.log.info(f"Imported {file_path} successfully. Deleting.")
        file_path.unlink()
        self.log.info(f"Deleted {file_path} successfully.")
