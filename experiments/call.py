class F:

    def __init__(self, function, x):
        """
        Initialize the function.

        Args:
            self: (todo): write your description
            function: (callable): write your description
            x: (int): write your description
        """
        self.function = function
        self.x = x

    def __call__(self, *args, **kwargs):
        """
        Calls the function call.

        Args:
            self: (todo): write your description
        """
        print('call: args = {}, kwargs = {}'.format(args, kwargs))
        return self.function(*args, **kwargs) + self.x


def f(a, b, **kwargs):
    """
    Compute a and b.

    Args:
        a: (int): write your description
        b: (int): write your description
    """
    print('Calling f({}, {}, {})'.format(a, b, kwargs))
    return a + b


x = F(f, 100)
print(x(1, 2))
print(x(1, 2, k1=111, k2=222))