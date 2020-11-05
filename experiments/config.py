def forget(x):
    """
    Get the given value

    Args:
        x: (str): write your description
    """
    print(f'forget({x})')


config = '''
def keep_f(x):
    print(f'keep_f({x})')
    
forget(10)
keep_f(20)
keep_v = 1
'''


globals = {'forget': forget}
locals = {}


exec(config, globals, locals)
print(f'globals: {globals.keys()}')
print(f'locals: {locals.keys()}')


def f():
    """
    Decorator that returns a function to a function.

    Args:
    """
    foobar = 1
    def g():
        """
        Åīľå»ºä¸ģ»ħåĳį

        Args:
        """
        global foobar
        foobar = 2
    g()
    return foobar

x = f()
print(f'foobar: {x}')
