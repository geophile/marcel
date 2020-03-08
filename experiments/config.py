def forget(x):
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
    foobar = 1
    def g():
        global foobar
        foobar = 2
    g()
    return foobar

x = f()
print(f'foobar: {x}')
