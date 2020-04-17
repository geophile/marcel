import os
import multiprocessing as mp
import multiprocessing.connection as mpc
import signal
import sys
import threading

import marcel.object.error
import marcel.exception
from marcel.util import *

# The code for processing child input from multiple processes is adapted from here:
# https://docs.python.org/3/library/multiprocessing.html#multiprocessing.connection.wait
# w.close() in the parent process is extremely subtle (to me).
# Multiprocessing and signal handling is discussed here:
# See https://www.titonbarua.com/posts/2014-10-29-safe-use-of-unix-signals-with-multiprocessing-modules-in-python


DEBUG = False


def debug(message):
    if DEBUG:
        print(f'{os.getpid()}: {message}', flush=True)


class Job:

    # Job state
    RUNNING_FOREGROUND = 0  # (*)
    RUNNING_BACKGROUND = 1  # (+)
    RUNNING_PAUSED = 2      # (-)
    DEAD = 3                # (x)
    JOB_STATE_SYMBOLS = ('*', '+', '-', 'x')

    # Params
    JOIN_DELAY_SEC = 0.2

    def __init__(self, command):
        super().__init__()
        self.command = command
        self.state = Job.RUNNING_FOREGROUND
        self.process = None
        self.start_process()

    def __str__(self):
        return f'job({self.process.pid}({self.state_symbol()}): {self.command.source})'

    def kill(self):
        if self.state != Job.DEAD:
            debug(f'kill {self}')
            self.state = Job.DEAD
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

    def state_symbol(self):
        return Job.JOB_STATE_SYMBOLS[self.state]

    # ctrl-z
    def pause(self):
        debug(f'pause {self}')
        if self.state not in (Job.RUNNING_PAUSED, Job.DEAD):
            os.kill(self.process.pid, signal.SIGSTOP)
            self.state = Job.RUNNING_PAUSED

    # bg
    def run_in_background(self):
        debug(f'run_in_background {self}')
        if self.state not in (Job.RUNNING_BACKGROUND, Job.DEAD):
            os.kill(self.process.pid, signal.SIGCONT)
            self.state = Job.RUNNING_BACKGROUND

    # fg
    def run_in_foreground(self):
        debug(f'run_in_foreground {self}')
        if self.state == Job.DEAD:
            raise marcel.exception.KillCommandException('Cannot foreground killed job')
        if self.state != Job.RUNNING_FOREGROUND:
            os.kill(self.process.pid, signal.SIGCONT)
            self.state = Job.RUNNING_FOREGROUND

    # For use by this class

    def start_process(self):
        # runs in child process
        def run_command(command, writer):
            debug(f'running: {command.source}')
            try:
                env_vars = command.execute()
                debug(f'completed: {command.source}')
                writer.send(env_vars)
            except marcel.exception.KillCommandException as e:
                print(e, file=sys.stderr)
            writer.close()

        # duplex=False: child writes to parent when function completes execution. No need to communicate in the
        # other direction
        debug(f'About to spawn process for {self.command.source}')
        reader, writer = mp.Pipe(duplex=False)
        JobControl.only.child_listener.add_listener(reader)
        self.process = mp.Process(target=run_command, args=(self.command, writer))
        self.process.daemon = True
        self.process.start()
        writer.close()  # See topmost comment

    def check_alive(self):
        if not self.process.is_alive():
            self.state = Job.DEAD


class ChildListener(threading.Thread):

    def __init__(self, child_completion_handler):
        super().__init__()
        self.daemon = True
        self.child_completion_handler = child_completion_handler
        self.waiter = threading.Condition()
        self.listeners = []

    def add_listener(self, listener):
        self.waiter.acquire()
        self.listeners.append(listener)
        self.waiter.notify()
        self.waiter.release()

    def run(self):
        to_remove = []
        while True:
            self.waiter.acquire()
            # Remove any listeners that threw EOFError in a previous iteration
            for listener in to_remove:
                self.listeners.remove(listener)
            to_remove.clear()
            # Wait until a listener has something
            while len(self.listeners) == 0:
                self.waiter.wait(1)
            listeners = list(self.listeners)
            self.waiter.release()
            # Process the listeners that are ready
            for listener in mpc.wait(listeners, 0.1):
                try:
                    self.child_completion_handler(listener.recv())
                except EOFError:
                    to_remove.append(listener)


class JobControl:

    only = None
    pid = os.getpid()

    def __init__(self, child_completion_handler):
        self.jobs = []
        self.child_listener = ChildListener(child_completion_handler)
        self.child_listener.start()
        signal.signal(signal.SIGINT, self.ctrl_c_handler)
        signal.signal(signal.SIGTSTP, self.ctrl_z_handler)

    def shutdown(self):
        for job in self.jobs:
            job.kill()

    def create_job(self, command):
        job = Job(command)
        self.jobs.append(job)

    def foreground(self):
        for job in self.jobs:
            job.check_alive()
            if job.state == Job.RUNNING_FOREGROUND:
                return job
        return None

    def foreground_is_alive(self):
        foreground = self.foreground()
        return foreground and foreground.state != Job.DEAD

    def remove_completed(self):
        new_jobs = []
        for job in self.jobs:
            if job.process.is_alive():
                new_jobs.append(job)
        self.jobs = new_jobs

    def ctrl_c_handler(self, signum, frame):
        debug(f'ctrl c handler')
        assert signum == signal.SIGINT
        if os.getpid() == JobControl.pid:
            # Parent process
            foreground = self.foreground()
            if foreground:
                foreground.kill()
                print()

    def ctrl_z_handler(self, signum, frame):
        debug(f'ctrl z handler')
        assert signum == signal.SIGTSTP
        if os.getpid() == JobControl.pid:
            # Parent process
            foreground = self.foreground()
            if foreground:
                foreground.pause()
                print()

    @staticmethod
    def start(child_completion_handler):
        debug('starting job control')
        JobControl.only = JobControl(child_completion_handler)
        return JobControl.only
