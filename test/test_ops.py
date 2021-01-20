import math
import os
import pathlib
import sys

import marcel.main
import marcel.version
import marcel.object.cluster
import marcel.object.error
import marcel.version

import test_base

Error = marcel.object.error.Error
start_dir = os.getcwd()
TEST = test_base.TestConsole()


def test_no_such_op():
    TEST.run('gen 5 | abc', expected_err='The variable abc is undefined')


def test_gen():
    # Explicit out
    TEST.run('gen 5 | out',
             expected_out=[0, 1, 2, 3, 4])
    # Implicit out
    TEST.run('gen 5',
             expected_out=[0, 1, 2, 3, 4])
    TEST.run('gen 5 10 | out',
             expected_out=[10, 11, 12, 13, 14])
    TEST.run('gen 5 10 123 | out',
             expected_err='Too many anonymous')
    TEST.run('gen 5 -5 | out',
             expected_out=[-5, -4, -3, -2, -1])
    TEST.run('gen 3 -p 2 | out',
             expected_err='Flags must all appear before the first anonymous arg')
    TEST.run('gen -p 2 3 | out',
             expected_out=['00', '01', '02'])
    TEST.run('gen --pad 2 3 | out',
             expected_out=['00', '01', '02'])
    TEST.run('gen -p 3 3 99 | out',
             expected_out=['099', '100', '101'])
    TEST.run('gen -p 2 3 99 | out',
             expected_err='Padding 2 too small')
    TEST.run('gen -p 4 3 -10 | out',
             expected_err='Padding incompatible with start < 0')
    # Error along with output
    TEST.run('gen 3 -1 | map (x: 5 / x)',
             expected_out=[-5.0, Error('division by zero'), 5.0])
    # Function-valued args
    TEST.run('N = (7)')
    TEST.run('gen (N - 2)',
             expected_out=[0, 1, 2, 3, 4])
    TEST.run('gen (N - 2) (N + 3)',
             expected_out=[10, 11, 12, 13, 14])
    TEST.run('gen -p (N - 4) (N - 2) (N + 3)',
             expected_out=['010', '011', '012', '013', '014'])
    TEST.run('N = ("7")')
    TEST.run('gen (N - 2)',
             expected_err="unsupported operand type(s) for -: 'str' and 'int'")


def test_out():
    output_filename = '/tmp/out.txt'
    TEST.run('gen 3 | out {}',
             expected_out=[0, 1, 2])
    TEST.run('gen 3',
             expected_out=[0, 1, 2])
    TEST.run('gen 3 | out -c',
             expected_out=[0, 1, 2])
    TEST.run('gen 3 | out --csv',
             expected_out=[0, 1, 2])
    TEST.run('gen 3 | out -c {}',
             expected_err='Cannot specify more than one of')
    TEST.run(f'gen 3 | out -f {output_filename}',
             expected_out=[0, 1, 2], file=output_filename)
    TEST.run(f'gen 3 | out --file {output_filename}',
             expected_out=[0, 1, 2], file=output_filename)
    TEST.delete_file(output_filename)
    TEST.run(f'gen 3 | out -a {output_filename}',
             expected_out=[0, 1, 2],
             file=output_filename)
    TEST.run(f'gen 3 | out --append {output_filename}',
             expected_out=[0, 1, 2, 0, 1, 2],
             file=output_filename)
    TEST.run(f'gen 3 | out -a {output_filename} -f {output_filename}',
             expected_err='Cannot specify more than one of')
    # Function-valued args
    TEST.run(f'gen 3 | out -f ("{output_filename}")',
             expected_out=[0, 1, 2],
             file=output_filename)
    TEST.run(f'gen 3 | out -a ("{output_filename}")',
             expected_out=[0, 1, 2, 0, 1, 2],
             file=output_filename)
    TEST.delete_file(output_filename)
    TEST.run('gen 3 | out ("{}")',
             expected_out=[0, 1, 2])
    # Pickle output
    TEST.run('gen 3 | out --pickle',
             expected_err='Must specify either --file or --append with --pickle')
    TEST.run(test='gen 3 | (x: [x] * x) | out --file /tmp/pickle.txt --pickle',
             verification='read --pickle /tmp/pickle.txt',
             expected_out=[[], 1, [2, 2]])
    TEST.run(test='gen 3 3 | (x: [x] * x) | out --append /tmp/pickle.txt --pickle',
             verification='read --pickle /tmp/pickle.txt',
             expected_out=[[], 1, [2, 2], [3, 3, 3], [4, 4, 4, 4], [5, 5, 5, 5, 5]])


def test_sort():
    TEST.run('gen 5 | sort',
             expected_out=[0, 1, 2, 3, 4])
    TEST.run('gen 5 | sort (lambda x: -x)',
             expected_out=[4, 3, 2, 1, 0])
    TEST.run('gen 5 | map (x: (-x, x)) | sort',
             expected_out=[(-4, 4), (-3, 3), (-2, 2), (-1, 1), (0, 0)])
    TEST.run('((1, "a", 2, "b")) | expand | sort',
             expected_err="'<' not supported between instances of 'str' and 'int'")
    # Bug 101
    TEST.run('(', expected_err='Malformed Python expression')


def test_map():
    TEST.run('gen 5 | map (x: -x)',
             expected_out=[0, -1, -2, -3, -4])
    TEST.run('gen 5 | map (lambda x: -x)',
             expected_out=[0, -1, -2, -3, -4])
    TEST.run('map (3)',
             expected_out=[3])
    TEST.run('map (: 3)',
             expected_out=[3])
    TEST.run('map (lambda: 3)',
             expected_out=[3])
    # Implicit map
    TEST.run('(419)',
             expected_out=[419])
    TEST.run('(File("/tmp").path)',
             expected_out=['/tmp'])
    # Empty function definition
    TEST.run('gen 3 | map ()',
             expected_err='Empty function definition')


def test_select():
    TEST.run('gen 5 | select (x: True)',
             expected_out=[0, 1, 2, 3, 4])
    TEST.run('gen 5 | select (x: False)',
             expected_out=[])
    TEST.run('gen 5 | select (x: x % 2 == 1)',
             expected_out=[1, 3])


def test_red():
    # Test function symbols
    TEST.run('gen 5 1 | red +',
             expected_out=[15])
    TEST.run('gen 5 1 | red *',
             expected_out=[120])
    TEST.run('gen 5 1 | red ^',
             expected_out=[1])
    TEST.run('gen 20 1 | select (x: x in (3, 7, 15)) | red &',
             expected_out=[3])
    TEST.run('gen 75 | select (x: x in (18, 36, 73)) | red \|',
             expected_out=[127])
    TEST.run('gen 3 | map (x: x == 1) | red and',
             expected_out=[False])
    TEST.run('gen 3 | map (x: x == 1) | red or',
             expected_out=[True])
    TEST.run('gen 5 | red max',
             expected_out=[4])
    TEST.run('gen 5 | red min',
             expected_out=[0])
    TEST.run('gen 5 | red count',
             expected_out=[5])
    TEST.run('gen 5 | red concat',
             expected_out=[[0, 1, 2, 3, 4]])
    # Test incremental reduction
    TEST.run('gen 5 1 | red -i +',
             expected_out=[(1, 1), (2, 3), (3, 6), (4, 10), (5, 15)])
    TEST.run('gen 5 1 | red --incremental +',
             expected_out=[(1, 1), (2, 3), (3, 6), (4, 10), (5, 15)])
    # Test multiple reduction
    TEST.run('gen 5 1 | map (x: (x, x)) | red + *',
             expected_out=[(15, 120)])
    # Test lambdas
    TEST.run('gen 5 1 | map (x: (x, x)) | red (x, y: y if x is None else x + y) (x, y: y if x is None else x * y)',
             expected_out=[(15, 120)])
    # Test multiple incremental reduction
    TEST.run('gen 5 1 | map (x: (x, x)) | red -i + *',
             expected_out=[(1, 1, 1, 1),
                           (2, 2, 3, 2),
                           (3, 3, 6, 6),
                           (4, 4, 10, 24),
                           (5, 5, 15, 120)])
    # Test grouping
    TEST.run('gen 9 1 | map (x: (x, x // 2, x * 100, x // 2)) | red + . + .',
             expected_out=[(1, 0, 100, 0),
                           (5, 1, 500, 1),
                           (9, 2, 900, 2),
                           (13, 3, 1300, 3),
                           (17, 4, 1700, 4)])
    # Test incremental grouping
    TEST.run('gen 9 1 | map (x: (x, x // 2, x * 100, x // 2)) | red -i + . + .',
             expected_out=[(1, 0, 100, 0, 1, 100),
                           (2, 1, 200, 1, 2, 200),
                           (3, 1, 300, 1, 5, 500),
                           (4, 2, 400, 2, 4, 400),
                           (5, 2, 500, 2, 9, 900),
                           (6, 3, 600, 3, 6, 600),
                           (7, 3, 700, 3, 13, 1300),
                           (8, 4, 800, 4, 8, 800),
                           (9, 4, 900, 4, 17, 1700)])
    # Test short input
    TEST.run('gen 4 | map (x: (x, 10*x) if x%2 == 0 else (x, 10*x, 100*x)) | red + + +',
             expected_out=[Error('too short'), Error('too short'), (4, 40, 400)])
    TEST.run('gen 4 | map (x: (x, 10*x) if x%2 == 0 else (x, 10*x, 100*x)) | red . + +',
             expected_out=[Error('too short'), Error('too short'), (1, 10, 100), (3, 30, 300)])
    TEST.run('gen 4 | map (x: (x, 10*x) if x%2 == 0 else (x, 10*x, 100*x)) | red -i . + +',
             expected_out=[Error('too short'), (1, 10, 100, 10, 100), Error('too short'), (3, 30, 300, 30, 300)])
    # Bug 153
    TEST.run('gen 3 | select (x: False) | red count',
             expected_out=[0])
    TEST.run('gen 3 | red -i count',
             expected_out=[(0, 1), (1, 2), (2, 3)])
    TEST.run('gen 5 | (x: (x // 2, None)) | red . count | sort',
             expected_out=[(0, 2), (1, 2), (2, 1)])


def test_expand():
    # Test singletons
    TEST.run('gen 5 | expand',
             expected_out=[0, 1, 2, 3, 4])
    TEST.run('gen 5 | map (x: ([x, x],)) | expand',
             expected_out=[0, 0, 1, 1, 2, 2, 3, 3, 4, 4])
    TEST.run('gen 5 | map (x: ((x, x),)) | expand',
             expected_out=[0, 0, 1, 1, 2, 2, 3, 3, 4, 4])
    TEST.run('gen 5 | expand 0',
             expected_out=[0, 1, 2, 3, 4])
    TEST.run('gen 5 | map (x: ([x, x],)) | expand 0',
             expected_out=[0, 0, 1, 1, 2, 2, 3, 3, 4, 4])
    # Test non-singletons
    TEST.run('gen 5 | map (x: (x, -x)) | expand',
             expected_out=[0, 0, 1, -1, 2, -2, 3, -3, 4, -4])
    TEST.run('gen 5 | map (x: (x, -x)) | expand 0',
             expected_out=[(0, 0), (1, -1), (2, -2), (3, -3), (4, -4)])
    TEST.run('gen 5 | map (x: (x, -x)) | expand 1',
             expected_out=[(0, 0), (1, -1), (2, -2), (3, -3), (4, -4)])
    TEST.run('gen 5 | map (x: (x, -x)) | expand 2',
             expected_out=[(0, 0), (1, -1), (2, -2), (3, -3), (4, -4)])
    # Expand list
    TEST.run('gen 5 | map (x: ([100, 200], x, -x)) | expand 0',
             expected_out=[(100, 0, 0),
                           (200, 0, 0),
                           (100, 1, -1),
                           (200, 1, -1),
                           (100, 2, -2),
                           (200, 2, -2),
                           (100, 3, -3),
                           (200, 3, -3),
                           (100, 4, -4),
                           (200, 4, -4)])
    TEST.run('gen 5 | map (x: (x, [100, 200], -x)) | expand 1',
             expected_out=[(0, 100, 0),
                           (0, 200, 0),
                           (1, 100, -1),
                           (1, 200, -1),
                           (2, 100, -2),
                           (2, 200, -2),
                           (3, 100, -3),
                           (3, 200, -3),
                           (4, 100, -4),
                           (4, 200, -4)])
    TEST.run('gen 5 | map (x: (x, -x, [100, 200])) | expand 2',
             expected_out=[(0, 0, 100),
                           (0, 0, 200),
                           (1, -1, 100),
                           (1, -1, 200),
                           (2, -2, 100),
                           (2, -2, 200),
                           (3, -3, 100),
                           (3, -3, 200),
                           (4, -4, 100),
                           (4, -4, 200)])
    TEST.run('gen 5 | map (x: (x, -x, [100, 200])) | expand 3',
             expected_out=[(0, 0, [100, 200]),
                           (1, -1, [100, 200]),
                           (2, -2, [100, 200]),
                           (3, -3, [100, 200]),
                           (4, -4, [100, 200])])
    # Expand tuple
    TEST.run('gen 5 | map (x: ((100, 200), x, -x)) | expand 0',
             expected_out=[(100, 0, 0),
                           (200, 0, 0),
                           (100, 1, -1),
                           (200, 1, -1),
                           (100, 2, -2),
                           (200, 2, -2),
                           (100, 3, -3),
                           (200, 3, -3),
                           (100, 4, -4),
                           (200, 4, -4)])
    # Function-valued args
    TEST.run('N = (1)')
    TEST.run('gen 3 | map (x: (x, (x * 10, x * 10 + 1))) | expand (N)',
             expected_out=[(0, 0), (0, 1), (1, 10), (1, 11), (2, 20), (2, 21)])
    # Bug 158
    TEST.run('gen 3 1 | (x: [str(x * 111)] * x) | expand',
             expected_out=[111, 222, 222, 333, 333, 333])


def test_head():
    TEST.run('gen 100 | head 0',
             expected_err="must not be 0")
    TEST.run('gen 100 | head 1',
             expected_out=[0])
    TEST.run('gen 100 | head 2',
             expected_out=[0, 1])
    TEST.run('gen 100 | head 3',
             expected_out=[0, 1, 2])
    TEST.run('gen 3 | head 3',
             expected_out=[0, 1, 2])
    TEST.run('gen 3 | head 4',
             expected_out=[0, 1, 2])
    # Negative arg
    TEST.run('gen 3 | head -1',
             expected_out=[1, 2])
    TEST.run('gen 3 | head -2',
             expected_out=[2])
    TEST.run('gen 3 | head -3',
             expected_out=[])
    TEST.run('gen 3 | head -4',
             expected_out=[])
    # Function-valued args
    TEST.run('gen 3 | head (4)',
             expected_out=[0, 1, 2])


def test_tail():
    TEST.run('gen 100 | tail 0',
             expected_err='must not be 0')
    TEST.run('gen 100 | tail 1',
             expected_out=[99])
    TEST.run('gen 100 | tail 2',
             expected_out=[98, 99])
    TEST.run('gen 100 | tail 3',
             expected_out=[97, 98, 99])
    TEST.run('gen 3 | tail 3',
             expected_out=[0, 1, 2])
    TEST.run('gen 3 | tail 4',
             expected_out=[0, 1, 2])
    # Negative arg
    TEST.run('gen 3 | tail -1',
             expected_out=[0, 1])
    TEST.run('gen 3 | tail -2',
             expected_out=[0])
    TEST.run('gen 3 | tail -3',
             expected_out=[])
    TEST.run('gen 3 | tail -4',
             expected_out=[])
    # Function-valued args
    TEST.run('gen 3 | tail (4)',
             expected_out=[0, 1, 2])


def test_reverse():
    TEST.run('gen 5 | select (x: False) | reverse',
             expected_out=[])
    TEST.run('gen 5 | reverse',
             expected_out=[4, 3, 2, 1, 0])


def test_squish():
    TEST.run('gen 5 | squish',
             expected_out=[0, 1, 2, 3, 4])
    TEST.run('gen 5 | squish +',
             expected_out=[0, 1, 2, 3, 4])
    TEST.run('gen 5 | map (x: (x, -x)) | squish',
             expected_out=[0, 0, 0, 0, 0])
    TEST.run('gen 5 | map (x: (x, -x)) | squish +',
             expected_out=[0, 0, 0, 0, 0])
    TEST.run('gen 5 | map (x: (x, -x)) | squish min',
             expected_out=[0, -1, -2, -3, -4])
    TEST.run('gen 5 | map (x: (x, -x)) | squish max',
             expected_out=[0, 1, 2, 3, 4])
    TEST.run('gen 5 | map (x: (x, -x)) | squish count',
             expected_out=[2, 2, 2, 2, 2])
    TEST.run('gen 5 | map (x: ([-x, x], [-x, x])) | squish +',
             expected_out=[[0, 0, 0, 0],
                           [-1, 1, -1, 1],
                           [-2, 2, -2, 2],
                           [-3, 3, -3, 3],
                           [-4, 4, -4, 4]])


def test_unique():
    TEST.run('gen 10 | unique',
             expected_out=[0, 1, 2, 3, 4, 5, 6, 7, 8, 9])
    TEST.run('gen 10 | select (x: False) | unique',
             expected_out=[])
    TEST.run('gen 10 | unique -c',
             expected_out=[0, 1, 2, 3, 4, 5, 6, 7, 8, 9])
    TEST.run('gen 10 | select (x: False) | unique -c',
             expected_out=[])
    TEST.run('gen 10 | map (x: x // 3) | unique',
             expected_out=[0, 1, 2, 3])
    TEST.run('gen 10 | map (x: x // 3) | unique -c',
             expected_out=[0, 1, 2, 3])
    TEST.run('gen 10 | map (x: x // 3) | unique --consecutive',
             expected_out=[0, 1, 2, 3])
    TEST.run('gen 10 | map (x: x % 3) | unique',
             expected_out=[0, 1, 2])
    TEST.run('gen 3 | (x: (x//2, [x//2])) | unique',
             expected_err='not hashable')


def test_window():
    TEST.run('gen 10 | window (x: False)',
             expected_out=[(0, 1, 2, 3, 4, 5, 6, 7, 8, 9)])
    TEST.run('gen 10 | window (x: True)',
             expected_out=[0, 1, 2, 3, 4, 5, 6, 7, 8, 9])
    TEST.run('gen 10 | window -o 1',
             expected_out=[0, 1, 2, 3, 4, 5, 6, 7, 8, 9])
    TEST.run('gen 10 | window -o 3',
             expected_out=[(0, 1, 2),
                           (1, 2, 3),
                           (2, 3, 4),
                           (3, 4, 5),
                           (4, 5, 6),
                           (5, 6, 7),
                           (6, 7, 8),
                           (7, 8, 9),
                           (8, 9, None),
                           (9, None, None)])
    TEST.run('gen 10 | window -d 1',
             expected_out=[0, 1, 2, 3, 4, 5, 6, 7, 8, 9])
    TEST.run('gen 10 | window -d 3',
             expected_out=[(0, 1, 2),
                           (3, 4, 5),
                           (6, 7, 8),
                           (9, None, None)])
    # Negative-test args
    TEST.run('gen 10 | window -d 33 -o 22',
             expected_err='Must specify exactly one')
    TEST.run('gen 10 | window',
             expected_err='Must specify exactly one')
    TEST.run('gen 10 | window -o 3 (x: True)',
             expected_err='Must specify exactly one')
    # Function-valued args
    TEST.run('THREE = (3)')
    TEST.run('gen 10 | window -o (THREE)',
             expected_out=[(0, 1, 2),
                           (1, 2, 3),
                           (2, 3, 4),
                           (3, 4, 5),
                           (4, 5, 6),
                           (5, 6, 7),
                           (6, 7, 8),
                           (7, 8, 9),
                           (8, 9, None),
                           (9, None, None)])
    TEST.run('gen 10 | window -d (THREE-2)',
             expected_out=[0, 1, 2, 3, 4, 5, 6, 7, 8, 9])


def test_bash():
    # Two space between hello and world not preserved.
    TEST.run('bash echo hello  world',
             expected_out=['hello world'])
    # Quoted, so they are preserved.
    TEST.run('bash echo "hello  world"',
             expected_out=['hello  world'])
    # Function-valued args
    TEST.run('HELLO = hello')
    TEST.run('''bash echo (f"'{HELLO}  world'")''',
             expected_out=['hello  world'])
    # without 'bash'
    TEST.run('echo hello  world',
             expected_out=['hello world'])
    TEST.run('echo "hello  world"',
             expected_out=['hello  world'])
    TEST.run('HELLO = hello')
    TEST.run('''echo (f"'{HELLO}  world'")''',
             expected_out=['hello  world'])


def test_namespace():
    config_file = '/tmp/.marcel.py'
    config_path = pathlib.Path(config_file)
    # Default namespace has just __builtins__ and initial set of env vars.
    config_path.touch()
    config_path.unlink()
    config_path.touch()
    TEST.reset_environment(config_file)
    TEST.run('map (list(globals().keys())) | expand | select (x: x == "USER")',
             expected_out=['USER'])
    # Try to use an undefined symbol
    TEST.run('map (pi)',
             expected_out=[Error("name 'pi' is not defined")])
    # Try a namespace importing symbols in the math module
    config_path.unlink()
    with open(config_file, 'w') as file:
        file.writelines('from math import *')
    TEST.reset_environment(config_file)
    TEST.run('map (pi)',
             expected_out=['3.141592653589793'])
    # Reset environment
    TEST.reset_environment()


def test_remote():
    localhost = marcel.object.cluster.Host('localhost', None)
    TEST.run('@jao [ gen 3 ]',
             expected_out=[(localhost, 0), (localhost, 1), (localhost, 2)])
    # Handling of remote error in execution
    TEST.run('@jao [ gen 3 -1 | map (x: 5 / x) ]',
             expected_out=[(localhost, -5.0), Error('division by zero'), (localhost, 5.0)])
    # Handling of remote error in setup
    TEST.run('@jao [ ls /nosuchfile ]',
             expected_out=[Error('No qualifying paths')])
    # Bug 4
    TEST.run('@jao [ gen 3 ] | red . +',
             expected_out=[(localhost, 3)])
    TEST.run('@jao [ gen 10 | map (x: (x%2, x)) | red . + ]',
             expected_out=[(localhost, 0, 20), (localhost, 1, 25)])
    # Implied map
    TEST.run('@jao[(419)]',
             expected_out=[(localhost, 419)])
    # Bug 121
    TEST.run('@notacluster [ gen 3]',
             expected_err='There is no cluster named')


def test_sudo():
    TEST.run(test='sudo [ gen 3 ]',
             expected_out=[0, 1, 2])
    os.system('sudo rm -rf /tmp/sudotest')
    os.system('sudo mkdir /tmp/sudotest')
    os.system('sudo touch /tmp/sudotest/f')
    os.system('sudo chmod 400 /tmp/sudotest')
    TEST.run(test='ls -f /tmp/sudotest',
             expected_out=[Error('Permission denied')])
    TEST.run(test='sudo [ ls -f /tmp/sudotest | map (f: f.render_compact()) ]',
             expected_out=['f'])


def test_version():
    TEST.run(test='version',
             expected_out=[marcel.version.VERSION])


def test_assign():
    TEST.run(test='a = 3',
             verification='(a)',
             expected_out=[3])
    TEST.run(test='a = (5+6)',
             verification='(a)',
             expected_out=[11])
    TEST.run(test='a = [(419)]',
             verification='a',
             expected_out=[419])
    TEST.run(test='a = [ map (x: (x, -x)) ]',
             verification='gen 3 | a',
             expected_out=[(0, 0), (1, -1), (2, -2)])
    # Bug 61
    TEST.run('a = [gen 3]')
    TEST.run(test='a',
             expected_out=[0, 1, 2])
    TEST.run('b = [a]')
    TEST.run(test='b',
             expected_out=[0, 1, 2])
    # Bug 65
    TEST.run('x = [(5)]')
    TEST.run(test='x',
             expected_out=[5])


def test_join():
    # Join losing right inputs
    TEST.run(test='gen 4 | map (x: (x, -x)) | join [gen 3 | map (x: (x, x * 100))]',
             expected_out=[(0, 0, 0), (1, -1, 100), (2, -2, 200)])
    # Left join
    TEST.run(test='gen 4 | map (x: (x, -x)) | join -k [gen 3 | map (x: (x, x * 100))]',
             expected_out=[(0, 0, 0), (1, -1, 100), (2, -2, 200), (3, -3)])
    TEST.run(test='gen 4 | map (x: (x, -x)) | join --keep [gen 3 | map (x: (x, x * 100))]',
             expected_out=[(0, 0, 0), (1, -1, 100), (2, -2, 200), (3, -3)])
    # Compound key
    TEST.run(test='gen 4 | map (x: ((x, x + 1), -x)) | join [gen 3 | map (x: ((x, x + 1), x * 100))]',
             expected_out=[((0, 1), 0, 0), ((1, 2), -1, 100), ((2, 3), -2, 200)])
    # Multiple matches on the right
    TEST.run(test='gen 4 '
                  '| map (x: (x, -x)) '
                  '| join [gen 3 '
                  '        | map (x: (x, (x * 100, x * 100 + 1))) '
                  '        | expand 1]',
             expected_out=[(0, 0, 0), (0, 0, 1), (1, -1, 100), (1, -1, 101), (2, -2, 200), (2, -2, 201)])
    # Right argument in variable
    TEST.run('x100 = [gen 3 | map (x: (x, x * 100))]')
    TEST.run(test='gen 4 | map (x: (x, -x)) | join x100',
             expected_out=[(0, 0, 0), (1, -1, 100), (2, -2, 200)])
    TEST.run(test='gen 4 | map (x: (x, -x)) | join [x100]',
             expected_out=[(0, 0, 0), (1, -1, 100), (2, -2, 200)])
    # Join with pipeline var taking arg
    TEST.run('xn = [n: gen 3 | map (x: (x, x * n))]')
    TEST.run(test='gen 4 | map (x: (x, -x)) | join [xn (100)]',
             expected_out=[(0, 0, 0), (1, -1, 100), (2, -2, 200)])
    os.system('rm -f /tmp/?.csv')
    TEST.run('gen 3 | map (x: (x, x*10)) | out -f /tmp/a.csv')
    TEST.run('gen 3 | map (x: (x, x*100)) | out -f /tmp/b.csv')
    TEST.run('get = [f: (File(f).readlines()) | expand | map (x: eval(x))]')
    TEST.run('get /tmp/a.csv | join [get /tmp/b.csv]',
             expected_out=[(0, 0, 0), (1, 10, 100), (2, 20, 200)])
    # Handle non-hashable join keys
    TEST.run('gen 3 | (x: ((x,), x)) | join [gen 3 | (x: ((x,), x*100))]',
             expected_out=[((0,), 0, 0), ((1,), 1, 100), ((2,), 2, 200)])
    TEST.run('gen 3 | (x: ([x], x)) | join [gen 3 | (x: ((x,), x*100))]',
             expected_err='not hashable')
    TEST.run('gen 3 | (x: ((x,), x)) | join [gen 3 | (x: ([x], x*100))]',
             expected_err='not hashable')


def test_comment():
    TEST.run('# this is a comment',
             expected_out=[])
    TEST.run('#',
             expected_out=[])
    TEST.run('gen 3 # comment',
             expected_out=[0, 1, 2])
    TEST.run('gen 3 | map (x: -x) # comment',
             expected_out=[0, -1, -2])


def test_pipeline_args():
    TEST.run('add = [a: map (x: (x, x + a))]')
    TEST.run('gen 3 | add (100)',
             expected_out=[(0, 100), (1, 101), (2, 102)])
    # Multiple functions
    TEST.run('add = [a: map (x: (x, x + a)) | map (x, y: (x + a, y - a))]')
    TEST.run('gen 3 | add (100)',
             expected_out=[(100, 0), (101, 1), (102, 2)])
    # Flag instead of anon arg
    TEST.run('add = [a: map (x: (x, x + a))]')
    TEST.run('gen 3 | add -a (100)',
             expected_out=[(0, 100), (1, 101), (2, 102)])
    # Multiple anon args
    TEST.run('f = [a, b: map (x: (x, x * a + b))]')
    TEST.run('gen 3 | f (100) (10)',
             expected_out=[(0, 10), (1, 110), (2, 210)])
    # Multiple flag args
    TEST.run('f = [a, b: map (x: (x, x * a + b))]')
    TEST.run('gen 3 | f -a (100) -b (10)',
             expected_out=[(0, 10), (1, 110), (2, 210)])
    TEST.run('gen 3 | f -b (10) -a (100)',
             expected_out=[(0, 10), (1, 110), (2, 210)])
    TEST.run('gen 3 | f -b (10) -a (100) -a (200)',
             expected_err='Flag a given more than once')
    TEST.run('gen 3 | f -b (10)',
             expected_err='Expected arguments: 2, given: 1')
    # Long flags
    TEST.run('foobar = [foo, bar: map (x: x * foo) | select (x: x < bar)]')
    TEST.run('gen 10 | foobar --foo (10) --bar (45)',
             expected_out=[0, 10, 20, 30, 40])
    TEST.run('gen 10 | foobar --bar (73) --foo (10)',
             expected_out=[0, 10, 20, 30, 40, 50, 60, 70])
    # Insufficient args
    # Bug 105 --  # Depends on ext being defined in .marcel.py
    TEST.run('ext',
             expected_err='Expected arguments: 1, given: 0')


def test_sql():
    TEST.run('''sql "drop table if exists t"''')
    TEST.run('''sql "create table t(id int primary key, s varchar)"''')
    TEST.run('''sql "insert into t values(1, 'one')"''',
             expected_out=[])
    TEST.run('''sql "insert into t values(%s, %s)" (2) two''',
             expected_out=[])
    TEST.run('''sql "select * from t order by id"''',
             expected_out=[(1, 'one'), (2, 'two')])
    TEST.run('''sql "update t set s = 'xyz'"''',
             expected_out=[])
    TEST.run('''sql "select * from t order by id"''',
             expected_out=[(1, 'xyz'), (2, 'xyz')])
    TEST.run('''gen 3 1000 | map (x: (x, 'aaa')) | sql -u "insert into t values(%s, %s)"''',
             expected_out=[1, 1, 1])
    TEST.run('''sql "select * from t order by id"''',
             expected_out=[(1, 'xyz'), (2, 'xyz'), (1000, 'aaa'), (1001, 'aaa'), (1002, 'aaa')])
    TEST.run('''gen 2 1 | sql "delete from t where id = %s"''',
             expected_out=[])
    TEST.run('''sql "select * from t order by id"''',
             expected_out=[(1000, 'aaa'), (1001, 'aaa'), (1002, 'aaa')])
    TEST.run('''sql "drop table if exists t"''')
    # TODO: sql types


def test_import():
    TEST.run('import math')
    TEST.run('(math.pi)', expected_out=[math.pi])
    TEST.run('(math.e)', expected_out=[math.e])
    TEST.run('import math pi')
    TEST.run('(pi)', expected_out=[math.pi])
    TEST.run('import sys *')
    TEST.run('(version)', expected_out=[sys.version])
    TEST.run('import sys')
    TEST.run('(version)', expected_out=[sys.version])
    TEST.run('import os')
    TEST.run('(os.popen)', expected_out=[os.popen])


def test_store_load():
    TEST.reset_environment()
    # Basics
    TEST.run(test='gen 3 | store x',
             verification='load x',
             expected_out=[0, 1, 2])
    TEST.run('env | map (k, v: k) | select (k: k == "x")',
             expected_out=['x'])
    # Overwrite
    TEST.run(test='gen 3 100 | store x',
             verification='load x',
             expected_out=[100, 101, 102])
    # Append
    TEST.run(test='gen 3 200 | store -a x',
             verification='load x',
             expected_out=[100, 101, 102, 200, 201, 202])
    # Append to undefined var
    TEST.run(test='gen 3 300 | store -a y',
             verification='load y',
             expected_out=[300, 301, 302])
    # Bind the variable to something other than a reservoir and then append
    TEST.run('x = (123)')
    TEST.run(test='gen 3 200 | store -a x',
             verification='load x',
             expected_err='not a Reservoir')
    # Files
    os.system('rm -rf /tmp/storeload.test')
    TEST.run(test='gen 3 | store /tmp/storeload.test',
             verification='load /tmp/storeload.test',
             expected_out=[0, 1, 2])


def test_store_load_sugar():
    # ------------------------ Test all the paths through Parser.pipeline()
    # var >
    TEST.run(test='gen 3 | store p1',
             verification='p1 >',
             expected_out=[0, 1, 2])
    # var >> (error)
    TEST.run(test='gen 3 | store p2',
             verification='p2 >>',
             expected_err='Append not permitted here')
    # var > var
    TEST.run('gen 3 | store p3')
    TEST.run(test='p3 > p4',
             verification='p4 >',
             expected_out=[0, 1, 2])
    # var >> var
    TEST.run('gen 3 | store p5')
    TEST.run('gen 3 | map (x: x + 100) | store p6')
    TEST.run(test='p5 >> p7',
             verification='p7 >',
             expected_out=[0, 1, 2])
    TEST.run(test='p6 >> p7',
             verification='p7 >',
             expected_out=[0, 1, 2, 100, 101, 102])
    # var > op_sequence
    TEST.run('gen 3 | store p8')
    TEST.run(test='p8 > map (x: x + 100)',
             expected_out=[100, 101, 102])
    # var >> op_sequence (error)
    TEST.run('gen 3 | store p9')
    TEST.run(test='p9 >> map (x: x + 100)',
             expected_err='Append not permitted here')
    # var > op_sequence > var
    TEST.run('gen 3 | store p10')
    TEST.run(test='p10 > map (x: x + 100) > p11',
             verification='p11 >',
             expected_out=[100, 101, 102])
    # var > op_sequence >> var
    TEST.run('gen 3 | store p12')
    TEST.run(test='p12 > map (x: x + 100) >> p13',
             verification='p13 >',
             expected_out=[100, 101, 102])
    TEST.run(test='p12 > map (x: x + 1000) >> p13',
             verification='p13 >',
             expected_out=[100, 101, 102, 1000, 1001, 1002])
    # op_sequence -- tested adequately elsewhere
    # op_sequence > var
    TEST.run(test='gen 3 > p14',
             verification='p14 >',
             expected_out=[0, 1, 2])
    # op_sequence >> var
    TEST.run(test='gen 3 >> p15',
             verification='p15 >',
             expected_out=[0, 1, 2])
    TEST.run(test='gen 3 | map (x: x + 100) >> p15',
             verification='p15 >',
             expected_out=[0, 1, 2, 100, 101, 102])
    # > var
    TEST.run(test='gen 6 | ifthen (x: x % 2 == 0) [> p16] | select (x: False)',
             verification='p16 >',
             expected_out=[0, 2, 4])
    # >> var
    TEST.run(test='gen 6 | ifthen (x: x % 2 == 0) [>> p17] | select (x: False)',
             verification='p17 >',
             expected_out=[0, 2, 4])
    TEST.run(test='gen 6 | ifthen (x: x % 2 == 1) [>> p17] | select (x: False)',
             verification='p17 >',
             expected_out=[0, 2, 4, 1, 3, 5])
    # ---------------------------------------------------------------------
    # Ops that look confusingly like vars
    # op >
    TEST.run(test='pwd >',
             expected_err='A variable must precede >')
    # op >>
    TEST.run(test='pwd >>',
             expected_err='A variable must precede >>')
    # op > var
    dir = os.getcwd()
    TEST.run(test='pwd > o1',
             verification='o1 > map (f: f.path)',
             expected_out=[dir])
    # op >> var
    dir = os.getcwd()
    TEST.run(test='pwd >> o2',
             verification='o2 > map (f: f.path)',
             expected_out=[dir])
    TEST.run(test='pwd >> o2',
             verification='o2 > map (f: f.path)',
             expected_out=[dir, dir])
    # var > op
    TEST.run('gen 3 > o3')
    TEST.run(test='o3 > reverse',
             expected_out=[2, 1, 0])
    # var >> op
    TEST.run('gen 3 > o4')
    TEST.run(test='o4 >> reverse',
             expected_err='Append not permitted here')
    # ---------------------------------------------------------------------
    # Store at end of top-level pipeline
    TEST.run(test='gen 5 > g5',
             verification='load g5',
             expected_out=[0, 1, 2, 3, 4])
    # Store at end of pipeline arg
    TEST.run(test='gen 10 | ifthen (x: x % 2 == 0) [map (x: x * 10) > e10x10]',
             verification='load e10x10',
             expected_out=[0, 20, 40, 60, 80])
    # Store as the entire pipeline arg
    TEST.run(test='gen 10 | ifthen (x: x % 2 == 0) [> e10]',
             verification='load e10',
             expected_out=[0, 2, 4, 6, 8])
    # Append
    TEST.run(test='gen 5 > g5g5',
             verification='load g5g5',
             expected_out=[0, 1, 2, 3, 4])
    TEST.run(test='gen 5 >> g5g5',
             verification='load g5g5',
             expected_out=[0, 1, 2, 3, 4, 0, 1, 2, 3, 4])
    # Load at beginning of top-level pipeline
    TEST.run(test='gen 4 > g4',
             verification='g4 > map (x: -x)',
             expected_out=[0, -1, -2, -3])
    # Load by itself at beginning of top-level pipeline
    TEST.run(test='gen 4 > g4',
             verification='g4 >',
             expected_out=[0, 1, 2, 3])
    # Load in pipeline arg
    TEST.run('gen 4 | map (x: (x, x * 10)) > x10')
    TEST.run('gen 4 | map (x: (x, x * 100)) > x100')
    TEST.run('x10 > join [x100 >]',
             expected_out=[(0, 0, 0), (1, 10, 100), (2, 20, 200), (3, 30, 300)])
    # Bug 73
    TEST.run('gen 3 | map (x: (x, x*10)) > a')
    TEST.run('gen 3 | map (x: (x, x*100)) > b')
    TEST.run('gen 3 | map (x: (x, x*1000)) > c')
    TEST.run('a > join [b >] | join [c >]',
             expected_out=[(0, 0, 0, 0), (1, 10, 100, 1000), (2, 20, 200, 2000)])
    # Bug 74
    TEST.run('gen 3 | map (x: (x, x*10)) > a')
    TEST.run('gen 3 | map (x: (x, x*100)) > b')
    TEST.run('gen 3 | map (x: (x, x*1000)) > c')
    TEST.run('a > join [b >] | join [c >] > d')
    TEST.run('d >',
             expected_out=[(0, 0, 0, 0), (1, 10, 100, 1000), (2, 20, 200, 2000)])


def test_loop():
    TEST.run('loop (0) [select (x: x < 3) | emit | map (x: x + 1)]',
             expected_out=[0, 1, 2])
    TEST.run('loop ((0, 1)) [select (x, y: x < 1000000) | emit | map (x, y: (y, x + y))] | map (x, y: x)',
             expected_out=[0, 1, 1, 2, 3, 5, 8, 13, 21,
                           34, 55, 89, 144, 233, 377, 610,
                           987, 1597, 2584, 4181, 6765, 10946,
                           17711, 28657, 46368, 75025, 121393,
                           196418, 317811, 514229, 832040])
    # Repeated execution, piping in initial value
    TEST.run('gen 3 | loop [select (n: n >= 0) | emit | map (n: n - 1)]',
             expected_out=[0, 1, 0, 2, 1, 0])
    # Bug 70
    TEST.run('p = [loop (0) [select (x: x < 5) | emit | map (x: x+1)]')
    TEST.run('p',
             expected_out=[0, 1, 2, 3, 4])


def test_if():
    TEST.run('gen 10 | ifthen (x: x % 2 == 0) [store even]',
             expected_out=[0, 1, 2, 3, 4, 5, 6, 7, 8, 9])
    TEST.run('load even',
             expected_out=[0, 2, 4, 6, 8])
    TEST.run('gen 10 | ifelse (x: x % 3 == 0) [store d3]',
             expected_out=[1, 2, 4, 5, 7, 8])
    TEST.run('load d3',
             expected_out=[0, 3, 6, 9])


def test_delete():
    TEST.run(test='a = (1)',
             verification='env | select (k, v: k == "a")',
             expected_out=[('a', 1)])
    TEST.run(test='delete a',
             verification='env | select (k, v: k == "a")',
             expected_out=[])
    TEST.run(test='delete not_a_variable',
             expected_err='not defined')
    # Multiple deletes
    TEST.run('a = (1)')
    TEST.run('b = two')
    TEST.run('c = (3.0)')
    TEST.run(test='env | select (k, v: k in ["a", "b", "c"]) | map (k, v: k) | sort',
             expected_out=['a', 'b', 'c'])
    TEST.run(test='delete a c',
             verification='env | select (k, v: k in ["a", "b", "c"]) | map (k, v: k) | sort',
             expected_out=['b'])


def test_read():
    os.system('rm -rf /tmp/read')
    os.system('mkdir /tmp/read')
    file = open('/tmp/read/f1.csv', 'w')
    file.writelines(['1,2.3,ab\n',
                     '2,3.4,xy\n',
                     '3,4.5,"m,n"\n'])
    file.close()
    file = open('/tmp/read/f2.tsv', 'w')
    file.writelines(['1\t2.3\tab\n',
                     '2\t3.4\txy\n'])
    file.close()
    file = open('/tmp/read/f3.txt', 'w')
    file.writelines(['hello,world\n',
                     'goodbye\n'])
    file.close()
    # Files
    TEST.run('cd /tmp/read')
    TEST.run('ls f1.csv f3.txt | read',
             expected_out=['1,2.3,ab',
                           '2,3.4,xy',
                           '3,4.5,"m,n"',
                           'hello,world',
                           'goodbye'])
    # Files with labels
    TEST.run('cd /tmp/read')
    TEST.run('ls f1.csv f3.txt | read -l | map (path, line: (str(path), line))',
             expected_out=[('f1.csv', '1,2.3,ab'),
                           ('f1.csv', '2,3.4,xy'),
                           ('f1.csv', '3,4.5,"m,n"'),
                           ('f3.txt', 'hello,world'),
                           ('f3.txt', 'goodbye')])
    # CSV
    TEST.run('cd /tmp/read')
    TEST.run('ls f1.csv | read -c',
             expected_out=[['1', '2.3', 'ab'],
                           ['2', '3.4', 'xy'],
                           ['3', '4.5', 'm,n']])
    # CSV with labels
    TEST.run('cd /tmp/read')
    TEST.run('ls f1.csv | read -cl | map (f, x, y, z: [str(f), x, y, z])',
             expected_out=[['f1.csv', '1', '2.3', 'ab'],
                           ['f1.csv', '2', '3.4', 'xy'],
                           ['f1.csv', '3', '4.5', 'm,n']])
    # TSV
    TEST.run('cd /tmp/read')
    TEST.run('ls f2.tsv | read -t',
             expected_out=[['1', '2.3', 'ab'],
                           ['2', '3.4', 'xy']])
    # TSV with labels
    TEST.run('cd /tmp/read')
    TEST.run('ls f2.tsv | read -tl | map (f, x, y, z: [str(f), x, y, z])',
             expected_out=[['f2.tsv', '1', '2.3', 'ab'],
                           ['f2.tsv', '2', '3.4', 'xy']])
    # --pickle testing is done in test_out()
    # Filenames on commandline
    TEST.run('cd /tmp/read')
    TEST.run('read f1.csv',
             expected_out=['1,2.3,ab', '2,3.4,xy', '3,4.5,"m,n"'])
    TEST.run('read f?.*',
             expected_out=['1,2.3,ab', '2,3.4,xy', '3,4.5,"m,n"',
                           '1\t2.3\tab', '2\t3.4\txy',
                           'hello,world', 'goodbye'])
    # Flags inherited from FilenamesOp
    TEST.run(test='read -lr /tmp/read/* | (f, l: (str(f), l))',
             expected_out=[('f1.csv', '1,2.3,ab'),
                           ('f1.csv', '2,3.4,xy'),
                           ('f1.csv', '3,4.5,"m,n"'),
                           ('f2.tsv', '1\t2.3\tab'),
                           ('f2.tsv', '2\t3.4\txy'),
                           ('f3.txt', 'hello,world'),
                           ('f3.txt', 'goodbye')])
    # File does not exist
    TEST.run(test='read /tmp/read/nosuchfile',
             expected_err='No qualifying paths')
    # directory
    TEST.run(test='read -0 /tmp/read',
             expected_out=[])
    # symlink
    os.system('ln -s /tmp/read/f1.csv /tmp/read/symlink_f1.csv')
    TEST.run('read /tmp/read/symlink_f1.csv',
             expected_out=['1,2.3,ab',
                           '2,3.4,xy',
                           '3,4.5,"m,n"'])


def test_intersect():
    TEST.reset_environment()
    # Empty inputs
    TEST.run('gen 1 | select (*x: False) > empty')
    TEST.run('gen 3 | intersect [empty >]',
             expected_out=[])
    TEST.run('empty > intersect [empty >]',
             expected_out=[])
    TEST.run('empty > intersect [gen 3]',
             expected_out=[])
    # Non-empty inputs, empty intersection
    TEST.run('gen 3 | intersect [gen 3]',
             expected_out=[0, 1, 2])
    TEST.run('gen 3 | intersect [gen 1 1]',
             expected_out=[1])
    # Duplicates
    TEST.run('gen 5 | map (x: [x] * x) | expand > a')
    TEST.run('gen 5 | map (x: [x] * 2) | expand > b')
    TEST.run('a > intersect [b >] | sort',
             expected_out=[1, 2, 2, 3, 3, 4, 4])
    # Composite elements
    TEST.run('gen 3 2 | '
             'map (x: [(x, x * 100)] * x) | '
             'expand | '
             'intersect [gen 3 2 | '
             '           map (x: [(x, x * 100)] * 3) | '
             '           expand] |'
             'sort',
             expected_out=[(2, 200), (2, 200),
                           (3, 300), (3, 300), (3, 300),
                           (4, 400), (4, 400), (4, 400)])
    # Lists cannot be hashed
    TEST.run('gen 2 | (x: (x, (x, x))) | intersect [gen 2 1 | (x: (x, (x, x)))]',
             expected_out=[(1, (1, 1))])
    TEST.run('gen 2 | (x: (x, [x, x])) | intersect [gen 2 1 | (x: (x, (x, x)))]',
             expected_err='not hashable')
    TEST.run('gen 2 | (x: (x, (x, x))) | intersect [gen 2 1 | (x: (x, [x, x]))]',
             expected_err='not hashable')


def test_union():
    TEST.reset_environment()
    # Empty inputs
    TEST.run('gen 1 | select (*x: False) > empty')
    TEST.run('empty > union [empty >]',
             expected_out=[])
    TEST.run('gen 3 | union [empty >] | sort',
             expected_out=[0, 1, 2])
    TEST.run('empty > union [gen 3] | sort',
             expected_out=[0, 1, 2])
    # Non-empty inputs4
    TEST.run('gen 3 | union [gen 3 100] | sort',
             expected_out=[0, 1, 2, 100, 101, 102])
    # Duplicates
    TEST.run('gen 3 | union [gen 3] | sort',
             expected_out=[0, 0, 1, 1, 2, 2])
    # Composite elements
    TEST.run('gen 4 | map (x: (x, x*100)) | union [gen 4 2 | map (x: (x, x*100))] | sort',
             expected_out=[(0, 0), (1, 100), (2, 200), (2, 200), (3, 300), (3, 300), (4, 400), (5, 500)])


def test_difference():
    TEST.reset_environment()
    # Empty inputs
    TEST.run('gen 1 | select (*x: False) > empty')
    TEST.run('empty > difference [empty >]',
             expected_out=[])
    TEST.run('gen 3 | difference [empty >] | sort',
             expected_out=[0, 1, 2])
    TEST.run('empty > difference [gen 3]',
             expected_out=[])
    # Non-empty inputs
    TEST.run('gen 6 | difference [gen 6 100] | sort',
             expected_out=[0, 1, 2, 3, 4, 5])
    TEST.run('gen 6 | difference [gen 6] | sort',
             expected_out=[])
    TEST.run('gen 6 | difference [gen 6 3] | sort',
             expected_out=[0, 1, 2])
    # Duplicates
    TEST.run('gen 5 | map (x: [x] * x) | expand | difference [gen 5 | map (x: [x] * 2) | expand] | sort',
             expected_out=[3, 4, 4])
    # Composite elements
    TEST.run('gen 5 2 | '
             'map (x: [(x, x*100)] * x) | '
             'expand | difference [gen 5 2 | '
             '                     map (x: [(x, x*100)] * 3) | '
             '                     expand] | '
             'sort',
             expected_out=[(4, 400), (5, 500), (5, 500), (6, 600), (6, 600), (6, 600)])
    # Lists aren't hashable
    TEST.run('gen 3 | (x: (x, (x, x))) | difference [gen 2 | (x: (x, (x, x)))]',
             expected_out=[(2, (2, 2))])
    TEST.run('gen 3 | (x: (x, [x, x])) | difference [gen 2 | (x: (x, (x, x)))]',
             expected_err='not hashable')
    TEST.run('gen 3 | (x: (x, (x, x))) | difference [gen 2 | (x: (x, [x, x]))]',
             expected_err='not hashable')


def test_args():
    TEST.reset_environment()
    # gen
    TEST.run('gen 5 1 | args [n: gen (n)] | map (x: -x)',
             expected_out=[0, 0, -1, 0, -1, -2, 0, -1, -2, -3, 0, -1, -2, -3, -4])
    TEST.run('gen 6 1 | args [count, start: gen (count) (start)]',
             expected_out=[2, 4, 5, 6, 6, 7, 8, 9, 10])
    # ls
    TEST.run('rm -rf /tmp/a')
    TEST.run('mkdir /tmp/a')
    TEST.run('mkdir /tmp/a/d1')
    TEST.run('mkdir /tmp/a/d2')
    TEST.run('mkdir /tmp/a/d3')
    TEST.run('touch /tmp/a/d1/f1')
    TEST.run('touch /tmp/a/d2/f2')
    TEST.run('touch /tmp/a/d3/f3')
    TEST.run('cd /tmp/a')
    TEST.run('ls -d | args [d: ls -f (d)] | map (f: f.name)',
             expected_out=['f1', 'f2', 'f3'])
    TEST.run('touch a_file')
    TEST.run('touch "a file"')
    TEST.run('touch "a file with a \' mark"')
    TEST.run('rm -rf d')
    TEST.run('mkdir d')
    TEST.run(test='ls -f | args --all [files: mv -t d (quote_files(files))]',
             verification='ls -f d | map (f: f.name)',
             expected_out=['a file', "a file with a ' mark", 'a_file'])
    # head
    TEST.run('gen 4 1 | args [n: gen 10 | head (n)]',
             expected_out=[0, 0, 1, 0, 1, 2, 0, 1, 2, 3])
    # tail
    TEST.run('gen 4 1 | args [n: gen 10 | tail (n+1)]',
             expected_out=[8, 9, 7, 8, 9, 6, 7, 8, 9, 5, 6, 7, 8, 9])
    # bash
    TEST.run('gen 5 | args [n: echo X(n)Y]',
             expected_out=['X0Y', 'X1Y', 'X2Y', 'X3Y', 'X4Y'])
    # expand
    TEST.run('gen 3 | args [x: (((1, 2), (3, 4), (5, 6))) | expand (x)]',
             expected_out=[(1, (3, 4), (5, 6)), (2, (3, 4), (5, 6)),
                           ((1, 2), 3, (5, 6)), ((1, 2), 4, (5, 6)),
                           ((1, 2), (3, 4), 5), ((1, 2), (3, 4), 6)])
    # sql
    TEST.run('sql "drop table if exists t" | select (x: False)')
    TEST.run('sql "create table t(x int)" | select (x: False)')
    TEST.run(test='gen 5 | args [x: sql "insert into t values(%s)" (x)]',
             verification='sql "select * from t order by x"',
             expected_out=[0, 1, 2, 3, 4])
    # window
    TEST.run('gen 3 | args [w: gen 10 | window -d (w)]',
             expected_out=[(0, 1, 2, 3, 4, 5, 6, 7, 8, 9),
                           0, 1, 2, 3, 4, 5, 6, 7, 8, 9,
                           (0, 1), (2, 3), (4, 5), (6, 7), (8, 9)])
    # nested args
    TEST.run('gen 3 | args [i: gen 3 (i+100) | args [j: gen 3 (j+1000)]]',
             expected_out=[1100, 1101, 1102, 1101, 1102, 1103, 1102, 1103, 1104,
                           1101, 1102, 1103, 1102, 1103, 1104, 1103, 1104, 1105,
                           1102, 1103, 1104, 1103, 1104, 1105, 1104, 1105, 1106])
    # --all
    TEST.run('gen 10 | args --all [x: ("".join([str(n) for n in x]))]',
             expected_out=['0123456789'])
    # no input to args
    TEST.run('gen 3 | select (x: False) | args [n: map (x: -x)]',
             expected_out=[])
    TEST.run('gen 3 | select (x: False) | args --all [n: map (x: -x)]',
             expected_out=[])
    # negative testing
    TEST.run('gen 3 | args [gen 3]',
             expected_err='The args pipeline must be parameterized')
    TEST.run('gen 10 | args --all [a, b: gen (a) (b)]',
             expected_err='the pipeline must have a single parameter')
    # Bug 94
    TEST.run('gen 4 1 | args [n: gen (n)] | window (x: x == 0)',
             expected_out=[0, (0, 1), (0, 1, 2), (0, 1, 2, 3)])
    # Bug 116
    TEST.run('g = [n: gen (n)]')
    TEST.run('gen 3 1 | args [n: g (n)]',
             expected_out=[0, 0, 1, 0, 1, 2])


def test_env():
    TEST.cd(start_dir)
    TEST.reset_environment()
    TEST.run('ko = [map (k, v: k)]')  # key only
    TEST.run('env | ko')
    TEST.run(test='env | ko > env_keys',
             verification='env_keys > red count',
             expected_out=[29])  # 2 of them were just defined: ko, env_keys
    TEST.run('env -a | ko | difference [env_keys >]',
             expected_out=[])
    TEST.run('env_keys > difference [env -a | ko]',
             expected_out=[])
    TEST.run('env -b | red count',
             expected_out=[26])
    TEST.run('env -c | ko',
             expected_out=['DB_DEFAULT'])
    TEST.run('env -s | ko',
             expected_out=['env_keys', 'ko'])
    TEST.run('env -bc | red count',
             expected_out=[27])
    TEST.run('env -bs | red count',
             expected_out=[28])
    TEST.run('env -bcs | red count',
             expected_out=[29])


def test_pos():
    TEST.run('gen 5 | (x: (x, pos())) | select (x, p1: x % 2 == 0) | (x, p1: (x, p1, pos()))',
             expected_out=[(0, 0, 0), (2, 2, 1), (4, 4, 2)])


def test_bug_126():
    TEST.run('fact = [x: gen (x) 1 | args [n: gen (n) 1 | red * | map (f: (n, f))]]')
    TEST.run(test='fact (5) > f',
             verification='f >',
             expected_out=[(1, 1), (2, 2), (3, 6), (4, 24), (5, 120)])


def test_bug_136():
    TEST.run('gen 3 1 | args [n: gen 2 100 | (x: x+n)] | red +',
             expected_out=[615])


def test_bug_151():
    TEST.run('bytime = [sort (f: f.mtime)]')
    TEST.run('ls | bytime > a')
    TEST.run('ls | sort (f: f.mtime) > b')
    TEST.run('a > difference [b >] | red count',
             expected_out=[0])
    TEST.run('b > difference [a >] | red count',
             expected_out=[0])


def test_bug_152():
    # Same test case as for bug 126. Failure was different as code changes.
    pass


def test_bug_10():
    TEST.run('sort', expected_err='cannot be the first operator in a pipeline')
    TEST.run('unique', expected_err='cannot be the first operator in a pipeline')
    TEST.run('window -o 2', expected_err='cannot be the first operator in a pipeline')
    TEST.run('map(3)', expected_out=[3])
    TEST.run('args[x: gen(3)]', expected_err='cannot be the first operator in a pipeline')


def test_bug_154():
    TEST.reset_environment()
    TEST.run('gen 3 > x')
    TEST.run('x >> (y: -y)', expected_err='Append not permitted')
    TEST.run('x > (y: -y)', expected_out=[0, -1, -2])


# For bugs that aren't specific to a single op.
def test_bugs():
    test_bug_10()
    test_bug_126()
    test_bug_136()
    test_bug_151()
    test_bug_154()


def main_stable():
    test_no_such_op()
    test_gen()
    test_out()
    test_sort()
    test_map()
    test_select()
    test_red()
    test_expand()
    test_head()
    test_tail()
    test_reverse()
    test_squish()
    test_unique()
    test_window()
    test_bash()
    test_namespace()
    test_remote()
    test_sudo()
    test_version()
    test_assign()
    test_join()
    test_comment()
    test_pipeline_args()
    test_sql()
    test_import()
    test_store_load()
    test_store_load_sugar()
    test_if()
    test_delete()
    test_read()
    test_intersect()
    test_union()
    test_difference()
    test_args()
    # test_env()
    test_pos()
    test_bugs()


def main_dev():
    pass


def main():
    TEST.reset_environment()
    main_stable()
    # main_dev()
    print(f'Test failures: {TEST.failures}')
    sys.exit(TEST.failures)


main()
