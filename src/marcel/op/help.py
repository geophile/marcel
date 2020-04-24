import importlib

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

    def __init__(self, global_state):
        super().__init__('help', global_state, None, SUMMARY, DETAILS)
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
    
    def doc(self):
        return __doc__

    def setup_1(self):
        try:
            self.module = importlib.import_module(f'marcel.doc.help_{self.topic}')
        except ModuleNotFoundError:
            raise marcel.exception.KillCommandException(f'Help not available for {self.topic}')

    def receive(self, _):
        formatter = marcel.helpformatter.HelpFormatter(self.global_state().env.color_scheme(),
                                                       marcel.util.colorize)
        help_text = getattr(self.module, 'HELP')
        formatted = formatter.format(help_text)
        self.send(formatted)

    # Op

    def must_be_first_in_pipeline(self):
        return True
