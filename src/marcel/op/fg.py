import marcel.core
import marcel.job


def fg():
    return Fg()


class FgArgParser(marcel.core.ArgParser):

    def __init__(self):
        super().__init__('fg')
        self.add_argument('job_id',
                          type=super().constrained_type(marcel.core.ArgParser.check_non_negative,
                                                        'must be non-negative'))


class Fg(marcel.core.Op):

    argparser = FgArgParser()

    def __init__(self):
        super().__init__()
        self.job_id = None

    def __repr__(self):
        return f'fg({self.job_id})'

    # BaseOp interface
    
    def doc(self):
        return __doc__

    def setup_1(self):
        if self.job_id >= len(marcel.job.JobControl.only.jobs):
            raise marcel.exception.KillCommandException(f'There is no job {self.job_id}')

    def receive(self, x):
        job = marcel.job.JobControl.only.jobs[self.job_id]
        job.run_in_foreground()

    # Op interface

    def arg_parser(self):
        return Fg.argparser

    def must_be_first_in_pipeline(self):
        return True

