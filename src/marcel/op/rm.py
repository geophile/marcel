"""C{rm FILENAME ...}

FILENAME                   Filename or glob pattern.

Remove the given files.
"""

import shutil

import marcel.core
import marcel.env
import marcel.object.error
import marcel.object.file
import marcel.op.filenames


def rm():
    return Rm()


class RmArgParser(marcel.core.ArgParser):

    def __init__(self):
        super().__init__('rm')
        self.add_argument('filename', nargs='+')


class Rm(marcel.core.Op):

    argparser = RmArgParser()

    def __init__(self):
        super().__init__()
        self.filename = None

    def __repr__(self):
        return 'rm({})'.format(self.filename)

    # BaseOp

    def doc(self):
        return __doc__

    def setup_1(self):
        pass

    def receive(self, _):
        paths = marcel.op.filenames.normalize_paths(self.filename)
        roots = marcel.op.filenames.roots(marcel.env.ENV.pwd(), paths)
        for root in roots:
            self.remove(root)
        self.send_complete()

    # Op

    def arg_parser(self):
        return Rm.argparser

    def must_be_first_in_pipeline(self):
        return True

    # For use by this class

    def remove(self, root):
        try:
            if root.is_dir():
                shutil.rmtree(root)
            else:  # This works for files and symlinks
                root.unlink()
        except PermissionError as e:
            self.send(marcel.object.error.Error(e))
        except FileNotFoundError:
            pass
