import signal

import marcel.core
import marcel.job
import marcel.op.jobop


def kill():
    return Kill()


class KillArgParser(marcel.op.jobop.JobOpArgParser):

    def __init__(self):
        super().__init__('kill')
        self.add_argument('-s', '--signal',
                          type=super().constrained_type(marcel.core.ArgParser.check_signal_number,
                                                        'must be a signal number (between 1 and 30)'))
        self.add_argument('signum',
                          nargs='?',
                          type=super().constrained_type(marcel.core.ArgParser.check_signal_number,
                                                        'must be a signal number (between 1 and 30)'))


class Kill(marcel.op.jobop.JobOp):

    argparser = KillArgParser()

    def __init__(self):
        super().__init__()
        self.signal = None
        self.signum = None

    def __repr__(self):
        buffer = ['fg(',
                  f'job={self.jid}' if self.jid is not None else f'pid={self.pid}',
                  f', signal={self.signal})']
        return ''.join(buffer)

    # BaseOp

    def doc(self):
        return __doc__

    def setup_1(self):
        super().setup_1()
        if self.signal is None and self.signum is None:
            self.signal = signal.SIGKILL
        elif self.signal is None and self.signum is not None:
            self.signal = self.signum
        elif self.signal is not None and self.signum is not None:
            raise marcel.exception.KillCommandException(f'Signal specified more than once.')

    # Op

    def arg_parser(self):
        return Kill.argparser

    # JobOp

    def action(self):
        self.job.kill()
