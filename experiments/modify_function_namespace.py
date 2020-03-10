source = '''
g(lambda: VAR)
'''


function = None


def g(from_source):
    global function
    function = from_source


namespace = {'VAR': 1, 'g': g}
exec(source, namespace)
print(f'function() -> {function()}')
namespace['VAR'] = 2
print(f'function() -> {function()}')
