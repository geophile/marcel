import os
import signal
import multiprocessing as mp
import time

PROMPT = '> '
MAIN_SLEEP_SEC = 0.1
JOIN_DELAY_SEC = 0.2
DEBUG = True


def debug(message):
    if DEBUG:
        print(f'{os.getpid()}: {message}', flush=True)


class Job:

    jobs = []
    RUNNING_FOREGROUND = 0
    RUNNING_BACKGROUND = 1
    RUNNING_PAUSED = 2
    KILLED = 3
    STATE_SYMBOLS = ['*', '+', '-', 'x']

    def __init__(self, line, function, args):
        super().__init__()
        self.line = line
        self.process = mp.Process(target=function, args=args)
        self.process.daemon = True
        self.state = Job.RUNNING_FOREGROUND
        try:
            # Set signal handling for child
            signal.signal(signal.SIGINT, signal.SIG_IGN)
            signal.signal(signal.SIGTSTP, signal.SIG_DFL)
            self.process.start()
            Job.jobs.append(self)
            debug(f'started child process {self.process.pid}')
        finally:
            # Restore original signal handling
            signal.signal(signal.SIGINT, ctrl_c_handler)
            signal.signal(signal.SIGTSTP, ctrl_z_handler)

    def __str__(self):
        return f'job({self.process.pid} ({Job.STATE_SYMBOLS[self.state]}): {self.line})'

    def kill(self):
        debug(f'kill {self}')
        self.state = Job.KILLED
        try:
            os.kill(self.process.pid, signal.SIGKILL)
            self.process.join(JOIN_DELAY_SEC)
            if self.process.is_alive():
                os.kill(self.process.pid, signal.SIGKILL)
                self.process.join(JOIN_DELAY_SEC)
                if self.process.is_alive():
                    debug(f'Unable to kill {self}')
        except ProcessLookupError:
            pass

    # ctrl-z
    def pause(self):
        debug(f'pause {self}')
        if self.state not in (Job.RUNNING_PAUSED, Job.KILLED):
            os.kill(self.process.pid, signal.SIGTSTP)
            self.state = Job.RUNNING_PAUSED

    # bg
    def run_in_background(self):
        debug(f'run_in_background {self}')
        if self.state != Job.KILLED:
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
                print(f'{i}: {Job.jobs[i]}')
        elif line.startswith('kill '):
            job_id = int(line.split()[-1])
            Job.jobs[job_id].kill()
        elif line.startswith('timer '):
            def timer(label, interval):
                debug(f'timer {label}, handler: {signal.getsignal(signal.SIGTSTP)}')
                try:
                    count = 0
                    while True:
                        debug(f'{os.getpid()}  {label}: {count}')
                        time.sleep(interval)
                        count += 1
                except KeyboardInterrupt:
                    debug(f'process {os.getpid()} caught KeyboardInterrupt, exiting?')
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
    debug(f'ctrl_z_handler, pause foreground: {foreground}')
    if foreground:
        foreground.pause()
    # ctrl-z propagates to children, suspending them. If they should be running in the background, then
    # get them going again.
    for job in Job.jobs:
        if job.state == Job.RUNNING_BACKGROUND:
            debug(f'ctrl_z_handler, revive background: {job}')
            job.run_in_background()
    print()


def ctrl_c_handler(signum, frame):
    assert signum == signal.SIGINT
    foreground = Job.foreground()
    debug(f'ctrl_c_handler, kill foreground: {foreground}')
    if foreground:
        foreground.kill()
    print()


def main():
    debug(f'main pid: {os.getpid()}')
    signal.signal(signal.SIGINT, ctrl_c_handler)
    signal.signal(signal.SIGTSTP, ctrl_z_handler)
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
