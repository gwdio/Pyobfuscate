class Animal:
    def __init__(self, name, sound):
        self.name = name
        self.sound = sound

    def speak(self):
        return self.name + " says " + self.sound


class Dog(Animal):
    def __init__(self, name):
        super().__init__(name, "woof")

    def fetch(self, item):
        return self.name + " fetches " + item


d = Dog("Rex")
print(d.speak())
print(d.fetch("ball"))
print(isinstance(d, Animal))
