import os
import pathlib

import test_base

TEST = test_base.TestTabCompletion()
TestDir = test_base.TestDir

ALL_OPS = ['args', 'assign', 'bash', 'bg', 'case', 'cast', 'cd', 'difference', 'dirs', 'download', 'edit',
           'exit', 'env', 'expand', 'fg', 'filter', 'fork', 'gen', 'head', 'help', 'history',
           'import', 'intersect', 'jobs', 'join', 'load', 'ls', 'map', 'popd', 'ps', 'pushd', 'pwd', 'read', 'red',
           'remote', 'reverse', 'run', 'select', 'sort', 'sql', 'squish', 'store', 'sudo', 'tail', 'tee', 'timer',
           'trace', 'union', 'unique', 'upload', 'version', 'window', 'write', 'ws']


def test_op():
    # No candidates
    TEST.run(line='xyz',
             expected=[])
    # Single candidate
    TEST.run(line='l',
             expected=['ls', 'load'])
    TEST.run(line='ls',
             expected=['ls'])
    # Multiple candidates
    TEST.run(line='h',
             expected=['head', 'help', 'history'])
    TEST.run(line='he',
             expected=['head', 'help'])
    TEST.run(line='hea',
             expected=['head'])
    TEST.run(line='head',
             expected=['head'])
    # Pipeline command
    TEST.run(line='ls | args (| l',
             expected=['ls', 'load'])
    TEST.run(line='ech',
             expected=['echo'])


def test_flags():
    TEST.run(line='window -',
             expected=['-o', '--overlap', '-d', '--disjoint'])
    TEST.run(line='window --',
             expected=['--overlap', '--disjoint'])
    TEST.run(line='reverse -',
             expected=[])
    # Bug 147
    TEST.run(line='ls --rec',
             expected=['--recursive'])


def test_pipeline_args():
    # Try (almost) every prefix of: ls --recursive -d | args (| d: ls -fs (d) |)
    with TestDir(TEST.env) as testdir:
        all_files = ['a', 'b', 'c']
        TEST.run(f'touch {testdir}/a')
        TEST.run(f'touch {testdir}/b')
        TEST.run(f'touch {testdir}/c')
        TEST.run(f'cd {testdir}')
        TEST.run(line='l',
                 expected=['ls', 'load'])
        TEST.run(line='ls',
                 expected=['ls'])
        TEST.run(line='ls ',
                 expected=all_files)
        TEST.run(line='ls -',
                 expected=['-0', '-1', '-r', '--recursive', '-f', '--file', '-d', '--dir', '-s', '--symlink'])
        TEST.run(line='ls --',
                 expected=['--recursive', '--file', '--dir', '--symlink'])
        TEST.run(line='ls --r',
                 expected=['--recursive'])
        TEST.run(line='ls --re',
                 expected=['--recursive'])
        TEST.run(line='ls --recursive',
                 expected=['--recursive'])
        TEST.run(line='ls --recursive ',
                 expected=all_files)
        TEST.run(line='ls --recursive -',
                 expected=['-0', '-1', '-r', '--recursive', '-f', '--file', '-d', '--dir', '-s', '--symlink'])
        TEST.run(line='ls --recursive -d',
                 expected=['-d'])
        TEST.run(line='ls --recursive -d ',
                 expected=all_files)
        TEST.run(line='ls --recursive -d |',
                 expected=ALL_OPS)
        TEST.run(line='ls --recursive -d | ',
                 expected=ALL_OPS)
        TEST.run(line='ls --recursive -d | ar',
                 expected=['args'])
        TEST.run(line='ls --recursive -d | args',
                 expected=['args'])
        TEST.run(line='ls --recursive -d | args ',
                 expected=all_files)
        # Not sure why, but Python's input invokes the completer with text = '' in this case
        TEST.run(line='ls --recursive -d | args (|',
                 expected=ALL_OPS)
        TEST.run(line='ls --recursive -d | args (|d',
                 expected=['difference', 'dirs', 'download'])
        # Not sure why, but Python's input invokes the completer with text = '' in this case
        TEST.run(line='ls --recursive -d | args (|d:',
                 expected=ALL_OPS)
        TEST.run(line='ls --recursive -d | args (|d: ',
                 expected=ALL_OPS)
        TEST.run(line='ls --recursive -d | args (|d: l',
                 expected=['load', 'ls'])
        TEST.run(line='ls --recursive -d | args (|d: ls',
                 expected=['ls'])
        TEST.run(line='ls --recursive -d | args (|d: ls ',
                 expected=all_files)
        TEST.run(line='ls --recursive -d | args (|d: ls -',
                 expected=['-0', '-1', '-r', '--recursive', '-f', '--file', '-d', '--dir', '-s', '--symlink'])
        TEST.run(line='ls --recursive -d | args (|d: ls -f',
                 expected=['-f'])
        TEST.run(line='ls --recursive -d | args (|d: ls -fs',
                 expected=[])
        TEST.run(line='ls --recursive -d | args (|d: ls -fs ',
                 expected=all_files)
        TEST.run(line='ls --recursive -d | args (|d: ls -fs (',
                 expected=[])
        TEST.run(line='ls --recursive -d | args (|d: ls -fs (d',
                 expected=[])
        TEST.run(line='ls --recursive -d | args (|d: ls -fs (d)',
                 expected=[])
        TEST.run(line='ls --recursive -d | args (|d: ls -fs (d) ',
                 expected=all_files)

def test_arg_username():
    TEST.run(line='ls ~ro',
             expected=['~root/'])
    TEST.run(line='ls ~9',
             expected=[])


def test_arg_absolute_path():
    with TestDir(TEST.env) as testdir:
        os.mkdir(f'{testdir}/abcx')
        os.mkdir(f'{testdir}/abcy')
        os.system(f'touch {testdir}/abcz')
        TEST.run(line=f'ls {testdir}/ab',
                 expected=[f'{testdir}/abcx/', f'{testdir}/abcy/', f'{testdir}/abcz'])
        TEST.run(line=f'ls {testdir}/abcx',
                 expected=[f'{testdir}/abcx/'])
        TEST.run(line=f'ls {testdir}/abcz',
                 expected=[f'{testdir}/abcz'])
        # Executable
        TEST.run(line=f'echo {testdir}/a',
                 expected=[f'{testdir}/abcx/', f'{testdir}/abcy/', f'{testdir}/abcz'])
    # Bug 147
    with TestDir(TEST.env) as testdir:
        os.system(f'touch {testdir}/x')
        TEST.run(line=f'ls {testdir}',
                 expected=[f'{testdir}/'])
    # Homedir is a special case of absolute
    # Whoever is running this test should have ~/.bash_history
    user = os.getlogin()
    # test harness resets the HOME env var, but we want a real one for this test
    os.environ['HOME'] = pathlib.Path(f'~{user}').expanduser().as_posix()
    TEST.run(line=f'ls ~/.bash_h',
             expected=['~/.bash_history'])
    TEST.run(line=f'ls ~{user}/.bash_h',
             expected=[f'~{user}/.bash_history'])
    # Restore HOME var for testing
    TEST.reset_environment()

def test_arg_local_path():
    with TestDir(TEST.env) as testdir:
        TEST.run(f'cd {testdir}')
        os.mkdir('abcx')
        os.mkdir('abcy')
        os.system('touch abcz')
        TEST.run(line=f'ls ab',
                 expected=['abcx/', 'abcy/', 'abcz'])
        TEST.run(line='ls abcx',
                 expected=['abcx/'])
        TEST.run(line='ls abcz',
                 expected=['abcz'])
        # Executable
        TEST.run(line='echo ./a',
                 expected=['abcx/', 'abcy/', 'abcz'])
        # Same tests, but using ./
        TEST.run(line=f'ls ./ab',
                 expected=['abcx/', 'abcy/', 'abcz'])
        TEST.run(line='ls ./abcx',
                 expected=['abcx/'])
        TEST.run(line='ls ./abcz',
                 expected=['abcz'])
        TEST.run(line='echo ./a',
                 expected=['abcx/', 'abcy/', 'abcz'])

def test_arg():
    test_arg_username()
    test_arg_absolute_path()
    test_arg_local_path()
    # test_quoted()
    # test_escaped()


def main_stable():
    # In the parlance of tabcompleter.py, completion applies to ops, flags, and args.
    # Filenames count as args.
    test_op()
    test_flags()
    test_arg()
    test_pipeline_args()


def main_dev():
    pass


def main():
    TEST.reset_environment()
    # main_dev()
    main_stable()
    TEST.report_failures('test_tab_completion')


main()
