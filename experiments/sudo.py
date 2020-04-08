
import subprocess

outcome = subprocess.run('sudo ls /home/jao/.dbus/session-bus',
                         stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE,
                         shell=True,
                         text=False)
print('returncode: {}'.format(outcome.returncode))
print('stdout:')
print(outcome.stdout.decode('utf-8'))
print('stderr:')
print(outcome.stderr.decode('utf-8'))
