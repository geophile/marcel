class StrVar(str):

    def __init__(self, x):
        super().__init__()
        self.value = x

    def __str__(self):
        return self.value

    def set(self, x):
        self.value = x


s = StrVar('a')
print(s)
s.set('b')
print(s)
print(isinstance(s, str))
print(StrVar('abcd').startswith('ab'))
print(StrVar('abcd').startswith('bc'))
