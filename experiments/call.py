class F:

    def __init__(self, function, x):
        self.function = function
        self.x = x

    def __call__(self, *args, **kwargs):
        print('call: args = {}, kwargs = {}'.format(args, kwargs))
        return self.function(*args, **kwargs) + self.x


def f(a, b, **kwargs):
    print('Calling f({}, {}, {})'.format(a, b, kwargs))
    return a + b


x = F(f, 100)
print(x(1, 2))
print(x(1, 2, k1=111, k2=222))