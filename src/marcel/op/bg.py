import marcel.core
import marcel.job
import marcel.op.jobop

job_control = marcel.job.JobControl.only


def bg():
    return Bg()


class BgArgParser(marcel.op.jobop.JobOpArgParser):

    def __init__(self):
        super().__init__('bg')


class Bg(marcel.op.jobop.JobOp):

    argparser = BgArgParser()

    def __init__(self):
        super().__init__()

    def __repr__(self):
        return f'bg(job={self.jid})' if self.jid is not None else f'bg(pid={self.pid})'

    # BaseOp

    def doc(self):
        return __doc__

    # Op

    def arg_parser(self):
        return Bg.argparser

    # JobOp

    def action(self):
        self.job.run_in_background()
