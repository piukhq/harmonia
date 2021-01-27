from unittest import mock


class MockSFTP:
    """
    Used in exports when settings.DEBUG == True
    """

    def __init__(self, *args, **kwargs):
        pass

    def __enter__(self):
        return mock.MagicMock()

    def __exit__(self, exc_type, exc_value, traceback):
        pass
