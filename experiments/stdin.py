import subprocess
import io

buffer = io.BytesIO(b'kitty')

process = subprocess.Popen(args=['./hello_kitty_out_err.py'],
                           stdin=subprocess.PIPE,
                           stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE,
                           shell=True,
                           universal_newlines=False)
process.stdin.write(buffer.read())
process.stdin.close()
process.wait()
print('returncode: %s' % process.returncode)
print('stdout:')
print(process.stdout.read().decode('utf-8'))
print('stderr:')
print(process.stderr.read().decode('utf-8'))
