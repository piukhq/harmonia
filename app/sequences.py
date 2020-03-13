import typing as t


def batch(seq: t.Sequence, size: int = 1):
    """
    Yield up to `size` length batches from `seq` until empty.
    """
    length = len(seq)
    for index in range(0, length, size):
        yield seq[index : index + size]
