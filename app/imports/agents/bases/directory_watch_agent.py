from pathlib import Path
import logging
import os

import inotify.adapters
import inotify.calls
import inotify.constants

from app.imports.agents.bases.base import BaseAgent, log


inotify.adapters._LOGGER.setLevel(logging.INFO)


class DirectoryWatchAgent(BaseAgent):
    def run(self, immediate=False, debug=False):
        self.debug = debug
        if immediate is True:
            raise ValueError('DirectoryWatchAgent does not support immediate mode.')

        adapter = inotify.adapters.Inotify()

        try:
            adapter.add_watch(self.Config.watch_directory)
        except inotify.calls.InotifyError as ex:
            log.critical(f"Failed to set watch on `{self.Config.watch_directory}`. "
                         'Please check that the directory exists, '
                         'and that we have read & execute permissions on it. '
                         f"Error code: {ex.errno}")
            return

        log.info(f"Awaiting events on \"{self.Config.watch_directory}\".")

        for event in adapter.event_gen(yield_nones=False):
            event, _, path, filename = event

            if event.mask & inotify.constants.IN_CLOSE_WRITE:
                file_path = os.path.join(path, filename)
                log.debug(f"Write event detected at {file_path}! Invoking handler.")
                self.do_import(file_path)

    def do_import(self, file_path):
        with open(file_path, 'r') as fd:
            transactions_data = list(self.yield_transactions_data(fd))
        transactions_data = self.get_schema().load(transactions_data, many=True)
        self._import_transactions(transactions_data, source=Path(file_path).name)
