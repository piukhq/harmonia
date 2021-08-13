import os
from functools import partial

from settings import delimited_list_conv, getenv


def test_getenv_delimited_list_conv():
    for sep, env in {None: "slug1,slug2,slug3", ",": "slug1,slug2,slug3", "|": "slug1 |   slug2| slug3"}.items():
        conv = partial(delimited_list_conv, sep=sep) if sep else delimited_list_conv
        os.environ["TXM_HERMES_SLUGS_TO_FORMAT"] = env
        assert getenv("TXM_HERMES_SLUGS_TO_FORMAT", conv=conv) == [
            "slug1",
            "slug2",
            "slug3",
        ]
