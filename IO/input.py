def greet(name):
    message = "lol " + name
    return message

def shout(text):
    result = ""
    for char in text:
        result = result + char.upper()
    return result

words = ["lol", "lmao", "rofl"]
count = 0
for word in words:
    count = count + 1
    print(shout(greet(word)))

print("done, printed " + str(count) + " lines")
