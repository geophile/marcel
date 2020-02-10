import subprocess

outcome = subprocess.run('./hello_out_err.py',
                         stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE,
                         shell=True,
                         text=False)
print('returncode: %s' % outcome.returncode)
print('stdout:')
print(outcome.stdout.decode('utf-8'))
print('stderr:')
print(outcome.stderr.decode('utf-8'))
