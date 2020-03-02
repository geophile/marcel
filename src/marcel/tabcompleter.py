import os
import pathlib
import readline

import marcel.core
import marcel.env
import marcel.op
from marcel.util import *


DEBUG = False


def debug(message):
    if DEBUG:
        print(message)


class TabCompleter:
    OPS = marcel.op.public
    FILENAME_OPS = ['cd', 'ls', 'out']

    def __init__(self):
        readline.set_completer(self.complete)
        # Removed '-', '/' from readline.get_completer_delims()
        readline.set_completer_delims(' \t\n`~!@#$%^&*()=+[{]}\\|;:\'",<>?')
        self.op_name = None
        self.executables = None

    def complete(self, text, state):
        line = readline.get_line_buffer()
        debug('complete: line={}, text={}'.format(line, text))
        if len(line.strip()) == 0:
            candidates = TabCompleter.OPS
        else:
            # Parse the text so far, to get information needed for tab completion. It is expected that
            # the text will end early, since we are doing tab completion here. This results in a PrematureEndError
            # which can be ignored. The important point is that the parse will set Parser.op.
            parser = marcel.parse.Parser(line)
            try:
                parser.parse(partial_text=True)
                debug('parse succeeded')
            except marcel.parse.PrematureEndError:
                debug('premature end')
                pass
            except Exception as e:
                debug('caught ({}) {}'.format(type(e), e))
                # Don't do tab completion
                return None
            debug('parser.op: {}'.format(parser.op))
            if parser.op is None:
                candidates = self.complete_op(text)
            else:
                self.op_name = parser.op.op_name()
                if text.startswith('-'):
                    candidates = TabCompleter.complete_flag(text, self.op_name)
                elif self.op_name in TabCompleter.FILENAME_OPS:
                    candidates = TabCompleter.complete_filename(text)
                else:
                    return None
        return candidates[state]

    def complete_op(self, text):
        debug('complete_op, text = {}'.format(text))
        candidates = []
        if len(text) > 0:
            # Display marcel ops.
            # Display executables only if there are no qualifying ops.
            for op in TabCompleter.OPS:
                op_with_space = op + ' '
                if op_with_space.startswith(text):
                    candidates.append(op_with_space)
            if len(candidates) == 0:
                self.ensure_executables()
                for command_set in [TabCompleter.OPS, self.executables]:
                    for ex in self.executables:
                        ex_with_space = ex + ' '
                        if ex_with_space.startswith(text):
                            candidates.append(ex_with_space)
            debug('complete_op candidates for {}: {}'.format(text, candidates))
        else:
            candidates = TabCompleter.OPS
        return candidates

    @staticmethod
    def complete_flag(text, op_name):
        flags = marcel.core.ArgParser.op_flags[op_name]
        candidates = []
        for f in flags:
            if f.startswith(text):
                candidates.append(f)
        debug('complete_flag candidates for {}: {}'.format(text, candidates))
        return candidates

    @staticmethod
    def complete_filename(text):
        current_dir = marcel.env.ENV.pwd()
        if text:
            base, pattern_prefix = (('/', text[1:])
                                    if text.startswith('/') else
                                    ('.', text))
            filenames = [p.as_posix() for p in pathlib.Path(base).glob(pattern_prefix + '*')]
        else:
            filenames = ['/'] + [p.relative_to(current_dir).as_posix() for p in current_dir.iterdir()]
        debug('complete_filename candidates for {}: {}'.format(text, filenames))
        return filenames

    @staticmethod
    def op_name(line):
        first = line.split()[0]
        return first if first in TabCompleter.OPS else None

    def ensure_executables(self):
        if self.executables is None:
            self.executables = []
            path = os.environ['PATH'].split(':')
            for p in path:
                for f in os.listdir(p):
                    if is_executable(f):
                        self.executables.append(f)
