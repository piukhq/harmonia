import typing as t

import paramiko


class SFTP:
    transport = None
    client = None

    def __init__(self, credentials: dict, skey: t.TextIO, path: t.Optional[str] = None):
        self.pkey = paramiko.RSAKey.from_private_key(skey)
        self.credentials = credentials
        self.transport = paramiko.Transport((credentials["host"], int(credentials["port"])))
        self.path = path

    def __enter__(self):
        self.transport.connect(
            username=self.credentials["username"], password=self.credentials["password"], pkey=self.pkey
        )
        self.client = paramiko.SFTPClient.from_transport(self.transport)
        if self.path:
            self.client.chdir(self.path)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if self.client:
            self.client.close()

        if self.transport:
            self.transport.close()
