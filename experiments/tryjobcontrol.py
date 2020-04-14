import os
import signal
import multiprocessing as mp
import time

import marcel.jobcontrol
Job = marcel.jobcontrol.Job

PROMPT = '> '
MAIN_SLEEP_SEC = 0.1


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


def main():
    marcel.jobcontrol.startup()
    try:
        Interact.run()
    except EOFError:  # ctrl-D
        print()
    finally:
        marcel.jobcontrol.shutdown()


if __name__ == '__main__':
    main()
