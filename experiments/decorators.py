import functools


def decorator(f):
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        print('BEFORE')
        f(*args, **kwargs)
        print('AFTER')
    return wrapper


@decorator
def g(name):
    print(f'Hello {name}')


# g('zack')

print(g.__name__)
