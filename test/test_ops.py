import math
import os
import pathlib
import shutil
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

SQL = False  # Until Postgres & psycopg2 are working again


# Utilities for testing filename ops


def relative(base, x):
    x_path = pathlib.Path(x)
    base_path = pathlib.Path(base)
    display_path = x_path.relative_to(base_path)
    return display_path


def absolute(base, x):
    return pathlib.Path(base) / x


def filename_op_setup(dir):
    # test/
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
        'rm -rf /tmp/test',
        'mkdir /tmp/test',
        'mkdir /tmp/test/d',
        'echo f > /tmp/test/f',
        'ln -s /tmp/test/f /tmp/test/sf',
        'ln /tmp/test/f /tmp/test/lf',
        'ln -s /tmp/test/d /tmp/test/sd',
        'echo df > /tmp/test/d/df',
        'ln -s /tmp/test/d/df /tmp/test/d/sdf',
        'ln /tmp/test/d/df /tmp/test/d/ldf',
        'mkdir /tmp/test/d/dd',
        'ln -s /tmp/test/d/dd /tmp/test/d/sdd',
        'echo ddf > /tmp/test/d/dd/ddf']
    # Start clean
    TEST.cd('/tmp')
    shutil.rmtree('/tmp/test', ignore_errors=True)
    # Create test data
    for x in setup_script:
        os.system(x)
    TEST.cd(dir)


def test_no_such_op():
    TEST.run('gen 5 | abc', expected_err='is not defined')


def test_gen():
    # Explicit write
    TEST.run('gen 5 | write',
             expected_out=[0, 1, 2, 3, 4])
    # Implicit write
    TEST.run('gen 5',
             expected_out=[0, 1, 2, 3, 4])
    TEST.run('gen 5 10 | write',
             expected_out=[10, 11, 12, 13, 14])
    TEST.run('gen 5 10 123 | write',
             expected_err='Too many anonymous')
    TEST.run('gen 5 -5 | write',
             expected_out=[-5, -4, -3, -2, -1])
    TEST.run('gen 3 -p 2 | write',
             expected_err='Flags must all appear before the first anonymous arg')
    TEST.run('gen -p 2 3 | write',
             expected_out=['00', '01', '02'])
    TEST.run('gen --pad 2 3 | write',
             expected_out=['00', '01', '02'])
    TEST.run('gen -p 3 3 99 | write',
             expected_out=['099', '100', '101'])
    TEST.run('gen -p 2 3 99 | write',
             expected_err='Padding 2 too small')
    TEST.run('gen -p 4 3 -10 | write',
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


def test_write():
    output_filename = '/tmp/out.txt'
    # Write to stdout
    TEST.run('gen 3 | (x: (x, -x))',
             expected_out=[(0, 0), (1, -1), (2, -2)])
    TEST.run('gen 3 | (x: (x, -x)) | write --format "{}~{}"',
             expected_out=['0~0', '1~-1', '2~-2'])
    TEST.run('gen 3 | (x: (x, -x)) | write -f "{}~{}"',
             expected_out=['0~0', '1~-1', '2~-2'])
    TEST.run('gen 3 | (x: (x, -x)) | write --csv',
             expected_out=['0,0', '1,-1', '2,-2'])
    TEST.run('gen 3 | (x: (x, -x)) | write -c',
             expected_out=['0,0', '1,-1', '2,-2'])
    TEST.run('gen 3 | (x: (x, -x)) | write --tsv',
             expected_out=['0\t0', '1\t-1', '2\t-2'])
    TEST.run('gen 3 | (x: (x, -x)) | write -t',
             expected_out=['0\t0', '1\t-1', '2\t-2'])
    TEST.run('gen 3 | (x: (x, -x)) | write --pickle',
             expected_err='--pickle incompatible with stdout')
    TEST.run('gen 3 | (x: (x, -x)) | write -p',
             expected_err='--pickle incompatible with stdout')
    TEST.run('gen 3 | (x: (x, -x)) | write --csv --tsv',
             expected_err='Cannot specify more than one of')
    # Write to file
    TEST.run('gen 3 | (x: (x, -x)) | write ' + output_filename,
             expected_out=[(0, 0), (1, -1), (2, -2)],
             file=output_filename)
    TEST.run('gen 3 | (x: (x, -x)) | write --format "{}~{}" ' + output_filename,
             expected_out=['0~0', '1~-1', '2~-2'],
             file=output_filename)
    TEST.run('gen 3 | (x: (x, -x)) | write -f "{}~{}" ' + output_filename,
             expected_out=['0~0', '1~-1', '2~-2'],
             file=output_filename)
    TEST.run('gen 3 | (x: (x, -x)) | write --csv ' + output_filename,
             expected_out=['0,0', '1,-1', '2,-2'],
             file=output_filename)
    TEST.run('gen 3 | (x: (x, -x)) | write -c ' + output_filename,
             expected_out=['0,0', '1,-1', '2,-2'],
             file=output_filename)
    TEST.run('gen 3 | (x: (x, -x)) | write --tsv ' + output_filename,
             expected_out=['0\t0', '1\t-1', '2\t-2'],
             file=output_filename)
    TEST.run('gen 3 | (x: (x, -x)) | write -t ' + output_filename,
             expected_out=['0\t0', '1\t-1', '2\t-2'],
             file=output_filename)
    TEST.run('gen 3 | (x: (x, -x)) | write --pickle ' + output_filename,
             verification=f'read --pickle {output_filename}',
             expected_out=[(0, 0), (1, -1), (2, -2)])
    TEST.run('gen 3 | (x: (x, -x)) | write -p ' + output_filename,
             verification=f'read --pickle {output_filename}',
             expected_out=[(0, 0), (1, -1), (2, -2)])
    # Append
    TEST.run('gen 3 | write --append',
             expected_err='--append incompatible with stdout')
    TEST.run('gen 3 | write -a',
             expected_err='--append incompatible with stdout')
    TEST.delete_files(output_filename)
    TEST.run('gen 3 | write --append ' + output_filename,
             verification='read ' + output_filename,
             expected_out=[0, 1, 2])
    TEST.run('gen 3 3 | write --append ' + output_filename,
             verification='read ' + output_filename,
             expected_out=[0, 1, 2, 3, 4, 5])
    TEST.delete_files(output_filename)
    TEST.run('gen 3 | (x: (x, -x)) | write --csv --append ' + output_filename,
             expected_out=['0,0', '1,-1', '2,-2'],
             file=output_filename)
    TEST.run('gen 3 | (x: (x, -x)) | write --tsv --append ' + output_filename,
             expected_out=['0,0', '1,-1', '2,-2',
                           '0\t0', '1\t-1', '2\t-2'],
             file=output_filename)
    TEST.run('gen 3 | (x: (x, -x)) | write --append ' + output_filename,
             expected_out=['0,0', '1,-1', '2,-2',
                           '0\t0', '1\t-1', '2\t-2',
                           (0, 0), (1, -1), (2, -2)],
             file=output_filename)
    TEST.delete_files(output_filename)
    TEST.run('gen 3 | (x: (x, -x)) | write --pickle --append ' + output_filename,
             verification='read --pickle ' + output_filename,
             expected_out=[(0, 0), (1, -1), (2, -2)])
    TEST.run('gen 3 3 | (x: (x, -x)) | write --pickle --append ' + output_filename,
             verification='read --pickle ' + output_filename,
             expected_out=[(0, 0), (1, -1), (2, -2), (3, -3), (4, -4), (5, -5)])
    # Function-valued filename
    TEST.run(f'gen 3 | write ("{output_filename}")',
             expected_out=[0, 1, 2],
             file=output_filename)


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
    # Mix of output and error
    TEST.run('gen 3 | (x: 1 / (1 - x))',
             expected_out=[1.0, Error('division by zero'), -1.0])


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
    original_dir = os.getcwd()
    original_config_file = TEST.config_file
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
    TEST.main = None
    TEST.reset_environment(config_file=config_file)
    TEST.run('map (pi)',
             expected_out=['3.141592653589793'])
    # Reset environment
    TEST.main = None
    os.chdir(original_dir)
    TEST.reset_environment(original_config_file)


def test_source_filenames():
    filename_op_setup('/tmp/test')
    # Relative path
    TEST.run('ls . | map (f: f.render_compact())',
             expected_out=sorted(['.', 'f', 'sf', 'lf', 'd', 'sd']))
    TEST.run('ls d | map (f: f.render_compact())',
             expected_out=sorted(['.', 'df', 'sdf', 'ldf', 'dd', 'sdd']))
    # Absolute path
    TEST.run('ls /tmp/test | map (f: f.render_compact())',
             expected_out=sorted(['.', 'f', 'sf', 'lf', 'd', 'sd']))
    TEST.run('ls /tmp/test/d | map (f: f.render_compact())',
             expected_out=sorted(['.', 'df', 'sdf', 'ldf', 'dd', 'sdd']))
    # Glob in last part of path
    TEST.run('ls -0 /tmp/test/s? | map (f: f.render_compact())',
             expected_out=sorted(['sf', 'sd']))
    TEST.run('ls -0 /tmp/test/*f | map (f: f.render_compact())',
             expected_out=sorted(['f', 'sf', 'lf']))
    # Glob in intermediate part of path
    TEST.run('ls -0 /tmp/test/*d/*dd | map (f: f.render_compact())',
             expected_out=sorted(['d/dd', 'd/sdd', 'sd/dd', 'sd/sdd']))
    TEST.run('ls -0 /tmp/test/*f | map (f: f.render_compact())',
             expected_out=sorted(['f', 'sf', 'lf']))
    # Glob identifying duplicates
    TEST.run('ls -0 *f s* | map (f: f.render_compact())',
             expected_out=sorted(['f', 'sd', 'sf', 'lf']))
    # No such file
    TEST.run('ls -0 x | map (f: f.render_compact())',
             expected_err='No qualifying paths')
    # No such file via glob
    TEST.run('ls -0 x* | map (f: f.render_compact())',
             expected_err='No qualifying paths')
    # ~ expansion
    TEST.run('ls -0 ~root | map (f: f.path)',
             expected_out=['/root'])


def test_ls():
    filename_op_setup('/tmp/test')
    # 0/1/r flags with no files specified.
    TEST.run('ls -0 | map (f: f.render_compact())',
             expected_out=sorted(['.']))
    TEST.run('ls -1 | map (f: f.render_compact())',
             expected_out=sorted(['.',
                                  'f', 'sf', 'lf', 'sd', 'd',  # Top-level
                                  ]))
    TEST.run('ls -r | map (f: f.render_compact())',
             expected_out=sorted(['.',
                                  'f', 'sf', 'lf', 'sd', 'd',  # Top-level
                                  'd/df', 'd/sdf', 'd/ldf', 'd/dd', 'd/sdd',  # Contents of d
                                  'sd/df', 'sd/sdf', 'sd/ldf', 'sd/dd', 'sd/sdd',  # Also reachable via sd
                                  'd/dd/ddf', 'd/sdd/ddf', 'sd/dd/ddf', 'sd/sdd/ddf'  # All paths to ddf
                                  ]))
    TEST.run('ls | map (f: f.render_compact())',
             expected_out=sorted(['.',
                                  'f', 'sf', 'lf', 'sd', 'd',  # Top-level
                                  ]))
    # 0/1/r flags with file
    TEST.run('ls -0 f | map (f: f.render_compact())',
             expected_out=sorted(['f']))
    TEST.run('ls -1 f | map (f: f.render_compact())',
             expected_out=sorted(['f']))
    TEST.run('ls -r f | map (f: f.render_compact())',
             expected_out=sorted(['f']))
    # 0/1/r flags with directory
    TEST.run('ls -0 /tmp/test | map (f: f.render_compact())',
             expected_out=sorted(['.']))
    TEST.run('ls -1 /tmp/test | map (f: f.render_compact())',
             expected_out=sorted(['.', 'f', 'sf', 'lf', 'sd', 'd']))
    TEST.run('ls -r /tmp/test | map (f: f.render_compact())',
             expected_out=sorted(['.',
                                  'f', 'sf', 'lf', 'sd', 'd',  # Top-level
                                  'd/df', 'd/sdf', 'd/ldf', 'd/dd', 'd/sdd',  # Contents of d
                                  'sd/df', 'sd/sdf', 'sd/ldf', 'sd/dd', 'sd/sdd',  # Also reachable via sd
                                  'd/dd/ddf', 'd/sdd/ddf', 'sd/dd/ddf', 'sd/sdd/ddf'  # All paths to ddf
                                  ]))
    # Test f/d/s flags
    TEST.run('ls -fr | map (f: f.render_compact())',
             expected_out=sorted(['f', 'lf',  # Top-level
                                  'd/df', 'd/ldf',  # Contents of d
                                  'sd/df', 'sd/ldf',  # Also reachable via sd
                                  'd/dd/ddf', 'd/sdd/ddf', 'sd/dd/ddf', 'sd/sdd/ddf'  # All paths to ddf
                                  ]))
    TEST.run('ls -dr | map (f: f.render_compact())',
             expected_out=sorted(['.',
                                  'd',  # Top-level
                                  'd/dd',  # Contents of d
                                  'sd/dd'  # Also reachable via sd
                                  ]))
    TEST.run('ls -sr | map (f: f.render_compact())',
             expected_out=sorted(['sf', 'sd',  # Top-level
                                  'd/sdf', 'd/sdd',  # Contents of d
                                  'sd/sdf', 'sd/sdd'  # Also reachable via sd
                                  ]))
    # Duplicates
    TEST.run('ls -0 *d ? | map (f: f.render_compact())',
             expected_out=sorted(['d', 'sd', 'f']))
    # This should find d twice
    expected = sorted(['.', 'f', 'sf', 'lf', 'd', 'sd'])
    expected.extend(sorted(['d/df', 'd/sdf', 'd/ldf', 'd/dd', 'd/sdd']))
    TEST.run('ls -1 . d | map (f: f.render_compact())',
             expected_out=expected)
    # ls should continue past permission error
    os.system('sudo rm -rf /tmp/lstest')
    os.system('mkdir /tmp/lstest')
    os.system('mkdir /tmp/lstest/d1')
    os.system('mkdir /tmp/lstest/d2')
    os.system('mkdir /tmp/lstest/d3')
    os.system('mkdir /tmp/lstest/d4')
    os.system('touch /tmp/lstest/d1/f1')
    os.system('touch /tmp/lstest/d2/f2')
    os.system('touch /tmp/lstest/d3/f3')
    os.system('touch /tmp/lstest/d4/f4')
    os.system('sudo chown root.root /tmp/lstest/d2')
    os.system('sudo chown root.root /tmp/lstest/d3')
    os.system('sudo chmod 700 /tmp/lstest/d?')
    TEST.run(test='ls -r /tmp/lstest | map (f: f.render_compact())',
             expected_out=['.',
                           'd1',
                           'd1/f1',
                           'd2',
                           Error('Permission denied'),
                           'd3',
                           Error('Permission denied'),
                           'd4',
                           'd4/f4'])
    # Args with vars
    TEST.run('TEST = test')
    TEST.run('ls -r /tmp/(TEST) | map (f: f.render_compact())',
             expected_out=sorted(['.',
                                  'f', 'sf', 'lf', 'sd', 'd',  # Top-level
                                  'd/df', 'd/sdf', 'd/ldf', 'd/dd', 'd/sdd',  # Contents of d
                                  'sd/df', 'sd/sdf', 'sd/ldf', 'sd/dd', 'sd/sdd',  # Also reachable via sd
                                  'd/dd/ddf', 'd/sdd/ddf', 'sd/dd/ddf', 'sd/sdd/ddf'  # All paths to ddf
                                  ]))
    TEST.run('TMP = TMP')
    TEST.run('ls -r /(TMP.lower())/(TEST) | map (f: f.render_compact())',
             expected_out=sorted(['.',
                                  'f', 'sf', 'lf', 'sd', 'd',  # Top-level
                                  'd/df', 'd/sdf', 'd/ldf', 'd/dd', 'd/sdd',  # Contents of d
                                  'sd/df', 'sd/sdf', 'sd/ldf', 'sd/dd', 'sd/sdd',  # Also reachable via sd
                                  'd/dd/ddf', 'd/sdd/ddf', 'sd/dd/ddf', 'sd/sdd/ddf'  # All paths to ddf
                                  ]))


# pushd, popd, dirs
def test_dir_stack():
    filename_op_setup('/tmp/test')
    TEST.run('mkdir a b c')
    TEST.run('rm -rf p')
    TEST.run('mkdir p')
    TEST.run('chmod 000 p')
    TEST.run(test='pwd | map (f: f.path)',
             expected_out=['/tmp/test'])
    TEST.run(test='dirs | map (f: f.path)',
             expected_out=['/tmp/test'])
    TEST.run(test='pushd a | map (f: f.path)',
             expected_out=['/tmp/test/a', '/tmp/test'])
    TEST.run(test='dirs | map (f: f.path)',
             expected_out=['/tmp/test/a', '/tmp/test'])
    TEST.run(test='pushd ../b | map (f: f.path)',
             expected_out=['/tmp/test/b', '/tmp/test/a', '/tmp/test'])
    TEST.run(test='dirs | map (f: f.path)',
             expected_out=['/tmp/test/b', '/tmp/test/a', '/tmp/test'])
    TEST.run(test='pushd | map (f: f.path)',
             expected_out=['/tmp/test/a', '/tmp/test/b', '/tmp/test'])
    TEST.run(test='dirs | map (f: f.path)',
             expected_out=['/tmp/test/a', '/tmp/test/b', '/tmp/test'])
    TEST.run(test='popd | map (f: f.path)',
             expected_out=['/tmp/test/b', '/tmp/test'])
    TEST.run(test='pwd | map (f: f.path)',
             expected_out=['/tmp/test/b'])
    TEST.run(test='dirs | map (f: f.path)',
             expected_out=['/tmp/test/b', '/tmp/test'])
    TEST.run(test='dirs -c | map (f: f.path)',
             expected_out=['/tmp/test/b'])
    TEST.run(test='pushd | map (f: f.path)',
             expected_out=['/tmp/test/b'])
    # Dir operations when the destination cd does not exist or cannot be entered due to permissions
    # cd
    TEST.run('cd /tmp/test')
    TEST.run(test='cd /tmp/test/doesnotexist',
             expected_err='No such file or directory')
    TEST.run(test='pwd | (f: str(f))',
             expected_out='/tmp/test')
    TEST.run(test='cd /tmp/test/p',
             expected_err='Permission denied')
    TEST.run(test='pwd | (f: str(f))',
             expected_out='/tmp/test')
    # pushd
    TEST.run(test='pushd /tmp/test/doesnotexist',
             expected_err='No such file or directory')
    TEST.run(test='pwd | (f: str(f))',
             expected_out='/tmp/test')
    TEST.run(test='pushd /tmp/test/p',
             expected_err='Permission denied')
    TEST.run(test='pwd | (f: str(f))',
             expected_out='/tmp/test')
    # popd: Arrange for a deleted dir on the stack and try popding into it.
    TEST.run('rm -rf x y')
    TEST.run('mkdir x y')
    TEST.run('cd x')
    TEST.run('pushd ../y | (f: str(f))',
             expected_out=['/tmp/test/y', '/tmp/test/x'])
    TEST.run('rm -rf /tmp/test/x')
    TEST.run('popd',
             expected_err='directories have been removed')
    TEST.run('dirs | (f: str(f))',
             expected_out=['/tmp/test/y'])


def test_remote():
    node1 = marcel.object.cluster.Host(TEST.env.getvar('NODE1'), None)
    TEST.run('@CLUSTER1 (| gen 3 |)',
             expected_out=[(node1, 0), (node1, 1), (node1, 2)])
    # Handling of remote error in execution
    TEST.run('@CLUSTER1 (| gen 3 -1 | map (x: 5 / x) |)',
             expected_out=[(node1, -5.0), Error('division by zero'), (node1, 5.0)])
    # Handling of remote error in setup
    TEST.run('@CLUSTER1 (| ls /nosuchfile |)',
             expected_out=[Error('No qualifying paths')])
    # Bug 4
    TEST.run('@CLUSTER1 (| gen 3 |) | red . +',
             expected_out=[(node1, 3)])
    TEST.run('@CLUSTER1 (| gen 10 | map (x: (x%2, x)) | red . + |)',
             expected_out=[(node1, 0, 20), (node1, 1, 25)])
    # Implied map
    TEST.run('@CLUSTER1(|(419)|)',
             expected_out=[(node1, 419)])
    # Bug 121
    TEST.run('@notacluster (| gen 3|)',
             expected_err='notacluster is not a Cluster')
    # Use explicit 'remote'
    TEST.run('remote CLUSTER1 (| gen 3 |)',
             expected_out=[(node1, 0), (node1, 1), (node1, 2)])


def test_fork():
    # int forkgen
    TEST.run('fork 3 (|gen 3 100|) | sort',
             expected_out=[100, 100, 100, 101, 101, 101, 102, 102, 102])
    TEST.run('fork 3 (|t: gen 3 100 | (x: (t, x))|) | sort',
             expected_out=[(0, 100), (0, 101), (0, 102),
                           (1, 100), (1, 101), (1, 102),
                           (2, 100), (2, 101), (2, 102)])
    TEST.run('fork 3 (|t, u: gen 3 100 | (x: (t, x))|) | sort',
             expected_err='Too many pipeline args')
    # iterable forkgen
    TEST.run('fork "abc" (|gen 3 100|) | sort',
             expected_out=[100, 100, 100, 101, 101, 101, 102, 102, 102])
    TEST.run('fork "abc" (|t: gen 3 100 | (x: (t, x))|) | sort',
             expected_out=[('a', 100), ('a', 101), ('a', 102),
                           ('b', 100), ('b', 101), ('b', 102),
                           ('c', 100), ('c', 101), ('c', 102)])
    TEST.run('fork "abc" (|t, u: gen 3 100 | (x: (t, x))|) | sort',
             expected_err='Too many pipeline args')
    # Cluster forkgen
    TEST.run('fork CLUSTER1 (|gen 3 100|)',
             expected_out=[100, 101, 102])
    TEST.run('fork CLUSTER1 (|t: gen 3 100 | (x: (str(t), x))|)',
             expected_out=[('127.0.0.1', 100), ('127.0.0.1', 101), ('127.0.0.1', 102)])
    TEST.run('fork CLUSTER1 (|t, u: gen 3 100 | (x: (str(t), x))|)',
             expected_err='Too many pipeline args')


def test_sudo():
    TEST.run(test='sudo (| gen 3 |)', expected_out=[0, 1, 2])
    os.system('sudo rm -rf /tmp/sudotest')
    os.system('sudo mkdir /tmp/sudotest')
    os.system('sudo touch /tmp/sudotest/f')
    os.system('sudo chmod 400 /tmp/sudotest')
    TEST.run(test='ls -f /tmp/sudotest', expected_out=[Error('Permission denied')])
    TEST.run(test='sudo (| ls -f /tmp/sudotest | map (f: f.render_compact()) |)', expected_out=['f'])


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
    TEST.run(test='a = (|(419)|)',
             verification='a',
             expected_out=[419])
    TEST.run(test='a = (| map (x: (x, -x)) |)',
             verification='gen 3 | a',
             expected_out=[(0, 0), (1, -1), (2, -2)])
    # Bug 61
    TEST.run('a = (|gen 3|)')
    TEST.run(test='a',
             expected_out=[0, 1, 2])
    TEST.run('b = (|a|)')
    TEST.run(test='b',
             expected_out=[0, 1, 2])
    # Bug 65
    TEST.run('x = (|(5)|)')
    TEST.run(test='x',
             expected_out=[5])
    # Bug 165
    TEST.run('ls = abc')
    TEST.run('(ls)',
             expected_out=['abc'])
    # Don't want the op ls masked by the variable ls
    TEST.run(test='env -d ls',
             verification='env -p ls',
             expected_out=[])


def test_join():
    # Join losing right inputs
    TEST.run(test='gen 4 | map (x: (x, -x)) | join (|gen 3 | map (x: (x, x * 100))|)',
             expected_out=[(0, 0, 0), (1, -1, 100), (2, -2, 200)])
    # Left join
    TEST.run(test='gen 4 | map (x: (x, -x)) | join -k (|gen 3 | map (x: (x, x * 100))|)',
             expected_out=[(0, 0, 0), (1, -1, 100), (2, -2, 200), (3, -3)])
    TEST.run(test='gen 4 | map (x: (x, -x)) | join --keep (|gen 3 | map (x: (x, x * 100))|)',
             expected_out=[(0, 0, 0), (1, -1, 100), (2, -2, 200), (3, -3)])
    # Compound key
    TEST.run(test='gen 4 | map (x: ((x, x + 1), -x)) | join (|gen 3 | map (x: ((x, x + 1), x * 100))|)',
             expected_out=[((0, 1), 0, 0), ((1, 2), -1, 100), ((2, 3), -2, 200)])
    # Multiple matches on the right
    TEST.run(test='gen 4 '
                  '| map (x: (x, -x)) '
                  '| join (|gen 3 '
                  '        | map (x: (x, (x * 100, x * 100 + 1))) '
                  '        | expand 1|)',
             expected_out=[(0, 0, 0), (0, 0, 1), (1, -1, 100), (1, -1, 101), (2, -2, 200), (2, -2, 201)])
    # Right argument in variable
    TEST.run('x100 = (|gen 3 | map (x: (x, x * 100))|)')
    TEST.run(test='gen 4 | map (x: (x, -x)) | join x100',
             expected_out=[(0, 0, 0), (1, -1, 100), (2, -2, 200)])
    TEST.run(test='gen 4 | map (x: (x, -x)) | join (|x100|)',
             expected_out=[(0, 0, 0), (1, -1, 100), (2, -2, 200)])
    # Join with pipeline var taking arg
    TEST.run('xn = (|n: gen 3 | map (x: (x, x * n))|)')
    TEST.run(test='gen 4 | map (x: (x, -x)) | join (|xn (100)|)',
             expected_out=[(0, 0, 0), (1, -1, 100), (2, -2, 200)])
    os.system('rm -f /tmp/?.csv')
    TEST.run('gen 3 | map (x: (x, x*10)) | write /tmp/a.csv')
    TEST.run('gen 3 | map (x: (x, x*100)) | write /tmp/b.csv')
    TEST.run('get = (|f: (File(f).readlines()) | expand | map (x: eval(x))|)')
    TEST.run('get /tmp/a.csv | join (|get /tmp/b.csv|)',
             expected_out=[(0, 0, 0), (1, 10, 100), (2, 20, 200)])
    # Handle non-hashable join keys
    TEST.run('gen 3 | (x: ((x,), x)) | join (|gen 3 | (x: ((x,), x*100))|)',
             expected_out=[((0,), 0, 0), ((1,), 1, 100), ((2,), 2, 200)])
    TEST.run('gen 3 | (x: ([x], x)) | join (|gen 3 | (x: ((x,), x*100))|)',
             expected_err='not hashable')
    TEST.run('gen 3 | (x: ((x,), x)) | join (|gen 3 | (x: ([x], x*100))|)',
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
    TEST.run('add = (|a: map (x: (x, x + a))|)')
    TEST.run('gen 3 | add (100)',
             expected_out=[(0, 100), (1, 101), (2, 102)])
    # Multiple functions
    TEST.run('add = (|a: map (x: (x, x + a)) | map (x, y: (x + a, y - a))|)')
    TEST.run('gen 3 | add (100)',
             expected_out=[(100, 0), (101, 1), (102, 2)])
    # Flag instead of anon arg
    TEST.run('add = (|a: map (x: (x, x + a))|)')
    TEST.run('gen 3 | add -a (100)',
             expected_out=[(0, 100), (1, 101), (2, 102)])
    # Multiple anon args
    TEST.run('f = (|a, b: map (x: (x, x * a + b))|)')
    TEST.run('gen 3 | f (100) (10)',
             expected_out=[(0, 10), (1, 110), (2, 210)])
    # Multiple flag args
    TEST.run('f = (|a, b: map (x: (x, x * a + b))|)')
    TEST.run('gen 3 | f -a (100) -b (10)',
             expected_out=[(0, 10), (1, 110), (2, 210)])
    TEST.run('gen 3 | f -b (10) -a (100)',
             expected_out=[(0, 10), (1, 110), (2, 210)])
    TEST.run('gen 3 | f -b (10) -a (100) -a (200)',
             expected_err='Flag a given more than once')
    TEST.run('gen 3 | f -b (10)',
             expected_err='Expected arguments: 2, given: 1')
    # Long flags
    TEST.run('foobar = (|foo, bar: map (x: x * foo) | select (x: x < bar)|)')
    TEST.run('gen 10 | foobar --foo (10) --bar (45)',
             expected_out=[0, 10, 20, 30, 40])
    TEST.run('gen 10 | foobar --bar (73) --foo (10)',
             expected_out=[0, 10, 20, 30, 40, 50, 60, 70])
    # Insufficient args
    # Bug 105 --  # Depends on ext being defined in .marcel.py
    TEST.run('ext',
             expected_err='Expected arguments: 1, given: 0')


def test_sql():
    if not SQL:
        return
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
    # Delete version var so that it does not mask the version op.
    TEST.run('env -d version | select (*_: False)')


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
    # Target is bound to something other than a reservoir
    TEST.run('x = 1')
    TEST.run(test='gen 3 | store x',
             verification='load x',
             expected_out=[0, 1, 2])
    TEST.run('x = 1')
    TEST.run(test='gen 3 | store -a x',
             expected_err='not usable as a reservoir')
    # Bad variable name
    TEST.run('gen 3 | store /tmp/storeload.test',
             expected_err='is not a Python identifier')


def test_redirect_file():
    # ------------------------ Test all the paths through Parser.pipeline() for files
    # file >
    TEST.delete_files('/tmp/p1')
    TEST.run(test='gen 3 | write /tmp/p1',
             verification='/tmp/p1 >',
             expected_out=[0, 1, 2])
    # file >> (error)
    TEST.delete_files('/tmp/p2')
    TEST.run(test='gen 3 | write /tmp/p2',
             verification='/tmp/p2 >>',
             expected_err='Append not permitted here')
    # file > file
    TEST.delete_files('/tmp/p3', '/tmp/p4')
    TEST.run('gen 3 | write /tmp/p3')
    TEST.run(test='/tmp/p3 > /tmp/p4',
             verification='/tmp/p4 >',
             expected_out=[0, 1, 2])
    # file >> file
    TEST.delete_files('/tmp/p5', '/tmp/p6', '/tmp/p7')
    TEST.run('gen 3 | write /tmp/p5')
    TEST.run('gen 3 | map (x: x + 100) | write /tmp/p6')
    TEST.run(test='/tmp/p5 >> /tmp/p7',
             verification='/tmp/p7 >',
             expected_out=[0, 1, 2])
    TEST.run(test='/tmp/p6 >> /tmp/p7',
             verification='/tmp/p7 >',
             expected_out=[0, 1, 2, 100, 101, 102])
    # file > op_sequence
    TEST.delete_files('/tmp/p8')
    TEST.run('gen 3 | write /tmp/p8')
    TEST.run(test='/tmp/p8 > map (x: int(x) + 100)',
             expected_out=[100, 101, 102])
    # file >> op_sequence (error)
    TEST.delete_files('tmp/p9')
    TEST.run('gen 3 | write /tmp/p9')
    TEST.run(test='/tmp/p9 >> map (x: x + 100)',
             expected_err='Append not permitted here')
    # file > op_sequence > file
    TEST.delete_files('/tmp/p10', '/tmp/p11')
    TEST.run('gen 3 | write /tmp/p10')
    TEST.run(test='/tmp/p10 > map (x: int(x) + 100) > /tmp/p11',
             verification='/tmp/p11 >',
             expected_out=[100, 101, 102])
    # file > op_sequence >> file
    TEST.delete_files('/tmp/p12', '/tmp/p13')
    TEST.run('gen 3 | write /tmp/p12')
    TEST.run(test='/tmp/p12 > map (x: int(x) + 100) >> /tmp/p13',
             verification='/tmp/p13 >',
             expected_out=[100, 101, 102])
    TEST.run(test='/tmp/p12 > map (x: int(x) + 1000) >> /tmp/p13',
             verification='/tmp/p13 >',
             expected_out=[100, 101, 102, 1000, 1001, 1002])
    # op_sequence -- tested adequately elsewhere
    # op_sequence > file
    TEST.delete_files('/tmp/p14')
    TEST.run(test='gen 3 > /tmp/p14',
             verification='/tmp/p14 >',
             expected_out=[0, 1, 2])
    # op_sequence >> file
    TEST.delete_files('/tmp/p15')
    TEST.run(test='gen 3 >> /tmp/p15',
             verification='/tmp/p15 >',
             expected_out=[0, 1, 2])
    TEST.run(test='gen 3 | map (x: int(x) + 100) >> /tmp/p15',
             verification='/tmp/p15 >',
             expected_out=[0, 1, 2, 100, 101, 102])
    # > file
    TEST.delete_files('/tmp/p16')
    TEST.run(test='gen 6 | ifthen (x: x % 2 == 0) (|> /tmp/p16|) | select (x: False)',
             verification='/tmp/p16 >',
             expected_out=[0, 2, 4])
    # >> file
    TEST.delete_files('/tmp/p17')
    TEST.run(test='gen 6 | ifthen (x: x % 2 == 0) (|>> /tmp/p17|) | select (x: False)',
             verification='/tmp/p17 >',
             expected_out=[0, 2, 4])
    TEST.run(test='gen 6 | ifthen (x: x % 2 == 1) (|>> /tmp/p17|) | select (x: False)',
             verification='/tmp/p17 >',
             expected_out=[0, 2, 4, 1, 3, 5])
    # ---------------------------------------------------------------------
    # Ops that look confusingly like files from context
    # op >
    TEST.run(test='pwd >',
             expected_err='A filename must precede >')
    # op >>
    TEST.run(test='pwd >>',
             expected_err='A filename must precede >>')
    # op > file
    TEST.delete_files('/tmp/o1')
    version = marcel.version.VERSION
    TEST.run(test='version > /tmp/o1',
             verification='/tmp/o1 > map (v: f"v{v}")',
             expected_out=[f"v{version}"])
    # op >> file
    TEST.delete_files('/tmp/o2')
    TEST.run(test='version >> /tmp/o2',
             verification='/tmp/o2 > map (v: f"v{v}")',
             expected_out=[f"v{version}"])
    TEST.run(test='version >> /tmp/o2',
             verification='/tmp/o2 > map (v: f"v{v}")',
             expected_out=[f"v{version}", f"v{version}"])
    # ---------------------------------------------------------------------
    # Store at end of top-level pipeline
    TEST.delete_files('/tmp/g5')
    TEST.run(test='gen 5 > /tmp/g5',
             verification='read /tmp/g5',
             expected_out=[0, 1, 2, 3, 4])
    # Store at end of pipeline arg
    TEST.delete_files('/tmp/e10x10')
    TEST.run(test='gen 10 | ifthen (x: x % 2 == 0) (|map (x: x * 10) > /tmp/e10x10|)',
             verification='read /tmp/e10x10',
             expected_out=[0, 20, 40, 60, 80])
    # Store as the entire pipeline arg
    TEST.delete_files('/tmp/e10')
    TEST.run(test='gen 10 | ifthen (x: x % 2 == 0) (|> /tmp/e10|)',
             verification='read /tmp/e10',
             expected_out=[0, 2, 4, 6, 8])
    # Append
    TEST.delete_files('/tmp/g10')
    TEST.run(test='gen 5 > /tmp/g10',
             verification='read /tmp/g10',
             expected_out=[0, 1, 2, 3, 4])
    TEST.run(test='gen 5 5 >> /tmp/g10',
             verification='read /tmp/g10',
             expected_out=[0, 1, 2, 3, 4, 5, 6, 7, 8, 9])
    # Load at beginning of top-level pipeline
    TEST.delete_files('/tmp/g4')
    TEST.run(test='gen 4 > /tmp/g4',
             verification='/tmp/g4 > map (x: -int(x))',
             expected_out=[0, -1, -2, -3])
    # Load in pipeline arg
    TEST.delete_files('/tmp/x10', '/tmp/x100')
    TEST.run('gen 4 | map (x: (x, x * 10)) > /tmp/x10')
    TEST.run('gen 4 | map (x: (x, x * 100)) > /tmp/x100')
    TEST.run('/tmp/x10 > map (x: eval(x)) | join (|/tmp/x100 > map (x: eval(x))|)',
             expected_out=[(0, 0, 0), (1, 10, 100), (2, 20, 200), (3, 30, 300)])
    # Bug 73
    TEST.delete_files('/tmp/a', '/tmp/b', '/tmp/c')
    TEST.run('gen 3 | map (x: (x, x*10)) > /tmp/a')
    TEST.run('gen 3 | map (x: (x, x*100)) > /tmp/b')
    TEST.run('gen 3 | map (x: (x, x*1000)) > /tmp/c')
    TEST.run('/tmp/a > (x: eval(x)) | join (|/tmp/b > (x: eval(x))|) | join (|/tmp/c > (x: eval(x))|)',
             expected_out=[(0, 0, 0, 0), (1, 10, 100, 1000), (2, 20, 200, 2000)])
    # Bug 74
    TEST.delete_files('/tmp/a', '/tmp/b', '/tmp/c', '/tmp/d')
    TEST.run('gen 3 | map (x: (x, x*10)) > /tmp/a')
    TEST.run('gen 3 | map (x: (x, x*100)) > /tmp/b')
    TEST.run('gen 3 | map (x: (x, x*1000)) > /tmp/c')
    TEST.run('/tmp/a > (x: eval(x)) | join (|/tmp/b > (x: eval(x))|) | join (|/tmp/c > (x: eval(x))|) > /tmp/d')
    TEST.run('/tmp/d >',
             expected_out=[(0, 0, 0, 0), (1, 10, 100, 1000), (2, 20, 200, 2000)])


def test_redirect_var():
    # ------------------------ Test all the paths through Parser.pipeline() for vars
    # var >$
    TEST.run(test='gen 3 | store p1',
             verification='p1 >$',
             expected_out=[0, 1, 2])
    # var >>$ (error)
    TEST.run(test='gen 3 | store p2',
             verification='p2 >>',
             expected_err='Append not permitted here')
    # file >$ file
    TEST.run('gen 3 | store p3')
    TEST.run(test='p3 >$ p4',
             verification='p4 >$',
             expected_out=[0, 1, 2])
    # var >> var4
    TEST.run('gen 3 | store p5')
    TEST.run('gen 3 | map (x: x + 100) | store p6')
    TEST.run(test='p5 >>$ p7',
             verification='p7 >$',
             expected_out=[0, 1, 2])
    TEST.run(test='p6 >>$ p7',
             verification='p7 >$',
             expected_out=[0, 1, 2, 100, 101, 102])
    # var >$ op_sequence
    TEST.run('gen 3 | store p8')
    TEST.run(test='p8 >$ map (x: x + 100)',
             expected_out=[100, 101, 102])
    # var >>$ op_sequence (error)
    TEST.run('gen 3 | store p9')
    TEST.run(test='p9 >>$ map (x: x + 100)',
             expected_err='Append not permitted here')
    # var >$ op_sequence >$ var
    TEST.run('gen 3 | store p10')
    TEST.run(test='p10 >$ map (x: x + 100) >$ p11',
             verification='p11 >$',
             expected_out=[100, 101, 102])
    # var >$ op_sequence >>$ var
    TEST.run('gen 3 | store p12')
    TEST.run(test='p12 >$ map (x: x + 100) >>$ p13',
             verification='p13 >$',
             expected_out=[100, 101, 102])
    TEST.run(test='p12 >$ map (x: x + 1000) >>$ p13',
             verification='p13 >$',
             expected_out=[100, 101, 102, 1000, 1001, 1002])
    # op_sequence -- tested adequately elsewhere
    # op_sequence >$ var
    TEST.run(test='gen 3 >$ p14',
             verification='p14 >$',
             expected_out=[0, 1, 2])
    # op_sequence >>$ var
    TEST.run(test='gen 3 >>$ p15',
             verification='p15 >$',
             expected_out=[0, 1, 2])
    TEST.run(test='gen 3 | map (x: x + 100) >>$ p15',
             verification='p15 >$',
             expected_out=[0, 1, 2, 100, 101, 102])
    # >$ var
    TEST.run(test='gen 6 | ifthen (x: x % 2 == 0) (|>$ p16|) | select (x: False)',
             verification='p16 >$',
             expected_out=[0, 2, 4])
    # >>$ var
    TEST.run(test='gen 6 | ifthen (x: x % 2 == 0) (|>>$ p17|) | select (x: False)',
             verification='p17 >$',
             expected_out=[0, 2, 4])
    TEST.run(test='gen 6 | ifthen (x: x % 2 == 1) (|>>$ p17|) | select (x: False)',
             verification='p17 >$',
             expected_out=[0, 2, 4, 1, 3, 5])
    # ---------------------------------------------------------------------
    # Ops that look confusingly like files from context
    # op >$
    TEST.run(test='pwd >$',
             expected_err='A variable must precede >$')
    # op >>$
    TEST.run(test='pwd >>$',
             expected_err='A variable must precede >>$')
    # op >$ var
    version = marcel.version.VERSION
    TEST.run(test='version >$ o1',
             verification='o1 >$ map (v: f"v{v}")',
             expected_out=[f"v{version}"])
    # op >>$ var
    TEST.run(test='version >>$ o2',
             verification='o2 >$ map (v: f"v{v}")',
             expected_out=[f"v{version}"])
    TEST.run(test='version >>$ o2',
             verification='o2 >$ map (v: f"v{v}")',
             expected_out=[f"v{version}", f"v{version}"])
    # ---------------------------------------------------------------------
    # Store at end of top-level pipeline
    TEST.run(test='gen 5 >$ g5',
             verification='load g5',
             expected_out=[0, 1, 2, 3, 4])
    # Store at end of pipeline arg
    TEST.run(test='gen 10 | ifthen (x: x % 2 == 0) (|map (x: x * 10) >$ e10x10|)',
             verification='load e10x10',
             expected_out=[0, 20, 40, 60, 80])
    # Store as the entire pipeline arg
    TEST.delete_files('e10')
    TEST.run(test='gen 10 | ifthen (x: x % 2 == 0) (|>$ e10|)',
             verification='load e10',
             expected_out=[0, 2, 4, 6, 8])
    # Append
    TEST.run(test='gen 5 >$ g10',
             verification='load g10',
             expected_out=[0, 1, 2, 3, 4])
    TEST.run(test='gen 5 5 >>$ g10',
             verification='load g10',
             expected_out=[0, 1, 2, 3, 4, 5, 6, 7, 8, 9])
    # Load at beginning of top-level pipeline
    TEST.run(test='gen 4 >$ g4',
             verification='g4 >$ map (x: -x)',
             expected_out=[0, -1, -2, -3])
    # Load in pipeline arg
    TEST.run('gen 4 | map (x: (x, x * 10)) >$ x10')
    TEST.run('gen 4 | map (x: (x, x * 100)) >$ x100')
    TEST.run('x10 >$ join (|x100 >$|)',
             expected_out=[(0, 0, 0), (1, 10, 100), (2, 20, 200), (3, 30, 300)])
    # Bug 73
    TEST.run('gen 3 | map (x: (x, x*10)) >$ a')
    TEST.run('gen 3 | map (x: (x, x*100)) >$ b')
    TEST.run('gen 3 | map (x: (x, x*1000)) >$ c')
    TEST.run('a >$ join (|b >$|) | join (|c >$|)',
             expected_out=[(0, 0, 0, 0), (1, 10, 100, 1000), (2, 20, 200, 2000)])
    # Bug 74
    TEST.delete_files('a', 'b', 'c', 'd')
    TEST.run('gen 3 | map (x: (x, x*10)) >$ a')
    TEST.run('gen 3 | map (x: (x, x*100)) >$ b')
    TEST.run('gen 3 | map (x: (x, x*1000)) >$ c')
    TEST.run('a >$ join (|b >$|) | join (|c >$|) >$ d')
    TEST.run('d >$',
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
    TEST.run('gen 10 | ifthen (x: x % 2 == 0) (|store even|)',
             expected_out=[0, 1, 2, 3, 4, 5, 6, 7, 8, 9])
    TEST.run('load even',
             expected_out=[0, 2, 4, 6, 8])
    TEST.run('gen 10 | ifelse (x: x % 3 == 0) (|store d3|)',
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
    file = open('/tmp/read/headings.csv', 'w')
    file.writelines(['c1, c2,c3 \n',  # various whitespace paddings
                     'a,b,c\n',
                     'd,e,f\n'])
    file.close()
    file = open('/tmp/read/headings_tricky_data.csv', 'w')
    file.writelines(['c1,c2,c3\n',
                     'a,b\n',
                     'c,d,e,f\n'
                     ',\n'])
    file.close()
    file = open('/tmp/read/headings_fixable.csv', 'w')
    file.writelines(['c 1, c$#2,c+3- \n',
                     'a,b,c\n',
                     'd,e,f\n'])
    file.close()
    file = open('/tmp/read/headings_unfixable_1.csv', 'w')
    file.writelines(['c1,c1,c3\n',
                     'a,b,c\n',
                     'd,e,f\n'])
    file.close()
    file = open('/tmp/read/headings_unfixable_2.csv', 'w')
    file.writelines(['c_1,c$1,c3\n',
                     'a,b,c\n',
                     'd,e,f\n'])
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
             expected_out=[('1', '2.3', 'ab'),
                           ('2', '3.4', 'xy'),
                           ('3', '4.5', 'm,n')])
    # CSV with labels
    TEST.run('cd /tmp/read')
    TEST.run('ls f1.csv | read -cl | map (f, x, y, z: (str(f), x, y, z))',
             expected_out=[('f1.csv', '1', '2.3', 'ab'),
                           ('f1.csv', '2', '3.4', 'xy'),
                           ('f1.csv', '3', '4.5', 'm,n')])
    # TSV
    TEST.run('cd /tmp/read')
    TEST.run('ls f2.tsv | read -t',
             expected_out=[('1', '2.3', 'ab'),
                           ('2', '3.4', 'xy')])
    # TSV with labels
    TEST.run('cd /tmp/read')
    TEST.run('ls f2.tsv | read -tl | map (f, x, y, z: (str(f), x, y, z))',
             expected_out=[('f2.tsv', '1', '2.3', 'ab'),
                           ('f2.tsv', '2', '3.4', 'xy')])
    # --pickle testing is done in test_write()
    # Filenames on commandline
    TEST.run('cd /tmp/read')
    TEST.run('read f1.csv',
             expected_out=['1,2.3,ab', '2,3.4,xy', '3,4.5,"m,n"'])
    TEST.run('read f?.*',
             expected_out=['1,2.3,ab', '2,3.4,xy', '3,4.5,"m,n"',
                           '1\t2.3\tab', '2\t3.4\txy',
                           'hello,world', 'goodbye'])
    # Flags inherited from FilenamesOp
    TEST.run(test='read -lr /tmp/read/f[1-3]* | (f, l: (str(f), l))',
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
    # Column headings
    TEST.run('read -h /tmp/read/f3.txt',
             expected_err='-h|--headings can only be specified with')
    TEST.run('read -hp /tmp/read/f3.txt',
             expected_err='-h|--headings can only be specified with')
    TEST.run('read -s /tmp/read/f3.txt',
             expected_err='-s|--skip-headings can only be specified with')
    TEST.run('read -sp /tmp/read/f3.txt',
             expected_err='-s|--skip-headings can only be specified with')
    TEST.run('read -hs /tmp/read/f3.txt',
             expected_err='Cannot specify more than one of')
    TEST.run('read -ch /tmp/read/headings.csv | (t: (t.c1, t.c2, t.c3))',
             expected_out=[('a', 'b', 'c'),
                           ('d', 'e', 'f')])
    TEST.run('read -chl /tmp/read/headings.csv | (t: (str(t.LABEL), t.c1, t.c2, t.c3))',
             expected_out=[('headings.csv', 'a', 'b', 'c'),
                           ('headings.csv', 'd', 'e', 'f')])
    TEST.run('read -cs /tmp/read/headings.csv',
             expected_out=[('a', 'b', 'c'),
                           ('d', 'e', 'f')])
    TEST.run('read -ch /tmp/read/headings_tricky_data.csv | (t: (t.c1, t.c2, t.c3))',
             expected_out=[('a', 'b', None),
                           Error('Incompatible with headings'),
                           ('', '', None)])
    TEST.run('read -ch /tmp/read/headings_fixable.csv | (t: (t.c_1, t.c__2, t.c_3_))',
             expected_out=[('a', 'b', 'c'),
                           ('d', 'e', 'f')])
    TEST.run('read -ch /tmp/read/headings_unfixable_1.csv',
             expected_out=[Error('Cannot generate identifiers from headings'),
                           ('a', 'b', 'c'),
                           ('d', 'e', 'f')])
    TEST.run('read -ch /tmp/read/headings_unfixable_2.csv',
             expected_out=[Error('Cannot generate identifiers from headings'),
                           ('a', 'b', 'c'),
                           ('d', 'e', 'f')])


def test_intersect():
    TEST.reset_environment()
    # Empty inputs
    TEST.run('gen 1 | select (*x: False) >$ empty')
    TEST.run('gen 3 | intersect (|empty >$|)',
             expected_out=[])
    TEST.run('empty >$ intersect (|empty >$|)',
             expected_out=[])
    TEST.run('empty >$ intersect (|gen 3|)',
             expected_out=[])
    # Non-empty inputs, empty intersection
    TEST.run('gen 3 | intersect (|gen 3|)',
             expected_out=[0, 1, 2])
    TEST.run('gen 3 | intersect (|gen 1 1|)',
             expected_out=[1])
    # Duplicates
    TEST.run('gen 5 | map (x: [x] * x) | expand >$ a')
    TEST.run('gen 5 | map (x: [x] * 2) | expand >$ b')
    TEST.run('a >$ intersect (|b >$|) | sort',
             expected_out=[1, 2, 2, 3, 3, 4, 4])
    # Composite elements
    TEST.run('gen 3 2 | '
             'map (x: [(x, x * 100)] * x) | '
             'expand | '
             'intersect (|gen 3 2 | '
             '           map (x: [(x, x * 100)] * 3) | '
             '           expand|) |'
             'sort',
             expected_out=[(2, 200), (2, 200),
                           (3, 300), (3, 300), (3, 300),
                           (4, 400), (4, 400), (4, 400)])
    # Lists cannot be hashed
    TEST.run('gen 2 | (x: (x, (x, x))) | intersect (|gen 2 1 | (x: (x, (x, x)))|)',
             expected_out=[(1, (1, 1))])
    TEST.run('gen 2 | (x: (x, [x, x])) | intersect (|gen 2 1 | (x: (x, (x, x)))|)',
             expected_err='not hashable')
    TEST.run('gen 2 | (x: (x, (x, x))) | intersect (|gen 2 1 | (x: (x, [x, x]))|)',
             expected_err='not hashable')
    # Multiple pipelines
    TEST.run('g41 = (| gen 4 1 |)')
    TEST.run('g42 = (| gen 4 2 |)')
    TEST.run('g43 = (| gen 4 3 |)')
    TEST.run('g41 | intersect g42 g43', expected_out=[3, 4])
    TEST.run('g41 | intersect g43 g42', expected_out=[3, 4])
    TEST.run('g42 | intersect g41 g43', expected_out=[3, 4])
    TEST.run('g42 | intersect g43 g41', expected_out=[3, 4])
    TEST.run('g43 | intersect g41 g42', expected_out=[3, 4])
    TEST.run('g43 | intersect g42 g41', expected_out=[3, 4])
    # Test duplicate handling
    TEST.run('x0 = (| (["x"] * 0) | expand |)')
    TEST.run('x1 = (| (["x"] * 1) | expand |)')
    TEST.run('x2 = (| (["x"] * 2) | expand |)')
    TEST.run('x3 = (| (["x"] * 3) | expand |)')
    TEST.run('x1 | intersect x2', expected_out=['x'])
    TEST.run('x2 | intersect x1', expected_out=['x'])
    TEST.run('x1 | intersect x3', expected_out=['x'])
    TEST.run('x3 | intersect x1', expected_out=['x'])
    TEST.run('x2 | intersect x3', expected_out=['x', 'x'])
    TEST.run('x3 | intersect x2', expected_out=['x', 'x'])
    TEST.run('x1 | intersect x2 x3', expected_out=['x'])
    TEST.run('x1 | intersect x3 x2', expected_out=['x'])
    TEST.run('x2 | intersect x1 x3', expected_out=['x'])
    TEST.run('x2 | intersect x3 x1', expected_out=['x'])
    TEST.run('x3 | intersect x1 x2', expected_out=['x'])
    TEST.run('x3 | intersect x2 x1', expected_out=['x'])
    TEST.run('x0 | intersect x2 x3', expected_out=[])
    TEST.run('x2 | intersect x3 x0', expected_out=[])


def test_union():
    TEST.reset_environment()
    # Empty inputs
    TEST.run('gen 1 | select (*x: False) >$ empty')
    TEST.run('empty >$ union (|empty >$|)',
             expected_out=[])
    TEST.run('gen 3 | union (|empty >$|) | sort',
             expected_out=[0, 1, 2])
    TEST.run('empty >$ union (|gen 3|) | sort',
             expected_out=[0, 1, 2])
    # Non-empty inputs4
    TEST.run('gen 3 | union (|gen 3 100|) | sort',
             expected_out=[0, 1, 2, 100, 101, 102])
    # Duplicates
    TEST.run('gen 3 | union (|gen 3|) | sort',
             expected_out=[0, 0, 1, 1, 2, 2])
    # Composite elements
    TEST.run('gen 4 | map (x: (x, x*100)) | union (|gen 4 2 | map (x: (x, x*100))|) | sort',
             expected_out=[(0, 0), (1, 100), (2, 200), (2, 200), (3, 300), (3, 300), (4, 400), (5, 500)])
    # Multiple inputs
    TEST.run('gen 3 100 | union (|gen 3 200|) | sort',
             expected_out=[100, 101, 102, 200, 201, 202])
    TEST.run('gen 3 100 | union (|gen 3 200|) (|gen 3 300|) | sort',
             expected_out=[100, 101, 102, 200, 201, 202, 300, 301, 302])


def test_difference():
    TEST.reset_environment()
    # Empty inputs
    TEST.run('gen 1 | select (*x: False) >$ empty')
    TEST.run('empty >$ difference (|empty >$|)',
             expected_out=[])
    TEST.run('gen 3 | difference (|empty >$|) | sort',
             expected_out=[0, 1, 2])
    TEST.run('empty >$ difference (|gen 3|)',
             expected_out=[])
    # Non-empty inputs
    TEST.run('gen 6 | difference (|gen 6 100|) | sort',
             expected_out=[0, 1, 2, 3, 4, 5])
    TEST.run('gen 6 | difference (|gen 6|) | sort',
             expected_out=[])
    TEST.run('gen 6 | difference (|gen 6 3|) | sort',
             expected_out=[0, 1, 2])
    # Duplicates
    TEST.run('gen 5 | map (x: [x] * x) | expand | difference (|gen 5 | map (x: [x] * 2) | expand|) | sort',
             expected_out=[3, 4, 4])
    # Composite elements
    TEST.run('gen 5 2 | '
             'map (x: [(x, x*100)] * x) | '
             'expand | difference (|gen 5 2 | '
             '                     map (x: [(x, x*100)] * 3) | '
             '                     expand|) | '
             'sort',
             expected_out=[(4, 400), (5, 500), (5, 500), (6, 600), (6, 600), (6, 600)])
    # Lists aren't hashable
    TEST.run('gen 3 | (x: (x, (x, x))) | difference (|gen 2 | (x: (x, (x, x)))|)',
             expected_out=[(2, (2, 2))])
    TEST.run('gen 3 | (x: (x, [x, x])) | difference (|gen 2 | (x: (x, (x, x)))|)',
             expected_err='not hashable')
    TEST.run('gen 3 | (x: (x, (x, x))) | difference (|gen 2 | (x: (x, [x, x]))|)',
             expected_err='not hashable')


def test_args():
    TEST.reset_environment()
    # gen
    TEST.run('gen 5 1 | args (|n: gen (n)|) | map (x: -x)',
             expected_out=[0, 0, -1, 0, -1, -2, 0, -1, -2, -3, 0, -1, -2, -3, -4])
    TEST.run('gen 6 1 | args (|count, start: gen (count) (start)|)',
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
    TEST.run('ls -d | args (|d: ls -f (d) |) | map (f: f.name)',
             expected_out=['f1', 'f2', 'f3'])
    TEST.run('touch a_file')
    TEST.run('touch "a file"')
    TEST.run('touch "a file with a \' mark"')
    TEST.run('rm -rf d')
    TEST.run('mkdir d')
    TEST.run(test='ls -f | args --all (|files: mv -t d (quote_files(files)) |)',
             verification='ls -f d | map (f: f.name)',
             expected_out=['a file', "a file with a ' mark", 'a_file'])
    # head
    TEST.run('gen 4 1 | args (|n: gen 10 | head (n)|)',
             expected_out=[0, 0, 1, 0, 1, 2, 0, 1, 2, 3])
    # tail
    TEST.run('gen 4 1 | args (|n: gen 10 | tail (n+1)|)',
             expected_out=[8, 9, 7, 8, 9, 6, 7, 8, 9, 5, 6, 7, 8, 9])
    # bash
    # Space between Y and ] is required, otherwise ] is lexed as part of the argument to echo.
    TEST.run('gen 5 | args (|n: echo X(n)Y |)',
             expected_out=['X0Y', 'X1Y', 'X2Y', 'X3Y', 'X4Y'])
    # expand
    TEST.run('gen 3 | args (|x: (((1, 2), (3, 4), (5, 6))) | expand (x)|)',
             expected_out=[(1, (3, 4), (5, 6)), (2, (3, 4), (5, 6)),
                           ((1, 2), 3, (5, 6)), ((1, 2), 4, (5, 6)),
                           ((1, 2), (3, 4), 5), ((1, 2), (3, 4), 6)])
    # sql
    if SQL:
        TEST.run('sql "drop table if exists t" | select (x: False)')
        TEST.run('sql "create table t(x int)" | select (x: False)')
        TEST.run(test='gen 5 | args (|x: sql "insert into t values(%s)" (x)|)',
                 verification='sql "select * from t order by x"',
                 expected_out=[0, 1, 2, 3, 4])
    # window
    TEST.run('gen 3 | args (|w: gen 10 | window -d (w)|)',
             expected_out=[(0, 1, 2, 3, 4, 5, 6, 7, 8, 9),
                           0, 1, 2, 3, 4, 5, 6, 7, 8, 9,
                           (0, 1), (2, 3), (4, 5), (6, 7), (8, 9)])
    # nested args
    TEST.run('gen 3 | args (|i: gen 3 (i+100) | args (|j: gen 3 (j+1000)|)|)',
             expected_out=[1100, 1101, 1102, 1101, 1102, 1103, 1102, 1103, 1104,
                           1101, 1102, 1103, 1102, 1103, 1104, 1103, 1104, 1105,
                           1102, 1103, 1104, 1103, 1104, 1105, 1104, 1105, 1106])
    # --all
    TEST.run('gen 10 | args --all (|x: ("".join([str(n) for n in x]))|)',
             expected_out=['0123456789'])
    # no input to args
    TEST.run('gen 3 | select (x: False) | args (|n: map (x: -x)|)',
             expected_out=[])
    TEST.run('gen 3 | select (x: False) | args --all (|n: map (x: -x)|)',
             expected_out=[])
    # negative testing
    TEST.run('gen 3 | args (|gen 3|)',
             expected_err='The args pipeline must be parameterized')
    TEST.run('gen 10 | args --all (|a, b: gen (a) (b)|)',
             expected_err='the pipeline must have a single parameter')
    # Bug 94
    TEST.run('gen 4 1 | args (|n: gen (n)|) | window (x: x == 0)',
             expected_out=[0, (0, 1), (0, 1, 2), (0, 1, 2, 3)])
    # Bug 116
    TEST.run('g = (|n: gen (n)|)')
    TEST.run('gen 3 1 | args (|n: g (n)|)',
             expected_out=[0, 0, 1, 0, 1, 2])
    # Bug 167
    os.system('rm -rf /tmp/hello')
    os.system('echo hello > /tmp/hello')
    os.system('echo hello >> /tmp/hello')


def test_env():
    TEST.reset_environment()
    # Get all env vars, and check for things that should definitely be there.
    # PATH, PWD are inherited from the process.
    # NODE1, NODE2 come from the test config file, ./.marcel.py
    TEST.run(test='env | (var, value: var) | select (var: var in ("NODE1", "NODE2", "PATH", "PWD"))',
             expected_out=["NODE1", "NODE2", "PATH", "PWD"])
    # Test some vars
    TEST.run(test='env -p NODE | (var, value: var) | select (var: var in ("NODE1", "NODE2"))',
             expected_out=["NODE1", "NODE2"])
    # One var
    TEST.run(test='env PATH | (var, value: var)',
             expected_out=["PATH"])
    # Missing var
    TEST.run(test='env NOSUCHVAR | (var, value: var)',
             expected_out=[Error('undefined')])
    # Delete var
    TEST.run('GARBAGE = asdf')
    TEST.run(test='env GARBAGE',
             expected_out=[('GARBAGE', 'asdf')])
    TEST.run(test='env -d GARBAGE',
             expected_out=[('GARBAGE', 'asdf')])
    TEST.run(test='env GARBAGE',
             expected_out=[Error('undefined')])
    # Delete missing var
    TEST.run(test='env -d GARBAGE',
             expected_out=[Error('undefined')])


def test_pos():
    TEST.run('gen 5 | (x: (x, pos())) | select (x, p1: x % 2 == 0) | (x, p1: (x, p1, pos()))',
             expected_out=[(0, 0, 0), (2, 2, 1), (4, 4, 2)])


def test_tee():
    TEST.run('gen 5 1 | tee',
             expected_err='No pipelines')
    TEST.run('gen 5 1 | tee (|red + >$ a|) (|red * >$ b|)',
             expected_out=[1, 2, 3, 4, 5])
    TEST.run('a >$', expected_out=[15])
    TEST.run('b >$', expected_out=[120])


def test_upload():
    os.system('rm -rf /tmp/source')
    os.system('mkdir /tmp/source')
    os.system('touch /tmp/source/a /tmp/source/b "/tmp/source/a b"')
    os.system('rm -rf /tmp/dest')
    os.system('mkdir /tmp/dest')
    # No qualifying paths
    TEST.run('upload CLUSTER1 /tmp/dest /nosuchfile',
             expected_err='No qualifying paths')
    # Qualifying paths exist but insufficient permission to read
    os.system('sudo touch /tmp/nope1')
    os.system('sudo rm /tmp/nope?')
    os.system('touch /tmp/nope1')
    os.system('touch /tmp/nope2')
    os.system('chmod 000 /tmp/nope?')
    TEST.run('upload CLUSTER1 /tmp/dest /tmp/nope1',
             expected_out=[Error('nope1: Permission denied')])
    TEST.run('upload CLUSTER1 /tmp/dest /tmp/nope?',
             expected_out=[Error('Permission denied'),
                           Error('Permission denied')])
    # Target dir must be absolute
    TEST.run('upload CLUSTER1 dest /tmp/source/a',
             expected_err='Target directory must be absolute: dest')
    # There must be at least one source
    TEST.run('upload CLUSTER1 /tmp/dest',
             expected_err='No qualifying paths')
    # Copy fully-specified filenames
    TEST.run(test='upload CLUSTER1 /tmp/dest /tmp/source/a /tmp/source/b',
             verification='ls -f /tmp/dest | (f: f.name)',
             expected_out=['a', 'b'])
    os.system('rm /tmp/dest/*')
    # Filename with spaces
    TEST.run(test='upload CLUSTER1 /tmp/dest "/tmp/source/a b"',
             verification='ls -f /tmp/dest | (f: f.name)',
             expected_out=['a b'])
    os.system('rm /tmp/dest/*')
    # Wildcard
    TEST.run(test='upload CLUSTER1 /tmp/dest /tmp/source/a*',
             verification='ls -f /tmp/dest | (f: f.name)',
             expected_out=['a', 'a b'])
    os.system('rm /tmp/dest/*')


def test_download():
    node1 = TEST.env.getvar("NODE1")
    node2 = TEST.env.getvar("NODE2")
    os.system('rm -rf /tmp/source')
    os.system('mkdir /tmp/source')
    os.system('touch /tmp/source/a /tmp/source/b "/tmp/source/a b"')
    os.system('rm -rf /tmp/dest')
    os.system('mkdir /tmp/dest')
    # No qualifying paths
    TEST.run('download /tmp/dest CLUSTER2 /nosuchfile',
             expected_out=[Error('No such file or directory'), Error('No such file or directory')])
    # Qualifying paths exist but insufficient permission to read
    os.system('sudo touch /tmp/nope1')
    os.system('sudo rm /tmp/nope?')
    os.system('touch /tmp/nope1')
    os.system('touch /tmp/nope2')
    os.system('chmod 000 /tmp/nope?')
    TEST.run('download /tmp/dest CLUSTER2 /tmp/nope1',
             expected_out=[Error('Permission denied'), Error('Permission denied')])
    TEST.run('download /tmp/dest CLUSTER2 /tmp/nope?',
             expected_out=[Error('Permission denied'), Error('Permission denied'),
                           Error('Permission denied'), Error('Permission denied')])
    # There must be at least one source specified (regardless of what actually exists remotely)
    TEST.run('download /tmp/dest CLUSTER2',
             expected_err='No remote files specified')
    # Copy fully-specified filenames
    TEST.run(test='download /tmp/dest CLUSTER2 /tmp/source/a /tmp/source/b',
             verification='ls -fr /tmp/dest | (f: f.relative_to("/tmp/dest")) | sort',
             expected_out=[f'{node1}/a', f'{node1}/b', f'{node2}/a', f'{node2}/b'])
    # Leave files in place, delete some of them, try downloading again
    os.system(f'rm -rf /tmp/dest/{node1}')
    os.system(f'rm -rf /tmp/dest/{node2}/*')
    TEST.run(test='download /tmp/dest CLUSTER2 /tmp/source/a /tmp/source/b',
             verification='ls -fr /tmp/dest | (f: f.relative_to("/tmp/dest")) | sort',
             expected_out=[f'{node1}/a', f'{node1}/b', f'{node2}/a', f'{node2}/b'])
    os.system('rm -rf /tmp/dest/*')
    # Filename with spaces
    TEST.run(test='download /tmp/dest CLUSTER2 "/tmp/source/a\\ b"',
             verification='ls -fr /tmp/dest | (f: f.relative_to("/tmp/dest")) | sort',
             expected_out=[f'{node1}/a b', f'{node2}/a b'])
    os.system('rm -rf /tmp/dest/*')
    # # Relative directory
    # TEST.run('cd /tmp')
    # TEST.run(test='download dest jao /tmp/source/a /tmp/source/b',
    #          verification='ls -f /tmp/dest | (f: f.name)',
    #          expected_out=['a', 'b'])
    # os.system('rm /tmp/dest/*')
    # Wildcard
    TEST.run(test='download /tmp/dest CLUSTER2 /tmp/source/a*',
             verification='ls -fr /tmp/dest | (f: f.relative_to("/tmp/dest")) | sort',
             expected_out=[f'{node1}/a', f'{node1}/a b',
                           f'{node2}/a', f'{node2}/a b'])
    os.system('rm -rf /tmp/dest/*')


def test_bug_126():
    TEST.run('fact = (|x: gen (x) 1 | args (|n: gen (n) 1 | red * | map (f: (n, f))|)|)')
    TEST.run(test='fact (5) >$ f',
             verification='f >$',
             expected_out=[(1, 1), (2, 2), (3, 6), (4, 24), (5, 120)])


def test_bug_136():
    TEST.run('gen 3 1 | args (|n: gen 2 100 | (x: x+n)|) | red +',
             expected_out=[615])


def test_bug_151():
    TEST.run('bytime = (|sort (f: f.mtime)|)')
    TEST.run('ls | bytime >$ a')
    TEST.run('ls | sort (f: f.mtime) >$ b')
    TEST.run('a >$ difference (|b >$|) | red count',
             expected_out=[0])
    TEST.run('b >$ difference (|a >$|) | red count',
             expected_out=[0])


def test_bug_152():
    # Same test case as for bug 126. Failure was different as code changes.
    pass


def test_bug_10():
    TEST.run('sort', expected_err='cannot be the first operator in a pipeline')
    TEST.run('unique', expected_err='cannot be the first operator in a pipeline')
    TEST.run('window -o 2', expected_err='cannot be the first operator in a pipeline')
    TEST.run('map (3)', expected_out=[3])
    TEST.run('args(|x: gen(3)|)', expected_err='cannot be the first operator in a pipeline')


def test_bug_154():
    TEST.reset_environment()
    TEST.run('gen 3 >$ x')
    TEST.run('x >>$ (y: -y)', expected_err='Append not permitted')
    TEST.run('x >$ (y: -y)', expected_out=[0, -1, -2])


def test_bug_168():
    os.system('rm -rf /tmp/hello')
    os.system('echo hello1 > /tmp/hello')
    os.system('echo hello2 >> /tmp/hello')
    TEST.run('read /tmp/hello | red count',
             expected_out=[2])
    TEST.run('cat /tmp/hello | red count',
             expected_out=[2])
    os.system('rm -rf /tmp/hello')


def test_bug_185():
    # Unbound var
    TEST.run('varop',
             expected_err='oops')
    # var masking executable
    # var masking builtin
    # Remove masking var


def test_bug_190():
    testdir = '/tmp/bug190'
    os.system(f'rm -rf {testdir}')
    os.system(f'mkdir {testdir}')
    os.system(f'echo xa1 > {testdir}/a1')
    os.system(f'echo xa2 > {testdir}/a2')
    os.system(f'echo xb1 > {testdir}/b1')
    os.system(f'echo xb2 > {testdir}/b2')
    TEST.run(f'cd {testdir}')
    # Test globbing for native executables
    TEST.run('grep x [ab]2 | sort',
             expected_out=['a2:xa2', 'b2:xb2'])
    TEST.run('grep x a[1-2] | sort',
             expected_out=['a1:xa1', 'a2:xa2'])
    TEST.run('grep x [ab][1-2] | sort',
             expected_out=['a1:xa1', 'a2:xa2', 'b1:xb1', 'b2:xb2'])
    TEST.run('grep x a* | sort',
             expected_out=['a1:xa1', 'a2:xa2'])
    TEST.run('grep x *2 | sort',
             expected_out=['a2:xa2', 'b2:xb2'])
    TEST.run('grep x a? | sort',
             expected_out=['a1:xa1', 'a2:xa2'])
    TEST.run('grep x ?2 | sort',
             expected_out=['a2:xa2', 'b2:xb2'])
    # Test globbing for native executables run via explicit invocation of bash (which is a marcel op)
    TEST.run('bash grep x [ab]2 | sort',
             expected_out=['a2:xa2', 'b2:xb2'])
    TEST.run('bash grep x a[1-2] | sort',
             expected_out=['a1:xa1', 'a2:xa2'])
    TEST.run('bash grep x [ab][1-2] | sort',
             expected_out=['a1:xa1', 'a2:xa2', 'b1:xb1', 'b2:xb2'])
    # Test globbing for ops that take shell args
    TEST.run('ls [ab]2 | (f: f.name) | sort',
             expected_out=['a2', 'b2'])
    TEST.run('ls a[1-2] | (f: f.name) | sort',
             expected_out=['a1', 'a2'])
    TEST.run('ls [ab][1-2] | (f: f.name) | sort',
             expected_out=['a1', 'a2', 'b1', 'b2'])
    TEST.run('ls a* | (f: f.name) | sort',
             expected_out=['a1', 'a2'])
    TEST.run('ls *2 | (f: f.name) | sort',
             expected_out=['a2', 'b2'])
    TEST.run('ls a? | (f: f.name) | sort',
             expected_out=['a1', 'a2'])
    TEST.run('ls ?2 | (f: f.name) | sort',
             expected_out=['a2', 'b2'])


# Generalization of bug 195
def test_pipeline_vars():
    TEST.reset_environment(new_main=True)
    # union
    TEST.run('genn = (| n: gen (int(n)) |)')
    TEST.run('g_3_100 = (| gen 3 100 |)')
    TEST.run('gen 3 | union g_3_100', expected_out=[0, 1, 2, 100, 101, 102])
    TEST.run('gen 3 | union g_3_100 (| genn 4 |)', expected_out=[0, 1, 2, 100, 101, 102, 0, 1, 2, 3])
    # intersection
    TEST.run('g41 = (| gen 4 1 |)')
    TEST.run('g43 = (| gen 4 3 |)')
    TEST.run('g41 | intersect g43', expected_out=[3, 4])
    # difference
    TEST.run('g61 = (| gen 6 1 |)')
    TEST.run('g64 = (| gen 6 4 |)')
    TEST.run('g61 | difference g64', expected_out=[1, 2, 3])
    # args
    TEST.run('p = (| args (| n: gen 3 100 | (x: (n, x)) |) |)')
    TEST.run('gen 3 1 | p',
             expected_out=[(1, 100), (1, 101), (1, 102),
                           (2, 100), (2, 101), (2, 102),
                           (3, 100), (3, 101), (3, 102)])
    TEST.run('q = (| args (| x, y: (x + y) |) |)')
    TEST.run('gen 10 | q', expected_out=[1, 5, 9, 13, 17])
    # ifelse, ifthen
    TEST.run('a = (| (x: x + 1000) | write |)')
    TEST.run('gen 6 | ifelse (x: x % 2 == 0) a', expected_out=[1000, 1, 1002, 3, 1004, 5])
    TEST.run('gen 6 | ifthen (x: x % 2 == 0) a', expected_out=[1000, 0, 1, 1002, 2, 3, 1004, 4, 5])
    # join
    TEST.run('x100 = (| gen 3 1 | (x: (x, x * 100)) |)')
    TEST.run('x1000 = (| gen 3 1 | (x: (x, x * 1000)) |)')
    TEST.run('gen 3 1 | (x: (x, x * 10)) | join x100 | join x1000',
             expected_out=[(1, 10, 100, 1000), (2, 20, 200, 2000), (3, 30, 300, 3000)])
    # remote
    node1 = marcel.object.cluster.Host(TEST.env.getvar('NODE1'), None)
    TEST.run('g3 = (| gen 3 |)')
    TEST.run('@CLUSTER1 g3', expected_out=[(node1, 0), (node1, 1), (node1, 2)])
    # sudo
    TEST.run('g = (| gen 3 |)')
    TEST.run('sudo g', expected_out=[0, 1, 2])
    # tee
    TEST.run('save_sum = (| red + >$ sum |)')
    TEST.run('save_prod = (| red * >$ prod |)')
    TEST.run('gen 5 1 | tee save_sum save_prod',
             expected_out=[1, 2, 3, 4, 5])
    TEST.run('sum >$', expected_out=[15])
    TEST.run('prod >$', expected_out=[120])


# For bugs that aren't specific to a single op.
def test_bugs():
    test_bug_10()
    test_bug_126()
    test_bug_136()
    test_bug_151()
    test_bug_154()
    test_bug_168()
    test_bug_190()


def main_stable():
    test_no_such_op()
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
    test_namespace()
    test_source_filenames()
    test_ls()
    test_dir_stack()
    test_fork()
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
    test_redirect_file()
    test_redirect_var()
    test_if()
    test_delete()
    test_read()
    test_intersect()
    test_union()
    test_difference()
    test_args()
    test_env()
    test_pos()
    test_tee()
    test_upload()
    test_download()
    test_pipeline_vars()
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
