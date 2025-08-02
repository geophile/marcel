import getpass
import os
import pathlib
import shutil
import sys
from math import pi

import marcel.object.error
import marcel.object.cluster
import marcel.version
from marcel.api import *
from marcel.api import _MAIN

import test_base

timeit = test_base.timeit
TestDir = test_base.TestDir

Error = marcel.object.error.Error
TEST = test_base.TestAPI(_MAIN)

SQL = True


# Convenient for testing to have NODE1 precede NODE2 lexicographically
def find_node(cluster, node_name):
    for host in cluster.hosts:
        if host.name == node_name:
            return host
    return None


CLUSTER1 = cluster(user='jao', host='127.0.0.1', identity='/home/jao/.ssh/id_rsa')
CLUSTER2 = cluster(user='jao', hosts=['127.0.0.1', 'localhost'], identity='/home/jao/.ssh/id_rsa')
NODE1 = find_node(CLUSTER2, '127.0.0.1')
NODE2 = find_node(CLUSTER2, 'localhost')
jdb = database(driver='psycopg2',
               dbname='jao',
               user='jao',
               password='jao')
ENV = marcel.api._ENV
ENV.setvar('DB_DEFAULT', jdb)


# Utilities for testing filename ops


def relative(base, x):
    x_path = pathlib.Path(x)
    base_path = pathlib.Path(base)
    display_path = x_path.relative_to(base_path)
    return display_path


def absolute(base, x):
    return pathlib.Path(base) / x


def filename_op_setup(testdir):
    # testdir contents
    #     f (file)
    #     sf (symlink to f)
    #     lf (hard link to f)
    #     d/ (dir)
    #     sd (symlink to d)
    #         df (file)
    #         sdf (symlink to df)
    #         ldf (hard link to df)
    #         dd/ (dir)
    #         sdd (symlink to dd)
    #             ddf (file)
    setup_script = [
        f'rm -rf {testdir}',
        f'mkdir {testdir}',
        f'mkdir {testdir}/d',
        f'echo f > {testdir}/f',
        f'ln -s {testdir}/f {testdir}/sf',
        f'ln {testdir}/f {testdir}/lf',
        f'ln -s {testdir}/d {testdir}/sd',
        f'echo df > {testdir}/d/df',
        f'ln -s {testdir}/d/df {testdir}/d/sdf',
        f'ln {testdir}/d/df {testdir}/d/ldf',
        f'mkdir {testdir}/d/dd',
        f'ln -s {testdir}/d/dd {testdir}/d/sdd',
        f'echo ddf > {testdir}/d/dd/ddf']
    # Start clean
    shutil.rmtree(testdir, ignore_errors=True)
    # Create test data
    for x in setup_script:
        os.system(x)
    TEST.run(lambda: run(cd(testdir)))


@timeit
def test_gen():
    # Explicit out
    TEST.run(test=lambda: run(gen(5) | write()),
             expected_out=[0, 1, 2, 3, 4])
    # Implicit out
    TEST.run(test=lambda: run(gen(5)),
             expected_out=[0, 1, 2, 3, 4])
    TEST.run(test=lambda: run(gen(count=5, start=10) | write()),
             expected_out=[10, 11, 12, 13, 14])
    TEST.run(test=lambda: run(gen(5, -5) | write()),
             expected_out=[-5, -4, -3, -2, -1])
    TEST.run(test=lambda: run(gen(count=3, pad=2) | write()),
             expected_out=['00', '01', '02'])
    TEST.run(test=lambda: run(gen(count=3, start=99, pad=3) | write()),
             expected_out=['099', '100', '101'])
    TEST.run(test=lambda: run(gen(count=3, start=99, pad=2) | write()),
             expected_err='Padding 2 too small')
    TEST.run(test=lambda: run(gen(count=3, start=-10, pad=4) | write()),
             expected_err='Padding incompatible with start < 0')
    TEST.run(test=lambda: run(gen(3, -1) | map(lambda x: 5 / x)),
             expected_out=[-5.0, Error('division by zero'), 5.0])
    # Bad types
    TEST.run(test=lambda: run(gen(True)),
             expected_err='count must be an int')
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


@timeit
def test_write():
    # Write to stdout
    TEST.run(test=lambda: run(gen(3) | map(lambda x: (x, -x)) | write()),
             expected_out=[(0, 0), (1, -1), (2, -2)])
    TEST.run(test=lambda: run(gen(3) | map(lambda x: (x, -x)) | write(format='{}~{}')),
             expected_out=['0~0', '1~-1', '2~-2'])
    TEST.run(test=lambda: run(gen(3) | map(lambda x: (x, -x)) | write(csv=True)),
             expected_out=['0,0', '1,-1', '2,-2'])
    TEST.run(test=lambda: run(gen(3) | map(lambda x: (x, -x)) | write(tsv=True)),
             expected_out=['0\t0', '1\t-1', '2\t-2'])
    TEST.run(test=lambda: run(gen(3) | map(lambda x: (x, -x)) | write(pickle=True)),
             expected_err='--pickle incompatible with stdout')
    TEST.run(test=lambda: run(gen(3) | map(lambda x: (x, -x)) | write(csv=True, tsv=True)),
             expected_err='Cannot specify more than one of')
    # Write to file
    with TestDir(TEST.env) as testdir:
        output_filename = f'{testdir}/out.txt'
        TEST.run(test=lambda: run(gen(3) | map(lambda x: (x, -x)) | write(filename=output_filename)),
                 expected_out=[(0, 0), (1, -1), (2, -2)],
                 file=output_filename)
        TEST.run(test=lambda: run(gen(3) | map(lambda x: (x, -x)) | write(output_filename, format='{}~{}')),
                 expected_out=['0~0', '1~-1', '2~-2'],
                 file=output_filename)
        TEST.run(test=lambda: run(gen(3) | map(lambda x: (x, -x)) | write(filename=output_filename, csv=True)),
                 expected_out=['0,0', '1,-1', '2,-2'],
                 file=output_filename)
        TEST.run(test=lambda: run(gen(3) | map(lambda x: (x, -x)) | write(output_filename, tsv=True)),
                 expected_out=['0\t0', '1\t-1', '2\t-2'],
                 file=output_filename)
        TEST.run(test=lambda: run(gen(3) | map(lambda x: (x, -x)) | write(output_filename, pickle=True)),
                 verification=lambda: run(read(output_filename, pickle=True)),
                 expected_out=[(0, 0), (1, -1), (2, -2)])
        # Append
        TEST.run(test=lambda: run(gen(3) | write(append=True)),
                 expected_err='--append incompatible with stdout')
        TEST.delete_files(output_filename)
        TEST.run(test=lambda: run(gen(3) | write(output_filename, append=True)),
                 verification=lambda: run(read(output_filename)),
                 expected_out=[0, 1, 2])
        TEST.run(test=lambda: run(gen(3, 3) | write(output_filename, append=True)),
                 verification=lambda: run(read(output_filename)),
                 expected_out=[0, 1, 2, 3, 4, 5])
        TEST.delete_files(output_filename)
        TEST.run(test=lambda: run(gen(3) | map(lambda x: (x, -x)) | write(output_filename, csv=True, append=True)),
                 expected_out=['0,0', '1,-1', '2,-2'],
                 file=output_filename)
        TEST.run(test=lambda: run(gen(3) | map(lambda x: (x, -x)) | write(output_filename, tsv=True, append=True)),
                 expected_out=['0,0', '1,-1', '2,-2',
                               '0\t0', '1\t-1', '2\t-2'],
                 file=output_filename)
        TEST.run(test=lambda: run(gen(3) | map(lambda x: (x, -x)) | write(output_filename, append=True)),
                 expected_out=['0,0', '1,-1', '2,-2',
                               '0\t0', '1\t-1', '2\t-2',
                               (0, 0), (1, -1), (2, -2)],
                 file=output_filename)
        TEST.delete_files(output_filename)
        TEST.run(test=lambda: run(gen(3) | map(lambda x: (x, -x)) | write(output_filename, pickle=True, append=True)),
                 verification=lambda: run(read(output_filename, pickle=True)),
                 expected_out=[(0, 0), (1, -1), (2, -2)])
        TEST.run(
            test=lambda: run(gen(3, 3) | map(lambda x: (x, -x)) | write(output_filename, pickle=True, append=True)),
            verification=lambda: run(read(output_filename, pickle=True)),
            expected_out=[(0, 0), (1, -1), (2, -2), (3, -3), (4, -4), (5, -5)])
        # Function-valued filename
        TEST.run(test=lambda: run(gen(3) | write(lambda: output_filename)),
                 expected_out=[0, 1, 2],
                 file=output_filename)


@timeit
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
    TEST.run(test=lambda: run(sort()), expected_err='sort cannot be the first operator in a pipeline')


@timeit
def test_map():
    TEST.run(test=lambda: run(gen(5) | map(lambda x: -x)),
             expected_out=[0, -1, -2, -3, -4])
    TEST.run(test=lambda: run(gen(5) | map(None)),
             expected_err='No value specified for function')
    TEST.run(test=lambda: run(gen(5) | map(True)),
             expected_err='function argument must be a function')
    # Mix of output and error
    TEST.run(test=lambda: run(gen(3) | map(lambda x: 1 / (1 - x))),
             expected_out=[1.0, Error('division by zero'), -1.0])


@timeit
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


@timeit
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
    TEST.run(test=lambda: run(gen(5) | map(lambda x: (x // 2, None)) | red(r_group, r_count) | sort()),
             expected_out=[(0, 2), (1, 2), (2, 1)])


@timeit
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
    # Expand set
    TEST.run(lambda: run(gen(5) | map(lambda x: (set((100, 200)), x, -x)) | expand(0) | sort()),
             expected_out=[(100, 0, 0),
                           (100, 1, -1),
                           (100, 2, -2),
                           (100, 3, -3),
                           (100, 4, -4),
                           (200, 0, 0),
                           (200, 1, -1),
                           (200, 2, -2),
                           (200, 3, -3),
                           (200, 4, -4)])
    # Function-valued args
    N = 1
    TEST.run(test=lambda: run(gen(3) | map(lambda x: (x, (x * 10, x * 10 + 1))) | expand(lambda: N)),
             expected_out=[(0, 0), (0, 1), (1, 10), (1, 11), (2, 20), (2, 21)])
    # Bug 158
    TEST.run(lambda: run(gen(3, 1) | map(lambda x: [str(x * 111)] * x) | expand()),
             expected_out=[111, 222, 222, 333, 333, 333])
    # dicts
    TEST.run(test=lambda: run(map(lambda: {1: 2, 3: 4, 5: 6}) | expand()),
             expected_out=[(1, 2), (3, 4), (5, 6)])
    TEST.run(test=lambda: run(map(lambda: ("a", {1: 2, 3: 4, 5: 6}, "b")) | expand(1)),
             expected_out=[('a', (1, 2), 'b'),
                           ('a', (3, 4), 'b'),
                           ('a', (5, 6), 'b')])
    # Expand generator-like objects (having __next__)
    TEST.run(test=lambda: run(map(lambda: zip([1, 2, 3], [4, 5, 6])) | expand()),
             expected_out=[(1, 4), (2, 5), (3, 6)])


@timeit
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


@timeit
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


@timeit
def test_reverse():
    TEST.run(lambda: run(gen(5) | select(lambda x: False) | reverse()),
             expected_out=[])
    TEST.run(lambda: run(gen(5) | reverse()),
             expected_out=[4, 3, 2, 1, 0])


@timeit
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


@timeit
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


@timeit
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
             expected_err='disjoint must be an int')
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


@timeit
def test_bash():
    with TestDir(TEST.env) as testdir:
        os.system(f'touch {testdir}/x1')
        os.system(f'touch {testdir}/x2')
        os.system(f'touch {testdir}/y1')
        os.system(f'touch {testdir}/y2')
        who = 'world'
        # Test command string
        TEST.run(lambda: run(cd(testdir)))
        TEST.run(lambda: run(bash('ls x*')),
                 expected_out=['x1', 'x2'])
        TEST.run(lambda: run(bash('ls -l *1') | map(lambda x: x.split()[-1])),
                 expected_out=['x1', 'y1'])
        TEST.run(lambda: run(bash('echo "hello  world"')),  # --- two spaces in string to be printed
                 expected_out='hello  world')
        # Test args
        TEST.run(lambda: run(bash('echo', f'hello {who}')),
                 expected_out='hello world')
        TEST.run(lambda: run(bash('echo', 'hello', 'world')),
                 expected_out=['hello world'])


@timeit
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


@timeit
def test_source_filenames():
    with TestDir(TEST.env) as testdir:
        filename_op_setup(testdir)
        # # Relative path
        # TEST.run('ls . | map (f: f.render_compact())',
        #          expected_out=sorted(['.', 'f', 'sf', 'lf', 'd', 'sd']))
        # TEST.run('ls d | map (f: f.render_compact())',
        #          expected_out=sorted(['.', 'df', 'sdf', 'ldf', 'dd', 'sdd']))
        # Absolute path
        TEST.run(test=lambda: run(ls(f'{testdir}') | map(lambda f: f.render_compact())),
                 expected_out=sorted(['.', 'f', 'sf', 'lf', 'd', 'sd']))
        TEST.run(test=lambda: run(ls(f'{testdir}/d') | map(lambda f: f.render_compact())),
                 expected_out=sorted(['.', 'df', 'sdf', 'ldf', 'dd', 'sdd']))
        # Glob in last part of path
        TEST.run(test=lambda: run(ls(f'{testdir}/s?', depth=0) | map(lambda f: f.render_compact())),
                 expected_out=sorted(['sf', 'sd']))
        TEST.run(test=lambda: run(ls(f'{testdir}/*f', depth=0) | map(lambda f: f.render_compact())),
                 expected_out=sorted(['f', 'sf', 'lf']))
        # Glob in intermediate part of path
        TEST.run(test=lambda: run(ls(f'{testdir}/*d/*dd', depth=0) | map(lambda f: f.render_compact())),
                 expected_out=sorted(['d/dd', 'd/sdd', 'sd/dd', 'sd/sdd']))
        TEST.run(test=lambda: run(ls(f'{testdir}/*f', depth=0) | map(lambda f: f.render_compact())),
                 expected_out=sorted(['f', 'sf', 'lf']))
        # Glob identifying duplicates
        TEST.run(test=lambda: run(ls(f'{testdir}/*f', f'{testdir}/s*', depth=0) | map(lambda f: f.render_compact())),
                 expected_out=sorted(['f', 'sd', 'sf', 'lf']))
        # No such file
        TEST.run(test=lambda: run(ls('no_such_file', depth=0) | map(lambda f: f.render_compact())),
                 expected_err='No qualifying paths')
        # No such file via glob
        TEST.run(test=lambda: run(ls(f'{testdir}/no_such_file*', depth=0) | map(lambda f: f.render_compact())),
                 expected_err='No qualifying paths')
        # ~ expansion
        TEST.run(test=lambda: run(ls('~root', depth=0) | map(lambda f: f.path)),
                 expected_out=['/root'])


@timeit
def test_ls():
    with TestDir(TEST.env) as testdir:
        filename_op_setup(testdir)
        # 0/1/r flags with no files specified.
        TEST.run(test=lambda: run(ls(depth=0) | map(lambda f: f.render_compact())),
                 expected_out=sorted(['.']))
        TEST.run(test=lambda: run(ls(depth=1) | map(lambda f: f.render_compact())),
                 expected_out=sorted(['.',
                                      'f', 'sf', 'lf', 'sd', 'd',  # Top-level
                                      ]))
        TEST.run(test=lambda: run(ls(recursive=True) | map(lambda f: f.render_compact())),
                 expected_out=sorted(['.',
                                      'f', 'sf', 'lf', 'sd', 'd',  # Top-level
                                      'd/df', 'd/sdf', 'd/ldf', 'd/dd', 'd/sdd',  # Contents of d
                                      'd/dd/ddf']))
        TEST.run(test=lambda: run(ls() | map(lambda f: f.render_compact())),
                 expected_out=sorted(['.',
                                      'f', 'sf', 'lf', 'sd', 'd',  # Top-level
                                      ]))
        # 0/1/r flags with file
        TEST.run(test=lambda: run(ls(f'{testdir}/f', depth=0) | map(lambda f: f.render_compact())),
                 expected_out=sorted(['f']))
        TEST.run(test=lambda: run(ls(f'{testdir}/f', depth=1) | map(lambda f: f.render_compact())),
                 expected_out=sorted(['f']))
        TEST.run(test=lambda: run(ls(f'{testdir}/f', recursive=True) | map(lambda f: f.render_compact())),
                 expected_out=sorted(['f']))
        # 0/1/r flags with directory
        TEST.run(test=lambda: run(ls(f'{testdir}', depth=0) | map(lambda f: f.render_compact())),
                 expected_out=sorted(['.']))
        TEST.run(test=lambda: run(ls(f'{testdir}', depth=1) | map(lambda f: f.render_compact())),
                 expected_out=sorted(['.', 'f', 'sf', 'lf', 'sd', 'd']))
        TEST.run(test=lambda: run(ls(f'{testdir}', recursive=True) | map(lambda f: f.render_compact())),
                 expected_out=sorted(['.',
                                      'f', 'sf', 'lf', 'sd', 'd',  # Top-level
                                      'd/df', 'd/sdf', 'd/ldf', 'd/dd', 'd/sdd',  # Contents of d
                                      'd/dd/ddf']))
        # Test f/d/s flags
        TEST.run(test=lambda: run(ls(file=True, recursive=True) | map(lambda f: f.render_compact())),
                 expected_out=sorted(['f', 'lf',  # Top-level
                                      'd/df', 'd/ldf',  # Contents of d
                                      'd/dd/ddf']))
        TEST.run(test=lambda: run(ls(dir=True, recursive=True) | map(lambda f: f.render_compact())),
                 expected_out=sorted(['.',
                                      'd',  # Top-level
                                      'd/dd']))  # Contents of d
        TEST.run(test=lambda: run(ls(symlink=True, recursive=True) | map(lambda f: f.render_compact())),
                 expected_out=sorted(['sf', 'sd',  # Top-level
                                      'd/sdf', 'd/sdd'  # Contents of d
                                      ]))
        # Duplicates
        TEST.run(test=lambda: run(ls(f'{testdir}/*d', f'{testdir}/?', depth=0) | map(lambda f: f.render_compact())),
                 expected_out=sorted(['d', 'sd', 'f']))
        # This should find d twice
        expected = sorted(['.', 'f', 'sf', 'lf', 'd', 'sd'])
        expected.extend(sorted(['d/df', 'd/sdf', 'd/ldf', 'd/dd', 'd/sdd']))
        TEST.run(test=lambda: run(ls(f'{testdir}', f'{testdir}/d', depth=1) | map(lambda f: f.render_compact())),
                 expected_out=expected)
    # ls should continue past permission error
    with TestDir(TEST.env) as testdir:
        os.system(f'mkdir {testdir}/d1')
        os.system(f'mkdir {testdir}/d2')
        os.system(f'mkdir {testdir}/d3')
        os.system(f'mkdir {testdir}/d4')
        os.system(f'touch {testdir}/d1/f1')
        os.system(f'touch {testdir}/d2/f2')
        os.system(f'touch {testdir}/d3/f3')
        os.system(f'touch {testdir}/d4/f4')
        os.system(f'sudo chown root.root {testdir}/d2')
        os.system(f'sudo chown root.root {testdir}/d3')
        os.system(f'sudo chmod 700 {testdir}/d?')
        TEST.run(test=lambda: run(ls(f'{testdir}', recursive=True) | map(lambda f: f.render_compact())),
                 expected_out=['.',
                               'd1',
                               'd1/f1',
                               'd2',
                               Error('Permission denied'),
                               'd3',
                               Error('Permission denied'),
                               'd4',
                               'd4/f4'])
        # # Args with vars -- see bug 186
        # TEST.env.setvar('TEST', 'test')
        # TEST.run(test=lambda: run(ls('/tmp/(TEST)', recursive=True) | map(lambda f: f.render_compact())),
        #          expected_out=sorted(['.',
        #                               'f', 'sf', 'lf', 'sd', 'd',  # Top-level
        #                               'd/df', 'd/sdf', 'd/ldf', 'd/dd', 'd/sdd',  # Contents of d
        #                               'sd/df', 'sd/sdf', 'sd/ldf', 'sd/dd', 'sd/sdd',  # Also reachable via sd
        #                               'd/dd/ddf', 'd/sdd/ddf', 'sd/dd/ddf', 'sd/sdd/ddf'  # All paths to ddf
        #                               ]))
        # TEST.env.setvar('TMP', 'TMP')
        # TEST.run(test=lambda: run(ls('/(TMP.lower())/(TEST)', recursive=True) | map(lambda f: f.render_compact())),
        #          expected_out=sorted(['.',
        #                               'f', 'sf', 'lf', 'sd', 'd',  # Top-level
        #                               'd/df', 'd/sdf', 'd/ldf', 'd/dd', 'd/sdd',  # Contents of d
        #                               'sd/df', 'sd/sdf', 'sd/ldf', 'sd/dd', 'sd/sdd',  # Also reachable via sd
        #                               'd/dd/ddf', 'd/sdd/ddf', 'sd/dd/ddf', 'sd/sdd/ddf'  # All paths to ddf
        #                               ]))
        # Restore owners so that cleanup can proceed
        me = os.getlogin()
        os.system(f'sudo chown {me}.{me} {testdir}/d2')
        os.system(f'sudo chown {me}.{me} {testdir}/d3')


# pushd, popd, dirs, cd
@timeit
def test_dir_stack():
    with TestDir(TEST.env) as testdir:
        filename_op_setup(testdir)
        os.system('mkdir a b c')
        os.system('touch f')
        os.system('rm -rf p')
        os.system('mkdir p')
        os.system('chmod 000 p')
        TEST.run(test=lambda: run(pwd() | map(lambda f: f.path)),
                 expected_out=[f'{testdir}'])
        TEST.run(test=lambda: run(dirs() | map(lambda f: f.path)),
                 expected_out=[f'{testdir}'])
        TEST.run(test=lambda: run(pushd('a') | map(lambda f: f.path)),
                 expected_out=[f'{testdir}/a', f'{testdir}'])
        TEST.run(test=lambda: run(dirs() | map(lambda f: f.path)),
                 expected_out=[f'{testdir}/a', f'{testdir}'])
        TEST.run(test=lambda: run(pushd('../b') | map(lambda f: f.path)),
                 expected_out=[f'{testdir}/b', f'{testdir}/a', f'{testdir}'])
        TEST.run(test=lambda: run(dirs() | map(lambda f: f.path)),
                 expected_out=[f'{testdir}/b', f'{testdir}/a', f'{testdir}'])
        TEST.run(test=lambda: run(pushd() | map(lambda f: f.path)),
                 expected_out=[f'{testdir}/a', f'{testdir}/b', f'{testdir}'])
        TEST.run(test=lambda: run(dirs() | map(lambda f: f.path)),
                 expected_out=[f'{testdir}/a', f'{testdir}/b', f'{testdir}'])
        TEST.run(test=lambda: run(popd() | map(lambda f: f.path)),
                 expected_out=[f'{testdir}/b', f'{testdir}'])
        TEST.run(test=lambda: run(pwd() | map(lambda f: f.path)),
                 expected_out=[f'{testdir}/b'])
        TEST.run(test=lambda: run(dirs() | map(lambda f: f.path)),
                 expected_out=[f'{testdir}/b', f'{testdir}'])
        TEST.run(test=lambda: run(dirs(clear=True) | map(lambda f: f.path)),
                 expected_out=[f'{testdir}/b'])
        TEST.run(test=lambda: run(pushd() | map(lambda f: f.path)),
                 expected_out=[f'{testdir}/b'])
        # Dir operations when the destination cd does not exist or cannot be entered due to permissions
        # cd
        TEST.run(test=lambda: run(cd(testdir)))
        TEST.run(test=lambda: run(cd(f'{testdir}/doesnotexist')),
                 expected_err='No qualifying path')
        TEST.run(test=lambda: run(pwd() | map(lambda f: str(f))),
                 expected_out=testdir)
        TEST.run(test=lambda: run(cd(f'{testdir}/p')),
                 expected_err='Permission denied')
        TEST.run(test=lambda: run(pwd() | map(lambda f: str(f))),
                 expected_out=testdir)
        TEST.run(test=lambda: run(cd(f'{testdir}/f')),
                 expected_err='is not a directory')

        # pushd
        TEST.run(test=lambda: run(pushd(f'{testdir}/doesnotexist')),
                 expected_err='No qualifying path')
        TEST.run(test=lambda: run(pwd() | map(lambda f: str(f))),
                 expected_out=f'{testdir}')
        TEST.run(test=lambda: run(pushd(f'{testdir}/p')),
                 expected_err='Permission denied')
        TEST.run(test=lambda: run(pwd() | map(lambda f: str(f))),
                 expected_out=f'{testdir}')
        # popd: Arrange for a deleted dir on the stack and try popding into it.
        os.system('rm -rf x y')
        os.system('mkdir x y')
        TEST.run(test=lambda: run(cd('x')))
        TEST.run(test=lambda: run(pushd('../y') | map(lambda f: str(f))),
                 expected_out=[f'{testdir}/y', f'{testdir}/x'])
        os.system(f'rm -rf {testdir}/x')
        TEST.run(test=lambda: run(popd()),
                 expected_err='directories have been removed')
        TEST.run(test=lambda: run(dirs() | map(lambda f: str(f))),
                 expected_out=[f'{testdir}/y'])


@timeit
def test_remote():
    TEST.run(lambda: run(remote(CLUSTER1, gen(3))),
             expected_out=[(NODE1, 0), (NODE1, 1), (NODE1, 2)])
    # Handling of remote error in execution
    TEST.run(lambda: run(remote(CLUSTER1, gen(3, -1) | map(lambda x: 5 / x))),
             expected_out=[(NODE1, -5.0), Error('division by zero'), (NODE1, 5.0)])
    # Handling of remote error in setup
    # TODO: Bug - should be expected_err
    TEST.run(lambda: run(remote(CLUSTER1, ls('/nosuchfile'))),
             expected_out=[Error('No qualifying paths')])
    # expected_err='No qualifying paths')
    # Bug 4
    TEST.run(lambda: run(remote(CLUSTER1,
                                gen(3)) | red(None, r_plus)),
             expected_out=[(NODE1, 3)])
    TEST.run(lambda: run(remote(CLUSTER1,
                                gen(10) | map(lambda x: (x % 2, x)) | red(None, r_plus))),
             expected_out=[(NODE1, 0, 20), (NODE1, 1, 25)])
    # Bug 121
    TEST.run(test=lambda: run(remote('notacluster', gen(3))),
             expected_err='notacluster is not a Cluster')


@timeit
def test_fork():
    # int forkgen
    TEST.run(lambda: run(fork(3, gen(3, 100)) | sort()),
             expected_out=[100, 100, 100, 101, 101, 101, 102, 102, 102])
    TEST.run(lambda: run(fork(3, lambda t: gen(3, 100) | map(lambda x: (t, x))) | sort()),
             expected_out=[(0, 100), (0, 101), (0, 102),
                           (1, 100), (1, 101), (1, 102),
                           (2, 100), (2, 101), (2, 102)])
    TEST.run(lambda: run(fork(3, lambda t, u: gen(3, 100) | map(lambda x: (t, x))) | sort()),
             expected_err='Too many pipelines args')
    # iterable forkgen
    TEST.run(lambda: run(fork('abc', lambda: gen(3, 100)) | sort()),
             expected_out=[100, 100, 100, 101, 101, 101, 102, 102, 102])
    TEST.run(lambda: run(fork('abc', lambda t: gen(3, 100) | map(lambda x: (t, x))) | sort()),
             expected_out=[('a', 100), ('a', 101), ('a', 102),
                           ('b', 100), ('b', 101), ('b', 102),
                           ('c', 100), ('c', 101), ('c', 102)])
    TEST.run(lambda: run(fork('abc', lambda t, u: gen(3, 100) | map(lambda x: (t, x))) | sort()),
             expected_err='Too many pipelines args')
    # Cluster forkgen
    localhost = marcel.object.cluster.Host(None, '127.0.0.1')
    TEST.run(lambda: run(fork(CLUSTER1, lambda: gen(3, 100)) | sort()),
             expected_out=[100, 101, 102])
    TEST.run(lambda: run(fork(CLUSTER1, lambda t: gen(3, 100) | map(lambda x: (t, x))) | sort()),
             expected_out=[(localhost, 100), (localhost, 101), (localhost, 102)])
    TEST.run(lambda: run(fork(CLUSTER1, lambda t, u: gen(3, 100) | map(lambda x: (t, x))) | sort()),
             expected_err='Too many pipelines args')


@timeit
def test_sudo():
    with TestDir(TEST.env) as testdir:
        TEST.run(test=lambda: run(sudo(gen(3))),
                 expected_out=[0, 1, 2])
        os.system(f'sudo mkdir {testdir}/sudotest')
        os.system(f'sudo touch {testdir}/sudotest/f')
        os.system(f'sudo chmod 400 {testdir}/sudotest')
        TEST.run(test=lambda: run(ls(f'{testdir}/sudotest', file=True)),
                 expected_out=[Error('Permission denied')])
        TEST.run(test=lambda: run(sudo(ls(f'{testdir}/sudotest', file=True) | map(lambda f: f.render_compact()))),
                 expected_out=['f'])
        os.system(f'sudo rm -rf {testdir}/sudotest')


@timeit
def test_version():
    TEST.run(test=lambda: run(version()),
             expected_out=[marcel.version.VERSION])


@timeit
def test_assign():
    TEST.run(test=lambda: run(assign('a', 3)),
             verification=lambda: run(env(var='a')),
             expected_out=[('a', 3)])
    # This makes more sense in test_ops, where marcel (not Python) has to evalute the expression.
    TEST.run(test=lambda: run(assign('a', 5 + 6)),
             verification=lambda: run(env(var='a')),
             expected_out=[('a', 11)])
    TEST.run(test=lambda: run(assign('a', [419])),
             verification=lambda: run(env(var='a')),
             expected_out=[('a', [419])])
    # test_ops assigns a pipelines to env var a and then uses the pipelines: gen 3 | a
    # But in the API, env vars can't be referred to an a marcel command, so we have to use
    # a program variable instead.
    a = map(lambda x: (x, -x))
    TEST.run(test=lambda: run(gen(3) | a),
             expected_out=[(0, 0), (1, -1), (2, -2)])
    # Bug 61
    a = gen(3)
    TEST.run(test=lambda: run(a),
             expected_out=[0, 1, 2])
    b = a
    TEST.run(test=lambda: run(b),
             expected_out=[0, 1, 2])
    # Bug 65
    x = map(lambda: 5)
    TEST.run(test=lambda: run(x),
             expected_out=[5])
    # Bug 165
    ls = 'abc'
    TEST.run(test=lambda: run(map(lambda: ls)),
             expected_out=['abc'])


@timeit
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
    TEST.run(test=lambda: run(gen(3) | map(lambda x: ((x,), x)) | join(gen(3) | map(lambda x: ((x,), x * 100)))),
             expected_out=[((0,), 0, 0), ((1,), 1, 100), ((2,), 2, 200)])
    TEST.run(test=lambda: run(gen(3) | map(lambda x: ([x], x)) | join(gen(3) | map(lambda x: ((x,), x * 100)))),
             expected_err='not hashable')
    TEST.run(test=lambda: run(gen(3) | map(lambda x: ((x,), x)) | join(gen(3) | map(lambda x: ([x], x * 100)))),
             expected_err='not hashable')


@timeit
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


@timeit
def test_sql():
    if not SQL:
        return
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


@timeit
def test_store_load():
    # Load
    x = reservoir('f')
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
    # Bad variable name
    TEST.run(test=lambda: run(gen(3) | store('/tmp/storeload.test')),
             expected_err='is not a Python identifier')


@timeit
def test_case():
    TEST.run(test=lambda: run(gen(5, 1) |
                              case(lambda x: x < 3, map(lambda x: (100 * x)),
                                   lambda x: x > 3, map(lambda x: (1000 * x)))),
             expected_out=[100, 200, 4000, 5000])
    TEST.run(test=lambda: run(gen(5, 1) |
                              case(lambda x: x < 3, map(lambda x: (100 * x)), map(lambda x: (-x)))),
             expected_out=[100, 200, -3, -4, -5])
    TEST.run(test=lambda: run(gen(5, 1) |
                              case(lambda x: x == 1, map(lambda x: "one"),
                                   lambda x: x == 2, map(lambda x: "two"),
                                   lambda x: x == 3, map(lambda x: "three"))),
             expected_out=['one', 'two', 'three'])
    # Just the default branch isn't allowed
    TEST.run(test=lambda: run(gen(5, 1) |
                              case(map(lambda x: (100 * x)))),
             expected_err='case requires at least 2 arguments')
    # Function/pipeline confusion
    TEST.run(test=lambda: run(gen(5, 1) |
                              case(map(lambda x: (100 * x)), map(lambda x: (-x)), lambda x: x < 3)),
             expected_err='Expected function')
    TEST.run(test=lambda: run(gen(5, 1) |
                              case(lambda x: x < 3, lambda: 123)),
             expected_err='Expected pipeline')


@timeit
def test_read():
    with TestDir(TEST.env) as testdir:
        file = open(f'{testdir}/f1.csv', 'w')
        file.writelines(['1,2.3,ab\n',
                         '2,3.4,xy\n',
                         '3,4.5,"m,n"\n'])
        file.close()
        file = open(f'{testdir}/f2.tsv', 'w')
        file.writelines(['1\t2.3\tab\n',
                         '2\t3.4\txy\n'])
        file.close()
        file = open(f'{testdir}/f3.txt', 'w')
        file.writelines(['hello,world\n',
                         'goodbye\n'])
        file.close()
        file = open(f'{testdir}/headings.csv', 'w')
        file.writelines(['c1, c2,c3 \n',  # various whitespace paddings
                         'a,b,c\n',
                         'd,e,f\n'])
        file.close()
        file = open(f'{testdir}/headings_tricky_data.csv', 'w')
        file.writelines(['c1,c2,c3\n',
                         'a,b\n',
                         'c,d,e,f\n'
                         ',\n'])
        file.close()
        file = open(f'{testdir}/headings_fixable.csv', 'w')
        file.writelines(['c 1, c$#2,c+3- \n',
                         'a,b,c\n',
                         'd,e,f\n'])
        file.close()
        file = open(f'{testdir}/headings_unfixable_1.csv', 'w')
        file.writelines(['c1,c1,c3\n',
                         'a,b,c\n',
                         'd,e,f\n'])
        file.close()
        file = open(f'{testdir}/headings_unfixable_2.csv', 'w')
        file.writelines(['c_1,c$1,c3\n',
                         'a,b,c\n',
                         'd,e,f\n'])
        file.close()
        # Files
        TEST.run(lambda: run(ls(f'{testdir}/f1.csv', f'{testdir}/f3.txt') | read()),
                 expected_out=['1,2.3,ab',
                               '2,3.4,xy',
                               '3,4.5,"m,n"',
                               'hello,world',
                               'goodbye'])
        # Files with labels
        TEST.run(lambda: run(ls(f'{testdir}/f1.csv', f'{testdir}/f3.txt')
                             | read(label=True)
                             | map(lambda f, x: (str(f), x))),
                 expected_out=[('f1.csv', '1,2.3,ab'),
                               ('f1.csv', '2,3.4,xy'),
                               ('f1.csv', '3,4.5,"m,n"'),
                               ('f3.txt', 'hello,world'),
                               ('f3.txt', 'goodbye')])
        # CSV
        TEST.run(lambda: run(ls(f'{testdir}/f1.csv') | read(csv=True)),
                 expected_out=[('1', '2.3', 'ab'),
                               ('2', '3.4', 'xy'),
                               ('3', '4.5', 'm,n')])
        # CSV with labels
        TEST.run(lambda: run(ls(f'{testdir}/f1.csv') |
                             read(csv=True, label=True) |
                             map(lambda f, x, y, z: (str(f), x, y, z))),
                 expected_out=[('f1.csv', '1', '2.3', 'ab'),
                               ('f1.csv', '2', '3.4', 'xy'),
                               ('f1.csv', '3', '4.5', 'm,n')])
        # TSV
        TEST.run(lambda: run(ls(f'{testdir}/f2.tsv') | read(tsv=True)),
                 expected_out=[('1', '2.3', 'ab'),
                               ('2', '3.4', 'xy')])
        # TSV with labels
        TEST.run(lambda: run(ls(f'{testdir}/f2.tsv') |
                             read(label=True, tsv=True) |
                             map(lambda f, x, y, z: (str(f), x, y, z))),
                 expected_out=[('f2.tsv', '1', '2.3', 'ab'),
                               ('f2.tsv', '2', '3.4', 'xy')])
        # --pickle testing is done in test_write()
        # Filenames on commandline
        TEST.run(lambda: run(read(f'{testdir}/f1.csv')),
                 expected_out=['1,2.3,ab', '2,3.4,xy', '3,4.5,"m,n"'])
        TEST.run(lambda: run(read(f'{testdir}/f?.*')),
                 expected_out=['1,2.3,ab', '2,3.4,xy', '3,4.5,"m,n"',
                               '1\t2.3\tab', '2\t3.4\txy',
                               'hello,world', 'goodbye'])
        # Flags inherited from FilenamesOp
        TEST.run(lambda: run(read(f'{testdir}/f[1-3]*', label=True, recursive=True) | map(lambda f, l: (str(f), l))),
                 expected_out=[('f1.csv', '1,2.3,ab'),
                               ('f1.csv', '2,3.4,xy'),
                               ('f1.csv', '3,4.5,"m,n"'),
                               ('f2.tsv', '1\t2.3\tab'),
                               ('f2.tsv', '2\t3.4\txy'),
                               ('f3.txt', 'hello,world'),
                               ('f3.txt', 'goodbye')])
        # File does not exist
        TEST.run(lambda: run(read(f'{testdir}/nosuchfile')),
                 expected_err='No qualifying paths')
        # directory
        TEST.run(lambda: run(read(f'{testdir}', depth=0)),
                 expected_out=[])
        # symlink
        os.system(f'ln -s {testdir}/f1.csv {testdir}/symlink_f1.csv')
        TEST.run(lambda: run(read(f'{testdir}/symlink_f1.csv')),
                 expected_out=['1,2.3,ab',
                               '2,3.4,xy',
                               '3,4.5,"m,n"'])
        # Column headings
        TEST.run(lambda: run(read(f'{testdir}/f3.txt', headings=True)),
                 expected_err='-h|--headings can only be specified with')
        TEST.run(lambda: run(read(f'{testdir}/f3.txt', headings=True, pickle=True)),
                 expected_err='-h|--headings can only be specified with')
        TEST.run(lambda: run(read(f'{testdir}/f3.txt', skip_headings=True)),
                 expected_err='-s|--skip-headings can only be specified with')
        TEST.run(lambda: run(read(f'{testdir}/f3.txt', skip_headings=True, pickle=True)),
                 expected_err='-s|--skip-headings can only be specified with')
        TEST.run(lambda: run(read(f'{testdir}/f3.txt', headings=True, skip_headings=True)),
                 expected_err='Cannot specify more than one of')
        TEST.run(
            lambda: run(read(f'{testdir}/headings.csv', csv=True, headings=True) | map(lambda t: (t.c1, t.c2, t.c3))),
            expected_out=[('a', 'b', 'c'),
                          ('d', 'e', 'f')])
        TEST.run(lambda: run(read(f'{testdir}/headings.csv', csv=True, headings=True, label=True) |
                             map(lambda t: (str(t.LABEL), t.c1, t.c2, t.c3))),
                 expected_out=[('headings.csv', 'a', 'b', 'c'),
                               ('headings.csv', 'd', 'e', 'f')])
        TEST.run(lambda: run(read(f'{testdir}/headings.csv', csv=True, skip_headings=True)),
                 expected_out=[('a', 'b', 'c'),
                               ('d', 'e', 'f')])
        TEST.run(lambda: run(read(f'{testdir}/headings_tricky_data.csv', csv=True, headings=True) |
                             map(lambda t: (t.c1, t.c2, t.c3))),
                 expected_out=[('a', 'b', None),
                               Error('Incompatible with headings'),
                               ('', '', None)])
        TEST.run(lambda: run(read(f'{testdir}/headings_fixable.csv', csv=True, headings=True) |
                             map(lambda t: (t.c_1, t.c__2, t.c_3_))),
                 expected_out=[('a', 'b', 'c'),
                               ('d', 'e', 'f')])
        TEST.run(lambda: run(read(f'{testdir}/headings_unfixable_1.csv', csv=True, headings=True)),
                 expected_out=[Error('Cannot generate identifiers from headings'),
                               ('a', 'b', 'c'),
                               ('d', 'e', 'f')])
        TEST.run(lambda: run(read(f'{testdir}/headings_unfixable_2.csv', csv=True, headings=True)),
                 expected_out=[Error('Cannot generate identifiers from headings'),
                               ('a', 'b', 'c'),
                               ('d', 'e', 'f')])
    # Resume after error
    with TestDir(TEST.env) as testdir:
        TEST.run(test=lambda: run(cd(testdir)))
        TEST.run(test=lambda: run(bash('echo aaa > a')))
        TEST.run(test=lambda: run(bash('echo aaa > aa')))
        TEST.run(test=lambda: run(bash('echo bbb > b')))
        TEST.run(test=lambda: run(bash('echo ccc > c')))
        TEST.run(test=lambda: run(bash('echo ccc > cc')))
        TEST.run(test=lambda: run(bash('echo ddd > d')))
        TEST.run(test=lambda: run(bash('chmod 000 aa b cc d')))
        TEST.run(test=lambda: run(read('*', label=True) | map(lambda f, line: (f.name, line))),
                 expected_out=[('a', 'aaa'),
                               ('c', 'ccc')])
        TEST.run(test=lambda: run(read('a*', 'c*', label=True) | map(lambda f, line: (f.name, line))),
                 expected_out=[('a', 'aaa'),
                               ('c', 'ccc')])
        TEST.run(test=lambda: run(ls('*', file=True) | read(label=True) | map(lambda f, line: (f.name, line))),
                 expected_out=[('a', 'aaa'),
                               ('c', 'ccc')])
        TEST.run(test=lambda: run(ls('a*', 'c*', file=True) | read(label=True) | map(lambda f, line: (f.name, line))),
                 expected_out=[('a', 'aaa'),
                               ('c', 'ccc')])


@timeit
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


@timeit
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


@timeit
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


@timeit
def test_filter():
    TEST.run(test=lambda: run(gen(6) | map(lambda x: (x, x)) | expand() | filt(gen(3))),
             expected_out=[0, 0, 1, 1, 2, 2])
    TEST.run(test=lambda: run(gen(6) | map(lambda x: (x, x)) | expand() | filt(gen(3), keep=True)),
             expected_out=[0, 0, 1, 1, 2, 2])
    TEST.run(test=lambda: run(gen(6) | map(lambda x: (x, x)) | expand() | filt(gen(3), discard=True)),
             expected_out=[3, 3, 4, 4, 5, 5])
    TEST.run(test=lambda: run(gen(6) | map(lambda x: (x, x)) | filt(gen(3), compare=lambda x, y: x)),
             expected_out=[(0, 0), (1, 1), (2, 2)])
    TEST.run(test=lambda: run(gen(6) | map(lambda x: (x, x)) | filt(gen(3), keep=True, compare=lambda x, y: x)),
             expected_out=[(0, 0), (1, 1), (2, 2)])
    TEST.run(test=lambda: run(gen(6) | map(lambda x: (x, x)) | filt(gen(3), discard=True, compare=lambda x, y: x)),
             expected_out=[(3, 3), (4, 4), (5, 5)])
    TEST.run(test=lambda: run(gen(6) | filt(gen(3), discard=True, keep=True)),
             expected_err='Cannot specify more than one')


@timeit
def test_args():
    # gen
    TEST.run(test=lambda: run(gen(5, 1) | args(lambda n: gen(n)) | map(lambda x: -x)),
             expected_out=[0, 0, -1, 0, -1, -2, 0, -1, -2, -3, 0, -1, -2, -3, -4])
    TEST.run(test=lambda: run(gen(6, 1) | args(lambda count, start: gen(count, start))),
             expected_out=[2, 4, 5, 6, 6, 7, 8, 9, 10])
    # ls
    with TestDir(TEST.env) as testdir:
        os.system(f'mkdir {testdir}/d1')
        os.system(f'mkdir {testdir}/d2')
        os.system(f'mkdir {testdir}/d3')
        os.system(f'touch {testdir}/d1/f1')
        os.system(f'touch {testdir}/d2/f2')
        os.system(f'touch {testdir}/d3/f3')
        TEST.run(
            test=lambda: run(ls(f'{testdir}/*', dir=True) | args(lambda d: ls(d, file=True)) | map(lambda f: f.name)),
            expected_out=['f1', 'f2', 'f3'])
        os.system(f'touch {testdir}/a_file')
        os.system(f'touch {testdir}/"a file"')
        os.system(f'touch {testdir}/"a file with a \' mark"')
        os.system(f'rm -rf {testdir}/d')
        os.system(f'mkdir {testdir}/d')
        # TODO: Disabled due to bug 108
        # TEST.run(test=lambda: run(ls(f'{testdir}', file=True) |
        #                           args(lambda files: bash(f'mv -t d {quote_files(files)}'), all=True)),
        #          verification=lambda: run(ls('d', file=True) | map(lambda f: f.name)),
        #          expected_out=['a file', "a file with a ' mark", 'a_file'])
    # head
    TEST.run(lambda: run(gen(4, 1) | args(lambda n: gen(10) | head(n))),
             expected_out=[0, 0, 1, 0, 1, 2, 0, 1, 2, 3])
    # tail
    TEST.run(test=lambda: run(gen(4, 1) | args(lambda n: gen(10) | tail(n + 1))),
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
    if SQL:
        TEST.run(test=lambda: run(sql("drop table if exists t") | select(lambda x: False)))
        TEST.run(test=lambda: run(sql("create table t(f int)") | select(lambda x: False)))
        TEST.run(test=lambda: run(gen(5) | args(lambda x: sql("insert into t values(%s)", x))),
                 verification=lambda: run(sql("select * from t order by f")),
                 expected_out=[0, 1, 2, 3, 4])
    # window
    TEST.run(test=lambda: run(gen(3) | args(lambda w: gen(10) | window(disjoint=w))),
             expected_out=[(0, 1, 2, 3, 4, 5, 6, 7, 8, 9),
                           0, 1, 2, 3, 4, 5, 6, 7, 8, 9,
                           (0, 1), (2, 3), (4, 5), (6, 7), (8, 9)])
    # nested args
    TEST.run(test=lambda: run(gen(3) | args(lambda i: gen(3, i + 100) | args(lambda j: gen(3, j + 1000)))),
             expected_out=[1100, 1101, 1102, 1101, 1102, 1103, 1102, 1103, 1104,
                           1101, 1102, 1103, 1102, 1103, 1104, 1103, 1104, 1105,
                           1102, 1103, 1104, 1103, 1104, 1105, 1104, 1105, 1106])
    # negative testing
    TEST.run(test=lambda: run(gen(3) | args(lambda x, y: 123, all=True)),
             expected_err="With -a|--all option, the pipelines must have exactly one parameter.")
    TEST.run(test=lambda: run(gen(3) | args(lambda: 123, all=True)),
             expected_err="With -a|--all option, the pipelines must have exactly one parameter.")
    TEST.run(test=lambda: run(gen(3) | args(lambda: 123)),
             expected_err="The args pipelines must be parameterized")

    TEST.run(test=lambda: run(gen(3) | args(lambda: gen(3))),
             expected_err='The args pipelines must be parameterized')
    # Bug 94
    TEST.run(test=lambda: run(gen(4, 1) | args(lambda n: gen(n)) | window(lambda x: x == 0)),
             expected_out=[0, (0, 1), (0, 1, 2), (0, 1, 2, 3)])
    # Bug 116
    g = lambda n: gen(n)
    TEST.run(test=lambda: run(gen(3, 1) | args(lambda n: g(n))),
             expected_out=[0, 0, 1, 0, 1, 2])


@timeit
def test_env():
    TEST.reset_environment()
    # Env vars defined by user
    TEST.run(test=lambda: run(env('v1')),
             expected_err='v1 is undefined')
    TEST.run(test=lambda: run(assign('v2', 'asdf')),
             verification=lambda: run(env('v2')),
             expected_out=[('v2', 'asdf')])
    TEST.run(test=lambda: run(env(delete='v2')),
             expected_out=[('v2', 'asdf')])
    TEST.run(test=lambda: run(env(delete='v2')),
             expected_out=[])
    TEST.run(test=lambda: run(assign('v3xyz', 1)))
    TEST.run(test=lambda: run(assign('v3xyzw', 2)))
    TEST.run(test=lambda: run(assign('v3xzw', 3)))
    TEST.run(test=lambda: run(env(pattern='xyz') | sort()),
             expected_out=[('v3xyz', 1),
                           ('v3xyzw', 2)])
    # Env defined by marcel
    TEST.run(test=lambda: run(env(var='USER')),
             expected_out=[('USER', getpass.getuser())])
    TEST.run(test=lambda: run(assign('USER', 'asdf')),
             expected_err='cannot be modified or deleted')
    TEST.run(test=lambda: run(env(delete='USER')),
             expected_err='cannot be modified or deleted')
    # Env inherited from host
    TEST.run(test=lambda: run(env('asdfasdf', os=True)),
             expected_err='is undefined')
    TEST.run(test=lambda: run(env('SHELL', os=True)),
             expected_out=[('SHELL', os.getenv('SHELL'))])
    TEST.run(test=lambda: run(env(pattern='SHELL', os=True) | select(lambda k, v: k == "SHELL")),
             expected_out=[('SHELL', os.getenv('SHELL'))])
    TEST.run(test=lambda: run(env(delete='SHELL', os=True)),
             expected_err='Cannot specify more than one of')


@timeit
def test_pos():
    TEST.run(test=lambda: run(gen(5) |
                              map(lambda x: (x, pos())) |
                              select(lambda x, p1: x % 2 == 0) |
                              map(lambda x, p1: (x, p1, pos()))),
             expected_out=[(0, 0, 0), (2, 2, 1), (4, 4, 2)])


@timeit
def test_json():
    def test_json_parse():
        # Scalars
        TEST.run(test=lambda: run(map(lambda: '"a"') | map(lambda j: json_parse(j))),
                 expected_out=['a'])
        TEST.run(test=lambda: run(map(lambda: '123') | map(lambda j: json_parse(j))),
                 expected_out=[123])
        TEST.run(test=lambda: run(map(lambda: '4.5') | map(lambda j: json_parse(j))),
                 expected_out=[4.5])
        TEST.run(test=lambda: run(map(lambda: 'true') | map(lambda j: json_parse(j))),
                 expected_out=[True])
        TEST.run(test=lambda: run(map(lambda: 'false') | map(lambda j: json_parse(j))),
                 expected_out=[False])
        TEST.run(test=lambda: run(map(lambda: 'null') | map(lambda j: json_parse(j))),
                 expected_out=[None])
        TEST.run(test=lambda: run(map(lambda: 'abc') | map(lambda j: json_parse(j))),  # Unquoted string
                 expected_out=[Error('Expecting value')])
        TEST.run(test=lambda: run(map(lambda: '--3') | map(lambda j: json_parse(j))),  # Malformed integer
                 expected_out=[Error('Expecting value')])
        TEST.run(test=lambda: run(map(lambda: '1.2.3') | map(lambda j: json_parse(j))),  # Malformed float
                 expected_out=[Error('Extra data')])
        # Structures (flat)
        TEST.run(test=lambda: run(map(lambda: '[]') | map(lambda j: json_parse(j))),
                 expected_out=[[]])
        TEST.run(test=lambda: run(map(lambda: '["a", 1]') | map(lambda j: json_parse(j))),
                 expected_out=[['a', 1]])
        TEST.run(test=lambda: run(map(lambda: '{}') | map(lambda j: json_parse(j))),
                 expected_out=[{}])
        TEST.run(test=lambda: run(map(lambda: '{"a": 1, "b": 2, "c c": 3.3}') | map(lambda j: json_parse(j))),
                 expected_out=[{'a': 1, 'b': 2, 'c c': 3.3}])
        # Structures (nested)
        TEST.run(test=lambda: run(map(lambda: '["a", {"b": 2, "c": [3, 4, {"d": 5, "e": [], "f": {}}]}]')
                                  | map(lambda j: json_parse(j))),
                 expected_out=[['a', {'b': 2, 'c': [3, 4, {'d': 5, 'e': [], 'f': {}}]}]])
        TEST.run(test=lambda: run(map(lambda: '{"q": ["a", {"b": 2, "c": [3, 4, {"d": 5, "e": [], "f": {}}]}]}')
                                  | map(lambda j: json_parse(j))),
                 expected_out=[{'q': ['a', {'b': 2, 'c': [3, 4, {'d': 5, 'e': [], 'f': {}}]}]}])
        TEST.run(test=lambda: run(map(lambda: '[1, 2') | map(lambda j: json_parse(j))),
                 expected_out=[Error("Expecting ',' delimiter")])
        TEST.run(test=lambda: run(map(lambda: '[1, ') | map(lambda j: json_parse(j))),
                 expected_out=[Error("Expecting value")])
        TEST.run(test=lambda: run(map(lambda: '{"a": 1,}') | map(lambda j: json_parse(j))),
                 expected_out=[Error("Expecting property name")])
        TEST.run(test=lambda: run(map(lambda: '{"a": 1') | map(lambda j: json_parse(j))),
                 expected_out=[Error("delimiter: ")])
        TEST.run(test=lambda: run(map(lambda: '{"a", 1}') | map(lambda j: json_parse(j))),
                 expected_out=[Error("delimiter: ")])
        # Structure access
        TEST.run(test=lambda: run(map(lambda: '["a", {"b": 2, "c": [3, 4, {"d": 5, "e": [], "f": {}, "g g": 7.7}]}]')
                                  | map(lambda j: json_parse(j))
                                  | map(lambda *j: (j[0], j[1].b, j[1].c[1], j[1].c[2].d, j[1].c[2]['g g']))),
                 expected_out=[('a', 2, 4, 5, 7.7)])

    def test_json_format():
        # Scalars
        TEST.run(test=lambda: run(map(lambda: ['a']) | map(lambda j: json_format(j))),
                 expected_out=['"a"'])
        TEST.run(test=lambda: run(map(lambda: [123]) | map(lambda j: json_format(j))),
                 expected_out=['123'])
        TEST.run(test=lambda: run(map(lambda: [4.5]) | map(lambda j: json_format(j))),
                 expected_out=['4.5'])
        TEST.run(test=lambda: run(map(lambda: [True]) | map(lambda j: json_format(j))),
                 expected_out=['true'])
        TEST.run(test=lambda: run(map(lambda: [False]) | map(lambda j: json_format(j))),
                 expected_out=['false'])
        TEST.run(test=lambda: run(map(lambda: [None]) | map(lambda j: json_format(j))),
                 expected_out=['null'])
        # Structures (nested)
        TEST.run(test=lambda: run(map(lambda: ['a', {'b': 2, 'c': [3, 4, {'d': 5, 'e': [], 'f': {}}]}])
                                  | map(lambda *j: json_format(j))),
                 expected_out=["""["a", {"b": 2, "c": [3, 4, {"d": 5, "e": [], "f": {}}]}]"""])
        TEST.run(test=lambda: run(map(lambda: {'q': ['a', {'b': 2, 'c': [3, 4, {'d': 5, 'e': [], 'f': {}}]}]})
                                  | map(lambda *j: json_format(j))),
                 expected_out=["""[{"q": ["a", {"b": 2, "c": [3, 4, {"d": 5, "e": [], "f": {}}]}]}]"""])

    test_json_parse()
    test_json_format()


@timeit
def test_upload():
    with TestDir(TEST.env) as testdir:
        os.system(f'mkdir {testdir}/source')
        os.system(f'touch {testdir}/source/a {testdir}/source/b "{testdir}/source/a b"')
        os.system(f'rm -rf {testdir}/dest')
        os.system(f'mkdir {testdir}/dest')
        # No qualifying paths
        # TEST.run(test=lambda: run(upload(CLUSTER1, f'{testdir}/dest', '/nosuchfile')),
        #          expected_err='No qualifying paths')
        # Qualifying paths exist but insufficient permission to read
        os.system(f'sudo touch {testdir}/nope1')
        os.system(f'sudo rm {testdir}/nope?')
        os.system(f'touch {testdir}/nope1')
        os.system(f'touch {testdir}/nope2')
        os.system(f'chmod 000 {testdir}/nope?')
        TEST.run(test=lambda: run(upload(CLUSTER1, f'{testdir}/dest', f'{testdir}/nope1')),
                 expected_out=[Error('nope1: Permission denied')])
        TEST.run(test=lambda: run(upload(CLUSTER1, f'{testdir}/dest', f'{testdir}/nope?')),
                 expected_out=[Error('Permission denied'),
                               Error('Permission denied')])
        # Target dir must be absolute
        TEST.run(test=lambda: run(upload(CLUSTER1, 'dest', f'{testdir}/source/a')),
                 expected_err='Target directory must be absolute: dest')
        # There must be at least one source
        TEST.run(test=lambda: run(upload(CLUSTER1, f'{testdir}/dest')),
                 expected_err='No qualifying paths')
        # Copy fully-specified filenames
        TEST.run(test=lambda: run(upload(CLUSTER1, f'{testdir}/dest', f'{testdir}/source/a', f'{testdir}/source/b')),
                 verification=lambda: run(ls(f'{testdir}/dest', file=True) | map(lambda f: f.name)),
                 expected_out=['a', 'b'])
        os.system(f'rm {testdir}/dest/*')
        # Filename with spaces
        TEST.run(test=lambda: run(upload(CLUSTER1, f'{testdir}/dest', f'{testdir}/source/a b')),
                 verification=lambda: run(ls(f'{testdir}/dest', file=True) | map(lambda f: f.name)),
                 expected_out=['a b'])
        os.system(f'rm {testdir}/dest/*')
        # Wildcard
        TEST.run(test=lambda: run(upload(CLUSTER1, f'{testdir}/dest', f'{testdir}/source/a*')),
                 verification=lambda: run(ls(f'{testdir}/dest', file=True) | map(lambda f: f.name)),
                 expected_out=['a', 'a b'])
        os.system(f'rm {testdir}/dest/*')


@timeit
def test_download():
    with TestDir(TEST.env) as testdir:
        os.system(f'rm -rf {testdir}/source')
        os.system(f'mkdir {testdir}/source')
        os.system(f'touch {testdir}/source/a {testdir}/source/b "{testdir}/source/a b"')
        os.system(f'rm -rf {testdir}/dest')
        os.system(f'mkdir {testdir}/dest')
        # No qualifying paths
        TEST.run(test=lambda: run(download(f'{testdir}/dest', CLUSTER2, '/nosuchfile')),
                 expected_out=[Error('No such file or directory'), Error('No such file or directory')])
        # Qualifying paths exist but insufficient permission to read
        os.system(f'sudo touch {testdir}/nope1')
        os.system(f'sudo rm {testdir}/nope?')
        os.system(f'touch {testdir}/nope1')
        os.system(f'touch {testdir}/nope2')
        os.system(f'chmod 000 {testdir}/nope?')
        TEST.run(test=lambda: run(download(f'{testdir}/dest', CLUSTER2, f'{testdir}/nope1')),
                 expected_out=[Error('Permission denied'), Error('Permission denied')])
        TEST.run(test=lambda: run(download(f'{testdir}/dest', CLUSTER2, f'{testdir}/nope?')),
                 expected_out=[Error('Permission denied'), Error('Permission denied'),
                               Error('Permission denied'), Error('Permission denied')])
        # There must be at least one source specified (regardless of what actually exists remotely)
        TEST.run(test=lambda: run(download(f'{testdir}/dest', CLUSTER2)),
                 expected_err='No remote files specified')
        # Copy fully-specified filenames
        TEST.run(
            test=lambda: run(download(f'{testdir}/dest', CLUSTER2, f'{testdir}/source/a', f'{testdir}/source/b')),
            verification=lambda: run(ls(f'{testdir}/dest', file=True, recursive=True) |
                                     map(lambda f: f.relative_to(f'{testdir}/dest')) |
                                     sort()),
            expected_out=[f'{NODE1}/a', f'{NODE1}/b', f'{NODE2}/a', f'{NODE2}/b'])
        # Leave files in place, delete some of them, try downloading again
        os.system(f'rm -rf {testdir}/dest/{NODE1}')
        os.system(f'rm -rf {testdir}/dest/{NODE2}/*')
        TEST.run(test=lambda: run(download(f'{testdir}/dest', CLUSTER2, f'{testdir}/source/a', f'{testdir}/source/b')),
                 verification=lambda: run(ls(f'{testdir}/dest', file=True, recursive=True) |
                                          map(lambda f: f.relative_to(f'{testdir}/dest')) |
                                          sort()),
                 expected_out=[f'{NODE1}/a', f'{NODE1}/b', f'{NODE2}/a', f'{NODE2}/b'])
        os.system(f'rm -rf {testdir}/dest/*')
        # Filename with spaces
        TEST.run(test=lambda: run(download(f'{testdir}/dest', CLUSTER2, f'{testdir}/source/a\\ b')),
                 verification=lambda: run(ls(f'{testdir}/dest', file=True, recursive=True) |
                                          map(lambda f: f.relative_to(f'{testdir}/dest')) |
                                          sort()),
                 expected_out=[f'{NODE1}/a b', f'{NODE2}/a b'])
        os.system(f'rm -rf {testdir}/dest/*')
        # # Relative directory
        # current_dir = os.getcwd()
        # os.chdir(f'{testdir}')
        # TEST.run(test=lambda: run(download('dest', 'CLUSTER1', f'{testdir}/source/a', f'{testdir}/source/b')),
        #          verification=lambda: run(ls(f'{testdir}/dest', file=True) | map(lambda f: f.name)),
        #          expected_out=['a', 'b'])
        # os.system(f'rm {testdir}/dest/*')
        # os.chdir(current_dir)
        # Wildcard
        TEST.run(test=lambda: run(download(f'{testdir}/dest', CLUSTER2, f'{testdir}/source/a*')),
                 verification=lambda: run(ls(f'{testdir}/dest', file=True, recursive=True) |
                                          map(lambda f: f.relative_to(f'{testdir}/dest')) |
                                          sort()),
                 expected_out=[f'{NODE1}/a', f'{NODE1}/a b',
                               f'{NODE2}/a', f'{NODE2}/a b'])
        os.system(f'rm -rf {testdir}/dest/*')


@timeit
def test_api_run():
    # Error-free output, just an op
    TEST.run(test=lambda: run(gen(3)),
             expected_out=[0, 1, 2])
    # Error-free output, pipelines
    TEST.run(test=lambda: run(gen(3) | map(lambda x: -x)),
             expected_out=[0, -1, -2])
    # With errors
    TEST.run(test=lambda: run(gen(3, -1) | map(lambda x: 1 / x)),
             expected_out=[-1.0, Error('division by zero'), 1.0])


@timeit
def test_api_gather():
    # Default gather behavior
    TEST.run(test=lambda: gather(gen(3, -1) | map(lambda x: 1 / x)),
             expected_return=[-1.0, Error('division by zero'), 1.0])
    # Don't unwrap singletons
    TEST.run(test=lambda: gather(gen(3, -1) | map(lambda x: 1 / x), unwrap_singleton=False),
             expected_return=[(-1.0,), Error('division by zero'), (1.0,)])


@timeit
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


@timeit
def test_api_iterator():
    TEST.run(test=lambda: list(gen(3)),
             expected_return=[0, 1, 2])
    TEST.run(test=lambda: list(gen(3, -1) | map(lambda x: 1 / x)),
             expected_return=[-1.0, Error('division by zero'), 1.0])


@timeit
def test_struct():
    TEST.run(test=lambda: run(gen(3) | map(lambda x: o(x=x, y=x + 1)) | map(lambda o: o.x + o.y)),
             expected_out=[1, 3, 5])


@timeit
def test_cast():
    TEST.run(test=lambda: run(gen(3) | cast(str) | map(lambda s: f"<<<{s}>>>")),
             expected_out=['<<<0>>>', '<<<1>>>', '<<<2>>>'])
    TEST.run(test=lambda: run(gen(3) | cast(str) | cast(float)),
             expected_out=[0.0, 1.0, 2.0])
    TEST.run(test=lambda: run(gen(3) | cast(float, float)),
             expected_out=[0.0, 1.0, 2.0])
    TEST.run(test=lambda: run(gen(3) | map(lambda x: (x, x, x)) | cast(float, str)),
             expected_out=[(0.0, '0', 0),
                           (1.0, '1', 1),
                           (2.0, '2', 2)])
    TEST.run(test=lambda: run(gen(1) |
                              map(lambda x: (x, x, x)) |
                              cast(float, str) |
                              map(lambda a, b, c: (type(a), type(b), type(c)))),
             expected_out=[(float, str, int)])
    TEST.run(test=lambda: run(map(lambda: (None, None, None)) | cast(str, float)),
             expected_out=[(None, None, None)])
    # Errors
    # A marcel function
    TEST.run(test=lambda: run(gen(1) | cast(map)),
             expected_out=[Error('map')])
    # A python function
    TEST.run(test=lambda: run(gen(1) | cast(list)),
             expected_out=[Error('list')])


@timeit
def test_bug_10():
    TEST.run(lambda: run(sort()), expected_err='cannot be the first operator in a pipeline')
    TEST.run(lambda: run(unique()), expected_err='cannot be the first operator in a pipeline')
    TEST.run(lambda: run(window(overlap=2)), expected_err='cannot be the first operator in a pipeline')
    TEST.run(lambda: run(map(lambda: 3)), expected_out=[3])
    TEST.run(lambda: run(args(lambda x: gen(3))), expected_err='cannot be the first operator in a pipeline')


@timeit
def test_bug_126():
    f = reservoir('f')
    fact = lambda x: gen(x, 1) | args(lambda n: gen(n, 1) | red(r_times) | map(lambda f: (n, f)))
    TEST.run(test=lambda: run(fact(5) | store(f)),
             verification=lambda: run(load(f)),
             expected_out=[(1, 1), (2, 2), (3, 6), (4, 24), (5, 120)])


@timeit
def test_bug_136():
    TEST.run(lambda: run(gen(3, 1) | args(lambda n: gen(2, 100) | map(lambda x: x + n)) | red(r_plus)),
             expected_out=[615])


@timeit
def test_bug_198():
    with TestDir(TEST.env) as testdir:
        # IsADirectoryError
        TEST.run(test=lambda: run(gen(3) | write(f'{testdir}')),
                 expected_err='Is a directory')
        os.system(f'touch {testdir}/cannot_write')
        # PermissionError
        os.system(f'chmod 000 {testdir}/cannot_write')
        TEST.run(test=lambda: run(gen(3) | write(f'{testdir}/cannot_write')),
                 expected_err='Permission denied')
        # FileExistsError: Can't happen?


@timeit
def test_bug_200():
    with TestDir(TEST.env) as testdir:
        source = f'{testdir}/source.csv'
        target = f'{testdir}/target.csv'
        target2 = f'{testdir}/target2.csv'
        os.system(f'rm -rf {testdir}')
        os.system(f'mkdir {testdir}')
        # number, unquoted string, single-quoted string
        os.system(f'''echo "123,a,'b,c'" > {source}''')
        # double-quoted string
        os.system(f'''echo '"d,e"' >> {source}''')
        # Check source
        TEST.run(test=lambda: run(read(source)),
                 expected_out=["""123,a,'b,c'""", '''"d,e"'''])
        TEST.run(test=lambda: run(read(source, csv=True)),
                 expected_out=[('123', 'a', "'b", "c'"),
                               'd,e'])
        # Test --csv reading and writing
        TEST.run(test=lambda: run(read(source, csv=True) | write(target, csv=True)))
        TEST.run(test=lambda: run(read(target)),
                 expected_out=['''"123","a","'b","c'"''', '"d,e"'])
        TEST.run(test=lambda: run(read(target, csv=True)),
                 expected_out=[('123', 'a', "'b", "c'"),
                               'd,e'])
        # Test whether write -c output followed by read -c/write -c is a fixed point.
        TEST.run(test=lambda: run(read(target, csv=True) | write(target2, csv=True)))
        TEST.run(test=lambda: run(read(target2)),
                 expected_out=['''"123","a","'b","c'"''', '"d,e"'])
        TEST.run(test=lambda: run(read(target2, csv=True)),
                 expected_out=[('123', 'a', "'b", "c'"),
                               'd,e'])


@timeit
def test_bug_206():
    with TestDir(TEST.env) as testdir:
        home = pathlib.Path('~').expanduser().absolute()
        TEST.run(test=lambda: run(cd(testdir)),
                 verification=lambda: run(pwd() | map(lambda d: str(d))),
                 expected_out=testdir)
        TEST.run(test=lambda: run(bash('mkdir "a b" x1 x2')),
                 verification=lambda: run(ls(file=True, dir=True) | sort() | map(lambda d: str(d))),
                 expected_out=['.', "'a b'", 'x1', 'x2'])
        # Wildcard
        TEST.run(test=lambda: run(cd('a*')),
                 verification=lambda: run(pwd() | map(lambda d: str(d))),
                 expected_out=f"'{testdir}/a b'")
        TEST.run(test=lambda: run(cd('..')),
                 verification=lambda: run(pwd() | map(lambda d: str(d))),
                 expected_out=testdir)
        TEST.run(test=lambda: run(pushd('*b')),
                 verification=lambda: run(pwd() | map(lambda d: str(d))),
                 expected_out=f"'{testdir}/a b'")
        TEST.run(test=lambda: run(popd()),
                 verification=lambda: run(pwd() | map(lambda d: str(d))),
                 expected_out=testdir)
        # Default
        TEST.run(test=lambda: run(cd()),
                 verification=lambda: run(pwd() | map(lambda d: str(d))),
                 expected_out=home)
        TEST.run(test=lambda: run(cd(testdir)),
                 verification=lambda: run(pwd() | map(lambda d: str(d))),
                 expected_out=testdir)
        # Errors
        TEST.run(test=lambda: run(cd('x*')),
                 expected_err='Too many paths')
        TEST.run(test=lambda: run(pwd() | map(lambda d: str(d))),
                 expected_out=testdir)
        TEST.run(test=lambda: run(pushd('x*')),
                 expected_err='Too many paths')
        TEST.run(test=lambda: run(pwd() | map(lambda d: str(d))),
                 expected_out=testdir)
        TEST.run(test=lambda: run(cd('no_such_dir')),
                 expected_err='No qualifying path')
        TEST.run(test=lambda: run(pwd() | map(lambda d: str(d))),
                 expected_out=testdir)
        TEST.run(test=lambda: run(pushd('no_such_dir')),
                 expected_err='No qualifying path')
        TEST.run(test=lambda: run(pwd() | map(lambda d: str(d))),
                 expected_out=testdir)
        TEST.run(test=lambda: run(cd('no_such_dir*')),
                 expected_err='No qualifying path')
        TEST.run(test=lambda: run(pwd() | map(lambda d: str(d))),
                 expected_out=testdir)
        TEST.run(test=lambda: run(pushd('no_such_dir*')),
                 expected_err='No qualifying path')
        TEST.run(test=lambda: run(pwd() | map(lambda d: str(d))),
                 expected_out=testdir)
        TEST.run(test=lambda: run(cd('/tmp')))
        os.system(f'rm -rf {testdir}')


@timeit
def test_bug_212():
    TEST.run(test=lambda: run(gen(3) | args(lambda x: map(lambda: (x, -x)))),
             expected_out=[(0, 0), (1, -1), (2, -2)])
    TEST.run(test=lambda: run(sudo(gen(3) | args(lambda x: map(lambda: (x, -x))))),
             expected_out=[(0, 0), (1, -1), (2, -2)])


@timeit
def test_bug_229():
    g = reservoir('g')
    gn = lambda n: gen(int(n)) | store(g)
    TEST.run(test=lambda: run(gn(3)))
    TEST.run(test=lambda: run(load(g)),
             expected_out=[0, 1, 2])


@timeit
def test_bug_230():
    with TestDir(TEST.env) as testdir:
        TEST.run(lambda: run(cd(testdir)))
        os.system('touch a1 a2')
        TEST.run(test=lambda: run(bash('ls -l a?') | map(lambda x: x[-2:])),
                 expected_out=['a1', 'a2'])
        TEST.run(test=lambda: run(bash('ls -i ??') | map(lambda x: x[-2:])),
                 expected_out=['a1', 'a2'])


@timeit
def test_bug_247():
    TEST.run(test=lambda: run(gen(3) | map(lambda x: x / (1 - x))),
             expected_out=[0.0, Error('division by zero'), -2.0])
    TEST.run(test=lambda: run(gen(3) | args(lambda x: map(lambda: x / (1 - x)))),
             expected_out=[0.0, Error('division by zero'), -2.0])
    TEST.run(test=lambda: run(gen(6) | case(lambda x: x % 2 == 0,
                                            map(lambda x: x // (x-2)),
                                            map(lambda x: x * 100))),
             expected_out=[0, 100, Error('by zero'), 300, 2, 500])


@timeit
def test_bug_252():
    TEST.run(test=lambda: run(gen(9) | args(lambda a, b, c: map(lambda: (-a, -b, -c)))),
             expected_out=[(0, -1, -2),
                           (-3, -4, -5),
                           (-6, -7, -8)])
    TEST.run(test=lambda: run(gen(8) | args(lambda a, b, c: map(lambda: (-a, -b, -c)))),
             expected_out=[(0, -1, -2),
                           (-3, -4, -5),
                           Error('bad operand type')])


@timeit
def test_bug_258():
    TEST.run(test=lambda: run(cd('/')),
             verification=lambda: run(pwd() | map(lambda p: str(p))),
             expected_out=['/'])


# For bugs that aren't specific to a single op.
@timeit
def test_bugs():
    test_bug_10()
    test_bug_126()
    test_bug_136()
    test_bug_198()
    test_bug_200()
    test_bug_206()
    test_bug_212()
    test_bug_229()
    test_bug_230()
    test_bug_247()
    test_bug_252()
    test_bug_258()


def main_slow_tests():
    TEST.reset_environment()
    test_upload()
    test_remote()
    test_download()


def main_stable():
    test_gen()
    test_write()
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
    test_source_filenames()
    test_ls()
    test_dir_stack()
    test_fork()
    test_sudo()
    test_version()
    test_assign()
    test_join()
    test_pipeline_args()
    test_sql()
    test_store_load()
    test_case()
    test_read()
    test_intersect()
    test_union()
    test_difference()
    test_filter()
    test_args()
    test_env()
    test_pos()
    test_json()
    test_struct()
    test_cast()
    test_api_run()
    test_api_gather()
    test_api_first()
    test_api_iterator()
    test_bugs()


def main_dev():
    pass


def main():
    TEST.reset_environment()
    main_dev()
    main_stable()
    main_slow_tests()
    TEST.report_failures('test_api')
    sys.exit(TEST.failures)


main()
