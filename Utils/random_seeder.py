import random
from contextlib import contextmanager

@contextmanager
def seeded(seed: int | None):
    """Temporarily set the global random seed, then restore previous RNG state."""
    if seed is None:
        # No seeding requested; do nothing.
        yield
        return
    state = random.getstate()
    random.seed(seed)
    try:
        yield
    finally:
        random.setstate(state)
