import os
import pathlib

import marcel.doc
import test_base

TEST = test_base.TestTabCompletion()
TestDir = test_base.TestDir

OPS = ['args', 'assign', 'bash', 'bg', 'case', 'cast', 'cd', 'difference',
       'dirs', 'download', 'edit', 'exit', 'env', 'expand', 'fg', 'filter',
       'fork', 'gen', 'head', 'help', 'history', 'import', 'intersect',
       'jobs', 'join', 'load', 'ls', 'map', 'popd', 'ps', 'pushd', 'pwd', 'read',
       'red', 'remote', 'reverse', 'run', 'select', 'sort', 'sql', 'squish', 'store',
       'sudo', 'tail', 'tee', 'timer', 'trace', 'union', 'unique', 'upload', 'version',
       'window', 'write', 'ws']

ALL_OPS = [op + ' ' for op in OPS]
ALL_HELP = sorted(OPS + list(marcel.doc.topics))


def test_op():
    # No candidates
    TEST.run(line='xyz',
             expected=[])
    # Single candidate
    TEST.run(line='l',
             expected=['s ', 'oad '])
    TEST.run(line='ls',
             expected=[' '])
    # Multiple candidates
    TEST.run(line='h',
             expected=['ead ', 'elp ', 'istory '])
    TEST.run(line='he',
             expected=['ad ', 'lp '])
    TEST.run(line='hea',
             expected=['d '])
    TEST.run(line='head',
             expected=[' '])
    # Pipeline command
    TEST.run(line='ls | args (| l',
             expected=['s ', 'oad '])
    TEST.run(line='ech',
             expected=['o '])


def test_flags():
    TEST.run(line='window -',
             expected=['o ', '-overlap ', 'd ', '-disjoint '])
    TEST.run(line='window --',
             expected=['overlap ', 'disjoint '])
    TEST.run(line='reverse -',
             expected=[])
    # Bug 147
    TEST.run(line='ls --rec',
             expected=['ursive '])


def test_pipeline_args():
    # Try (almost) every prefix of: ls --recursive -d | args (| d: ls -fs (d) |)
    with TestDir(TEST.env) as testdir:
        all_files = ['a ', 'b ', 'c ']
        TEST.run(f'touch {testdir}/a')
        TEST.run(f'touch {testdir}/b')
        TEST.run(f'touch {testdir}/c')
        TEST.run(f'cd {testdir}')
        TEST.run(line='l',
                 expected=['s ', 'oad '])
        TEST.run(line='ls',
                 expected=[' '])
        TEST.run(line='ls ',
                 expected=all_files)
        TEST.run(line='ls -',
                 expected=['0 ', '1 ', 'r ', '-recursive ', 'f ', '-file ', 'd ', '-dir ', 's ', '-symlink '])
        TEST.run(line='ls --',
                 expected=['recursive ', 'file ', 'dir ', 'symlink '])
        TEST.run(line='ls --r',
                 expected=['ecursive '])
        TEST.run(line='ls --re',
                 expected=['cursive '])
        TEST.run(line='ls --recursive',
                 expected=[' '])
        TEST.run(line='ls --recursive ',
                 expected=all_files)
        TEST.run(line='ls --recursive -',
                 expected=['0 ', '1 ', 'r ', '-recursive ', 'f ', '-file ', 'd ', '-dir ', 's ', '-symlink '])
        TEST.run(line='ls --recursive -d',
                 expected=[' '])
        TEST.run(line='ls --recursive -d ',
                 expected=all_files)
        TEST.run(line='ls --recursive -d |',
                 expected=ALL_OPS)
        TEST.run(line='ls --recursive -d | ',
                 expected=ALL_OPS)
        TEST.run(line='ls --recursive -d | ar',
                 expected=['gs '])
        TEST.run(line='ls --recursive -d | args',
                 expected=[' '])
        TEST.run(line='ls --recursive -d | args ',
                 expected=all_files)
        TEST.run(line='ls --recursive -d | args (|',
                 expected=ALL_OPS)
        TEST.run(line='ls --recursive -d | args (|d',
                 expected=['ifference ', 'irs ', 'ownload '])
        TEST.run(line='ls --recursive -d | args (|d:',
                 expected=ALL_OPS)
        TEST.run(line='ls --recursive -d | args (|d: ',
                 expected=ALL_OPS)
        TEST.run(line='ls --recursive -d | args (|d: l',
                 expected=['oad ', 's '])
        TEST.run(line='ls --recursive -d | args (|d: ls',
                 expected=[' '])
        TEST.run(line='ls --recursive -d | args (|d: ls ',
                 expected=all_files)
        TEST.run(line='ls --recursive -d | args (|d: ls -',
                 expected=['0 ', '1 ', 'r ', '-recursive ', 'f ', '-file ', 'd ', '-dir ', 's ', '-symlink '])
        TEST.run(line='ls --recursive -d | args (|d: ls -f',
                 expected=[' '])
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
             expected=['ot/'])
    TEST.run(line='ls ~9',
             expected=[])


def test_arg_homedir():
    TEST.run(line='ls ~/.',
             expected=['config/', 'local/'])


def test_arg_absolute_path():
    with TestDir(TEST.env) as testdir:
        os.mkdir(f'{testdir}/abcx')
        os.mkdir(f'{testdir}/abcy')
        os.system(f'touch {testdir}/abcz')
        TEST.run(line=f'ls {testdir}/ab',
                 expected=[f'cx/', f'cy/', f'cz '])
        TEST.run(line=f'ls {testdir}/abcx',
                 expected=[f'/'])
        TEST.run(line=f'ls {testdir}/abcz',
                 expected=[f' '])
        # Executable
        TEST.run(line=f'echo {testdir}/a',
                 expected=[f'bcx/', f'bcy/', f'bcz '])
    # Bug 147
    with TestDir(TEST.env) as testdir:
        os.system(f'touch {testdir}/x')
        TEST.run(line=f'ls {testdir}',
                 expected=[f'/'])
    # Homedir is a special case of absolute
    # Whoever is running this test should have ~/.bash_history
    user = os.getlogin()
    # test harness resets the HOME env var, but we want a real one for this test
    os.environ['HOME'] = pathlib.Path(f'~{user}').expanduser().as_posix()
    TEST.run(line=f'ls ~/.bash_h',
             expected=['istory '])
    TEST.run(line=f'ls ~{user}/.bash_h',
             expected=[f'istory '])
    # Restore HOME var for testing
    TEST.reset_environment()

def test_arg_local_path():
    with TestDir(TEST.env) as testdir:
        TEST.run(f'cd {testdir}')
        os.mkdir('abcx')
        os.mkdir('abcy')
        os.system('touch abcz')
        TEST.run(line=f'ls ab',
                 expected=['cx/', 'cy/', 'cz '])
        TEST.run(line='ls abcx',
                 expected=['/'])
        TEST.run(line='ls abcz',
                 expected=[' '])
        # Executable
        TEST.run(line='echo ./a',
                 expected=['bcx/', 'bcy/', 'bcz '])
        # Same tests, but using ./
        TEST.run(line=f'ls ./ab',
                 expected=['cx/', 'cy/', 'cz '])
        TEST.run(line='ls ./abcx',
                 expected=['/'])
        TEST.run(line='ls ./abcz',
                 expected=[' '])
        TEST.run(line='echo ./a',
                 expected=['bcx/', 'bcy/', 'bcz '])

def test_arg_quoted():
    with TestDir(TEST.env) as testdir:
        TEST.run(f'cd {testdir}')
        os.system('touch ab1')
        os.system('touch ab2')
        os.system('touch "fg 1"')
        os.system('touch "fg 2"')
        # local path
        TEST.run(line='ls a',
                 expected=['b1 ', 'b2 '])
        TEST.run(line='ls "a',
                 expected=['b1" ', 'b2" '])
        TEST.run(line="ls 'a",
                 expected=["b1' ", "b2' "])
        TEST.run(line='ls "f',
                 expected=['g 1" ', 'g 2" '])
        TEST.run(line="ls 'f",
                 expected=["g 1' ", "g 2' "])
        # absolute path
        TEST.run(line=f'ls {testdir}/a',
                 expected=[f'b1 ', f'b2 '])
        TEST.run(line=f'ls "{testdir}/a',
                 expected=[f'b1" ', f'b2" '])
        TEST.run(line=f"ls '{testdir}/a",
                 expected=[f"b1' ", f"b2' "])
        TEST.run(line=f'ls "{testdir}/f',
                 expected=[f'g 1" ', f'g 2" '])
        TEST.run(line=f"ls '{testdir}/f",
                 expected=[f"g 1' ", f"g 2' "])
    # Special case: ~ inside quoted string
    user = os.getlogin()
    os.environ['HOME'] = pathlib.Path(f'~{user}').expanduser().as_posix()
    TEST.run(line='ls ~/.bash_h',
             expected=['istory '])
    TEST.run(line="ls '~/.bash_h",
             expected=["istory' "])
    TEST.run(line='ls "~/.bash_h',
             expected=[])
    # Restore HOME var for testing
    TEST.reset_environment()

def test_arg_escaped():
    with TestDir(TEST.env) as testdir:
        TEST.run(f'cd {testdir}')
        os.system('touch "a b"')
        os.system('touch "a!b"')
        os.system('touch "c  d"')
        os.system('touch "c= d"')
        TEST.run(line='ls a',
                 expected=['\\ b ', '\\!b '])
        TEST.run(line='ls a\\ ',
                 expected=['b '])
        TEST.run(line='ls a\\!',
                 expected=['b '])
        TEST.run(line='ls c',
                 expected=['\\ \\ d ', '=\ d '])
        TEST.run(line='ls c\\ ',
                 expected=['\\ d '])
        TEST.run(line='ls c=',
                 expected=['\\ d '])

def test_arg_help():
    TEST.run(line='help',
             expected=[' '])
    TEST.run(line='help ',
             expected=ALL_HELP)
    TEST.run(line='help x',
             expected=[])
    TEST.run(line='help r',
             expected=['ead', 'ed', 'emote', 'everse', 'un'])
    TEST.run(line='help re',
             expected=['ad', 'd', 'mote', 'verse'])

def test_arg():
    test_arg_username()
    test_arg_homedir()
    test_arg_absolute_path()
    test_arg_local_path()
    test_arg_quoted()
    test_arg_escaped()
    test_arg_help()


def main_stable():
    # In the parlance of tabcompleter.py, completion applies to ops, flags, and args.
    # Filenames count as args.
    test_op()
    test_flags()
    test_arg()
    test_pipeline_args()


def main_dev():
    test_arg_help()
    pass


def main():
    TEST.reset_environment()
    main_dev()
    # main_stable()
    TEST.report_failures('test_tab_completion')


main()
