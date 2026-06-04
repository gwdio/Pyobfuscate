import math
import collections

print(math.floor(3.7))
print(math.ceil(3.2))
print(math.gcd(12, 8))

counter = collections.Counter([1, 2, 2, 3, 3, 3])
print(counter[3])
print(counter[2])

deque = collections.deque([1, 2, 3])
deque.appendleft(0)
print(list(deque))
