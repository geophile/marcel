def g(n):
    """
    Yield n - th n - th integer n.

    Args:
        n: (int): write your description
    """
    for i in range(n):
        yield i

for x in g(5):
    print(x)
