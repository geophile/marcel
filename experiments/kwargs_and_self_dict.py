class X:

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

x = X(a=1, b=2, c=3)
print(f'a: {x.a}')
print(f'b: {x.b}')
print(f'c: {x.c}')
print(f'd: {x.d}')
