LIMIT = 10
total = 0


def add(n):
    global total
    total += n


def is_within_limit(n):
    return n < LIMIT


for i in range(1, 4):
    add(i)

print(total)
print(is_within_limit(5))
print(is_within_limit(15))
