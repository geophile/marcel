import marcel.job
import marcel.op.jobop

job_control = marcel.job.JobControl.only


SUMMARY = '''
Resume background execution of a suspended job. 
'''


DETAILS = '''
Resume execution of the selected job, and leave it running in the background.
'''


def bg():
    return Bg()


class BgArgParser(marcel.op.jobop.JobOpArgParser):

    def __init__(self, global_state):
        super().__init__('bg', global_state, SUMMARY, DETAILS)


class Bg(marcel.op.jobop.JobOp):

    def __init__(self):
        super().__init__()

    def __repr__(self):
        return f'bg(job={self.jid})' if self.jid is not None else f'bg(pid={self.pid})'

    # BaseOp

    def doc(self):
        return __doc__

    # JobOp

    def action(self):
        self.job.run_in_background()
