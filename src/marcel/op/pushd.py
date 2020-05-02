import pathlib

import marcel.core


SUMMARY = '''
Push a given directory onto the directory stack, and cd to that directory.
'''


DETAILS = '''
If no {r:directory} is supplied, then the top two items on the directory stack are swapped,
and the current directory is changed to the new top directory on the stack.
'''


def pushd(directory=None):
    op = Pushd()
    op.directory = directory
    return op


class PushdArgParser(marcel.core.ArgParser):

    def __init__(self, env):
        super().__init__('pushd', env, None, SUMMARY, DETAILS)
        self.add_argument('directory', nargs='?', help='New current directory')


class Pushd(marcel.core.Op):

    def __init__(self):
        super().__init__()
        self.directory = None

    def __repr__(self):
        return f'pushd({self.directory})' if self.directory else 'pushd()'

    # BaseOp

    def doc(self):
        return self.__doc__

    def setup_1(self):
        if self.directory is not None:
            self.directory = pathlib.Path(self.directory).expanduser()
            if not self.directory.is_dir():
                raise marcel.exception.KillCommandException(f'{self.directory} is not a directory')

    def receive(self, _):
        self.env().dir_state().pushd(self.directory)
        for dir in self.env().dir_state().dirs():
            self.send(dir)

    # Op

    def must_be_first_in_pipeline(self):
        return True
