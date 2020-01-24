def g(n):
    for i in range(n):
        yield i

for x in g(5):
    print(x)
