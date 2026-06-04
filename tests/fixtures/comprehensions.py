nums = [1, 2, 3, 4, 5, 6, 7, 8]
squares = [x * x for x in nums]
evens = [x for x in nums if x % 2 == 0]
print(squares)
print(evens)

word_lengths = {word: len(word) for word in ["alpha", "beta", "gamma", "delta"]}
print(sorted(word_lengths.items()))

pairs = [(i, j) for i in range(3) for j in range(3) if i != j]
print(len(pairs))

total = sum(x for x in range(10) if x % 3 == 0)
print(total)
