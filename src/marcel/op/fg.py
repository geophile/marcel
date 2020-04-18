import marcel.core
import marcel.job
import marcel.op.jobop


def fg():
    return Fg()


class FgArgParser(marcel.op.jobop.JobOpArgParser):

    def __init__(self):
        super().__init__('fg')


class Fg(marcel.op.jobop.JobOp):

    argparser = FgArgParser()

    def __init__(self):
        super().__init__()

    def __repr__(self):
        return f'fg(job={self.jid})' if self.jid is not None else f'fg(pid={self.pid})'

    # BaseOp
    
    def doc(self):
        return __doc__

    # Op

    def arg_parser(self):
        return Fg.argparser

    # JobOp

    def action(self):
        self.job.run_in_foreground()
