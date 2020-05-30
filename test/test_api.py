import os
import pathlib
from math import pi

import marcel.object.error
import marcel.object.cluster
import marcel.version
import test_base
from marcel.api import *

Error = marcel.object.error.Error
start_dir = os.getcwd()
TEST = test_base.TestAPI()


def test_gen():
    # Explicit out
    TEST.run(test=lambda: run(gen(5) | out()),
             expected_out=[0, 1, 2, 3, 4])
    # Implicit out
    TEST.run(test=lambda: run(gen(5)),
             expected_out=[0, 1, 2, 3, 4])
    TEST.run(test=lambda: run(gen(count=5, start=10) | out()),
             expected_out=[10, 11, 12, 13, 14])
    TEST.run(test=lambda: run(gen(5, -5) | out()),
             expected_out=[-5, -4, -3, -2, -1])
    TEST.run(test=lambda: run(gen(count=3, pad=2) | out()),
             expected_out=['00', '01', '02'])
    TEST.run(test=lambda: run(gen(count=3, start=99, pad=3) | out()),
             expected_out=['099', '100', '101'])
    TEST.run(test=lambda: run(gen(count=3, start=99, pad=2) | out()),
             expected_err='Padding 2 too small')
    TEST.run(test=lambda: run(gen(count=3, start=-10, pad=4) | out()),
             expected_err='Padding incompatible with start < 0')
    TEST.run(test=lambda: run(gen(3, -1) | map(lambda x: 5 / x)),
             expected_out=[-5.0, Error('division by zero'), 5.0])
    # Bad types
    TEST.run(test=lambda: run(gen(True)),
             expected_err='count must be a string')
    # str is OK, but it had better look like an int
    TEST.run(test=lambda: run(gen('5')),
             expected_out=[0, 1, 2, 3, 4])
    TEST.run(test=lambda: run(gen('abc')),
             expected_err='count cannot be converted to int')
    # Function-valued args
    N = 7
    TEST.run(test=lambda: run(gen(lambda: N - 2)),
             expected_out=[0, 1, 2, 3, 4])
    TEST.run(test=lambda: run(gen(lambda: N - 2, lambda: N + 3)),
             expected_out=[10, 11, 12, 13, 14])
    TEST.run(test=lambda: run(gen(lambda: N - 2, lambda: N + 3, pad=lambda: N - 4)),
             expected_out=['010', '011', '012', '013', '014'])


def test_out():
    output_filename = '/tmp/out.txt'
    TEST.run(test=lambda: run(gen(3) | out(format='{}')),
             expected_out=[0, 1, 2])
    TEST.run(test=lambda: run(gen(3)),
             expected_out=[0, 1, 2])
    TEST.run(test=lambda: run(gen(3) | out(csv=True)),
             expected_out=[0, 1, 2])
    TEST.run(test=lambda: run(gen(3) | out(csv=True, format='{}')),
             expected_err='Cannot specify more than one of')
    TEST.run(test=lambda: run(gen(3) | out(file=output_filename)),
             expected_out=[0, 1, 2],
             file=output_filename)
    TEST.delete_file(output_filename)
    TEST.run(test=lambda: run(gen(3) | out(append=output_filename)),
             expected_out=[0, 1, 2],
             file=output_filename)
    TEST.run(test=lambda: run(gen(3) | out(append=output_filename)),
             expected_out=[0, 1, 2, 0, 1, 2],
             file=output_filename)
    TEST.run(test=lambda: run(gen(3) | out(append=output_filename, file=output_filename)),
             expected_err='Cannot specify more than one of')
    TEST.delete_file(output_filename)
    # Function-valued args
    TEST.run(test=lambda: run(gen(3) | out(file=lambda: output_filename)),
             expected_out=[0, 1, 2],
             file=output_filename)
    TEST.run(test=lambda: run(gen(3) | out(append=lambda: output_filename)),
             expected_out=[0, 1, 2, 0, 1, 2],
             file=output_filename)
    TEST.delete_file(output_filename)
    TEST.run(test=lambda: run(gen(3)| out(format=lambda: '{}')),
             expected_out=[0, 1, 2])


def test_sort():
    TEST.run(test=lambda: run(gen(5) | sort()),
             expected_out=[0, 1, 2, 3, 4])
    TEST.run(test=lambda: run(gen(5) | sort(lambda x: -x)),
             expected_out=[4, 3, 2, 1, 0])
    TEST.run(test=lambda: run(gen(5) | map(lambda x: (-x, x)) | sort()),
             expected_out=[(-4, 4), (-3, 3), (-2, 2), (-1, 1), (0, 0)])
    # Bad types
    TEST.run(test=lambda: run(gen(5) | map(lambda x: (-x, x)) | sort(123)),
             expected_err='key argument must be a function')


def test_map():
    TEST.run(test=lambda: run(gen(5) | map(lambda x: -x)),
             expected_out=[0, -1, -2, -3, -4])
    TEST.run(test=lambda: run(gen(5) | map(None)),
             expected_err='No value specified for function')
    TEST.run(test=lambda: run(gen(5) | map(True)),
             expected_err='function argument must be a function')


def test_select():
    TEST.run(lambda: run(gen(5) | select(lambda x: True)),
             expected_out=[0, 1, 2, 3, 4])
    TEST.run(lambda: run(gen(5) | select(lambda x: False)),
             expected_out=[])
    TEST.run(lambda: run(gen(5) | select(lambda x: x % 2 == 1)),
             expected_out=[1, 3])
    # Negative tests
    TEST.run(lambda: run(gen(5) | select(None)),
             expected_err='No value specified for function')
    TEST.run(lambda: run(gen(5) | select(5.6)),
             expected_err='function argument must be a function')


def test_red():
    # Test function symbols
    TEST.run(lambda: run(gen(5, 1) | red(r_plus)),
             expected_out=[15])
    TEST.run(lambda: run(gen(5, 1) | red(r_times)),
             expected_out=[120])
    TEST.run(lambda: run(gen(5, 1) | red(r_xor)),
             expected_out=[1])
    TEST.run(lambda: run(gen(20, 1) | select(lambda x: x in (3, 7, 15)) | red(r_bit_and)),
             expected_out=[3])
    TEST.run(lambda: run(gen(75) | select(lambda x: x in (18, 36, 73)) | red(r_bit_or)),
             expected_out=[127])
    TEST.run(lambda: run(gen(3) | map(lambda x: x == 1) | red(r_and)),
             expected_out=[False])
    TEST.run(lambda: run(gen(3) | map(lambda x: x == 1) | red(r_or)),
             expected_out=[True])
    TEST.run(lambda: run(gen(5) | red(r_max)),
             expected_out=[4])
    TEST.run(lambda: run(gen(5) | red(r_min)),
             expected_out=[0])
    TEST.run(lambda: run(gen(5) | red(r_count)),
             expected_out=[5])
    # Test incremental reduction
    TEST.run(lambda: run(gen(5, 1) | red(r_plus, incremental=True)),
             expected_out=[(1, 1), (2, 3), (3, 6), (4, 10), (5, 15)])
    # Test multiple reduction
    TEST.run(lambda: run(gen(5, 1) |
                         map(lambda x: (x, x)) |
                         red(r_plus, r_times)),
             expected_out=[(15, 120)])
    # Test lambdas
    TEST.run(lambda: run(gen(5, 1) |
                         map(lambda x: (x, x)) |
                         red(lambda x, y: y if x is None else x + y, lambda x, y: y if x is None else x * y)),
             expected_out=[(15, 120)])
    # Test multiple incremental reduction
    TEST.run(lambda: run(gen(5, 1) | map(lambda x: (x, x)) | red(r_plus, r_times, incremental=True)),
             expected_out=[(1, 1, 1, 1),
                           (2, 2, 3, 2),
                           (3, 3, 6, 6),
                           (4, 4, 10, 24),
                           (5, 5, 15, 120)])
    # Test grouping
    TEST.run(lambda: run(gen(9, 1) |
                         map(lambda x: (x, x // 2, x * 100, x // 2)) |
                         red(r_plus, None, r_plus, None)),
             expected_out=[(1, 0, 100, 0),
                           (5, 1, 500, 1),
                           (9, 2, 900, 2),
                           (13, 3, 1300, 3),
                           (17, 4, 1700, 4)])
    # Test incremental grouping
    TEST.run(lambda: run(gen(9, 1) |
                         map(lambda x: (x, x // 2, x * 100, x // 2)) |
                         red(r_plus, None, r_plus, None, incremental=True)),
             expected_out=[(1, 0, 100, 0, 1, 100),
                           (2, 1, 200, 1, 2, 200),
                           (3, 1, 300, 1, 5, 500),
                           (4, 2, 400, 2, 4, 400),
                           (5, 2, 500, 2, 9, 900),
                           (6, 3, 600, 3, 6, 600),
                           (7, 3, 700, 3, 13, 1300),
                           (8, 4, 800, 4, 8, 800),
                           (9, 4, 900, 4, 17, 1700)])


def test_expand():
    # Test singletons
    TEST.run(lambda: run(gen(5) | expand()),
             expected_out=[0, 1, 2, 3, 4])
    TEST.run(lambda: run(gen(5) | map(lambda x: ([x, x],)) | expand()),
             expected_out=[0, 0, 1, 1, 2, 2, 3, 3, 4, 4])
    TEST.run(lambda: run(gen(5) | map(lambda x: ((x, x),)) | expand()),
             expected_out=[0, 0, 1, 1, 2, 2, 3, 3, 4, 4])
    TEST.run(lambda: run(gen(5) | expand(0)),
             expected_out=[0, 1, 2, 3, 4])
    TEST.run(lambda: run(gen(5) | map(lambda x: ([x, x],)) | expand(0)),
             expected_out=[0, 0, 1, 1, 2, 2, 3, 3, 4, 4])
    # Test non-singletons
    TEST.run(lambda: run(gen(5) | map(lambda x: (x, -x)) | expand()),
             expected_out=[0, 0, 1, -1, 2, -2, 3, -3, 4, -4])
    TEST.run(lambda: run(gen(5) | map(lambda x: (x, -x)) | expand(0)),
             expected_out=[(0, 0), (1, -1), (2, -2), (3, -3), (4, -4)])
    TEST.run(lambda: run(gen(5) | map(lambda x: (x, -x)) | expand(1)),
             expected_out=[(0, 0), (1, -1), (2, -2), (3, -3), (4, -4)])
    TEST.run(lambda: run(gen(5) | map(lambda x: (x, -x)) | expand(2)),
             expected_out=[(0, 0), (1, -1), (2, -2), (3, -3), (4, -4)])
    # Expand list
    TEST.run(lambda: run(gen(5) | map(lambda x: ([100, 200], x, -x)) | expand(0)),
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
    TEST.run(lambda: run(gen(5) | map(lambda x: (x, [100, 200], -x)) | expand(1)),
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
    TEST.run(lambda: run(gen(5) | map(lambda x: (x, -x, [100, 200])) | expand(2)),
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
    TEST.run(lambda: run(gen(5) | map(lambda x: (x, -x, [100, 200])) | expand(3)),
             expected_out=[(0, 0, [100, 200]),
                           (1, -1, [100, 200]),
                           (2, -2, [100, 200]),
                           (3, -3, [100, 200]),
                           (4, -4, [100, 200])])
    # Expand tuple
    TEST.run(lambda: run(gen(5) | map(lambda x: ((100, 200), x, -x)) | expand(0)),
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
    N = 1
    TEST.run(test=lambda: run(gen(3) | map(lambda x: (x, (x * 10, x * 10 + 1))) | expand(lambda: N)),
             expected_out=[(0, 0), (0, 1), (1, 10), (1, 11), (2, 20), (2, 21)])


def test_head():
    TEST.run(lambda: run(gen(100) | head(0)),
             expected_out=[])
    TEST.run(lambda: run(gen(100) | head(1)),
             expected_out=[0])
    TEST.run(lambda: run(gen(100) | head(2)),
             expected_out=[0, 1])
    TEST.run(lambda: run(gen(100) | head(3)),
             expected_out=[0, 1, 2])
    TEST.run(lambda: run(gen(3) | head(3)),
             expected_out=[0, 1, 2])
    TEST.run(lambda: run(gen(3) | head(4)),
             expected_out=[0, 1, 2])
    # Function-valued args
    TEST.run(test=lambda: run(gen(3) | head(lambda: 4)),
             expected_out=[0, 1, 2])


def test_tail():
    TEST.run(lambda: run(gen(100) | tail(0)),
             expected_out=[])
    TEST.run(lambda: run(gen(100) | tail(1)),
             expected_out=[99])
    TEST.run(lambda: run(gen(100) | tail(2)),
             expected_out=[98, 99])
    TEST.run(lambda: run(gen(100) | tail(3)),
             expected_out=[97, 98, 99])
    TEST.run(lambda: run(gen(3) | tail(3)),
             expected_out=[0, 1, 2])
    TEST.run(lambda: run(gen(3) | tail(4)),
             expected_out=[0, 1, 2])
    # Function-valued args
    TEST.run(lambda: run(gen(3) | tail(lambda: 4)),
             expected_out=[0, 1, 2])


def test_reverse():
    TEST.run(lambda: run(gen(5) | select(lambda x: False) | reverse()),
             expected_out=[])
    TEST.run(lambda: run(gen(5) | reverse()),
             expected_out=[4, 3, 2, 1, 0])


def test_squish():
    TEST.run(lambda: run(gen(5) | squish()),
             expected_out=[0, 1, 2, 3, 4])
    TEST.run(lambda: run(gen(5) | squish(r_plus)),
             expected_out=[0, 1, 2, 3, 4])
    TEST.run(lambda: run(gen(5) | map(lambda x: (x, -x)) | squish()),
             expected_out=[0, 0, 0, 0, 0])
    TEST.run(lambda: run(gen(5) | map(lambda x: (x, -x)) | squish(r_plus)),
             expected_out=[0, 0, 0, 0, 0])
    TEST.run(lambda: run(gen(5) | map(lambda x: (x, -x)) | squish(r_min)),
             expected_out=[0, -1, -2, -3, -4])
    TEST.run(lambda: run(gen(5) | map(lambda x: (x, -x)) | squish(r_max)),
             expected_out=[0, 1, 2, 3, 4])
    TEST.run(lambda: run(gen(5) | map(lambda x: (x, -x)) | squish(r_count)),
             expected_out=[2, 2, 2, 2, 2])
    TEST.run(lambda: run(gen(5) | map(lambda x: ([-x, x], [-x, x])) | squish(r_plus)),
             expected_out=[(0, 0, 0, 0),
                           (-1, 1, -1, 1),
                           (-2, 2, -2, 2),
                           (-3, 3, -3, 3),
                           (-4, 4, -4, 4)])


def test_unique():
    TEST.run(lambda: run(gen(10) | unique()),
             expected_out=[0, 1, 2, 3, 4, 5, 6, 7, 8, 9])
    TEST.run(lambda: run(gen(10) | select(lambda x: False) | unique()),
             expected_out=[])
    TEST.run(lambda: run(gen(10) | unique(consecutive=True)),
             expected_out=[0, 1, 2, 3, 4, 5, 6, 7, 8, 9])
    TEST.run(lambda: run(gen(10) | select(lambda x: False) | unique(consecutive=True)),
             expected_out=[])
    TEST.run(lambda: run(gen(10) | map(lambda x: x // 3) | unique()),
             expected_out=[0, 1, 2, 3])
    TEST.run(lambda: run(gen(10) | map(lambda x: x // 3) | unique(consecutive=True)),
             expected_out=[0, 1, 2, 3])
    TEST.run(lambda: run(gen(10) | map(lambda x: x % 3) | unique()),
             expected_out=[0, 1, 2])


def test_window():
    TEST.run(lambda: run(gen(10) | window(lambda x: False)),
             expected_out=[((0,), (1,), (2,), (3,), (4,), (5,), (6,), (7,), (8,), (9,))])
    TEST.run(lambda: run(gen(10) | window(lambda x: True)),
             expected_out=[(0,), (1,), (2,), (3,), (4,), (5,), (6,), (7,), (8,), (9,)])
    TEST.run(lambda: run(gen(10) | window(overlap=1)),
             expected_out=[(0,), (1,), (2,), (3,), (4,), (5,), (6,), (7,), (8,), (9,)])
    TEST.run(lambda: run(gen(10) | window(overlap=3)),
             expected_out=[((0,), (1,), (2,)),
                           ((1,), (2,), (3,)),
                           ((2,), (3,), (4,)),
                           ((3,), (4,), (5,)),
                           ((4,), (5,), (6,)),
                           ((5,), (6,), (7,)),
                           ((6,), (7,), (8,)),
                           ((7,), (8,), (9,)),
                           ((8,), (9,), (None,)),
                           ((9,), (None,), (None,))])
    TEST.run(lambda: run(gen(10) | window(disjoint=1)),
             expected_out=[(0,), (1,), (2,), (3,), (4,), (5,), (6,), (7,), (8,), (9,)])
    TEST.run(lambda: run(gen(10) | window(disjoint=3)),
             expected_out=[((0,), (1,), (2,)),
                           ((3,), (4,), (5,)),
                           ((6,), (7,), (8,)),
                           ((9,), (None,), (None,))])
    # Negative-test args
    TEST.run(lambda: run(gen(10) | window(disjoint=33, overlap=33)),
             expected_err='Must specify exactly one')
    TEST.run(lambda: run(gen(10) | window()),
             expected_err='Must specify exactly one')
    TEST.run(lambda: run(gen(10) | window(lambda x: True, overlap=3)),
             expected_err='Must specify exactly one')
    TEST.run(lambda: run(gen(10) | window(overlap='abc')),
             expected_err='overlap cannot be converted to int')
    TEST.run(lambda: run(gen(10) | window(disjoint=[])),
             expected_err='disjoint must be a string')
    # Function-valued args
    THREE = 3
    TEST.run(lambda: run(gen(10) | window(overlap=lambda: THREE)),
             expected_out=[((0,), (1,), (2,)),
                           ((1,), (2,), (3,)),
                           ((2,), (3,), (4,)),
                           ((3,), (4,), (5,)),
                           ((4,), (5,), (6,)),
                           ((5,), (6,), (7,)),
                           ((6,), (7,), (8,)),
                           ((7,), (8,), (9,)),
                           ((8,), (9,), (None,)),
                           ((9,), (None,), (None,))])
    TEST.run(lambda: run(gen(10) | window(disjoint=lambda: THREE - 2)),
             expected_out=[(0,), (1,), (2,), (3,), (4,), (5,), (6,), (7,), (8,), (9,)])


def test_bash():
    # Two space between hello and world not preserved.
    TEST.run(lambda: run(bash('echo', 'hello', 'world')),
             expected_out=['hello world'])
    # Quoted, so they are preserved.
    TEST.run(lambda: run(bash('echo', "hello  world")),
             expected_out=['hello  world'])
    # Function-valed args
    HELLO = 'hello'
    TEST.run(test=lambda: run(bash('echo', lambda: HELLO+'  world')),
             expected_out=['hello  world'])


def test_fork():
    TEST.run(lambda: run(fork(1, gen(3, 100))),
             expected_out=[(0, 100), (0, 101), (0, 102)])
    TEST.run(lambda: run(fork(3, gen(3, 100)) | sort()),
             expected_out=[(0, 100), (0, 101), (0, 102),
                           (1, 100), (1, 101), (1, 102),
                           (2, 100), (2, 101), (2, 102)])
    # Bug 40
    TEST.run(lambda: run(fork('notacluster', gen(5))),
             expected_err='Invalid fork specification')
    # Function-valued args
    TEST.run(lambda: run(fork(lambda: 1, gen(lambda: 3, 100))),
             expected_out=[(0, 100), (0, 101), (0, 102)])


def test_namespace():
    config_file = '/tmp/.marcel.py'
    config_path = pathlib.Path(config_file)
    # Default namespace has just __builtins__ and initial set of env vars.
    config_path.touch()
    config_path.unlink()
    config_path.touch()
    TEST.reset_environment(config_file)

    # TODO: These tests are weird. They are trying to test the marcel namespace, but rely on symbols
    # TODO: in this namespace.

    TEST.run(lambda: run(map(lambda: list(globals().keys())) | expand() | select(lambda x: x == 'USER')),
             expected_out=['USER'])
    # Try to use an undefined symbol
    TEST.run(lambda: run(map(pi)),
             expected_out=[Error("name 'pi' is not defined")])
    # Try a namespace importing symbols in the math module
    config_path.unlink()
    with open(config_file, 'w') as file:
        file.writelines('from math import *')
    TEST.reset_environment(config_file)
    TEST.run(lambda: run(map(pi)),
             expected_out=['3.141592653589793'])
    # Reset environment
    TEST.reset_environment()


def test_remote():
    localhost = marcel.object.cluster.Host('localhost', None)
    TEST.run(lambda: run(fork('jao', gen(3))),
             expected_out=[(localhost, 0), (localhost, 1), (localhost, 2)])
    # Handling of remote error in execution
    TEST.run(lambda: run(fork('jao', gen(3, -1) | map(lambda x: 5 / x))),
             expected_out=[(localhost, -5.0), Error('division by zero'), (localhost, 5.0)])
    # Handling of remote error in setup
    TEST.run(lambda: run(fork('jao', ls('/nosuchfile'))),
             expected_err='No qualifying paths')
    # Bug 4
    TEST.run(lambda: run(fork('jao', gen(3)) | red(None, r_plus)),
             expected_out=[(localhost, 3)])
    TEST.run(lambda: run(fork('jao', gen(10) | map(lambda x: (x % 2, x)) | red(None, r_plus))),
             expected_out=[(localhost, 0, 20), (localhost, 1, 25)])
    # Function-valued args
    TEST.run(lambda: run(fork(lambda: 'jao', map(lambda: 419))),
             expected_out=[(localhost, 419)])


def test_sudo():
    TEST.run(test='sudo -i [ gen 3 ]',
             expected_out=[0, 1, 2])
    # os.system('sudo rm -rf /tmp/sudotest')
    # os.system('sudo mkdir /tmp/sudotest')
    # os.system('sudo touch /tmp/sudotest/f')
    # os.system('sudo chmod 400 /tmp/sudotest')
    # TEST.run(test='ls -f /tmp/sudotest',
    #          expected_out=[Error('Permission denied')])
    # TEST.run(test='sudo -i [ ls -f /tmp/sudotest | map (f: f.render_compact()) ]',
    #          expected_out=['f'])
    # # TEST.run(test='sudo -i [ ls -f /tmp/sudotest ]',
    # #          expected_out=['f'])


def test_version():
    TEST.run(test=lambda: run(version()),
             expected_out=[marcel.version.VERSION])


def test_join():
    # Join losing right inputs
    TEST.run(test=lambda: run(gen(4) | map(lambda x: (x, -x)) | join(gen(3) | map(lambda x: (x, x * 100)))),
             expected_out=[(0, 0, 0), (1, -1, 100), (2, -2, 200)])
    # Left join
    TEST.run(test=lambda: run(gen(4) | map(lambda x: (x, -x)) | join(gen(3) | map(lambda x: (x, x * 100)), keep=True)),
             expected_out=[(0, 0, 0), (1, -1, 100), (2, -2, 200), (3, -3)])
    # Compound key
    TEST.run(test=lambda: run(gen(4)
                              | map(lambda x: ((x, x + 1), -x))
                              | join(gen(3) | map(lambda x: ((x, x + 1), x * 100)))),
             expected_out=[((0, 1), 0, 0), ((1, 2), -1, 100), ((2, 3), -2, 200)])
    # Multiple matches on the right
    TEST.run(test=lambda: run(gen(4)
                              | map(lambda x: (x, -x))
                              | join(gen(3)
                                     | map(lambda x: (x, (x * 100, x * 100 + 1)))
                                     | expand(1))),
             expected_out=[(0, 0, 0), (0, 0, 1), (1, -1, 100), (1, -1, 101), (2, -2, 200), (2, -2, 201)])
    # Right argument in variable
    x100 = gen(3) | map(lambda x: (x, x * 100))
    TEST.run(test=lambda: run(gen(4)
                              | map(lambda x: (x, -x))
                              | join(x100)),
             expected_out=[(0, 0, 0), (1, -1, 100), (2, -2, 200)])


def test_api_run():
    # Error-free output, just an op
    TEST.run(test=lambda: run(gen(3)),
             expected_out=[0, 1, 2])
    # Error-free output, pipeline
    TEST.run(test=lambda: run(gen(3) | map(lambda x: -x)),
             expected_out=[0, -1, -2])
    # With errors
    TEST.run(test=lambda: run(gen(3, -1) | map(lambda x: 1 / x)),
             expected_out=[-1.0, Error('division by zero'), 1.0])


def test_api_gather():
    # Default gather behavior
    TEST.run(test=lambda: gather(gen(3, -1) | map(lambda x: 1 / x)),
             expected_return=[-1.0, Error('division by zero'), 1.0])
    # Don't unwrap singletons
    TEST.run(test=lambda: gather(gen(3, -1) | map(lambda x: 1 / x), unwrap_singleton=False),
             expected_return=[(-1.0,), Error('division by zero'), (1.0,)])
    # Collect errors separately
    errors = []
    TEST.run(test=lambda: gather(gen(3, -1) | map(lambda x: 1 / x), errors=errors),
             expected_return=[-1.0, 1.0],
             expected_errors=[Error('division by zero')],
             actual_errors=errors)
    # error handler
    errors = []
    TEST.run(test=lambda: gather(gen(3, -1) | map(lambda x: 1 / x),
                                 error_handler=lambda env, error: errors.append(error)),
             expected_return=[-1.0, 1.0],
             expected_errors=[Error('division by zero')],
             actual_errors=errors)
    # errors and error_handler are mutually exclusive
    errors = []
    TEST.run(test=lambda: gather(gen(3, -1) | map(lambda x: 1 / x),
                                 errors=[],
                                 error_handler=lambda env, error: errors.append(error)),
             expected_err='Specify at most one of the errors and error_handler arguments')


def test_api_first():
    # Default first behavior
    TEST.run(test=lambda: first(gen(3, -1) | map(lambda x: 1 / x)),
             expected_return=-1.0)
    # Don't unwrap singletons
    TEST.run(test=lambda: first(gen(3, -1) | map(lambda x: 1 / x), unwrap_singleton=False),
             expected_return=(-1.0,))
    # First is Error
    TEST.run(test=lambda: first(gen(3, 0) | map(lambda x: 1 / x)),
             expected_exception='division by zero')
    # Collect errors separately
    errors = []
    TEST.run(test=lambda: first(gen(3) | map(lambda x: x // 2) | map(lambda x: 1 / x), errors=errors),
             expected_return=1.0,
             expected_errors=[Error('division by zero'), Error('division by zero')],
             actual_errors=errors)
    # error handler
    errors = []
    TEST.run(test=lambda: first(gen(3) | map(lambda x: x // 2) | map(lambda x: 1 / x),
                                error_handler=lambda env, error: errors.append(error)),
             expected_return=1.0,
             expected_errors=[Error('division by zero'), Error('division by zero')],
             actual_errors=errors)
    # errors and error_handler are mutually exclusive
    errors = []
    TEST.run(test=lambda: first(gen(3, -1) | map(lambda x: 1 / x),
                                errors=[],
                                error_handler=lambda env, error: errors.append(error)),
             expected_err='Specify at most one of the errors and error_handler arguments')


def test_api_iterator():
    TEST.run(test=lambda: list(gen(3)),
             expected_return=[0, 1, 2])
    TEST.run(test=lambda: list(gen(3, -1) | map(lambda x: 1 / x)),
             expected_return=[-1.0, Error('division by zero'), 1.0])


def main_stable():
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
    test_fork()
    # test_namespace()
    test_remote()
    # test_sudo()
    test_version()
    test_join()
    test_api_run()
    test_api_gather()
    test_api_first()
    test_api_iterator()


def main_dev():
    pass


def main():
    TEST.reset_environment()
    main_stable()
    # main_dev()
    print(f'Test failures: {TEST.failures}')


main()
