from uuid import uuid4

import pendulum

from harness.providers.base import BaseImportDataProvider


def pipe(*args):
    return "|".join(args)


class Amex(BaseImportDataProvider):
    def provide(self, fixture: dict) -> bytes:
        lines = []
        # header
        lines.append(
            pipe(
                "H",  # header identifier
                pendulum.now().format("YYYY-MM-DD"),
                "0000000001",  # sequence number
                "A2P",  # from/to
                "03",  # file type (03 = tlog)
                "AMEX TLOG FILE".ljust(40),  # file description
                " " * 209,  # filler
            )
        )

        lines.extend(
            (
                pipe(
                    "D",  # detail identifier
                    "AADP0050",  # partner id
                    str(uuid4()),  # transaction ID
                    pendulum.instance(transaction["date"]).format("YYYY-MM-DD"),
                    str(transaction["amount"] / 100).rjust(17, "0"),
                    user["token"].ljust(200),
                    fixture["mid"].ljust(15),
                    pendulum.instance(transaction["date"]).format("YYYY-MM-DD-hh.mm.ss"),
                    f'{user["first_six"]}XXXXX{user["last_four"]}',
                )
                for user in fixture["users"]
                for transaction in user["transactions"]
            )
        )

        # trailer
        lines.append(
            pipe(
                "T",  # trialer identifier
                "03",  # file type (03 = tlog)
                str(len(lines) - 1).rjust(12, "0"),  # record count
                " " * 263,  # filler
            )
        )

        return "\n".join(lines).encode()
