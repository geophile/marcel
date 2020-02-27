import readline

import marcel.core
import marcel.op


class TabCompleter:

    OPS = marcel.op.public
    FILENAME_OPS = ['cd', 'ls', 'out']

    def __init__(self):
        readline.set_completer(lambda text, state: self.complete(text, state))
        # Removed '-' from readline.get_completer_delims()
        readline.set_completer_delims(' \t\n`~!@#$%^&*()=+[{]}\\|;:\'",<>/?')
        self.op_name = None

    def complete(self, text, state):
        line = readline.get_line_buffer()
        op_name = TabCompleter.op_name(line)
        if op_name is None:
            candidates = TabCompleter.complete_op(text)
        elif text.startswith('-'):
            candidates = TabCompleter.complete_flag(text, op_name)
        elif op_name in TabCompleter.FILENAME_OPS:
            candidates = TabCompleter.complete_filename(text)
        else:
            # TODO: Is this right?
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
        return []

    @staticmethod
    def op_name(line):
        first = line.split()[0]
        return first if first in TabCompleter.OPS else None
