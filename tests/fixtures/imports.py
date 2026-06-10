import math
import os.path
import collections as col

from pathlib import Path
from json import dumps, loads

print(math.floor(3.7))
print(math.ceil(3.2))
print(math.gcd(12, 8))

counter = col.Counter([1, 2, 2, 3, 3, 3])
print(counter[3])
print(counter[2])

deque = col.deque([1, 2, 3])
deque.appendleft(0)
print(list(deque))

print(os.path.join("a", "b"))
print(Path("/tmp").name)
data = dumps({"k": "v"})
print(loads(data)["k"])
