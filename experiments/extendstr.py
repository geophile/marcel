class StrVar(str):

    def __init__(self, x):
        """
        Initialize the value.

        Args:
            self: (todo): write your description
            x: (int): write your description
        """
        super().__init__()
        self.value = x

    def __str__(self):
        """
        Returns the string representation of the string.

        Args:
            self: (todo): write your description
        """
        return self.value

    def set(self, x):
        """
        Set the value of x.

        Args:
            self: (todo): write your description
            x: (dict): write your description
        """
        self.value = x


s = StrVar('a')
print(s)
s.set('b')
print(s)
print(isinstance(s, str))
print(StrVar('abcd').startswith('ab'))
print(StrVar('abcd').startswith('bc'))
