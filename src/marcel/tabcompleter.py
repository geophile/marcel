import pathlib
import readline

import marcel.core
import marcel.env
import marcel.op
from marcel.util import *


class TabCompleter:
    OPS = marcel.op.public
    FILENAME_OPS = ['cd', 'ls', 'out']

    def __init__(self):
        readline.set_completer(TabCompleter.complete)
        # Removed '-', '/' from readline.get_completer_delims()
        readline.set_completer_delims(' \t\n`~!@#$%^&*()=+[{]}\\|;:\'",<>?')
        self.op_name = None

    @staticmethod
    def complete(text, state):
        # Parse the text so far, to get information needed for tab completion. It is expected that
        # the text will end early, since we are doing tab completion here. This results in a PrematureEndError
        # which can be ignored. The important point is that the parse will set Parser.op.
        parser = marcel.parse.Parser(readline.get_line_buffer())
        try:
            parser.parse(partial_text=True)
        except marcel.parse.PrematureEndError:
            pass
        except Exception as e:
            # Don't do tab completion
            return None
        op_name = parser.last_op_name
        if op_name is None:
            candidates = TabCompleter.complete_op(text)
        elif text.startswith('-'):
            candidates = TabCompleter.complete_flag(text, op_name)
        elif op_name in TabCompleter.FILENAME_OPS:
            candidates = TabCompleter.complete_filename(text)
        else:
            return None
        return candidates[state]

    @staticmethod
    def complete_op(text):
        candidates = []
        for op in TabCompleter.OPS:
            op_with_space = op + ' '
            if op_with_space.startswith(text):
                candidates.append(op_with_space)
        return candidates

    @staticmethod
    def complete_flag(text, op_name):
        flags = marcel.core.ArgParser.op_flags[op_name]
        candidates = []
        for f in flags:
            if f.startswith(text):
                candidates.append(f)
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
        return filenames

    @staticmethod
    def op_name(line):
        first = line.split()[0]
        return first if first in TabCompleter.OPS else None
