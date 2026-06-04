def make_adder(n):
    def adder(x):
        return x + n
    return adder

add5 = make_adder(5)
print(add5(3))
print(add5(10))

def make_counter(start):
    count = [start]
    def increment():
        count[0] += 1
        return count[0]
    return increment

counter = make_counter(0)
print(counter())
print(counter())
print(counter())
