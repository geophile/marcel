import marcel.op.jobop


def fg():
    return Fg()


class FgArgParser(marcel.op.jobop.JobOpArgParser):

    def __init__(self, global_state):
        super().__init__('fg', global_state, None, None)


class Fg(marcel.op.jobop.JobOp):

    def __init__(self):
        super().__init__()

    def __repr__(self):
        return f'fg(job={self.jid})' if self.jid is not None else f'fg(pid={self.pid})'

    # BaseOp
    
    def doc(self):
        return __doc__

    # JobOp

    def action(self):
        self.job.run_in_foreground()
