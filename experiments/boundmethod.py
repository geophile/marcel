class C:

    def __init__(self, base):
        self.base = base

    def add(self, x):
        return self.base + x


c = C(10)
f = c.add
print(f(5))