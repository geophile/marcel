import marcel.core
import marcel.job


def jobs():
    return Jobs()


class JobsArgParser(marcel.core.ArgParser):

    def __init__(self):
        super().__init__('jobs')


class Jobs(marcel.core.Op):

    argparser = JobsArgParser()

    def __init__(self):
        super().__init__()

    def __repr__(self):
        return f'jobs'

    # BaseOp interface
    
    def doc(self):
        return __doc__

    def setup_1(self):
        pass

    def receive(self, x):
        job_id = 0
        for job in marcel.job.JobControl.only.jobs:
            # TODO: If job were a marcel.object, then it would have render_compact/full methods.
            description = f'{job_id}({job.state_symbol()}): {job.process.pid}  {job.command.source}'
            self.send(description)
            job_id += 1

    # Op interface

    def arg_parser(self):
        return Jobs.argparser

    def must_be_first_in_pipeline(self):
        return True

