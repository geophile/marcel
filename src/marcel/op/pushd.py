"""C{pushd [DIRECTORY]}

cd to the given DIRECTORY, and push it onto the stack of directory (obtainable by the dirs operator).
If no DIRECTORY is supplied, then swap the top two items on the stack and cd to the new topmost directory.
"""

import pathlib

import marcel.core


def pushd():
    return Pushd()


class PushdArgParser(marcel.core.ArgParser):

    def __init__(self):
        super().__init__('pushd')
        self.add_argument('directory', nargs='?')


class Pushd(marcel.core.Op):

    argparser = PushdArgParser()

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
        self.global_state().env.pushd(self.directory)
        for dir in self.global_state().env.dirs():
            self.send(dir)

    # Op

    def arg_parser(self):
        return Pushd.argparser

    def must_be_first_in_pipeline(self):
        return True
