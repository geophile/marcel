import marcel.core
import marcel.job


def jobs():
    return Jobs()


class JobsArgParser(marcel.core.ArgParser):

    def __init__(self, global_state):
        super().__init__('jobs', global_state)


class Jobs(marcel.core.Op):

    def __init__(self):
        super().__init__()

    def __repr__(self):
        return f'jobs'

    # BaseOp
    
    def doc(self):
        return __doc__

    def setup_1(self):
        pass

    def receive(self, x):
        job_id = 0
        for job in marcel.job.JobControl.only.jobs():
            # TODO: If job were a marcel.object, then it would have render_compact/full methods.
            description = f'{job_id}({job.state_symbol()}): {job.process.pid}  {job.command.source}'
            self.send(description)
            job_id += 1

