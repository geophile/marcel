import os
import subprocess


def run(command):
    process = subprocess.Popen(command,
                               shell=True,
                               executable='/bin/bash',
                               stdin=subprocess.PIPE,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE,
                               universal_newlines=True,
                               preexec_fn=os.setsid)
    while True:
        line = process.stdout.readline()
        if len(line) > 0:
            print(f'stdout: {line[:-1]}')
            break
        else:
            break
    while True:
        line = process.stderr.readline()
        if len(line) > 0:
            print(f'stderr: {line[:-1]}')
            break
        else:
            break


run('cat /tmp/cant_read')
