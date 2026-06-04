total = 0
for i in range(5):
    total += i
print(total)

for i in range(2, 8, 2):
    print(i)

matrix = []
for row in range(3):
    for col in range(3):
        matrix.append(row * 3 + col)
print(matrix)
