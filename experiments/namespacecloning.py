import dill


def copy(x):
    """
    Copy dill copy of x

    Args:
        x: (todo): write your description
    """
    return dill.loads(dill.dumps(x))


# A function with a custom namespace is copied correctly.
namespace = {'x': 10}
f_source = 'lambda a: a + x'
f = eval(f_source, namespace)
print(f'Size of f globals: {len(f.__globals__)}')
print(f'f(5): {f(5)}')
f_copy = copy(f)
print(f'Size of f_copy globals: {len(f_copy.__globals__)}')
print(f'f_copy(5): {f_copy(5)}')

# The same function in the namespace is broken in a copy of the namespace. The copied function's globals is empty.
namespace['f'] = f
print(f'Size of namespace[f] globals: {len(namespace["f"].__globals__)}')
print(f'namespace[f](5): {namespace["f"](5)}')
namespace_copy = copy(namespace)
print(f'Size of namespace_copy[f] globals: {len(namespace_copy["f"].__globals__)}')
# print(f'namespace_copy[f](5): {namespace_copy["f"](5)}')

# Try repairing the function
print(f'FUNCTION REPAIRED?')
namespace_copy['f'].__globals__.update(namespace_copy)
print(f'Size of namespace_copy[f] globals: {len(namespace_copy["f"].__globals__)}')
print(f'namespace_copy[f](5): {namespace_copy["f"](5)}')
