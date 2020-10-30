import pstats
import cProfile
import contextlib


@contextlib.contextmanager
def profiled(name: str):
    pr = cProfile.Profile()
    pr.enable()
    yield
    pr.disable()
    stats = pstats.Stats(pr)
    stats.dump_stats(f"{name}.stats")
