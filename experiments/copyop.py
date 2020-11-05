class Parent:

    def __init__(self):
        """
        Initialize p1 p1

        Args:
            self: (todo): write your description
        """
        self.p1 = 1
        self.p2 = 2

    def copy(self):
        """
        Returns a copy of the instance.

        Args:
            self: (todo): write your description
        """
        x = self.__class__()
        x.__dict__.update(self.__dict__)
        return x


class Child(Parent):

    def __init__(self):
        """
        Initialize the data

        Args:
            self: (todo): write your description
        """
        super().__init__()
        self.c1 = 3
        self.c2 = 4

    def __repr__(self):
        """
        Return a repr representation of a repr__.

        Args:
            self: (todo): write your description
        """
        return f'({self.p1}, {self.p2}, {self.c1}, {self.c2})'


a = Child()
b = a.copy()
print(f'{a.__class__}: {a}')
print(f'{b.__class__}: {b}')

import time
start = time.time()
N = 1000000
for i in range(N):
    a.copy()
stop = time.time()
msec = (stop - start) * 1000 / N
print(f'{msec} msec/copy')
