import os
import signal
import multiprocessing as mp


class Job:

    # Track active jobs
    jobs = []

    # Job state
    RUNNING_FOREGROUND = 1
    RUNNING_BACKGROUND = 2
    RUNNING_PAUSED = 3
    KILLED = 4

    # Params
    JOIN_DELAY_SEC = 0.2
    DEBUG = False

    def __init__(self, line, function, args):
        super().__init__()
        self.line = line
        self.process = mp.Process(target=function, args=args)
        self.process.daemon = True
        self.state = Job.RUNNING_FOREGROUND
        self.process.start()
        Job.jobs.append(self)

    def __str__(self):
        return f'job({self.process.pid} state={self.state}: {self.line})'

    def kill(self):
        if self.state != Job.KILLED:
            Job.debug(f'kill {self}')
            self.state = Job.KILLED
            try:
                os.kill(self.process.pid, signal.SIGINT)
                self.process.join(Job.JOIN_DELAY_SEC)
                if self.process.is_alive():
                    self.process.kill()
                    self.process.join(Job.JOIN_DELAY_SEC)
                    if self.process.is_alive():
                        print(f'Unable to kill {self}')
            except ProcessLookupError:
                pass

    # ctrl-z
    def pause(self):
        Job.debug(f'kill {self}')
        if self.state not in (Job.RUNNING_PAUSED, Job.KILLED):
            os.kill(self.process.pid, signal.SIGSTOP)
            self.state = Job.RUNNING_PAUSED

    # bg
    def run_in_background(self):
        Job.debug(f'run_in_background {self}')
        if self.state not in (Job.RUNNING_BACKGROUND, Job.KILLED):
            os.kill(self.process.pid, signal.SIGCONT)
            self.state = Job.RUNNING_BACKGROUND

    # fg
    def run_in_foreground(self):
        Job.debug(f'run_in_foreground {self}')
        if self.state == Job.KILLED:
            raise Exception('Cannot foreground killed job')
        if self.state != Job.RUNNING_FOREGROUND:
            os.kill(self.process.pid, signal.SIGCONT)
            self.state = Job.RUNNING_FOREGROUND

    @staticmethod
    def foreground():
        for job in Job.jobs:
            if job.state == Job.RUNNING_FOREGROUND:
                return job
        return None

    @staticmethod
    def foreground_is_alive():
        foreground = Job.foreground()
        return foreground and foreground.process.is_alive()

    @staticmethod
    def remove_completed():
        new_jobs = []
        for job in Job.jobs:
            if job.process.is_alive():
                new_jobs.append(job)
        Job.jobs = new_jobs

    @staticmethod
    def debug(message):
        if Job.DEBUG:
            print(message, flush=True)


def startup():
    def ctrl_z_handler(signum, frame):
        assert signum == signal.SIGTSTP
        foreground = Job.foreground()
        if foreground:
            foreground.pause()
            print()

    def ctrl_c_handler(signum, frame):
        assert signum == signal.SIGINT
        foreground = Job.foreground()
        if foreground:
            foreground.kill()
            print()

    signal.signal(signal.SIGINT, ctrl_c_handler)
    signal.signal(signal.SIGTSTP, ctrl_z_handler)


def shutdown():
    for job in Job.jobs:
        job.kill()

