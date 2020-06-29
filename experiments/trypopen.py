import subprocess
import io
import pickle

buffer = io.BytesIO()
pickle.Pickler(buffer).dump(['hello', 'goodbye'])
buffer.seek(0)
pickled = buffer.read()

command = ['ssh', '-l', 'jao', '127.0.0.1', 'echo hello']
# print('command: %s' % str(command))
# process = subprocess.Popen(' '.join(command),
#                            stdin=subprocess.PIPE,
#                            stdout=subprocess.PIPE,
#                            stderr=subprocess.PIPE,
#                            shell=True,
#                            universal_newlines=True)
# out, err = process.communicate(input=hello.getvalue())
# print('out: %s' % out)
# print('err: %s' % err)
# process.wait()
# print('return code: %s' % process.returncode)

# buffer = io.BytesIO(b'kitty')
#
# process = subprocess.Popen(args=['./hello_kitty_out_err.py'],
#                            stdin=subprocess.PIPE,
#                            stdout=subprocess.PIPE,
#                            stderr=subprocess.PIPE,
#                            shell=True,
#                            universal_newlines=False)
# process.stdin.write(buffer.read())
# process.stdin.close()
# process.wait()
# print('returncode: {}'.format(process.returncode))
# print('stdout:')
# print(process.stdout.read().decode('utf-8'))
# print('stderr:')
# print(process.stderr.read().decode('utf-8'))