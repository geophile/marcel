import os
import signal
import multiprocessing as mp
import time

PROMPT = '> '
MAIN_SLEEP_SEC = 0.1
JOIN_DELAY_SEC = 0.2
DEBUG = False

def debug(message):
    if DEBUG:
        print(message, flush=True)


class Job:

    jobs = []
    RUNNING_FOREGROUND = 1
    RUNNING_BACKGROUND = 2
    RUNNING_PAUSED = 3
    KILLED = 4

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
        debug(f'kill {self}')
        self.state = Job.KILLED
        os.kill(self.process.pid, signal.SIGINT)
        self.process.join(JOIN_DELAY_SEC)
        if self.process.is_alive():
            self.process.kill()
            self.process.join(JOIN_DELAY_SEC)
            if self.process.is_alive():
                print(f'Unable to kill {self}')

    # ctrl-z
    def pause(self):
        debug(f'kill {self}')
        if self.state not in (Job.RUNNING_PAUSED, Job.KILLED):
            os.kill(self.process.pid, signal.SIGSTOP)
            self.state = Job.RUNNING_PAUSED

    # bg
    def run_in_background(self):
        debug(f'run_in_background {self}')
        if self.state not in (Job.RUNNING_BACKGROUND, Job.KILLED):
            os.kill(self.process.pid, signal.SIGCONT)
            self.state = Job.RUNNING_BACKGROUND

    # fg
    def run_in_foreground(self):
        debug(f'run_in_foreground {self}')
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


class Interact:

    @staticmethod
    def run():
        while True:
            try:
                line = input(PROMPT)
                Interact.process_line(line)
                while Job.foreground_is_alive():
                    time.sleep(MAIN_SLEEP_SEC)
            except KeyboardInterrupt:  # ctrl-C
                print()

    @staticmethod
    def process_line(line):
        if line.startswith('fg '):
            job_id = int(line.split()[-1])
            Job.jobs[job_id].run_in_foreground()
        elif line.startswith('bg '):
            job_id = int(line.split()[-1])
            Job.jobs[job_id].run_in_background()
        elif len(line) == 0:
            def noop():
                pass
            Job(line, noop, tuple())
        elif line.startswith('sleep '):
            def sleep():
                label, sleeptime = line.split()[1:]
                time.sleep(int(sleeptime))
                print(f'Wakey wakey {label}')
            Job(line, sleep, tuple())
        elif line.startswith('jobs'):
            Job.remove_completed()
            for i in range(len(Job.jobs)):
                print(f'{i}: {Job.jobs[i].line}')
        elif line.startswith('kill '):
            job_id = int(line.split()[-1])
            Job.jobs[job_id].kill()
        elif line.startswith('timer '):
            def timer(label, interval):
                try:
                    count = 0
                    while True:
                        print(f'{os.getpid()}  {label}: {count}', flush=True)
                        time.sleep(interval)
                        count += 1
                except KeyboardInterrupt:
                    print(f'process {os.getpid()} caught KeyboardInterrupt, exiting?')
            label, interval = line.split()[1:]
            interval = int(interval)
            Job(line, timer, (label, interval))
        else:
            def echo():
                print(f'<<<{line}>>>')
            Job(line, echo, tuple())


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


def main():
    Interact.only = Interact()
    try:
        Interact.run()
    except EOFError:  # ctrl-D
        print()
    finally:
        for job in Job.jobs:
            job.kill()


if __name__ == '__main__':
    main()
