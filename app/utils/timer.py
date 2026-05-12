import time
from contextlib import contextmanager
from typing import Generator


@contextmanager
def timed(label: str = "") -> Generator[dict, None, None]:
    result: dict = {}
    start = time.perf_counter()
    try:
        yield result
    finally:
        result["elapsed_ms"] = round((time.perf_counter() - start) * 1000, 2)
        if label:
            result["label"] = label
