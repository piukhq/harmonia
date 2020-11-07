import io
import typing as t
from time import sleep

import paramiko

from app.reporting import get_logger


log = get_logger("sftp")


class SFTPCredentials(t.NamedTuple):
    host: str
    port: t.Union[str, int]
    username: str
    password: t.Optional[str]


class SFTP:
    transport = None
    client = None

    def __init__(
        self,
        credentials: SFTPCredentials,
        skey: t.Optional[str] = None,
        path: t.Optional[str] = None,
        retry_count: int = 50,  # default=5     TEMPORARILY INCREASED! revert ASAP
        retry_sleep: float = 5,  # default=0.5   TEMPORARILY INCREASED! revert ASAP
    ):
        self.pkey = paramiko.RSAKey.from_private_key(io.StringIO(skey)) if skey else None
        self.credentials = credentials
        self.path = path
        self.retry_count = retry_count
        self.retry_sleep = retry_sleep

    def __enter__(self):
        self.ssh_client = paramiko.SSHClient()
        self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        for retry in range(self.retry_count):
            try:
                self.ssh_client.connect(
                    hostname=self.credentials.host,
                    port=self.credentials.port,
                    username=self.credentials.username,
                    password=self.credentials.password,
                    pkey=self.pkey,
                )
            except Exception as ex:
                remaining = self.retry_count - retry - 1
                if remaining > 0:
                    log.warning(
                        f"Failed to connect to SFTP @ {self.credentials.host}: {ex}. "
                        f"Retrying after {self.retry_sleep}s ({remaining} attempt(s) remaining.)"
                    )
                    sleep(self.retry_sleep)
                else:
                    log.error("Failed to connect to SFTP, max retries exceeded.")
                    raise
            else:
                break

        self.client = self.ssh_client.open_sftp()

        if self.path:
            self.client.chdir(self.path)

        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if self.client:
            self.client.close()
        if self.ssh_client:
            self.ssh_client.close()
