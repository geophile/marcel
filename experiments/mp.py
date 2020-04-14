import multiprocessing as mp
import os


class XmitStr:

    def __init__(self, value):
        self.value = value

    def __getstate__(self):
        print(f'{os.getpid()} getstate {self.value}')
        return self.__dict__

    def __setstate__(self, state):
        self.__dict__.update(state)
        print(f'{os.getpid()} selfstate {self.value}')


def f(name, q, child):
    print(f'hello {name.value}: {os.getpid()} -> {os.getppid()}')
    q.put(XmitStr('goodbye'))
    print(f'child reads pipe: {os.getpid()} {child.recv().value}')
    print(f'child writes pipe: {os.getpid()} {child.send(XmitStr("from child to parent"))}')


if __name__ == '__main__':
    q = mp.Queue()
    parent, child = mp.Pipe()
    p = mp.Process(target=f, args=(XmitStr('bob'), q, child))
    print(f'main: {os.getpid()} -> {os.getppid()}')
    p.start()
    print(q.get().value)
    print(f'parent writes pipe: {os.getpid()} {parent.send(XmitStr("from parent to child"))}')
    print(f'parent reads pipe: {os.getpid()} {parent.recv().value}')
    p.join()
