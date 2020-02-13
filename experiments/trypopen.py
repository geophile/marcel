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
