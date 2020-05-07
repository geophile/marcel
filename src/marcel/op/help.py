import contextlib
import importlib
import io

import marcel.core
import marcel.helpformatter
import marcel.util


SUMMARY = '''
Provide help on marcel's concepts, objects, and operations.  
'''


DETAILS = None


def help():
    return Help()


class HelpArgParser(marcel.core.ArgParser):

    def __init__(self, env):
        super().__init__('help', env, None, SUMMARY, DETAILS)
        self.add_argument('topic',
                          default='marcel',
                          nargs='?',
                          help='Topic to be described.')


class Help(marcel.core.Op):

    def __init__(self):
        super().__init__()
        self.topic = None
        self.module = None

    def __repr__(self):
        return f'help({self.topic})'

    # BaseOp
    
    def setup_1(self):
        self.topic = self.topic.lower()

    def receive(self, _):
        op_module = self.env().op_modules.get(self.topic, None)
        help_text = Help.op_help(op_module) if op_module else self.topic_help()
        self.send(help_text)

    # Op

    def must_be_first_in_pipeline(self):
        return True

    # For use by this class

    @staticmethod
    def op_help(op_module):
        arg_parser = op_module.arg_parser()
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            try:
                arg_parser.parse_args(['-h'], op_module.create_op())
            except KeyboardInterrupt:
                # Parsing -h causes exit to raise KeyboardInterrupt
                pass
        return buffer.getvalue()

    def topic_help(self):
        try:
            self.module = importlib.import_module(f'marcel.doc.help_{self.topic}')
        except ModuleNotFoundError:
            raise marcel.exception.KillCommandException(f'Help not available for {self.topic}')
        formatter = marcel.helpformatter.HelpFormatter(self.env().color_scheme())
        help_text = getattr(self.module, 'HELP')
        return formatter.format(help_text)
