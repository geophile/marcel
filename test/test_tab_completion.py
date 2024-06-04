import os

import test_base

TEST = test_base.TestTabCompletion()
TestDir = test_base.TestDir

ALL_OPS = ['args', 'assign', 'bash', 'bg', 'case', 'cast', 'cd', 'difference', 'dirs', 'download', 'edit',
           'exit', 'env', 'expand', 'fg', 'filter', 'fork', 'gen', 'head', 'help', 'history', 'ifelse', 'ifthen',
           'import', 'intersect', 'jobs', 'join', 'load', 'ls', 'map', 'popd', 'ps', 'pushd', 'pwd', 'read', 'red',
           'remote', 'reverse', 'run', 'select', 'sort', 'sql', 'squish', 'store', 'sudo', 'tail', 'tee', 'timer',
           'trace', 'union', 'unique', 'upload', 'version', 'window', 'write', 'ws']


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
    TEST.run(line='ls | args (| l', text='l',
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
    # Bug 147
    TEST.run(line='ls --rec', text='--rec',
             expected=['--recursive '])


def test_filenames():
    with TestDir(TEST.env) as testdir:
        os.mkdir(f'{testdir}/abcx')
        os.mkdir(f'{testdir}/abcy')
        os.system(f'touch {testdir}/abcz')
        TEST.run(line=f'ls {testdir}/ab', text=f'{testdir}/ab',
                 expected=[f'{testdir}/abcx/', f'{testdir}/abcy/', f'{testdir}/abcz'])
        TEST.run(line=f'ls {testdir}/abcz', text=f'{testdir}/abcz',
                 expected=[f'{testdir}/abcz '])
        # Executable
        TEST.run(line=f'echo {testdir}/a', text=f'{testdir}/a',
                 expected=[f'{testdir}/abcx/', f'{testdir}/abcy/', f'{testdir}/abcz'])
    # Bug 147
    with TestDir(TEST.env) as testdir:
        os.system(f'touch {testdir}/x')
        TEST.run(line=f'ls {testdir}', text=f'{testdir}',
                 expected=[f'{testdir}/'])


# Inspired by bug 189
def test_filenames_with_whitespace():
    with TestDir(TEST.env) as testdir:
        os.system(f'touch "{testdir}/space xx"')
        os.system(f'touch "{testdir}/tab\txx"')


def test_pipeline_args():
    # Try (almost) every prefix of: ls --recursive -d | args (| d: ls -fs (d) |)
    with TestDir(TEST.env) as testdir:
        all_files = ['a', 'b', 'c']
        TEST.run(f'touch {testdir}/a')
        TEST.run(f'touch {testdir}/b')
        TEST.run(f'touch {testdir}/c')
        TEST.run(f'cd {testdir}')
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
                 expected=['--recursive '])
        TEST.run(line='ls --re', text='--re',
                 expected=['--recursive '])
        TEST.run(line='ls --recursive', text='--recursive',
                 expected=['--recursive '])
        TEST.run(line='ls --recursive ', text='--recursive ',
                 expected=all_files)
        TEST.run(line='ls --recursive -', text='-',
                 expected=['-0', '-1', '-r', '--recursive', '-f', '--file', '-d', '--dir', '-s', '--symlink'])
        TEST.run(line='ls --recursive -d', text='-d',
                 expected=['-d '])
        TEST.run(line='ls --recursive -d ', text='-d ',
                 expected=all_files)
        # Not sure why, but Python's input invokes the completer with text = '' in this case
        TEST.run(line='ls --recursive -d |', text='',
                 expected=ALL_OPS)
        TEST.run(line='ls --recursive -d | ar', text='ar',
                 expected=['args '])
        TEST.run(line='ls --recursive -d | args', text='args',
                 expected=['args '])
        TEST.run(line='ls --recursive -d | args ', text='',
                 expected=all_files)
        # Not sure why, but Python's input invokes the completer with text = '' in this case
        TEST.run(line='ls --recursive -d | args (|', text='',
                 expected=ALL_OPS)
        TEST.run(line='ls --recursive -d | args (|d', text='d',
                 expected=['difference', 'dirs', 'download'])
        # Not sure why, but Python's input invokes the completer with text = '' in this case
        TEST.run(line='ls --recursive -d | args (|d:', text='',
                 expected=ALL_OPS)
        TEST.run(line='ls --recursive -d | args (|d: ', text='',
                 expected=ALL_OPS)
        TEST.run(line='ls --recursive -d | args (|d: l', text='l',
                 expected=['load', 'ls'])
        TEST.run(line='ls --recursive -d | args (|d: ls', text='ls',
                 expected=['ls '])
        TEST.run(line='ls --recursive -d | args (|d: ls ', text='',
                 expected=all_files)
        TEST.run(line='ls --recursive -d | args (|d: ls -', text='-',
                 expected=['-0', '-1', '-r', '--recursive', '-f', '--file', '-d', '--dir', '-s', '--symlink'])
        TEST.run(line='ls --recursive -d | args (|d: ls -f', text='-f',
                 expected=['-f '])
        TEST.run(line='ls --recursive -d | args (|d: ls -fs', text='-fs',
                 expected=[])
        TEST.run(line='ls --recursive -d | args (|d: ls -fs ', text='',
                 expected=all_files)
        TEST.run(line='ls --recursive -d | args (|d: ls -fs (', text='(',
                 expected=[])
        TEST.run(line='ls --recursive -d | args (|d: ls -fs (d', text='(d',
                 expected=[])
        TEST.run(line='ls --recursive -d | args (|d: ls -fs (d)', text='(d)',
                 expected=[])
        TEST.run(line='ls --recursive -d | args (|d: ls -fs (d) ', text='',
                 expected=all_files)


def main_stable():
    test_op()
    test_executables()
    test_flags()
    test_filenames()
    test_filenames_with_whitespace()
    test_pipeline_args()


def main_dev():
    pass


def main():
    TEST.reset_environment()
    main_dev()
    main_stable()
    TEST.report_failures('test_tab_completion')


main()
