import os

import test_base

TEST = test_base.TestTabCompletion()

ALL_OPS = [
    'args', 'ifelse', 'ls', 'red', 'sudo', 'bash',
    'env', 'ifthen', 'map', 'reverse', 'tail', 'bg', 'expand',
    'import', 'out', 'run', 'timer', 'cd', 'fg', 'intersect',
    'popd', 'select', 'union', 'delete', 'gen', 'jobs', 'ps',
    'sort', 'unique', 'difference', 'head', 'join', 'pushd',
    'sql', 'version', 'dirs', 'help', 'load', 'pwd', 'squish',
    'window', 'edit', 'history', 'read', 'store'
]


def test_op():
    # No candidates
    TEST.run(line='xyz', text='xyz',
             expected=[])
    # Single candidate
    TEST.run(line='l', text='l',
             expected=['ls', 'load'])
    TEST.run(line='ls', text='ls',
             expected=['ls '])
    # Multiple candidates
    TEST.run(line='h', text='h',
             expected=['head', 'help', 'history'])
    TEST.run(line='he', text='he',
             expected=['head', 'help'])
    TEST.run(line='hea', text='hea',
             expected=['head '])
    TEST.run(line='head', text='head',
             expected=['head '])
    # Pipeline command
    TEST.run(line='ls | args [ l', text='l',
             expected=['ls', 'load'])


def test_executables():
    TEST.run(line='ech', text='ech',
             expected=['echo '])


def test_flags():
    TEST.run(line='window -', text='-',
             expected=['-o', '--overlap', '-d', '--disjoint'])
    TEST.run(line='window --', text='--',
             expected=['--overlap', '--disjoint'])
    TEST.run(line='reverse -', text='-',
             expected=[])


def test_filenames():
    os.system('rm -rf /tmp/test')
    os.mkdir('/tmp/test')
    os.mkdir('/tmp/test/abcx')
    os.mkdir('/tmp/test/abcy')
    os.system('touch /tmp/test/abcz')
    TEST.run(line='ls /tmp/test/ab', text='/tmp/test/ab',
             expected=['/tmp/test/abcx/', '/tmp/test/abcy/', '/tmp/test/abcz'])
    TEST.run(line='ls /tmp/test/abcz', text='/tmp/test/abcz',
             expected=['/tmp/test/abcz '])
    # Executable
    TEST.run(line='echo /tmp/test/a', text='/tmp/test/a',
             expected=['/tmp/test/abcx/', '/tmp/test/abcy/', '/tmp/test/abcz'])


def test_pipeline_args():
    # Try (almost) every prefix of: ls --recursive -d | args [d: ls -fs (d)]
    all_files = ['a', 'b', 'c']
    TEST.run('rm -rf /tmp/test_pipeline_args')
    TEST.run('mkdir /tmp/test_pipeline_args')
    TEST.run('touch /tmp/test_pipeline_args/a')
    TEST.run('touch /tmp/test_pipeline_args/b')
    TEST.run('touch /tmp/test_pipeline_args/c')
    TEST.run('cd /tmp/test_pipeline_args')
    TEST.run(line='l', text='l',
             expected=['ls', 'load'])
    TEST.run(line='ls', text='ls',
             expected=['ls '])
    TEST.run(line='ls ', text='',
             expected=all_files)
    TEST.run(line='ls -', text='-',
             expected=['-0', '-1', '-r', '--recursive', '-f', '--file', '-d', '--dir', '-s', '--symlink'])
    TEST.run(line='ls --', text='--',
             expected=['--recursive', '--file', '--dir', '--symlink'])
    TEST.run(line='ls --r', text='--r',
             expected=['--recursive'])
    TEST.run(line='ls --re', text='--re',
             expected=['--recursive'])
    TEST.run(line='ls --recursive', text='--recursive',
             expected=['--recursive'])
    TEST.run(line='ls --recursive ', text='--recursive ',
             expected=all_files)
    TEST.run(line='ls --recursive -', text='-',
             expected=['-0', '-1', '-r', '--recursive', '-f', '--file', '-d', '--dir', '-s', '--symlink'])
    TEST.run(line='ls --recursive -d', text='-d',
             expected=['-d'])
    TEST.run(line='ls --recursive -d ', text='-d ',
             expected=all_files)
    # Not sure why, but Python's input invokes the completer with text = '' in this case
    TEST.run(line='ls --recursive -d |', text='',
             expected=ALL_OPS)
    TEST.run(line='ls --recursive -d | a', text='a',
             expected=['args '])
    TEST.run(line='ls --recursive -d | args', text='args',
             expected=['args '])
    TEST.run(line='ls --recursive -d | args ', text='',
             expected=all_files)
    # Not sure why, but Python's input invokes the completer with text = '' in this case
    TEST.run(line='ls --recursive -d | args [', text='',
             expected=ALL_OPS)
    TEST.run(line='ls --recursive -d | args [d', text='d',
             expected=['delete', 'difference', 'dirs'])
    # Not sure why, but Python's input invokes the completer with text = '' in this case
    TEST.run(line='ls --recursive -d | args [d:', text='',
             expected=ALL_OPS)
    TEST.run(line='ls --recursive -d | args [d: ', text='',
             expected=ALL_OPS)
    TEST.run(line='ls --recursive -d | args [d: l', text='l',
             expected=['load', 'ls'])
    TEST.run(line='ls --recursive -d | args [d: ls', text='ls',
             expected=['ls '])
    TEST.run(line='ls --recursive -d | args [d: ls ', text='',
             expected=all_files)
    TEST.run(line='ls --recursive -d | args [d: ls -', text='-',
             expected=['-0', '-1', '-r', '--recursive', '-f', '--file', '-d', '--dir', '-s', '--symlink'])
    TEST.run(line='ls --recursive -d | args [d: ls -f', text='-f',
             expected=['-f'])
    TEST.run(line='ls --recursive -d | args [d: ls -fs', text='-fs',
             expected=[])
    TEST.run(line='ls --recursive -d | args [d: ls -fs ', text='',
             expected=all_files)
    TEST.run(line='ls --recursive -d | args [d: ls -fs (', text='(',
             expected=[])
    TEST.run(line='ls --recursive -d | args [d: ls -fs (d', text='(d',
             expected=[])
    TEST.run(line='ls --recursive -d | args [d: ls -fs (d)', text='(d)',
             expected=[])
    TEST.run(line='ls --recursive -d | args [d: ls -fs (d) ', text='',
             expected=all_files)


def main_stable():
    test_op()
    test_executables()
    test_flags()
    test_filenames()
    test_pipeline_args()


def main_dev():

    pass


def main():
    TEST.reset_environment()
    main_stable()
    # main_dev()
    print(f'Test failures: {TEST.failures}')


main()
