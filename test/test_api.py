import os
import pathlib
import sys
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
    TEST.run(test=lambda: run(gen(3) | out(format=lambda: '{}')),
             expected_out=[0, 1, 2])
    # Pickle output
    TEST.run(test=lambda: run(gen(3) | out(pickle=True)),
             expected_err='Must specify either --file or --append with --pickle')
    TEST.run(test=lambda: run(gen(3) | map(lambda x: [x] * x) | out(file='/tmp/pickle.txt', pickle=True)),
             verification=lambda: run(read('/tmp/pickle.txt', pickle=True)),
             expected_out=[[], 1, [2, 2]])
    TEST.run(test=lambda: run(gen(3, 3) | map(lambda x: [x] * x) | out(append='/tmp/pickle.txt', pickle=True)),
             verification=lambda: run(read('/tmp/pickle.txt', pickle=True)),
             expected_out=[[], 1, [2, 2], [3, 3, 3], [4, 4, 4, 4], [5, 5, 5, 5, 5]])


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
    TEST.run(test=lambda: run(map(lambda: (1, "a", 2, "b")) | expand() | sort()),
             expected_err="'<' not supported between instances of 'str' and 'int'")
    # Bug 10
    TEST.run(test=lambda: run(sort()), expected_out=[])


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
    TEST.run(lambda: run(gen(5) | red(r_concat)),
             expected_out=[[0, 1, 2, 3, 4]])
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
    # Test short input
    TEST.run(test=lambda: run(gen(4)
                              | map(lambda x: (x, 10 * x) if x % 2 == 0 else (x, 10 * x, 100 * x))
                              | red(r_plus, r_plus, r_plus)),
             expected_out=[Error('too short'), Error('too short'), (4, 40, 400)])
    TEST.run(test=lambda: run(gen(4)
                              | map(lambda x: (x, 10 * x) if x % 2 == 0 else (x, 10 * x, 100 * x))
                              | red(None, r_plus, r_plus)),
             expected_out=[Error('too short'), Error('too short'), (1, 10, 100), (3, 30, 300)])
    TEST.run(test=lambda: run(gen(4)
                              | map(lambda x: (x, 10 * x) if x % 2 == 0 else (x, 10 * x, 100 * x))
                              | red(None, r_plus, r_plus, incremental=True)),
             expected_out=[Error('too short'), (1, 10, 100, 10, 100), Error('too short'), (3, 30, 300, 30, 300)])
    # Bug 153
    TEST.run(test=lambda: run(gen(3) | select(lambda x: False) | red(r_count)),
             expected_out=[0])
    TEST.run(test=lambda: run(gen(3) | red(r_count, incremental=True)),
             expected_out=[(0, 1), (1, 2), (2, 3)])
    TEST.run(test=lambda: run(gen(5) | map(lambda x: (x//2, None)) | red(r_group, r_count) | sort()),
             expected_out=[(0, 2), (1, 2), (2, 1)])


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
    # Bug 158
    TEST.run(lambda: run(gen(3, 1) | map(lambda x: [str(x * 111)] * x) | expand()),
             expected_out=[111, 222, 222, 333, 333, 333])


def test_head():
    TEST.run(lambda: run(gen(100) | head(0)),
             expected_err="must not be 0")
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
    # Negative arg
    TEST.run(lambda: run(gen(3) | head(-1)),
             expected_out=[1, 2])
    TEST.run(lambda: run(gen(3) | head(-2)),
             expected_out=[2])
    TEST.run(lambda: run(gen(3) | head(-3)),
             expected_out=[])
    TEST.run(lambda: run(gen(3) | head(-4)),
             expected_out=[])
    # Function-valued args
    TEST.run(test=lambda: run(gen(3) | head(lambda: 4)),
             expected_out=[0, 1, 2])


def test_tail():
    TEST.run(lambda: run(gen(100) | tail(0)),
             expected_err="must not be 0")
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
    # Negative arg
    TEST.run(lambda: run(gen(3) | tail(-1)),
             expected_out=[0, 1])
    TEST.run(lambda: run(gen(3) | tail(-2)),
             expected_out=[0])
    TEST.run(lambda: run(gen(3) | tail(-3)),
             expected_out=[])
    TEST.run(lambda: run(gen(3) | tail(-4)),
             expected_out=[])
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
             expected_out=[[0, 0, 0, 0],
                           [-1, 1, -1, 1],
                           [-2, 2, -2, 2],
                           [-3, 3, -3, 3],
                           [-4, 4, -4, 4]])


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
             expected_out=[(0, 1, 2, 3, 4, 5, 6, 7, 8, 9)])
    TEST.run(lambda: run(gen(10) | window(lambda x: True)),
             expected_out=[0, 1, 2, 3, 4, 5, 6, 7, 8, 9])
    TEST.run(lambda: run(gen(10) | window(overlap=1)),
             expected_out=[0, 1, 2, 3, 4, 5, 6, 7, 8, 9])
    TEST.run(lambda: run(gen(10) | window(overlap=3)),
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
    TEST.run(lambda: run(gen(10) | window(disjoint=1)),
             expected_out=[0, 1, 2, 3, 4, 5, 6, 7, 8, 9])
    TEST.run(lambda: run(gen(10) | window(disjoint=3)),
             expected_out=[(0, 1, 2),
                           (3, 4, 5),
                           (6, 7, 8),
                           (9, None, None)])
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
    TEST.run(lambda: run(gen(10) | window(disjoint=lambda: THREE - 2)),
             expected_out=[0, 1, 2, 3, 4, 5, 6, 7, 8, 9])


def test_bash():
    # Two space between hello and world not preserved.
    TEST.run(lambda: run(bash('echo', 'hello', 'world')),
             expected_out=['hello world'])
    # Quoted, so they are preserved.
    TEST.run(lambda: run(bash('echo', '"hello  world"')),
             expected_out=['hello  world'])
    # Function-valued args
    HELLO = 'hello'
    TEST.run(lambda: run(bash('echo', f"'{HELLO}  world'")),
             expected_out=['hello  world'])


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
    # TODO: Bug - should be expected_err
    TEST.run(lambda: run(fork('jao', ls('/nosuchfile'))),
             expected_out=[Error('No qualifying paths')])
             # expected_err='No qualifying paths')
    # Bug 4
    TEST.run(lambda: run(fork('jao', gen(3)) | red(None, r_plus)),
             expected_out=[(localhost, 3)])
    TEST.run(lambda: run(fork('jao', gen(10) | map(lambda x: (x % 2, x)) | red(None, r_plus))),
             expected_out=[(localhost, 0, 20), (localhost, 1, 25)])
    # Bug 121
    TEST.run(test=lambda: run(fork('notacluster', gen(3))),
             expected_err='There is no cluster named')


def test_sudo():
    TEST.run(test=lambda: run(sudo(gen(3))),
             expected_out=[0, 1, 2])
    os.system('sudo rm -rf /tmp/sudotest')
    os.system('sudo mkdir /tmp/sudotest')
    os.system('sudo touch /tmp/sudotest/f')
    os.system('sudo chmod 400 /tmp/sudotest')
    TEST.run(test=lambda: run(ls('/tmp/sudotest', file=True)),
             expected_out=[Error('Permission denied')])
    TEST.run(test=lambda: run(sudo(ls('/tmp/sudotest', file=True) | map(lambda f: f.render_compact()))),
             expected_out=['f'])


def test_version():
    TEST.run(test=lambda: run(version()),
             expected_out=[marcel.version.VERSION])


def test_assign():
    a = 3
    TEST.run(test=lambda: run(map(lambda: a)),
             expected_out=[3])
    a = map(lambda x: (x, -x))
    TEST.run(test=lambda: run(gen(3) | a),
             expected_out=[(0, 0), (1, -1), (2, -2)])


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
    # Handle non-hashable join keys
    TEST.run(test=lambda: run(gen(3) | map(lambda x: ((x,), x)) | join(gen(3) | map(lambda x: ((x,), x*100)))),
             expected_out=[((0,), 0, 0), ((1,), 1, 100), ((2,), 2, 200)])
    TEST.run(test=lambda: run(gen(3) | map(lambda x: ([x], x)) | join(gen(3) | map(lambda x: ((x,), x*100)))),
             expected_err='not hashable')
    TEST.run(test=lambda: run(gen(3) | map(lambda x: ((x,), x)) | join(gen(3) | map(lambda x: ([x], x*100)))),
             expected_err='not hashable')



def test_pipeline_args():
    add = lambda a: map(lambda x: (x, x + a))
    TEST.run(test=lambda: run(gen(3) | add(100)),
             expected_out=[(0, 100), (1, 101), (2, 102)])
    # Multiple functions
    add = lambda a: map(lambda x: (x, x + a)) | map(lambda x, y: (x + a, y - a))
    TEST.run(test=lambda: run(gen(3) | add(100)),
             expected_out=[(100, 0), (101, 1), (102, 2)])
    # Flag instead of anon arg
    add = lambda a: map(lambda x: (x, x + a))
    TEST.run(test=lambda: run(gen(3) | add(a=100)),
             expected_out=[(0, 100), (1, 101), (2, 102)])
    # Multiple anon args
    ab = lambda a, b: map(lambda x: (x, x * a + b))
    TEST.run(test=lambda: run(gen(3) | ab(100, 10)),
             expected_out=[(0, 10), (1, 110), (2, 210)])
    # Multiple flag args
    TEST.run(test=lambda: run(gen(3) | ab(a=100, b=10)),
             expected_out=[(0, 10), (1, 110), (2, 210)])
    TEST.run(test=lambda: run(gen(3) | ab(b=10, a=100)),
             expected_out=[(0, 10), (1, 110), (2, 210)])


def test_sql():
    TEST.run(test=lambda: run(sql('drop table if exists t') | select(lambda *t: False)))
    TEST.run(test=lambda: run(sql('create table t(id int primary key, s varchar)') | select(lambda *t: False)))
    TEST.run(test=lambda: run(sql("insert into t values(1, 'one')")),
             expected_out=[])
    TEST.run(test=lambda: run(sql("insert into t values(%s, %s)", 2, 'two')),
             expected_out=[])
    TEST.run(test=lambda: run(sql("select * from t order by id")),
             expected_out=[(1, 'one'), (2, 'two')])
    TEST.run(test=lambda: run(sql("update t set s = 'xyz'", update_counts=True)),
             expected_out=[2])
    TEST.run(test=lambda: run(sql("select * from t order by id")),
             expected_out=[(1, 'xyz'), (2, 'xyz')])
    TEST.run(test=lambda: run(gen(3, 1000) | map(lambda x: (x, 'aaa')) | sql("insert into t values(%s, %s)")),
             expected_out=[])
    TEST.run(test=lambda: run(sql("select * from t order by id")),
             expected_out=[(1, 'xyz'), (2, 'xyz'), (1000, 'aaa'), (1001, 'aaa'), (1002, 'aaa')])
    TEST.run(test=lambda: run(gen(2, 1) | sql("delete from t where id = %s", update_counts=True)),
             expected_out=[1, 1])
    TEST.run(test=lambda: run(sql("select * from t order by id")),
             expected_out=[(1000, 'aaa'), (1001, 'aaa'), (1002, 'aaa')])
    # Define database directly (not in .marcel.py)
    jdb_too = database('psycopg2', 'jao', 'jao', 'jao')
    TEST.run(test=lambda: run(sql("select * from t order by id", db=jdb_too)),
             expected_out=[(1000, 'aaa'), (1001, 'aaa'), (1002, 'aaa')])
    # Cleanup
    TEST.run(test=lambda: run(sql("drop table if exists t") | select(lambda *x: False)))
    # TODO: sql types


def test_store_load():
    # Load
    x = reservoir('x')
    TEST.run(test=lambda: run(gen(3, 1) | map(lambda x: x * 10) | store(x)),
             verification=lambda: run(load(x)),
             expected_out=[10, 20, 30])
    a = None
    TEST.run(test=lambda: run(load(a)),
             expected_err='is not a Reservoir')
    j = 123
    TEST.run(test=lambda: run(load(j)),
             expected_err='is not a Reservoir')
    # Store (first to an undefined var, then to a defined one)
    y = reservoir('y')
    TEST.run(test=lambda: run(gen(count=3, start=100) | store(y)),
             verification=lambda: run(load(y)),
             expected_out=[100, 101, 102])
    TEST.run(test=lambda: run(gen(count=3, start=200) | store(y, append=True)),
             verification=lambda: run(load(y)),
             expected_out=[100, 101, 102, 200, 201, 202])
    # Store to a defined var that isn't a list
    i = 123
    TEST.run(test=lambda: run(gen(3) | store(i)),
             expected_err='is not a Reservoir')
    # Files
    os.system('rm -rf /tmp/storeload.test')
    TEST.run(test=lambda: run(gen(3) | store('/tmp/storeload.test')),
             verification=lambda: run(load('/tmp/storeload.test')),
             expected_out=[0, 1, 2])


def test_if():
    even = reservoir('even')
    TEST.run(test=lambda: run(gen(10) | ifthen(lambda x: x % 2 == 0, store(even))),
             expected_out=[0, 1, 2, 3, 4, 5, 6, 7, 8, 9])
    TEST.run(test=lambda: run(load(even)),
             expected_out=[0, 2, 4, 6, 8])
    d3 = reservoir('d3')
    TEST.run(test=lambda: run(gen(10) | ifelse(lambda x: x % 3 == 0, store(d3))),
             expected_out=[1, 2, 4, 5, 7, 8])
    TEST.run(test=lambda: run(load(d3)),
             expected_out=[0, 3, 6, 9])


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
    TEST.run(lambda: run(ls('/tmp/read/f1.csv', '/tmp/read/f3.txt') | read()),
             expected_out=['1,2.3,ab',
                           '2,3.4,xy',
                           '3,4.5,"m,n"',
                           'hello,world',
                           'goodbye'])
    # Files with labels
    TEST.run(lambda: run(ls('/tmp/read/f1.csv', '/tmp/read/f3.txt')
                         | read(label=True)
                         | map(lambda f, x: (str(f), x))),
             expected_out=[('f1.csv', '1,2.3,ab'),
                           ('f1.csv', '2,3.4,xy'),
                           ('f1.csv', '3,4.5,"m,n"'),
                           ('f3.txt', 'hello,world'),
                           ('f3.txt', 'goodbye')])
    # CSV
    TEST.run(lambda: run(ls('/tmp/read/f1.csv') | read(csv=True)),
             expected_out=[['1', '2.3', 'ab'],
                           ['2', '3.4', 'xy'],
                           ['3', '4.5', 'm,n']])
    # CSV with labels
    TEST.run(lambda: run(ls('/tmp/read/f1.csv') |
                         read(csv=True, label=True) |
                         map(lambda f, x, y, z: (str(f), x, y, z))),
             expected_out=[('f1.csv', '1', '2.3', 'ab'),
                           ('f1.csv', '2', '3.4', 'xy'),
                           ('f1.csv', '3', '4.5', 'm,n')])
    # TSV
    TEST.run(lambda: run(ls('/tmp/read/f2.tsv') | read(tsv=True)),
             expected_out=[['1', '2.3', 'ab'],
                           ['2', '3.4', 'xy']])
    # TSV with labels
    TEST.run(lambda: run(ls('/tmp/read/f2.tsv') |
                         read(label=True, tsv=True) |
                         map(lambda f, x, y, z: (str(f), x, y, z))),
             expected_out=[('f2.tsv', '1', '2.3', 'ab'),
                           ('f2.tsv', '2', '3.4', 'xy')])
    # --pickle testing is done in test_out()
    # Filenames on commandline
    TEST.run(lambda: run(read('/tmp/read/f1.csv')),
             expected_out=['1,2.3,ab', '2,3.4,xy', '3,4.5,"m,n"'])
    TEST.run(lambda: run(read('/tmp/read/f?.*')),
             expected_out=['1,2.3,ab', '2,3.4,xy', '3,4.5,"m,n"',
                           '1\t2.3\tab', '2\t3.4\txy',
                           'hello,world', 'goodbye'])
    # Flags inherited from FilenamesOp
    TEST.run(lambda: run(read('/tmp/read/*', label=True, recursive=True) | map(lambda f, l: (str(f), l))),
             expected_out=[('f1.csv', '1,2.3,ab'),
                           ('f1.csv', '2,3.4,xy'),
                           ('f1.csv', '3,4.5,"m,n"'),
                           ('f2.tsv', '1\t2.3\tab'),
                           ('f2.tsv', '2\t3.4\txy'),
                           ('f3.txt', 'hello,world'),
                           ('f3.txt', 'goodbye')])
    # File does not exist
    TEST.run(lambda: run(read('/tmp/read/nosuchfile')),
             expected_err='No qualifying paths')
    # directory
    TEST.run(lambda: run(read('/tmp/read', depth=0)),
             expected_out=[])
    # symlink
    os.system('ln -s /tmp/read/f1.csv /tmp/read/symlink_f1.csv')
    TEST.run(lambda: run(read('/tmp/read/symlink_f1.csv')),
             expected_out=['1,2.3,ab',
                           '2,3.4,xy',
                           '3,4.5,"m,n"'])


def test_intersect():
    # Empty inputs
    empty = reservoir('empty')
    TEST.run(lambda: run(gen(3) | intersect(load(empty))),
             expected_out=[])
    TEST.run(lambda: run(load(empty) | intersect(load(empty))),
             expected_out=[])
    TEST.run(lambda: run(load(empty) | intersect(gen(3))),
             expected_out=[])
    # Non-empty inputs, empty intersection
    TEST.run(lambda: run(gen(3) | intersect(gen(3))),
             expected_out=[0, 1, 2])
    TEST.run(lambda: run(gen(3) | intersect(gen(1, 1))),
             expected_out=[1])
    # Duplicates
    a = reservoir('a')
    b = reservoir('b')
    TEST.run(lambda: run(gen(5) | map(lambda x: [x] * x) | expand() | store(a)))
    TEST.run(lambda: run(gen(5) | map(lambda x: [x] * 2) | expand() | store(b)))
    TEST.run(lambda: run(load(a) | intersect(load(b)) | sort()),
             expected_out=[1, 2, 2, 3, 3, 4, 4])
    # Composite elements
    TEST.run(lambda: run(gen(3, 2) |
                         map(lambda x: [(x, x * 100)] * x) |
                         expand() |
                         intersect(gen(3, 2) |
                                   map(lambda x: [(x, x * 100)] * 3) |
                                   expand()) |
                         sort()),
             expected_out=[(2, 200), (2, 200),
                           (3, 300), (3, 300), (3, 300),
                           (4, 400), (4, 400), (4, 400)])
    # Lists cannot be hashed
    TEST.run(lambda: run(gen(2) | map(lambda x: (x, (x, x))) | intersect(gen(2, 1) | map(lambda x: (x, (x, x))))),
             expected_out=[(1, (1, 1))])
    TEST.run(lambda: run(gen(2) | map(lambda x: (x, [x, x])) | intersect(gen(2, 1) | map(lambda x: (x, (x, x))))),
             expected_err='not hashable')
    TEST.run(lambda: run(gen(2) | map(lambda x: (x, (x, x))) | intersect(gen(2, 1) | map(lambda x: (x, [x, x])))),
             expected_err='not hashable')


def test_union():
    # Empty inputs
    empty = reservoir('empty')
    TEST.run(lambda: run(load(empty) | union(load(empty))),
             expected_out=[])
    TEST.run(lambda: run(gen(3) | union(load(empty))),
             expected_out=[0, 1, 2])
    TEST.run(lambda: run(load(empty) | union(gen(3))),
             expected_out=[0, 1, 2])
    # Non-empty inputs
    TEST.run(lambda: run(gen(3) | union(gen(3, 100)) | sort()),
             expected_out=[0, 1, 2, 100, 101, 102])
    # Duplicates
    TEST.run(lambda: run(gen(3) | union(gen(3)) | sort()),
             expected_out=[0, 0, 1, 1, 2, 2])
    # Composite elements
    TEST.run(
        lambda: run(gen(4) | map(lambda x: (x, x * 100)) | union(gen(4, 2) | map(lambda x: (x, x * 100))) | sort()),
        expected_out=[(0, 0), (1, 100), (2, 200), (2, 200), (3, 300), (3, 300), (4, 400), (5, 500)])


def test_difference():
    # Empty inputs
    empty = reservoir('empty')
    TEST.run(lambda: run(load(empty) | difference(load(empty))),
             expected_out=[])
    TEST.run(lambda: run(gen(3) | difference(load(empty)) | sort()),
             expected_out=[0, 1, 2])
    TEST.run(lambda: run(load(empty) | difference(gen(3)) | sort()),
             expected_out=[])
    # Non-empty inputs
    TEST.run(lambda: run(gen(6) | difference(gen(6, 100)) | sort()),
             expected_out=[0, 1, 2, 3, 4, 5])
    TEST.run(lambda: run(gen(6) | difference(gen(6)) | sort()),
             expected_out=[])
    TEST.run(lambda: run(gen(6) | difference(gen(6, 3)) | sort()),
             expected_out=[0, 1, 2])
    # Duplicates
    TEST.run(lambda: run(gen(5) |
                         map(lambda x: [x] * x) |
                         expand() | difference(gen(5) |
                                               map(lambda x: [x] * 2) |
                                               expand()) |
                         sort()),
             expected_out=[3, 4, 4])
    # Composite elements
    TEST.run(lambda: run(gen(5, 2) |
                         map(lambda x: [(x, x * 100)] * x) |
                         expand() |
                         difference(gen(5, 2) |
                                    map(lambda x: [(x, x * 100)] * 3) |
                                    expand()) |
                         sort()),
             expected_out=[(4, 400), (5, 500), (5, 500), (6, 600), (6, 600), (6, 600)])
    # Lists aren't hashable
    TEST.run(lambda: run(gen(3) | map(lambda x: (x, (x, x))) | difference(gen(2) | map(lambda x: (x, (x, x))))),
             expected_out=[(2, (2, 2))])
    TEST.run(lambda: run(gen(3) | map(lambda x: (x, [x, x])) | difference(gen(2) | map(lambda x: (x, (x, x))))),
             expected_err='not hashable')
    TEST.run(lambda: run(gen(3) | map(lambda x: (x, (x, x))) | difference(gen(2) | map(lambda x: (x, [x, x])))),
             expected_err='not hashable')


def test_args():
    # gen
    TEST.run(test=lambda: run(gen(5, 1) | args(lambda n: gen(n)) | map(lambda x: -x)),
             expected_out=[0, 0, -1, 0, -1, -2, 0, -1, -2, -3, 0, -1, -2, -3, -4])
    TEST.run(test=lambda: run(gen(6, 1) | args(lambda count, start: gen(count, start))),
             expected_out=[2, 4, 5, 6, 6, 7, 8, 9, 10])
    # ls
    os.system('rm -rf /tmp/a')
    os.system('mkdir /tmp/a')
    os.system('mkdir /tmp/a/d1')
    os.system('mkdir /tmp/a/d2')
    os.system('mkdir /tmp/a/d3')
    os.system('touch /tmp/a/d1/f1')
    os.system('touch /tmp/a/d2/f2')
    os.system('touch /tmp/a/d3/f3')
    # TEST.run(test=lambda: run(ls('/tmp/a/*', dir=True) | args(lambda d: ls(d, file=True)) | map(lambda f: f.name)),
    #          expected_out=['f1', 'f2', 'f3'])
    os.system('touch /tmp/a/a_file')
    os.system('touch /tmp/a/"a file"')
    os.system('touch /tmp/a/"a file with a \' mark"')
    os.system('rm -rf /tmp/a/d')
    os.system('mkdir /tmp/a/d')
    # TODO: Disabled due to bug 108
    # TEST.run(test=lambda: run(ls('/tmp/a', file=True) |
    #                           args(lambda files: bash(f'mv -t d {quote_files(files)}'), all=True)),
    #          verification=lambda: run(ls('d', file=True) | map(lambda f: f.name)),
    #          expected_out=['a file', "a file with a ' mark", 'a_file'])
    # head
    TEST.run(lambda: run(gen(4, 1) | args(lambda n: gen(10) | head(n))),
             expected_out=[0, 0, 1, 0, 1, 2, 0, 1, 2, 3])
    # tail
    TEST.run(test=lambda: run(gen(4, 1) | args(lambda n: gen(10) | tail(n+1))),
             expected_out=[8, 9, 7, 8, 9, 6, 7, 8, 9, 5, 6, 7, 8, 9])
    # bash
    TEST.run(test=lambda: run(gen(5) | args(lambda n: bash('echo', f'X{n}Y'))),
             expected_out=['X0Y', 'X1Y', 'X2Y', 'X3Y', 'X4Y'])
    # expand
    TEST.run(test=lambda: run(gen(3) | args(lambda x: map(lambda: ((1, 2), (3, 4), (5, 6))) | expand(x))),
             expected_out=[(1, (3, 4), (5, 6)), (2, (3, 4), (5, 6)),
                           ((1, 2), 3, (5, 6)), ((1, 2), 4, (5, 6)),
                           ((1, 2), (3, 4), 5), ((1, 2), (3, 4), 6)])
    # sql
    TEST.run(test=lambda: run(sql("drop table if exists t") | select(lambda x: False)))
    TEST.run(test=lambda: run(sql("create table t(x int)") | select(lambda x: False)))
    TEST.run(test=lambda: run(gen(5) | args(lambda x: sql("insert into t values(%s)", x))),
             verification=lambda: run(sql("select * from t order by x")),
             expected_out=[0, 1, 2, 3, 4])
    # window
    TEST.run(test=lambda: run(gen(3) | args(lambda w: gen(10) | window(disjoint=w))),
             expected_out=[(0, 1, 2, 3, 4, 5, 6, 7, 8, 9),
                           0, 1, 2, 3, 4, 5, 6, 7, 8, 9,
                           (0, 1), (2, 3), (4, 5), (6, 7), (8, 9)])
    # nested args
    TEST.run(test=lambda: run(gen(3) | args(lambda i: gen(3, i+100) | args(lambda j: gen(3, j+1000)))),
             expected_out=[1100, 1101, 1102, 1101, 1102, 1103, 1102, 1103, 1104,
                           1101, 1102, 1103, 1102, 1103, 1104, 1103, 1104, 1105,
                           1102, 1103, 1104, 1103, 1104, 1105, 1104, 1105, 1106])
    # negative testing
    TEST.run(test=lambda: run(gen(3) | args(lambda: gen(3))),
             expected_err='The args pipeline must be parameterized')
    # Bug 94
    TEST.run(test=lambda: run(gen(4, 1) | args(lambda n: gen(n)) | window(lambda x: x == 0)),
             expected_out=[0, (0, 1), (0, 1, 2), (0, 1, 2, 3)])
    # Bug 116
    g = lambda n: gen (n)
    TEST.run(test=lambda: run(gen(3, 1) | args(lambda n: g(n))),
             expected_out=[0, 0, 1, 0, 1, 2])


def test_pos():
    TEST.run(test=lambda: run(gen(5) |
                              map(lambda x: (x, pos())) |
                              select(lambda x, p1: x % 2 == 0) |
                              map(lambda x, p1: (x, p1, pos()))),
             expected_out=[(0, 0, 0), (2, 2, 1), (4, 4, 2)])


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


def test_bug_126():
    f = reservoir('f')
    fact = lambda x: gen(x, 1) | args(lambda n: gen(n, 1) | red(r_times) | map(lambda f: (n, f)))
    TEST.run(test=lambda: run(fact(5) | store(f)),
             verification=lambda: run(load(f)),
             expected_out=[(1, 1), (2, 2), (3, 6), (4, 24), (5, 120)])


def test_bug_136():
    TEST.run(lambda: run(gen(3, 1) | args(lambda n: gen(2, 100) | map(lambda x: x+n)) | red(r_plus)),
             expected_out=[615])


def test_bug_10():
    TEST.run(lambda: run(sort()), expected_err='cannot be the first operator in a pipeline')
    TEST.run(lambda: run(unique()), expected_err='cannot be the first operator in a pipeline')
    TEST.run(lambda: run(window(overlap=2)), expected_err='cannot be the first operator in a pipeline')
    TEST.run(lambda: run(map(lambda: 3)), expected_out=[3])
    TEST.run(lambda: run(args(lambda x: gen(3))), expected_err='cannot be the first operator in a pipeline')


# For bugs that aren't specific to a single op.
def test_bugs():
    test_bug_126()
    test_bug_136()
    test_bug_10()


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
    # test_namespace()
    test_remote()
    test_sudo()
    test_version()
    test_assign()
    test_join()
    test_pipeline_args()
    test_sql()
    test_store_load()
    test_if()
    test_read()
    test_intersect()
    test_union()
    test_difference()
    test_args()
    test_pos()
    test_api_run()
    test_api_gather()
    test_api_first()
    test_api_iterator()
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
