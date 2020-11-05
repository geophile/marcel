class C:

    def __init__(self, base):
        """
        Initialize base

        Args:
            self: (todo): write your description
            base: (float): write your description
        """
        self.base = base

    def add(self, x):
        """
        Add a new value to the list.

        Args:
            self: (todo): write your description
            x: (int): write your description
        """
        return self.base + x


c = C(10)
f = c.add
print(f(5))