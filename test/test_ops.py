import getpass
import math
import os
import pathlib
import sys

import marcel.main
import marcel.version
import marcel.object.cluster
import marcel.object.error
import marcel.object.workspace
import marcel.version

import test_base

timeit = test_base.timeit
TestDir = test_base.TestDir

Error = marcel.object.error.Error
start_dir = os.getcwd()
TEST = test_base.TestConsole()

SQL = True


# Utilities for testing filename ops


def relative(base, x):
    x_path = pathlib.Path(x)
    base_path = pathlib.Path(base)
    display_path = x_path.relative_to(base_path)
    return display_path


def absolute(base, x):
    return pathlib.Path(base) / x


def filename_op_setup(testdir):
    # testdir contents:
    #     f (file)
    #     sf (symlink to f)
    #     lf (hard link to f)
    #     d/ (dir)
    #         df (file)
    #         sdf (symlink to df)
    #         ldf (hard link to df)
    #         dd/ (dir)
    #         sdd (symlink to dd)
    #             ddf (file)
    #     sd (symlink to d)
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
    # Create test data
    for x in setup_script:
        os.system(x)
    TEST.cd(f'{testdir}')


@timeit
def test_no_such_op():
    TEST.run('gen 5 | abc', expected_err='not executable')


@timeit
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
    TEST.run('gen 3 -1 | map (f: 5 / f)',
             expected_out=[-5.0, Error('division by zero'), 5.0])
    # # Function-valued args
    # TEST.run('N = (7)')
    # TEST.run('gen (N - 2)',
    #          expected_out=[0, 1, 2, 3, 4])
    # TEST.run('gen (N - 2) (N + 3)',
    #          expected_out=[10, 11, 12, 13, 14])
    # TEST.run('gen -p (N - 4) (N - 2) (N + 3)',
    #          expected_out=['010', '011', '012', '013', '014'])
    # TEST.run('N = ("7")')
    # TEST.run('gen (N - 2)',
    #          expected_err="unsupported operand type(s) for -: 'str' and 'int'")


@timeit
def test_write():
    # Write to stdout
    TEST.run('gen 3 | (f: (f, -f))',
             expected_out=[(0, 0), (1, -1), (2, -2)])
    TEST.run('gen 3 | (f: (f, -f)) | write --format "{}~{}"',
             expected_out=['0~0', '1~-1', '2~-2'])
    TEST.run('gen 3 | (f: (f, -f)) | write -f "{}~{}"',
             expected_out=['0~0', '1~-1', '2~-2'])
    TEST.run('gen 3 | (f: (f, -f)) | write --csv',
             expected_out=['0,0', '1,-1', '2,-2'])
    TEST.run('gen 3 | (f: (f, -f)) | write -c',
             expected_out=['0,0', '1,-1', '2,-2'])
    TEST.run('gen 3 | (f: (f, -f)) | write --tsv',
             expected_out=['0\t0', '1\t-1', '2\t-2'])
    TEST.run('gen 3 | (f: (f, -f)) | write -t',
             expected_out=['0\t0', '1\t-1', '2\t-2'])
    TEST.run('gen 3 | (f: (f, -f)) | write --pickle',
             expected_err='--pickle incompatible with stdout')
    TEST.run('gen 3 | (f: (f, -f)) | write -p',
             expected_err='--pickle incompatible with stdout')
    TEST.run('gen 3 | (f: (f, -f)) | write --csv --tsv',
             expected_err='Cannot specify more than one of')
    # Write to file
    with TestDir(TEST.env) as testdir:
        output_filename = f'{testdir}/out.txt'
        TEST.run('gen 3 | (f: (f, -f)) | write ' + output_filename,
                 expected_out=[(0, 0), (1, -1), (2, -2)],
                 file=output_filename)
        TEST.run('gen 3 | (f: (f, -f)) | write --format "{}~{}" ' + output_filename,
                 expected_out=['0~0', '1~-1', '2~-2'],
                 file=output_filename)
        TEST.run('gen 3 | (f: (f, -f)) | write -f "{}~{}" ' + output_filename,
                 expected_out=['0~0', '1~-1', '2~-2'],
                 file=output_filename)
        TEST.run('gen 3 | (f: (f, -f)) | write --csv ' + output_filename,
                 expected_out=['0,0', '1,-1', '2,-2'],
                 file=output_filename)
        TEST.run('gen 3 | (f: (f, -f)) | write -c ' + output_filename,
                 expected_out=['0,0', '1,-1', '2,-2'],
                 file=output_filename)
        TEST.run('gen 3 | (f: (f, -f)) | write --tsv ' + output_filename,
                 expected_out=['0\t0', '1\t-1', '2\t-2'],
                 file=output_filename)
        TEST.run('gen 3 | (f: (f, -f)) | write -t ' + output_filename,
                 expected_out=['0\t0', '1\t-1', '2\t-2'],
                 file=output_filename)
        TEST.run('gen 3 | (f: (f, -f)) | write --pickle ' + output_filename,
                 verification=f'read --pickle {output_filename}',
                 expected_out=[(0, 0), (1, -1), (2, -2)])
        TEST.run('gen 3 | (f: (f, -f)) | write -p ' + output_filename,
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
        TEST.run('gen 3 | (f: (f, -f)) | write --csv --append ' + output_filename,
                 expected_out=['0,0', '1,-1', '2,-2'],
                 file=output_filename)
        TEST.run('gen 3 | (f: (f, -f)) | write --tsv --append ' + output_filename,
                 expected_out=['0,0', '1,-1', '2,-2',
                               '0\t0', '1\t-1', '2\t-2'],
                 file=output_filename)
        TEST.run('gen 3 | (f: (f, -f)) | write --append ' + output_filename,
                 expected_out=['0,0', '1,-1', '2,-2',
                               '0\t0', '1\t-1', '2\t-2',
                               (0, 0), (1, -1), (2, -2)],
                 file=output_filename)
        TEST.delete_files(output_filename)
        TEST.run('gen 3 | (f: (f, -f)) | write --pickle --append ' + output_filename,
                 verification='read --pickle ' + output_filename,
                 expected_out=[(0, 0), (1, -1), (2, -2)])
        TEST.run('gen 3 3 | (f: (f, -f)) | write --pickle --append ' + output_filename,
                 verification='read --pickle ' + output_filename,
                 expected_out=[(0, 0), (1, -1), (2, -2), (3, -3), (4, -4), (5, -5)])
        # Function-valued filename
        TEST.run(f'gen 3 | write ("{output_filename}")',
                 expected_out=[0, 1, 2],
                 file=output_filename)


@timeit
def test_sort():
    TEST.run('gen 5 | sort',
             expected_out=[0, 1, 2, 3, 4])
    TEST.run('gen 5 | sort (lambda f: -f)',
             expected_out=[4, 3, 2, 1, 0])
    TEST.run('gen 5 | map (f: (-f, f)) | sort',
             expected_out=[(-4, 4), (-3, 3), (-2, 2), (-1, 1), (0, 0)])
    TEST.run('((1, "a", 2, "b")) | expand | sort',
             expected_err="'<' not supported between instances of 'str' and 'int'")
    # Bug 101
    TEST.run('(', expected_err='Malformed Python expression')


@timeit
def test_map():
    TEST.run('gen 5 | map (f: -f)',
             expected_out=[0, -1, -2, -3, -4])
    TEST.run('gen 5 | map (lambda f: -f)',
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
             expected_err='invalid syntax')
    # Mix of output and error
    TEST.run('gen 3 | (f: 1 / (1 - f))',
             expected_out=[1.0, Error('division by zero'), -1.0])


@timeit
def test_select():
    TEST.run('gen 5 | select (f: True)',
             expected_out=[0, 1, 2, 3, 4])
    TEST.run('gen 5 | select (f: False)',
             expected_out=[])
    TEST.run('gen 5 | select (f: f % 2 == 1)',
             expected_out=[1, 3])


@timeit
def test_red():
    # Test function symbols
    TEST.run('gen 5 1 | red +',
             expected_out=[15])
    TEST.run('gen 5 1 | red *',
             expected_out=[120])
    TEST.run('gen 5 1 | red ^',
             expected_out=[1])
    TEST.run('gen 20 1 | select (f: f in (3, 7, 15)) | red &',
             expected_out=[3])
    TEST.run('gen 75 | select (f: f in (18, 36, 73)) | red \\|',
             expected_out=[127])
    TEST.run('gen 3 | map (f: f == 1) | red and',
             expected_out=[False])
    TEST.run('gen 3 | map (f: f == 1) | red or',
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
    TEST.run('gen 5 1 | map (f: (f, f)) | red + *',
             expected_out=[(15, 120)])
    # Test lambdas
    TEST.run('gen 5 1 | map (f: (f, f)) | red (f, y: y if f is None else f + y) (f, y: y if f is None else f * y)',
             expected_out=[(15, 120)])
    # Test multiple incremental reduction
    TEST.run('gen 5 1 | map (f: (f, f)) | red -i + *',
             expected_out=[(1, 1, 1, 1),
                           (2, 2, 3, 2),
                           (3, 3, 6, 6),
                           (4, 4, 10, 24),
                           (5, 5, 15, 120)])
    # Test grouping
    TEST.run('gen 9 1 | map (f: (f, f // 2, f * 100, f // 2)) | red + . + .',
             expected_out=[(1, 0, 100, 0),
                           (5, 1, 500, 1),
                           (9, 2, 900, 2),
                           (13, 3, 1300, 3),
                           (17, 4, 1700, 4)])
    # Test incremental grouping
    TEST.run('gen 9 1 | map (f: (f, f // 2, f * 100, f // 2)) | red -i + . + .',
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
    TEST.run('gen 4 | map (f: (f, 10*f) if f%2 == 0 else (f, 10*f, 100*f)) | red + + +',
             expected_out=[Error('too short'), Error('too short'), (4, 40, 400)])
    TEST.run('gen 4 | map (f: (f, 10*f) if f%2 == 0 else (f, 10*f, 100*f)) | red . + +',
             expected_out=[Error('too short'), Error('too short'), (1, 10, 100), (3, 30, 300)])
    TEST.run('gen 4 | map (f: (f, 10*f) if f%2 == 0 else (f, 10*f, 100*f)) | red -i . + +',
             expected_out=[Error('too short'), (1, 10, 100, 10, 100), Error('too short'), (3, 30, 300, 30, 300)])
    # Bug 153
    TEST.run('gen 3 | select (f: False) | red count',
             expected_out=[0])
    TEST.run('gen 3 | red -i count',
             expected_out=[(0, 1), (1, 2), (2, 3)])
    TEST.run('gen 5 | (f: (f // 2, None)) | red . count | sort',
             expected_out=[(0, 2), (1, 2), (2, 1)])
    # Bug 242
    TEST.run('gen 3 | red growset',
             expected_out=[{0, 1, 2}])


@timeit
def test_expand():
    # Test singletons
    TEST.run('gen 5 | expand',
             expected_out=[0, 1, 2, 3, 4])
    TEST.run('gen 5 | map (f: ([f, f],)) | expand',
             expected_out=[0, 0, 1, 1, 2, 2, 3, 3, 4, 4])
    TEST.run('gen 5 | map (f: ((f, f),)) | expand',
             expected_out=[0, 0, 1, 1, 2, 2, 3, 3, 4, 4])
    TEST.run('gen 5 | expand 0',
             expected_out=[0, 1, 2, 3, 4])
    TEST.run('gen 5 | map (f: ([f, f],)) | expand 0',
             expected_out=[0, 0, 1, 1, 2, 2, 3, 3, 4, 4])
    # Test non-singletons
    TEST.run('gen 5 | map (f: (f, -f)) | expand',
             expected_out=[0, 0, 1, -1, 2, -2, 3, -3, 4, -4])
    TEST.run('gen 5 | map (f: (f, -f)) | expand 0',
             expected_out=[(0, 0), (1, -1), (2, -2), (3, -3), (4, -4)])
    TEST.run('gen 5 | map (f: (f, -f)) | expand 1',
             expected_out=[(0, 0), (1, -1), (2, -2), (3, -3), (4, -4)])
    TEST.run('gen 5 | map (f: (f, -f)) | expand 2',
             expected_out=[(0, 0), (1, -1), (2, -2), (3, -3), (4, -4)])
    # Expand list
    TEST.run('gen 5 | map (f: ([100, 200], f, -f)) | expand 0',
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
    TEST.run('gen 5 | map (f: (f, [100, 200], -f)) | expand 1',
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
    TEST.run('gen 5 | map (f: (f, -f, [100, 200])) | expand 2',
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
    TEST.run('gen 5 | map (f: (f, -f, [100, 200])) | expand 3',
             expected_out=[(0, 0, [100, 200]),
                           (1, -1, [100, 200]),
                           (2, -2, [100, 200]),
                           (3, -3, [100, 200]),
                           (4, -4, [100, 200])])
    # Expand tuple
    TEST.run('gen 5 | map (f: ((100, 200), f, -f)) | expand 0',
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
    TEST.run('gen 5 | map (f: (set((100, 200)), f, -f)) | expand 0 | sort',
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
    TEST.run('N = (1)')
    TEST.run('gen 3 | map (f: (f, (f * 10, f * 10 + 1))) | expand (N)',
             expected_out=[(0, 0), (0, 1), (1, 10), (1, 11), (2, 20), (2, 21)])
    # Bug 158
    TEST.run('gen 3 1 | (f: [str(f * 111)] * f) | expand',
             expected_out=[111, 222, 222, 333, 333, 333])
    # Expand generator-like objects (having __next__)
    TEST.run('(zip([1, 2, 3], [4, 5, 6])) | expand',
             expected_out=[(1, 4), (2, 5), (3, 6)])


@timeit
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


@timeit
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


@timeit
def test_reverse():
    TEST.run('gen 5 | select (f: False) | reverse',
             expected_out=[])
    TEST.run('gen 5 | reverse',
             expected_out=[4, 3, 2, 1, 0])


@timeit
def test_squish():
    TEST.run('gen 5 | squish',
             expected_out=[0, 1, 2, 3, 4])
    TEST.run('gen 5 | squish +',
             expected_out=[0, 1, 2, 3, 4])
    TEST.run('gen 5 | map (f: (f, -f)) | squish',
             expected_out=[0, 0, 0, 0, 0])
    TEST.run('gen 5 | map (f: (f, -f)) | squish +',
             expected_out=[0, 0, 0, 0, 0])
    TEST.run('gen 5 | map (f: (f, -f)) | squish min',
             expected_out=[0, -1, -2, -3, -4])
    TEST.run('gen 5 | map (f: (f, -f)) | squish max',
             expected_out=[0, 1, 2, 3, 4])
    TEST.run('gen 5 | map (f: (f, -f)) | squish count',
             expected_out=[2, 2, 2, 2, 2])
    TEST.run('gen 5 | map (f: ([-f, f], [-f, f])) | squish +',
             expected_out=[[0, 0, 0, 0],
                           [-1, 1, -1, 1],
                           [-2, 2, -2, 2],
                           [-3, 3, -3, 3],
                           [-4, 4, -4, 4]])


@timeit
def test_unique():
    TEST.run('gen 10 | unique',
             expected_out=[0, 1, 2, 3, 4, 5, 6, 7, 8, 9])
    TEST.run('gen 10 | select (f: False) | unique',
             expected_out=[])
    TEST.run('gen 10 | unique -c',
             expected_out=[0, 1, 2, 3, 4, 5, 6, 7, 8, 9])
    TEST.run('gen 10 | select (f: False) | unique -c',
             expected_out=[])
    TEST.run('gen 10 | map (f: f // 3) | unique',
             expected_out=[0, 1, 2, 3])
    TEST.run('gen 10 | map (f: f // 3) | unique -c',
             expected_out=[0, 1, 2, 3])
    TEST.run('gen 10 | map (f: f // 3) | unique --consecutive',
             expected_out=[0, 1, 2, 3])
    TEST.run('gen 10 | map (f: f % 3) | unique',
             expected_out=[0, 1, 2])
    TEST.run('gen 3 | (f: (f//2, [f//2])) | unique',
             expected_err='not hashable')


@timeit
def test_window():
    TEST.run('gen 10 | window (f: False)',
             expected_out=[(0, 1, 2, 3, 4, 5, 6, 7, 8, 9)])
    TEST.run('gen 10 | window (f: True)',
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
    TEST.run('gen 10 | window -o 3 (f: True)',
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


@timeit
def test_bash():
    with TestDir(TEST.env) as testdir:
        os.system(f'touch {testdir}/x1')
        os.system(f'touch {testdir}/x2')
        os.system(f'touch {testdir}/y1')
        os.system(f'touch {testdir}/y2')
        TEST.run('who = world')
        # Test command string
        TEST.run(f'cd {testdir}')
        TEST.run('bash "ls x*"',
                 expected_out=['x1', 'x2'])
        TEST.run('bash "ls -l *1" | (x: x.split()[-1])',
                 expected_out=['x1', 'y1'])
        TEST.run("""bash 'echo "hello  world"'""",  # Two spaces in string to be printed
                 expected_out='hello  world')
        TEST.run('''echo (f"hello {who}")''',
                 expected_out='hello world')
        # Test args
        TEST.run('echo hello  world',          # Two spaces between args should not be reproduced
                 expected_out=['hello world'])
        TEST.run('echo hello (who)',
                 expected_out=['hello world'])


@timeit
def test_namespace():
    TEST.run(test='ws -n namespace_test',
             verification='ws | (w: str(w))',
             expected_out=['Workspace(namespace_test)'])
    TEST.run('map (list(globals().keys())) | expand | select (f: f == "USER")',
             expected_out=['USER'])
    # Try to use an undefined symbol
    TEST.run('map (pi)',
             expected_out=[Error('not defined')])
    TEST.run(test='import math *',
             verification='map (pi)',
             expected_out=['3.141592653589793'])
    TEST.run(test='ws -c',
             verification='ws | (w: str(w))',
             expected_out=['Workspace()'])
    TEST.run('ws -d namespace_test')
    TEST.run('map (pi)',
             expected_out=[Error('not defined')])


@timeit
def test_source_filenames():
    with TestDir(TEST.env) as testdir:
        filename_op_setup(testdir)
        # Relative path
        TEST.run('ls . | map (f: f.render_compact())',
                 expected_out=sorted(['.', 'f', 'sf', 'lf', 'd', 'sd']))
        TEST.run('ls d | map (f: f.render_compact())',
                 expected_out=sorted(['.', 'df', 'sdf', 'ldf', 'dd', 'sdd']))
        # Absolute path
        TEST.run(f'ls {testdir} | map (f: f.render_compact())',
                 expected_out=sorted(['.', 'f', 'sf', 'lf', 'd', 'sd']))
        TEST.run(f'ls {testdir}/d | map (f: f.render_compact())',
                 expected_out=sorted(['.', 'df', 'sdf', 'ldf', 'dd', 'sdd']))
        # Glob in last part of path
        TEST.run(f'ls -0 {testdir}/s? | map (f: f.render_compact())',
                 expected_out=sorted(['sf', 'sd']))
        TEST.run(f'ls -0 {testdir}/*f | map (f: f.render_compact())',
                 expected_out=sorted(['f', 'sf', 'lf']))
        # Glob in intermediate part of path
        TEST.run(f'ls -0 {testdir}/*d/*dd | map (f: f.render_compact())',
                 expected_out=sorted(['d/dd', 'd/sdd', 'sd/dd', 'sd/sdd']))
        TEST.run(f'ls -0 {testdir}/*f | map (f: f.render_compact())',
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


@timeit
def test_ls():
    # with TestDir(TEST.env) as testdir:
    #     filename_op_setup(testdir)
    #     # 0/1/r flags with no files specified.
    #     TEST.run('ls -0 | map (f: f.render_compact())',
    #              expected_out=sorted(['.']))
    #     TEST.run('ls -1 | map (f: f.render_compact())',
    #              expected_out=sorted(['.',
    #                                   'f', 'sf', 'lf', 'sd', 'd',  # Top-level
    #                                   ]))
    #     TEST.run('ls -r | map (f: f.render_compact())',
    #              expected_out=sorted(['.',
    #                                   'f', 'sf', 'lf', 'sd', 'd',  # Top-level
    #                                   'd/df', 'd/sdf', 'd/ldf', 'd/dd', 'd/sdd',  # Contents of d
    #                                   'd/dd/ddf']))
    #     TEST.run('ls | map (f: f.render_compact())',
    #              expected_out=sorted(['.',
    #                                   'f', 'sf', 'lf', 'sd', 'd',  # Top-level
    #                                   ]))
    #     # 0/1/r flags with file
    #     TEST.run('ls -0 f | map (f: f.render_compact())',
    #              expected_out=sorted(['f']))
    #     TEST.run('ls -1 f | map (f: f.render_compact())',
    #              expected_out=sorted(['f']))
    #     TEST.run('ls -r f | map (f: f.render_compact())',
    #              expected_out=sorted(['f']))
    #     # 0/1/r flags with directory
    #     TEST.run(f'ls -0 {testdir} | map (f: f.render_compact())',
    #              expected_out=sorted(['.']))
    #     TEST.run(f'ls -1 {testdir} | map (f: f.render_compact())',
    #              expected_out=sorted(['.', 'f', 'sf', 'lf', 'sd', 'd']))
    #     TEST.run(f'ls -r {testdir} | map (f: f.render_compact())',
    #              expected_out=sorted(['.',
    #                                   'f', 'sf', 'lf', 'sd', 'd',  # Top-level
    #                                   'd/df', 'd/sdf', 'd/ldf', 'd/dd', 'd/sdd',  # Contents of d
    #                                   'd/dd/ddf']))
    #     # Test f/d/s flags
    #     TEST.run('ls -fr | map (f: f.render_compact())',
    #              expected_out=sorted(['f', 'lf',  # Top-level
    #                                   'd/df', 'd/ldf',  # Contents of d
    #                                   'd/dd/ddf']))
    #     TEST.run('ls -dr | map (f: f.render_compact())',
    #              expected_out=sorted(['.',
    #                                   'd',  # Top-level
    #                                   'd/dd']))  # Contents of d
    #     TEST.run('ls -sr | map (f: f.render_compact())',
    #              expected_out=sorted(['sf', 'sd',  # Top-level
    #                                   'd/sdf', 'd/sdd'  # Contents of d
    #                                   ]))
    #     # Duplicates
    #     TEST.run('ls -0 *d ? | map (f: f.render_compact())',
    #              expected_out=sorted(['d', 'sd', 'f']))
    #     # This should find d twice
    #     expected = sorted(['.', 'f', 'sf', 'lf', 'd', 'sd'])
    #     expected.extend(sorted(['d/df', 'd/sdf', 'd/ldf', 'd/dd', 'd/sdd']))
    #     TEST.run('ls -1 . d | map (f: f.render_compact())',
    #              expected_out=expected)
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
        TEST.run(test=f'ls -r {testdir} | map (f: f.render_compact())',
                 expected_out=['.',
                               'd1',
                               'd1/f1',
                               'd2',
                               Error('Permission denied'),
                               'd3',
                               Error('Permission denied'),
                               'd4',
                               'd4/f4'])
        # Restore owners so that cleanup can proceed
        me = os.getlogin()
        os.system(f'sudo chown {me}.{me} {testdir}/d2')
        os.system(f'sudo chown {me}.{me} {testdir}/d3')
        # Args with vars
    with TestDir(TEST.env) as testdir:
        filename_op_setup(f'{testdir}/vartest')
        TEST.run('VARTEST = vartest')
        TEST.run(f'ls -r {testdir}/(VARTEST) | map (f: f.render_compact())',
                 expected_out=sorted(['.',
                                      'f', 'sf', 'lf', 'sd', 'd',  # Top-level
                                      'd/df', 'd/sdf', 'd/ldf', 'd/dd', 'd/sdd',  # Contents of d
                                      'd/dd/ddf']))
        TEST.run(f'TESTDIR = {str(testdir).upper()}')
        TEST.run('ls -r (TESTDIR.lower())/(VARTEST) | map (f: f.render_compact())',
                 expected_out=sorted(['.',
                                      'f', 'sf', 'lf', 'sd', 'd',  # Top-level
                                      'd/df', 'd/sdf', 'd/ldf', 'd/dd', 'd/sdd',  # Contents of d
                                      'd/dd/ddf']))


# pushd, popd, dirs, cd
@timeit
def test_dir_stack():
    with TestDir(TEST.env) as testdir:
        filename_op_setup(testdir)
        TEST.run('mkdir a b c')
        TEST.run('touch f')
        TEST.run('rm -rf p')
        TEST.run('mkdir p')
        TEST.run('chmod 000 p')
        TEST.run(test='pwd | map (f: f.path)',
                 expected_out=[testdir])
        TEST.run(test='dirs | map (f: f.path)',
                 expected_out=[f'{testdir}'])
        TEST.run(test='pushd a | map (f: f.path)',
                 expected_out=[f'{testdir}/a', f'{testdir}'])
        TEST.run(test='dirs | map (f: f.path)',
                 expected_out=[f'{testdir}/a', f'{testdir}'])
        TEST.run(test='pushd ../b | map (f: f.path)',
                 expected_out=[f'{testdir}/b', f'{testdir}/a', f'{testdir}'])
        TEST.run(test='dirs | map (f: f.path)',
                 expected_out=[f'{testdir}/b', f'{testdir}/a', f'{testdir}'])
        TEST.run(test='pushd | map (f: f.path)',
                 expected_out=[f'{testdir}/a', f'{testdir}/b', f'{testdir}'])
        TEST.run(test='dirs | map (f: f.path)',
                 expected_out=[f'{testdir}/a', f'{testdir}/b', f'{testdir}'])
        TEST.run(test='popd | map (f: f.path)',
                 expected_out=[f'{testdir}/b', f'{testdir}'])
        TEST.run(test='pwd | map (f: f.path)',
                 expected_out=[f'{testdir}/b'])
        TEST.run(test='dirs | map (f: f.path)',
                 expected_out=[f'{testdir}/b', f'{testdir}'])
        TEST.run(test='dirs -c | map (f: f.path)',
                 expected_out=[f'{testdir}/b'])
        TEST.run(test='pushd | map (f: f.path)',
                 expected_out=[f'{testdir}/b'])
        # Dir operations when the destination cd does not exist or cannot be entered due to permissions
        # cd
        TEST.run(f'cd {testdir}')
        TEST.run(test=f'cd {testdir}/doesnotexist',
                 expected_err='No qualifying path')
        TEST.run(test='pwd | (f: str(f))',
                 expected_out=f'{testdir}')
        TEST.run(test=f'cd {testdir}/p',
                 expected_err='Permission denied')
        TEST.run(test='pwd | (f: str(f))',
                 expected_out=f'{testdir}')
        TEST.run(test='cd f',
                 expected_err='is not a directory')
        # pushd
        TEST.run(test=f'pushd {testdir}/doesnotexist',
                 expected_err='No qualifying path')
        TEST.run(test='pwd | (f: str(f))',
                 expected_out=f'{testdir}')
        TEST.run(test=f'pushd {testdir}/p',
                 expected_err='Permission denied')
        TEST.run(test='pwd | (f: str(f))',
                 expected_out=f'{testdir}')
        # popd: Arrange for a deleted dir on the stack and try popding into it.
        TEST.run('rm -rf f y')
        TEST.run('mkdir f y')
        TEST.run('cd f')
        TEST.run('pushd ../y | (f: str(f))',
                 expected_out=[f'{testdir}/y', f'{testdir}/f'])
        TEST.run(f'rm -rf {testdir}/f')
        TEST.run('popd',
                 expected_err='directories have been removed')
        TEST.run('dirs | (f: str(f))',
                 expected_out=[f'{testdir}/y'])


@timeit
def test_remote():
    node1 = marcel.object.cluster.Host(None, TEST.env.getvar('NODE1'))
    TEST.run('@CLUSTER1 (| gen 3 |)',
             expected_out=[(node1, 0), (node1, 1), (node1, 2)])
    # Handling of remote error in execution
    TEST.run('@CLUSTER1 (| gen 3 -1 | map (f: 5 / f) |)',
             expected_out=[(node1, -5.0), Error('division by zero'), (node1, 5.0)])
    # Handling of remote error in setup
    TEST.run('@CLUSTER1 (| ls /nosuchfile |)',
             expected_out=[Error('No qualifying paths')])
    # Bug 4
    TEST.run('@CLUSTER1 (| gen 3 |) | red . +',
             expected_out=[(node1, 3)])
    TEST.run('@CLUSTER1 (| gen 10 | map (f: (f%2, f)) | red . + |)',
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


@timeit
def test_fork():
    # int forkgen
    TEST.run('fork 3 (|gen 3 100|) | sort',
             expected_out=[100, 100, 100, 101, 101, 101, 102, 102, 102])
    TEST.run('fork 3 (|t: gen 3 100 | (f: (t, f))|) | sort',
             expected_out=[(0, 100), (0, 101), (0, 102),
                           (1, 100), (1, 101), (1, 102),
                           (2, 100), (2, 101), (2, 102)])
    TEST.run('fork 3 (|t, u: gen 3 100 | (f: (t, f))|) | sort',
             expected_err='Too many pipelines args')
    # iterable forkgen
    TEST.run('fork "abc" (|gen 3 100|) | sort',
             expected_out=[100, 100, 100, 101, 101, 101, 102, 102, 102])
    TEST.run('fork "abc" (|t: gen 3 100 | (f: (t, f))|) | sort',
             expected_out=[('a', 100), ('a', 101), ('a', 102),
                           ('b', 100), ('b', 101), ('b', 102),
                           ('c', 100), ('c', 101), ('c', 102)])
    TEST.run('fork "abc" (|t, u: gen 3 100 | (f: (t, f))|) | sort',
             expected_err='Too many pipelines args')
    # Cluster forkgen
    TEST.run('fork CLUSTER1 (|gen 3 100|)',
             expected_out=[100, 101, 102])
    TEST.run('fork CLUSTER1 (|t: gen 3 100 | (f: (str(t), f))|)',
             expected_out=[('127.0.0.1', 100), ('127.0.0.1', 101), ('127.0.0.1', 102)])
    TEST.run('fork CLUSTER1 (|t, u: gen 3 100 | (f: (str(t), f))|)',
             expected_err='Too many pipelines args')


@timeit
def test_sudo():
    with TestDir(TEST.env) as testdir:
        TEST.run(test='sudo (| gen 3 |)', expected_out=[0, 1, 2])
        os.system(f'sudo mkdir {testdir}/sudotest')
        os.system(f'sudo touch {testdir}/sudotest/f')
        os.system(f'sudo chmod 400 {testdir}/sudotest')
        TEST.run(test=f'ls -f {testdir}/sudotest', expected_out=[Error('Permission denied')])
        TEST.run(test=f'sudo (| ls -f {testdir}/sudotest | map (f: f.render_compact()) |)', expected_out=['f'])
        os.system(f'sudo rm -rf {testdir}/sudotest')


@timeit
def test_version():
    TEST.run(test='version',
             expected_out=[marcel.version.VERSION])


@timeit
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
    TEST.run(test='a = (| map (f: (f, -f)) |)',
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
    TEST.run('f = (|(5)|)')
    TEST.run(test='f',
             expected_out=[5])
    # Bug 165
    TEST.run('ls = abc')
    TEST.run('(ls)',
             expected_out=['abc'])
    # Don't want the op ls masked by the variable ls
    TEST.run(test='env -d ls',
             verification='env -p ls',
             expected_out=[])
    # Evaluate -> int (non-function)
    TEST.run(test='a = (lambda: 5+6)',
             verification='(a)',
             expected_out=[11])
    TEST.run(test='a = (: 5+6)',
             verification='(a)',
             expected_out=[11])
    TEST.run(test='a = (5+6)',
             verification='(a)',
             expected_out=[11])
    # Evaluate -> function
    TEST.run(test='b = (lambda: lambda f: 5+6+f)',
             verification='(b(7))',
             expected_out=[18])
    TEST.run(test='b = (lambda f: 5+6+f)',
             verification='(b(7))',
             expected_out=[18])
    TEST.run(test='b = (f: 5+6+f)',
             verification='(b(7))',
             expected_out=[18])


@timeit
def test_join():
    # Join losing right inputs
    TEST.run(test='gen 4 | map (f: (f, -f)) | join (|gen 3 | map (f: (f, f * 100))|)',
             expected_out=[(0, 0, 0), (1, -1, 100), (2, -2, 200)])
    # Left join
    TEST.run(test='gen 4 | map (f: (f, -f)) | join -k (|gen 3 | map (f: (f, f * 100))|)',
             expected_out=[(0, 0, 0), (1, -1, 100), (2, -2, 200), (3, -3)])
    TEST.run(test='gen 4 | map (f: (f, -f)) | join --keep (|gen 3 | map (f: (f, f * 100))|)',
             expected_out=[(0, 0, 0), (1, -1, 100), (2, -2, 200), (3, -3)])
    # Compound key
    TEST.run(test='gen 4 | map (f: ((f, f + 1), -f)) | join (|gen 3 | map (f: ((f, f + 1), f * 100))|)',
             expected_out=[((0, 1), 0, 0), ((1, 2), -1, 100), ((2, 3), -2, 200)])
    # Multiple matches on the right
    TEST.run(test='gen 4 '
                  '| map (f: (f, -f)) '
                  '| join (|gen 3 '
                  '        | map (f: (f, (f * 100, f * 100 + 1))) '
                  '        | expand 1|)',
             expected_out=[(0, 0, 0), (0, 0, 1), (1, -1, 100), (1, -1, 101), (2, -2, 200), (2, -2, 201)])
    # Right argument in variable
    TEST.run('x100 = (|gen 3 | map (f: (f, f * 100))|)')
    TEST.run(test='gen 4 | map (f: (f, -f)) | join x100',
             expected_out=[(0, 0, 0), (1, -1, 100), (2, -2, 200)])
    TEST.run(test='gen 4 | map (f: (f, -f)) | join (|x100|)',
             expected_out=[(0, 0, 0), (1, -1, 100), (2, -2, 200)])
    # Join with pipelines var taking arg
    TEST.run('xn = (|n: gen 3 | map (f: (f, f * n))|)')
    TEST.run(test='gen 4 | map (f: (f, -f)) | join (|xn (100)|)',
             expected_out=[(0, 0, 0), (1, -1, 100), (2, -2, 200)])
    with TestDir(TEST.env) as testdir:
        TEST.run(f'gen 3 | map (f: (f, f*10)) | write {testdir}/a.csv')
        TEST.run(f'gen 3 | map (f: (f, f*100)) | write {testdir}/b.csv')
        TEST.run(f'get = (|f: (File(f).readlines()) | expand | map (f: eval(f))|)')
        TEST.run(f'get {testdir}/a.csv | join (|get {testdir}/b.csv|)',
                 expected_out=[(0, 0, 0), (1, 10, 100), (2, 20, 200)])
    # Handle non-hashable join keys
    TEST.run('gen 3 | (f: ((f,), f)) | join (|gen 3 | (f: ((f,), f*100))|)',
             expected_out=[((0,), 0, 0), ((1,), 1, 100), ((2,), 2, 200)])
    TEST.run('gen 3 | (f: ([f], f)) | join (|gen 3 | (f: ((f,), f*100))|)',
             expected_err='not hashable')
    TEST.run('gen 3 | (f: ((f,), f)) | join (|gen 3 | (f: ([f], f*100))|)',
             expected_err='not hashable')


@timeit
def test_comment():
    TEST.run('# this is a comment',
             expected_out=[])
    TEST.run('#',
             expected_out=[])
    TEST.run('gen 3 # comment',
             expected_out=[0, 1, 2])
    TEST.run('gen 3 | map (f: -f) # comment',
             expected_out=[0, -1, -2])


@timeit
def test_pipeline_args():
    TEST.run('add = (|a: map (f: (f, f + a))|)')
    TEST.run('gen 3 | add (100)',
             expected_out=[(0, 100), (1, 101), (2, 102)])
    # Multiple functions
    TEST.run('add = (|a: map (f: (f, f + a)) | map (f, y: (f + a, y - a))|)')
    TEST.run('gen 3 | add (100)',
             expected_out=[(100, 0), (101, 1), (102, 2)])
    # Flag instead of anon arg
    TEST.run('add = (|a: map (f: (f, f + a))|)')
    TEST.run('gen 3 | add -a (100)',
             expected_out=[(0, 100), (1, 101), (2, 102)])
    # Multiple anon args
    TEST.run('f = (|a, b: map (f: (f, f * a + b))|)')
    TEST.run('gen 3 | f (100) (10)',
             expected_out=[(0, 10), (1, 110), (2, 210)])
    # Multiple flag args
    TEST.run('f = (|a, b: map (f: (f, f * a + b))|)')
    TEST.run('gen 3 | f -a (100) -b (10)',
             expected_out=[(0, 10), (1, 110), (2, 210)])
    TEST.run('gen 3 | f -b (10) -a (100)',
             expected_out=[(0, 10), (1, 110), (2, 210)])
    TEST.run('gen 3 | f -b (10) -a (100) -a (200)',
             expected_err='Flag a given more than once')
    TEST.run('gen 3 | f -b (10)',
             expected_out=[Error("unsupported operand type(s) for *: 'int' and 'NoneType'")]*3)
    # Long flags
    TEST.run('foobar = (|foo, bar: map (f: f * foo) | select (f: f < bar)|)')
    TEST.run('gen 10 | foobar --foo (10) --bar (45)',
             expected_out=[0, 10, 20, 30, 40])
    TEST.run('gen 10 | foobar --bar (73) --foo (10)',
             expected_out=[0, 10, 20, 30, 40, 50, 60, 70])
    # Insufficient args
    # Bug 105
    TEST.run('p = (| n: gen (1 if n is None else int(n)) |)')
    TEST.run('p 3',
             expected_out=[0, 1, 2])
    TEST.run('p',
             expected_out=[0])


@timeit
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
    TEST.run('''gen 3 1000 | map (f: (f, 'aaa')) | sql -u "insert into t values(%s, %s)"''',
             expected_out=[1, 1, 1])
    TEST.run('''sql "select * from t order by id"''',
             expected_out=[(1, 'xyz'), (2, 'xyz'), (1000, 'aaa'), (1001, 'aaa'), (1002, 'aaa')])
    TEST.run('''gen 2 1 | sql "delete from t where id = %s"''',
             expected_out=[])
    TEST.run('''sql "select * from t order by id"''',
             expected_out=[(1000, 'aaa'), (1001, 'aaa'), (1002, 'aaa')])
    TEST.run('''sql "drop table if exists t"''')
    # TODO: sql types


@timeit
def test_import():
    # import MODULE
    TEST.run(test='import math',
             verification='env math | (k, v: k)',
             expected_out=['math'])
    TEST.run('(math.pi)', expected_out=[math.pi])
    TEST.run('(math.e)', expected_out=[math.e])
    TEST.run(test='import nosuchmodule',
             expected_err='nosuchmodule not found')
    # import --as NAME MODULE
    TEST.run(test='import --as PATHLIB pathlib',
             verification='env PATHLIB | (k, v: k)',
             expected_out=['PATHLIB'])
    TEST.run(test='import --as 123badname pathlib',
             expected_err='not a valid identifier')
    # import MODULE SYMBOL
    TEST.run(test='import math pi',
             verification='(pi)',
             expected_out=[math.pi])
    TEST.run(test='import math nosuchsymbol',
             expected_err='nosuchsymbol is not defined')
    # import --as NAME MODULE SYMBOL
    TEST.run(test='import --as PI math pi',
             verification='(PI)',
             expected_out=[math.pi])
    TEST.run(test='import --as 123oops math pi',
             expected_err='not a valid identifier')
    # import MODULE *
    TEST.run(test='import sys *',
             verification='(version)',
             expected_out=[sys.version])
    TEST.reset_environment()


@timeit
def test_store_load():
    TEST.reset_environment()
    # Basics
    TEST.run(test='gen 3 | store f',
             verification='load f',
             expected_out=[0, 1, 2])
    TEST.run('env | map (k, v: k) | select (k: k == "f")',
             expected_out=['f'])
    # Overwrite
    TEST.run(test='gen 3 100 | store f',
             verification='load f',
             expected_out=[100, 101, 102])
    # Append
    TEST.run(test='gen 3 200 | store -a f',
             verification='load f',
             expected_out=[100, 101, 102, 200, 201, 202])
    # Append to undefined var
    TEST.run(test='gen 3 300 | store -a y',
             verification='load y',
             expected_out=[300, 301, 302])
    # Target is bound to something other than a reservoir
    TEST.run('f = 1')
    TEST.run(test='gen 3 | store f',
             verification='load f',
             expected_out=[0, 1, 2])
    TEST.run('f = 1')
    TEST.run(test='gen 3 | store -a f',
             expected_err='A stream cannot be appended')
    # Bad variable name
    TEST.run('gen 3 | store /tmp/storeload.test',
             expected_err='is not a Python identifier')


@timeit
def test_redirect_file():
    with TestDir(TEST.env) as testdir:
        # ------------------------ Test all the paths through Parser.pipelines() for files
        # file <
        TEST.run(test=f'gen 3 | write {testdir}/p1',
                 verification=f'{testdir}/p1 <',
                 expected_out=[0, 1, 2])
        # file < > file
        TEST.run(f'gen 3 | write {testdir}/p3')
        TEST.run(test=f'{testdir}/p3 < > {testdir}/p4',
                 verification=f'{testdir}/p4 <',
                 expected_out=[0, 1, 2])
        # file < >> file
        TEST.run(f'gen 3 | write {testdir}/p5')
        TEST.run(f'gen 3 | map (f: f + 100) | write {testdir}/p6')
        TEST.run(test=f'{testdir}/p5 < >> {testdir}/p7',
                 verification=f'{testdir}/p7 <',
                 expected_out=[0, 1, 2])
        TEST.run(test=f'{testdir}/p6 < >> {testdir}/p7',
                 verification=f'{testdir}/p7 <',
                 expected_out=[0, 1, 2, 100, 101, 102])
        # file < op_sequence
        TEST.run(f'gen 3 | write {testdir}/p8')
        TEST.run(test=f'{testdir}/p8 < map (f: int(f) + 100)',
                 expected_out=[100, 101, 102])
        # file < op_sequence > file
        TEST.run(f'gen 3 | write {testdir}/p10')
        TEST.run(test=f'{testdir}/p10 < map (f: int(f) + 100) > {testdir}/p11',
                 verification=f'{testdir}/p11 <',
                 expected_out=[100, 101, 102])
        # file < op_sequence >> file
        TEST.run(f'gen 3 | write {testdir}/p12')
        TEST.run(test=f'{testdir}/p12 < map (f: int(f) + 100) >> {testdir}/p13',
                 verification=f'{testdir}/p13 <',
                 expected_out=[100, 101, 102])
        TEST.run(test=f'{testdir}/p12 < map (f: int(f) + 1000) >> {testdir}/p13',
                 verification=f'{testdir}/p13 <',
                 expected_out=[100, 101, 102, 1000, 1001, 1002])
        # op_sequence -- tested adequately elsewhere
        # op_sequence > file
        TEST.run(test=f'gen 3 > {testdir}/p14',
                 verification=f'{testdir}/p14 <',
                 expected_out=[0, 1, 2])
        # op_sequence >> file
        TEST.delete_files(f'{testdir}/p15')
        TEST.run(test=f'gen 3 >> {testdir}/p15',
                 verification=f'{testdir}/p15 <',
                 expected_out=[0, 1, 2])
        TEST.run(test=f'gen 3 | map (f: int(f) + 100) >> {testdir}/p15',
                 verification=f'{testdir}/p15 <',
                 expected_out=[0, 1, 2, 100, 101, 102])
        # > file
        TEST.run(test=f'gen 6 | case (f: f % 2 == 0) (|> {testdir}/p16|) | select (f: False)',
                 verification=f'{testdir}/p16 <',
                 expected_out=[0, 2, 4])
        # >> file
        TEST.run(test=f'gen 6 | case (f: f % 2 == 0) (|>> {testdir}/p17|) | select (f: False)',
                 verification=f'{testdir}/p17 <',
                 expected_out=[0, 2, 4])
        TEST.run(test=f'gen 6 | case (f: f % 2 == 1) (|>> {testdir}/p17|) | select (f: False)',
                 verification=f'{testdir}/p17 <',
                 expected_out=[0, 2, 4, 1, 3, 5])
        # ---------------------------------------------------------------------
        # Ops that look confusingly like files from context
        # op <
        TEST.run(test='pwd <',
                 expected_err='No qualifying paths')
        # op > file
        version = marcel.version.VERSION
        TEST.run(test=f'version > {testdir}/o1',
                 verification=f'{testdir}/o1 < map (v: f"v{version}")',
                 expected_out=[f"v{version}"])
        # op >> file
        TEST.run(test=f'version >> {testdir}/o2',
                 verification=f'{testdir}/o2 < map (v: f"v{version}")',
                 expected_out=[f"v{version}"])
        TEST.run(test=f'version >> {testdir}/o2',
                 verification=f'{testdir}/o2 < map (v: f"v{version}")',
                 expected_out=[f"v{version}", f"v{version}"])
        # ---------------------------------------------------------------------
        # Store at end of top-level pipelines
        TEST.run(test=f'gen 5 > {testdir}/g5',
                 verification=f'read {testdir}/g5',
                 expected_out=[0, 1, 2, 3, 4])
        # Store at end of pipelines arg
        TEST.run(test=f'gen 10 | case (f: f % 2 == 0) (|map (f: f * 10) > {testdir}/e10x10|)',
                 verification=f'read {testdir}/e10x10',
                 expected_out=[0, 20, 40, 60, 80])
        # Store as the entire pipelines arg
        TEST.run(test=f'gen 10 | case (f: f % 2 == 0) (|> {testdir}/e10|)',
                 verification=f'read {testdir}/e10',
                 expected_out=[0, 2, 4, 6, 8])
        # Append
        TEST.run(test=f'gen 5 > {testdir}/g10',
                 verification=f'read {testdir}/g10',
                 expected_out=[0, 1, 2, 3, 4])
        TEST.run(test=f'gen 5 5 >> {testdir}/g10',
                 verification=f'read {testdir}/g10',
                 expected_out=[0, 1, 2, 3, 4, 5, 6, 7, 8, 9])
        # Load at beginning of top-level pipelines
        TEST.run(test=f'gen 4 > {testdir}/g4',
                 verification=f'{testdir}/g4 < map (f: -int(f))',
                 expected_out=[0, -1, -2, -3])
        # Load in pipelines arg
        TEST.run(f'gen 4 | map (f: (f, f * 10)) > {testdir}/x10')
        TEST.run(f'gen 4 | map (f: (f, f * 100)) > {testdir}/x100')
        TEST.run(f'{testdir}/x10 < map (f: eval(f)) | join (|{testdir}/x100 < map (f: eval(f))|)',
                 expected_out=[(0, 0, 0), (1, 10, 100), (2, 20, 200), (3, 30, 300)])
        # Bug 73
        TEST.run(f'gen 3 | map (f: (f, f*10)) > {testdir}/a')
        TEST.run(f'gen 3 | map (f: (f, f*100)) > {testdir}/b')
        TEST.run(f'gen 3 | map (f: (f, f*1000)) > {testdir}/c')
        TEST.run(f'{testdir}/a < (f: eval(f)) | join (|{testdir}/b < (f: eval(f))|) | join (|{testdir}/c < (f: eval(f))|)',
                 expected_out=[(0, 0, 0, 0), (1, 10, 100, 1000), (2, 20, 200, 2000)])
        # Bug 74
        TEST.delete_files(f'{testdir}/a', f'{testdir}/b', f'{testdir}/c', f'{testdir}/d')
        TEST.run(f'gen 3 | map (f: (f, f*10)) > {testdir}/a')
        TEST.run(f'gen 3 | map (f: (f, f*100)) > {testdir}/b')
        TEST.run(f'gen 3 | map (f: (f, f*1000)) > {testdir}/c')
        TEST.run(f'{testdir}/a < (f: eval(f)) | join (|{testdir}/b < (f: eval(f))|) | join (|{testdir}/c < (f: eval(f))|) > {testdir}/d')
        TEST.run(f'{testdir}/d <',
                 expected_out=[(0, 0, 0, 0), (1, 10, 100, 1000), (2, 20, 200, 2000)])
        # ---------------------------------------------------------------------
        # Erroneous syntax
        TEST.run(f'{testdir}/a >',
                 expected_err='excess tokens')
        TEST.run('gen 3 < (f: f)',
                 expected_err='excess tokens')


@timeit
def test_redirect_var():
    # ------------------------ Test all the paths through Parser.pipelines() for vars
    # var <$
    TEST.run(test='gen 3 | store p1',
             verification='p1 <$',
             expected_out=[0, 1, 2])
    # var <$ >$ var
    TEST.run('gen 3 | store p3')
    TEST.run(test='p3 <$ >$ p4',
             verification='p4 <$',
             expected_out=[0, 1, 2])
    # var <$ >>$ var
    TEST.run('gen 3 | store p5')
    TEST.run('gen 3 | (f: f + 100) | store p6')
    TEST.run('p5 <$ >>$ p7',
             verification='p7 <$',
             expected_out=[0, 1, 2])
    TEST.run('p6 <$ >>$ p7',
             verification='p7 <$',
             expected_out=[0, 1, 2, 100, 101, 102])
    # var <$ op_sequence
    TEST.run('gen 3 | store p8')
    TEST.run(test='p8 <$ map (f: f + 100)',
             expected_out=[100, 101, 102])
    # var <$ op_sequence >$ var
    TEST.run('gen 3 | store p10')
    TEST.run(test='p10 <$ map (f: f + 100) >$ p11',
             verification='p11 <$',
             expected_out=[100, 101, 102])
    # var <$ op_sequence >>$ var
    TEST.run('gen 3 | store p12')
    TEST.run(test='p12 <$ map (f: f + 100) >>$ p13',
             verification='p13 <$',
             expected_out=[100, 101, 102])
    TEST.run(test='p12 <$ map (f: f + 1000) >>$ p13',
             verification='p13 <$',
             expected_out=[100, 101, 102, 1000, 1001, 1002])
    # op_sequence -- tested adequately elsewhere
    # op_sequence >$ var
    TEST.run(test='gen 3 >$ p14',
             verification='p14 <$',
             expected_out=[0, 1, 2])
    # op_sequence >>$ var
    TEST.run(test='gen 3 >>$ p15',
             verification='p15 <$',
             expected_out=[0, 1, 2])
    TEST.run(test='gen 3 | map (f: f + 100) >>$ p15',
             verification='p15 <$',
             expected_out=[0, 1, 2, 100, 101, 102])
    # >$ var
    TEST.run(test='gen 6 | case (f: f % 2 == 0) (|>$ p16|) | select (f: False)',
             verification='p16 <$',
             expected_out=[0, 2, 4])
    # >>$ var
    TEST.run(test='gen 6 | case (f: f % 2 == 0) (|>>$ p17|) | select (f: False)',
             verification='p17 <$',
             expected_out=[0, 2, 4])
    TEST.run(test='gen 6 | case (f: f % 2 == 1) (|>>$ p17|) | select (f: False)',
             verification='p17 <$',
             expected_out=[0, 2, 4, 1, 3, 5])
    # ---------------------------------------------------------------------
    # Ops that look confusingly like files from context
    # op <$
    TEST.run(test='pwd <$',
             expected_err='Variable pwd is undefined')
    # op >$ var
    version = marcel.version.VERSION
    TEST.run(test='version >$ o1',
             verification='o1 <$ map (v: f"v{v}")',
             expected_out=[f"v{version}"])
    # op >>$ var
    TEST.run(test='version >>$ o2',
             verification='o2 <$ map (v: f"v{v}")',
             expected_out=[f"v{version}"])
    TEST.run(test='version >>$ o2',
             verification='o2 <$ map (v: f"v{v}")',
             expected_out=[f"v{version}", f"v{version}"])
    # ---------------------------------------------------------------------
    # Store at end of top-level pipelines
    TEST.run(test='gen 5 >$ g5',
             verification='load g5',
             expected_out=[0, 1, 2, 3, 4])
    # Store at end of pipelines arg
    TEST.run(test='gen 10 | case (f: f % 2 == 0) (|map (f: f * 10) >$ e10x10|)',
             verification='load e10x10',
             expected_out=[0, 20, 40, 60, 80])
    # Store as the entire pipelines arg
    TEST.run(test='gen 10 | case (f: f % 2 == 0) (|>$ e10|)',
             verification='load e10',
             expected_out=[0, 2, 4, 6, 8])
    # Append
    TEST.run(test='gen 5 >$ g10',
             verification='load g10',
             expected_out=[0, 1, 2, 3, 4])
    TEST.run(test='gen 5 5 >>$ g10',
             verification='load g10',
             expected_out=[0, 1, 2, 3, 4, 5, 6, 7, 8, 9])
    # Load at beginning of top-level pipelines
    TEST.run(test='gen 4 >$ g4',
             verification='g4 <$ map (f: -f)',
             expected_out=[0, -1, -2, -3])
    # Load in pipelines arg
    TEST.run('gen 4 | map (f: (f, f * 10)) >$ x10')
    TEST.run('gen 4 | map (f: (f, f * 100)) >$ x100')
    TEST.run('x10 <$ join (|x100 <$|)',
             expected_out=[(0, 0, 0), (1, 10, 100), (2, 20, 200), (3, 30, 300)])
    # Bug 73
    TEST.run('gen 3 | map (f: (f, f*10)) >$ a')
    TEST.run('gen 3 | map (f: (f, f*100)) >$ b')
    TEST.run('gen 3 | map (f: (f, f*1000)) >$ c')
    TEST.run('a <$ join (|b <$|) | join (|c <$|)',
             expected_out=[(0, 0, 0, 0), (1, 10, 100, 1000), (2, 20, 200, 2000)])
    # Bug 74
    TEST.run('gen 3 | map (f: (f, f*10)) >$ a')
    TEST.run('gen 3 | map (f: (f, f*100)) >$ b')
    TEST.run('gen 3 | map (f: (f, f*1000)) >$ c')
    TEST.run('a <$ join (|b <$|) | join (|c <$|) >$ d')
    TEST.run('d <$',
             expected_out=[(0, 0, 0, 0), (1, 10, 100, 1000), (2, 20, 200, 2000)])
    # Erroneous syntax
    # Var undefined
    TEST.run('env -d z')
    TEST.run('z >$',
             expected_err='excess tokens')
    # Var defined
    TEST.run('z = (| gen 3 |)')
    TEST.run('z >$',
             expected_err='followed by excess tokens')
    TEST.run('gen 3 < (f: f)',
             expected_err='excess tokens')


@timeit
def test_loop():
    TEST.run('loop (0) [select (f: f < 3) | emit | map (f: f + 1)]',
             expected_out=[0, 1, 2])
    TEST.run('loop ((0, 1)) [select (f, y: f < 1000000) | emit | map (f, y: (y, f + y))] | map (f, y: f)',
             expected_out=[0, 1, 1, 2, 3, 5, 8, 13, 21,
                           34, 55, 89, 144, 233, 377, 610,
                           987, 1597, 2584, 4181, 6765, 10946,
                           17711, 28657, 46368, 75025, 121393,
                           196418, 317811, 514229, 832040])
    # Repeated execution, piping in initial value
    TEST.run('gen 3 | loop [select (n: n >= 0) | emit | map (n: n - 1)]',
             expected_out=[0, 1, 0, 2, 1, 0])
    # Bug 70
    TEST.run('p = [loop (0) [select (f: f < 5) | emit | map (f: f+1)]')
    TEST.run('p',
             expected_out=[0, 1, 2, 3, 4])


@timeit
def test_case():
    TEST.run(test='gen 5 1 | case (f: f < 3) (| (f: (100 * f)) |) '
                  '               (f: f > 3) (| (f: (1000 * f)) |)',
             expected_out=[100, 200, 4000, 5000])
    TEST.run(test='gen 5 1 | case (f: f < 3) (| (f: (100 * f)) |) (| (f: (-f)) |)',
             expected_out=[100, 200, -3, -4, -5])
    TEST.run(test='gen 5 1 | case (f: f == 1) (| (f: "one") |) '
                  '               (f: f == 2) (| (f: "two") |) '
                  '               (f: f == 3) (| (f: "three") |) ',
             expected_out=['one', 'two', 'three'])
    # Just the default branch isn't allowed
    TEST.run(test='gen 5 1 | case (| (f: (100 * f)) |)',
             expected_err='case requires at least 2 arguments')
    # Function/pipeline confusion
    TEST.run(test='gen 5 1 | case (| (f: (100 * f)) |) (| (f: (-f)) |) (f: f < 3)',
             expected_err='Expected function')
    TEST.run(test='gen 5 1 | case (f: f < 3) (123)',
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
        TEST.run(f'cd {testdir}')
        TEST.run('ls f1.csv f3.txt | read',
                 expected_out=['1,2.3,ab',
                               '2,3.4,xy',
                               '3,4.5,"m,n"',
                               'hello,world',
                               'goodbye'])
        # Files with labels
        TEST.run(f'cd {testdir}')
        TEST.run('ls f1.csv f3.txt | read -l | map (path, line: (str(path), line))',
                 expected_out=[('f1.csv', '1,2.3,ab'),
                               ('f1.csv', '2,3.4,xy'),
                               ('f1.csv', '3,4.5,"m,n"'),
                               ('f3.txt', 'hello,world'),
                               ('f3.txt', 'goodbye')])
        # CSV
        TEST.run(f'cd {testdir}')
        TEST.run('ls f1.csv | read -c',
                 expected_out=[('1', '2.3', 'ab'),
                               ('2', '3.4', 'xy'),
                               ('3', '4.5', 'm,n')])
        # CSV with labels
        TEST.run(f'cd {testdir}')
        TEST.run('ls f1.csv | read -cl | map (f, x, y, z: (str(f), x, y, z))',
                 expected_out=[('f1.csv', '1', '2.3', 'ab'),
                               ('f1.csv', '2', '3.4', 'xy'),
                               ('f1.csv', '3', '4.5', 'm,n')])
        # TSV
        TEST.run(f'cd {testdir}')
        TEST.run('ls f2.tsv | read -t',
                 expected_out=[('1', '2.3', 'ab'),
                               ('2', '3.4', 'xy')])
        # TSV with labels
        TEST.run(f'cd {testdir}')
        TEST.run('ls f2.tsv | read -tl | map (f, x, y, z: (str(f), x, y, z))',
                 expected_out=[('f2.tsv', '1', '2.3', 'ab'),
                               ('f2.tsv', '2', '3.4', 'xy')])
        # --pickle testing is done in test_write()
        # Filenames on commandline
        TEST.run(f'cd {testdir}')
        TEST.run('read f1.csv',
                 expected_out=['1,2.3,ab', '2,3.4,xy', '3,4.5,"m,n"'])
        TEST.run('read f?.*',
                 expected_out=['1,2.3,ab', '2,3.4,xy', '3,4.5,"m,n"',
                               '1\t2.3\tab', '2\t3.4\txy',
                               'hello,world', 'goodbye'])
        # Flags inherited from FilenamesOp
        TEST.run(test=f'read -lr {testdir}/f[1-3]* | (f, l: (str(f), l))',
                 expected_out=[('f1.csv', '1,2.3,ab'),
                               ('f1.csv', '2,3.4,xy'),
                               ('f1.csv', '3,4.5,"m,n"'),
                               ('f2.tsv', '1\t2.3\tab'),
                               ('f2.tsv', '2\t3.4\txy'),
                               ('f3.txt', 'hello,world'),
                               ('f3.txt', 'goodbye')])
        # File does not exist
        TEST.run(test=f'read {testdir}/nosuchfile',
                 expected_err='No qualifying paths')
        # directory
        TEST.run(test=f'read -0 {testdir}',
                 expected_out=[])
        # symlink
        os.system(f'ln -s {testdir}/f1.csv {testdir}/symlink_f1.csv')
        TEST.run(f'read {testdir}/symlink_f1.csv',
                 expected_out=['1,2.3,ab',
                               '2,3.4,xy',
                               '3,4.5,"m,n"'])
        # Column headings
        TEST.run(f'read -h {testdir}/f3.txt',
                 expected_err='-h|--headings can only be specified with')
        TEST.run(f'read -hp {testdir}/f3.txt',
                 expected_err='-h|--headings can only be specified with')
        TEST.run(f'read -s {testdir}/f3.txt',
                 expected_err='-s|--skip-headings can only be specified with')
        TEST.run(f'read -sp {testdir}/f3.txt',
                 expected_err='-s|--skip-headings can only be specified with')
        TEST.run(f'read -hs {testdir}/f3.txt',
                 expected_err='Cannot specify more than one of')
        TEST.run(f'read -ch {testdir}/headings.csv | (t: (t.c1, t.c2, t.c3))',
                 expected_out=[('a', 'b', 'c'),
                               ('d', 'e', 'f')])
        TEST.run(f'read -chl {testdir}/headings.csv | (t: (str(t.LABEL), t.c1, t.c2, t.c3))',
                 expected_out=[('headings.csv', 'a', 'b', 'c'),
                               ('headings.csv', 'd', 'e', 'f')])
        TEST.run(f'read -cs {testdir}/headings.csv',
                 expected_out=[('a', 'b', 'c'),
                               ('d', 'e', 'f')])
        TEST.run(f'read -ch {testdir}/headings_tricky_data.csv | (t: (t.c1, t.c2, t.c3))',
                 expected_out=[('a', 'b', None),
                               Error('Incompatible with headings'),
                               ('', '', None)])
        TEST.run(f'read -ch {testdir}/headings_fixable.csv | (t: (t.c_1, t.c__2, t.c_3_))',
                 expected_out=[('a', 'b', 'c'),
                               ('d', 'e', 'f')])
        TEST.run(f'read -ch {testdir}/headings_unfixable_1.csv',
                 expected_out=[Error('Cannot generate identifiers from headings'),
                               ('a', 'b', 'c'),
                               ('d', 'e', 'f')])
        TEST.run(f'read -ch {testdir}/headings_unfixable_2.csv',
                 expected_out=[Error('Cannot generate identifiers from headings'),
                               ('a', 'b', 'c'),
                               ('d', 'e', 'f')])
    # Resume after error
    with TestDir(TEST.env) as testdir:
        TEST.run(f'cd {testdir}')
        TEST.run('echo aaa > a')
        TEST.run('echo aaa > aa')
        TEST.run('echo bbb > b')
        TEST.run('echo ccc > c')
        TEST.run('echo ccc > cc')
        TEST.run('echo ddd > d')
        TEST.run('chmod 000 aa b cc d')
        TEST.run('read -l * | (f, line: (f.name, line))',
                 expected_out=[('a', 'aaa'),
                               ('c', 'ccc')])
        TEST.run('read -l a* c* | (f, line: (f.name, line))',
                 expected_out=[('a', 'aaa'),
                               ('c', 'ccc')])
        TEST.run('ls -f * | read -l | (f, line: (f.name, line))',
                 expected_out=[('a', 'aaa'),
                               ('c', 'ccc')])
        TEST.run('ls -f a* c* | read -l | (f, line: (f.name, line))',
                 expected_out=[('a', 'aaa'),
                               ('c', 'ccc')])


@timeit
def test_intersect():
    TEST.reset_environment()
    # Empty inputs
    TEST.run('gen 1 | select (*f: False) >$ empty')
    TEST.run('gen 3 | intersect (|empty <$|)',
             expected_out=[])
    TEST.run('empty <$ intersect (|empty <$|)',
             expected_out=[])
    TEST.run('empty <$ intersect (|gen 3|)',
             expected_out=[])
    # Non-empty inputs, empty intersection
    TEST.run('gen 3 | intersect (|gen 3|)',
             expected_out=[0, 1, 2])
    TEST.run('gen 3 | intersect (|gen 1 1|)',
             expected_out=[1])
    # Duplicates
    TEST.run('gen 5 | map (f: [f] * f) | expand >$ a')
    TEST.run('gen 5 | map (f: [f] * 2) | expand >$ b')
    TEST.run('a <$ intersect (|b <$|) | sort',
             expected_out=[1, 2, 2, 3, 3, 4, 4])
    # Composite elements
    TEST.run('gen 3 2 | '
             'map (f: [(f, f * 100)] * f) | '
             'expand | '
             'intersect (|gen 3 2 | '
             '           map (f: [(f, f * 100)] * 3) | '
             '           expand|) |'
             'sort',
             expected_out=[(2, 200), (2, 200),
                           (3, 300), (3, 300), (3, 300),
                           (4, 400), (4, 400), (4, 400)])
    # Lists cannot be hashed
    TEST.run('gen 2 | (f: (f, (f, f))) | intersect (|gen 2 1 | (f: (f, (f, f)))|)',
             expected_out=[(1, (1, 1))])
    TEST.run('gen 2 | (f: (f, [f, f])) | intersect (|gen 2 1 | (f: (f, (f, f)))|)',
             expected_err='not hashable')
    TEST.run('gen 2 | (f: (f, (f, f))) | intersect (|gen 2 1 | (f: (f, [f, f]))|)',
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
    TEST.run('x0 = (| (["f"] * 0) | expand |)')
    TEST.run('x1 = (| (["f"] * 1) | expand |)')
    TEST.run('x2 = (| (["f"] * 2) | expand |)')
    TEST.run('x3 = (| (["f"] * 3) | expand |)')
    TEST.run('x1 | intersect x2', expected_out=['f'])
    TEST.run('x2 | intersect x1', expected_out=['f'])
    TEST.run('x1 | intersect x3', expected_out=['f'])
    TEST.run('x3 | intersect x1', expected_out=['f'])
    TEST.run('x2 | intersect x3', expected_out=['f', 'f'])
    TEST.run('x3 | intersect x2', expected_out=['f', 'f'])
    TEST.run('x1 | intersect x2 x3', expected_out=['f'])
    TEST.run('x1 | intersect x3 x2', expected_out=['f'])
    TEST.run('x2 | intersect x1 x3', expected_out=['f'])
    TEST.run('x2 | intersect x3 x1', expected_out=['f'])
    TEST.run('x3 | intersect x1 x2', expected_out=['f'])
    TEST.run('x3 | intersect x2 x1', expected_out=['f'])
    TEST.run('x0 | intersect x2 x3', expected_out=[])
    TEST.run('x2 | intersect x3 x0', expected_out=[])


@timeit
def test_union():
    TEST.reset_environment()
    # Empty inputs
    TEST.run('gen 1 | select (*f: False) >$ empty')
    TEST.run('empty <$ union (|empty <$|)',
             expected_out=[])
    TEST.run('gen 3 | union (|empty <$|) | sort',
             expected_out=[0, 1, 2])
    TEST.run('empty <$ union (|gen 3|) | sort',
             expected_out=[0, 1, 2])
    # Non-empty inputs4
    TEST.run('gen 3 | union (|gen 3 100|) | sort',
             expected_out=[0, 1, 2, 100, 101, 102])
    # Duplicates
    TEST.run('gen 3 | union (|gen 3|) | sort',
             expected_out=[0, 0, 1, 1, 2, 2])
    # Composite elements
    TEST.run('gen 4 | map (f: (f, f*100)) | union (|gen 4 2 | map (f: (f, f*100))|) | sort',
             expected_out=[(0, 0), (1, 100), (2, 200), (2, 200), (3, 300), (3, 300), (4, 400), (5, 500)])
    # Multiple inputs
    TEST.run('gen 3 100 | union (|gen 3 200|) | sort',
             expected_out=[100, 101, 102, 200, 201, 202])
    TEST.run('gen 3 100 | union (|gen 3 200|) (|gen 3 300|) | sort',
             expected_out=[100, 101, 102, 200, 201, 202, 300, 301, 302])


@timeit
def test_filter():
    TEST.run('gen 6 | (f: (f, f)) | expand | filter (| gen 3|)',
             expected_out=[0, 0, 1, 1, 2, 2])
    TEST.run('gen 6 | (f: (f, f)) | expand | filter -k (| gen 3|)',
             expected_out=[0, 0, 1, 1, 2, 2])
    TEST.run('gen 6 | (f: (f, f)) | expand | filter --keep (| gen 3|)',
             expected_out=[0, 0, 1, 1, 2, 2])
    TEST.run('gen 6 | (f: (f, f)) | expand | filter -d (| gen 3|)',
             expected_out=[3, 3, 4, 4, 5, 5])
    TEST.run('gen 6 | (f: (f, f)) | expand | filter --discard (| gen 3|)',
             expected_out=[3, 3, 4, 4, 5, 5])
    TEST.run('gen 6 | (f: (f, f)) | filter -c (f, y: f) (| gen 3 |)',
             expected_out=[(0, 0), (1, 1), (2, 2)])
    TEST.run('gen 6 | (f: (f, f)) | filter -c (f, y: f) -k (| gen 3 |)',
             expected_out=[(0, 0), (1, 1), (2, 2)])
    TEST.run('gen 6 | (f: (f, f)) | filter -c (f, y: f) -d (| gen 3 |)',
             expected_out=[(3, 3), (4, 4), (5, 5)])
    TEST.run('gen 6 | filter -d -k (| gen 3 |)',
             expected_err='Cannot specify more than one')


@timeit
def test_difference():
    TEST.reset_environment()
    # Empty inputs
    TEST.run('gen 1 | select (*f: False) >$ empty')
    TEST.run('empty <$ difference (|empty <$|)',
             expected_out=[])
    TEST.run('gen 3 | difference (|empty <$|) | sort',
             expected_out=[0, 1, 2])
    TEST.run('empty <$ difference (|gen 3|)',
             expected_out=[])
    # Non-empty inputs
    TEST.run('gen 6 | difference (|gen 6 100|) | sort',
             expected_out=[0, 1, 2, 3, 4, 5])
    TEST.run('gen 6 | difference (|gen 6|) | sort',
             expected_out=[])
    TEST.run('gen 6 | difference (|gen 6 3|) | sort',
             expected_out=[0, 1, 2])
    # Duplicates
    TEST.run('gen 5 | map (f: [f] * f) | expand | difference (|gen 5 | map (f: [f] * 2) | expand|) | sort',
             expected_out=[3, 4, 4])
    # Composite elements
    TEST.run('gen 5 2 | '
             'map (f: [(f, f*100)] * f) | '
             'expand | difference (|gen 5 2 | '
             '                     map (f: [(f, f*100)] * 3) | '
             '                     expand|) | '
             'sort',
             expected_out=[(4, 400), (5, 500), (5, 500), (6, 600), (6, 600), (6, 600)])
    # Lists aren't hashable
    TEST.run('gen 3 | (f: (f, (f, f))) | difference (|gen 2 | (f: (f, (f, f)))|)',
             expected_out=[(2, (2, 2))])
    TEST.run('gen 3 | (f: (f, [f, f])) | difference (|gen 2 | (f: (f, (f, f)))|)',
             expected_err='not hashable')
    TEST.run('gen 3 | (f: (f, (f, f))) | difference (|gen 2 | (f: (f, [f, f]))|)',
             expected_err='not hashable')


@timeit
def test_args():
    TEST.reset_environment()
    # gen
    TEST.run('gen 5 1 | args (|n: gen (n)|) | map (f: -f)',
             expected_out=[0, 0, -1, 0, -1, -2, 0, -1, -2, -3, 0, -1, -2, -3, -4])
    TEST.run('gen 6 1 | args (|count, start: gen (count) (start)|)',
             expected_out=[2, 4, 5, 6, 6, 7, 8, 9, 10])
    # ls
    with TestDir(TEST.env) as testdir:
        TEST.run(f'mkdir {testdir}/d1')
        TEST.run(f'mkdir {testdir}/d2')
        TEST.run(f'mkdir {testdir}/d3')
        TEST.run(f'touch {testdir}/d1/f1')
        TEST.run(f'touch {testdir}/d2/f2')
        TEST.run(f'touch {testdir}/d3/f3')
        TEST.run(f'cd {testdir}')
        TEST.run(f'ls -d | args (|d: ls -f (d) |) | map (f: f.name)',
                 expected_out=['f1', 'f2', 'f3'])
        TEST.run(f'touch a_file')
        TEST.run(f'touch "a file"')
        TEST.run(f'touch "a file with a \' mark"')
        TEST.run(f'rm -rf d')
        TEST.run(f'mkdir d')
        TEST.run(test=f'ls -f | args --all (|files: mv -t d (quote_files(*files)) |)',
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
        TEST.run('gen 3 | args (|f: (((1, 2), (3, 4), (5, 6))) | expand (f)|)',
                 expected_out=[(1, (3, 4), (5, 6)), (2, (3, 4), (5, 6)),
                               ((1, 2), 3, (5, 6)), ((1, 2), 4, (5, 6)),
                               ((1, 2), (3, 4), 5), ((1, 2), (3, 4), 6)])
        # sql
        if SQL:
            TEST.run('sql "drop table if exists t" | select (f: False)')
            TEST.run('sql "create table t(f int)" | select (f: False)')
            TEST.run(test='gen 5 | args (|f: sql "insert into t values(%s)" (f)|)',
                     verification='sql "select * from t order by f"',
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
        TEST.run('gen 10 | args --all (|f: ("".join([str(n) for n in f]))|)',
                 expected_out=['0123456789'])
        # no input to args
        TEST.run('gen 3 | select (f: False) | args (|n: map (f: -f)|)',
                 expected_out=[])
        TEST.run('gen 3 | select (f: False) | args --all (|n: map (f: -f)|)',
                 expected_out=[])
        # negative testing
        TEST.run('gen 3 | args --all (|f, y: (123) |)',
                 expected_err="With -a|--all option, the pipelines must have exactly one parameter.")
        TEST.run('gen 3 | args --all (| (123) |)',
                 expected_err="With -a|--all option, the pipelines must have exactly one parameter.")
        TEST.run('gen 3 | args (| (123) |)',
                 expected_err="The args pipelines must be parameterized")
        # Bug 94
        TEST.run('gen 4 1 | args (|n: gen (n)|) | window (f: f == 0)',
                 expected_out=[0, (0, 1), (0, 1, 2), (0, 1, 2, 3)])
        # Bug 116
        TEST.run('g = (|n: gen (n)|)')
        TEST.run('gen 3 1 | args (|n: g (n)|)',
                 expected_out=[0, 0, 1, 0, 1, 2])
        # Bug 167
        with TestDir(TEST.env) as testdir:
            os.system(f'rm -rf {testdir}/hello')
            os.system(f'echo hello > {testdir}/hello')
            os.system(f'echo hello >> {testdir}/hello')
        # Bug 237
        TEST.run('gen 3 | args -a (f: (f))',
                 expected_err='must be a Pipeline')


@timeit
def test_env():
    TEST.reset_environment()
    # Env vars defined by user
    TEST.run(test='env v1',
             expected_err='v1 is undefined')
    TEST.run(test='v2 = asdf',
             verification='env v2',
             expected_out=[('v2', 'asdf')])
    TEST.run(test='env -d v2',
             expected_out=[('v2', 'asdf')])
    TEST.run(test='env -d v2',
             expected_out=[])
    TEST.run(test='v3xyz = 1')
    TEST.run(test='v3xyzw = 2')
    TEST.run(test='v3xzw = 3')
    TEST.run(test='env -p xyz | sort',
             expected_out=[('v3xyz', '1'),
                           ('v3xyzw', '2')])
    # Env defined by startup
    TEST.run(test='env NODE1',
             expected_out=[('NODE1', '127.0.0.1')])
    TEST.run(test='env --delete NODE1',
             expected_err='cannot be modified or deleted')
    TEST.run(test='NODE1 = asdf',
             expected_err='cannot be modified or deleted')
    # Env defined by marcel
    TEST.run(test='env USER',
             expected_out=[('USER', getpass.getuser())])
    TEST.run(test='USER = asdf',
             expected_err='cannot be modified or deleted')
    TEST.run(test='env -d USER',
             expected_err='cannot be modified or deleted')
    # Env inherited from host
    TEST.run(test='env -o asdfasdf',
             expected_err='is undefined')
    TEST.run(test='env -o SHELL',
             expected_out=[('SHELL', os.getenv('SHELL'))])
    TEST.run(test='env -o -p SHELL | select (k, v: k == "SHELL")',
             expected_out=[('SHELL', os.getenv('SHELL'))])
    TEST.run(test='env -o -d SHELL',
             expected_err='Cannot specify more than one of')


@timeit
def test_pos():
    TEST.run('gen 5 | (f: (f, pos())) | select (f, p1: f % 2 == 0) | (f, p1: (f, p1, pos()))',
             expected_out=[(0, 0, 0), (2, 2, 1), (4, 4, 2)])

@timeit
def test_json():
    def test_json_parse():
        # Scalars
        TEST.run("""('"a"') | (j: json_parse(j))""",
                 expected_out=['a'])
        TEST.run("""('123') | (j: json_parse(j))""",
                 expected_out=[123])
        TEST.run("""('4.5') | (j: json_parse(j))""",
                 expected_out=[4.5])
        TEST.run("""('true') | (j: json_parse(j))""",
                 expected_out=[True])
        TEST.run("""('false') | (j: json_parse(j))""",
                 expected_out=[False])
        TEST.run("""('null') | (j: json_parse(j))""",
                 expected_out=[None])
        TEST.run("""('abc') | (j: json_parse(j))""",  # Unquoted string
                 expected_out=[Error('Expecting value')])
        TEST.run("""('--3') | (j: json_parse(j))""",  # Malformed integer
                 expected_out=[Error('Expecting value')])
        TEST.run("""('1.2.3') | (j: json_parse(j))""",  # Malformed float
                 expected_out=[Error('Extra data')])
        # Structures (flat)
        TEST.run("""('[]') | (j: json_parse(j))""",
                 expected_out=[[]])
        TEST.run("""('["a", 1]') | (j: json_parse(j))""",
                 expected_out=[['a', 1]])
        TEST.run("""('{}') | (j: json_parse(j))""",
                 expected_out=[{}])
        TEST.run("""('{"a": 1, "b": 2, "c c": 3.3}') | (j: json_parse(j))""",
                 expected_out=[{'a': 1, 'b': 2, 'c c': 3.3}])
        # Structures (nested)
        TEST.run("""('["a", {"b": 2, "c": [3, 4, {"d": 5, "e": [], "f": {}}]}]') | (j: json_parse(j))""",
                 expected_out=[['a', {'b': 2, 'c': [3, 4, {'d': 5, 'e': [], 'f': {}}]}]])
        TEST.run("""('{"q": ["a", {"b": 2, "c": [3, 4, {"d": 5, "e": [], "f": {}}]}]}') | (j: json_parse(j))""",
                 expected_out=[{'q': ['a', {'b': 2, 'c': [3, 4, {'d': 5, 'e': [], 'f': {}}]}]}])
        TEST.run("""('[1, 2') | (j: json_parse(j))""",  # Malformed list
                 expected_out=[Error("Expecting ',' delimiter")])
        TEST.run("""('[1, ') | (j: json_parse(j))""",  # Malformed list
                 expected_out=[Error("Expecting value")])
        TEST.run("""('[1, ]') | (j: json_parse(j))""",  # Malformed list
                 expected_out=[Error("Expecting value")])
        TEST.run("""('{"a": 1,}') | (j: json_parse(j))""",  # Malformed dict
                 expected_out=[Error("Expecting property name")])
        TEST.run("""('{"a": 1') | (j: json_parse(j))""",  # Malformed dict
                 expected_out=[Error("delimiter: ")])
        TEST.run("""('{"a", 1}') | (j: json_parse(j))""",  # Malformed dict
                 expected_out=[Error("delimiter: ")])
        # Structure access
        TEST.run("""('["a", {"b": 2, "c": [3, 4, {"d": 5, "e": [], "f": {}, "g g": 7.7}]}]') 
        | (j: json_parse(j)) 
        | (*j: (j[0], j[1].b, j[1].c[1], j[1].c[2].d, j[1].c[2]['g g']))""",
                 expected_out=[('a', 2, 4, 5, 7.7)])
        # Broken JSON

    def test_json_format():
        # Scalars
        TEST.run("""(['a']) | (j: json_format(j))""",
                 expected_out=['"a"'])
        TEST.run("""([123]) | (j: json_format(j))""",
                 expected_out=['123'])
        TEST.run("""([4.5]) | (j: json_format(j))""",
                 expected_out=['4.5'])
        TEST.run("""([True]) | (j: json_format(j))""",
                 expected_out=['true'])
        TEST.run("""([False]) | (j: json_format(j))""",
                 expected_out=['false'])
        TEST.run("""([None]) | (j: json_format(j))""",
                 expected_out=['null'])
        TEST.run("""(['a]) | (j: json_format(j))""",
                 expected_err='Not a python string')
        # Structures (flat)
        TEST.run("""([]) | (*j: json_format(j))""",
                 expected_out=['[]'])
        TEST.run("""(['a', 1]) | (*j: json_format(j))""",
                 expected_out=['["a", 1]'])
        TEST.run("""({}) | (j: json_format(j))""",
                 expected_out=['{}'])
        TEST.run("""({'a': 1, 'b': 2, 'c c': 3.3}) | (j: json_format(j))""",
                 expected_out=['{"a": 1, "b": 2, "c c": 3.3}'])
        # Structures (nested)
        TEST.run("""(['a', {'b': 2, 'c': [3, 4, {'d': 5, 'e': [], 'f': {}}]}]) | (*j: json_format(j))""",
                 expected_out=["""["a", {"b": 2, "c": [3, 4, {"d": 5, "e": [], "f": {}}]}]"""])
        TEST.run("""({'q': ['a', {'b': 2, 'c': [3, 4, {'d': 5, 'e': [], 'f': {}}]}]}) | (j: json_format(j))""",
                 expected_out=["""{"q": ["a", {"b": 2, "c": [3, 4, {"d": 5, "e": [], "f": {}}]}]}"""])
        # Format anything with a __dict__

    test_json_parse()
    test_json_format()


@timeit
def test_struct():
    TEST.run('gen 3 | (f: o(f=f, y=f+1)) | (o: o.f + o.y)',
             expected_out=[1, 3, 5])


@timeit
def test_cast():
    TEST.run('gen 3 | cast str | (s: f"<<<{s}>>>")',
             expected_out=['<<<0>>>', '<<<1>>>', '<<<2>>>'])
    TEST.run('gen 3 | cast str | cast float',
             expected_out=[0.0, 1.0, 2.0])
    TEST.run('gen 3 | cast float float',
             expected_out=[0.0, 1.0, 2.0])
    TEST.run('gen 3 | (f: (f, f, f)) | cast float str',
             expected_out=[(0.0, '0', 0),
                           (1.0, '1', 1),
                           (2.0, '2', 2)])
    TEST.run('gen 1 | (f: (f, f, f)) | cast float str | (a, b, c: (type(a), type(b), type(c)))',
             expected_out=[(float, str, int)])
    TEST.run('((None, None, None)) | cast str float',
             expected_out=[(None, None, None)])
    # Errors
    # Not defined
    TEST.run('gen 1 | cast asdf',
             expected_err='Not a valid type name')
    # A marcel function
    TEST.run('gen 1 | cast map',
             expected_out=[Error('map')])
    # A python function
    TEST.run('gen 1 | cast list',
             expected_out=[Error('list')])


@timeit
def test_upload():
    with TestDir(TEST.env) as testdir:
        os.system(f'mkdir {testdir}/source')
        os.system(f'touch {testdir}/source/a {testdir}/source/b "{testdir}/source/a b"')
        os.system(f'mkdir {testdir}/dest')
        # No qualifying paths
        TEST.run(f'upload CLUSTER1 {testdir}/dest /nosuchfile',
                 expected_err='No qualifying paths')
        # Qualifying paths exist but insufficient permission to read
        os.system(f'sudo touch {testdir}/nope1')
        os.system(f'sudo rm {testdir}/nope?')
        os.system(f'touch {testdir}/nope1')
        os.system(f'touch {testdir}/nope2')
        os.system(f'chmod 000 {testdir}/nope?')
        TEST.run(f'upload CLUSTER1 {testdir}/dest {testdir}/nope1',
                 expected_out=[Error('nope1: Permission denied')])
        TEST.run(f'upload CLUSTER1 {testdir}/dest {testdir}/nope?',
                 expected_out=[Error('Permission denied'),
                               Error('Permission denied')])
        # Target dir must be absolute
        TEST.run(f'upload CLUSTER1 dest {testdir}/source/a',
                 expected_err='Target directory must be absolute: dest')
        # There must be at least one source
        TEST.run(f'upload CLUSTER1 {testdir}/dest',
                 expected_err='No qualifying paths')
        # Copy fully-specified filenames
        TEST.run(test=f'upload CLUSTER1 {testdir}/dest {testdir}/source/a {testdir}/source/b',
                 verification=f'ls -f {testdir}/dest | (f: f.name)',
                 expected_out=['a', 'b'])
        os.system(f'rm {testdir}/dest/*')
        # Filename with spaces
        TEST.run(test=f'upload CLUSTER1 {testdir}/dest "{testdir}/source/a b"',
                 verification=f'ls -f {testdir}/dest | (f: f.name)',
                 expected_out=['a b'])
        os.system(f'rm {testdir}/dest/*')
        # Wildcard
        TEST.run(test=f'upload CLUSTER1 {testdir}/dest {testdir}/source/a*',
                 verification=f'ls -f {testdir}/dest | (f: f.name)',
                 expected_out=['a', 'a b'])
        os.system(f'rm {testdir}/dest/*')


@timeit
def test_download():
    with TestDir(TEST.env) as testdir:
        node1 = TEST.env.getvar("NODE1")
        node2 = TEST.env.getvar("NODE2")
        os.system(f'mkdir {testdir}/source')
        os.system(f'touch {testdir}/source/a {testdir}/source/b "{testdir}/source/a b"')
        os.system(f'rm -rf {testdir}/dest')
        os.system(f'mkdir {testdir}/dest')
        # No qualifying paths
        TEST.run(f'download {testdir}/dest CLUSTER2 /nosuchfile',
                 expected_out=[Error('No such file or directory'), Error('No such file or directory')])
        # Qualifying paths exist but insufficient permission to read
        os.system(f'sudo touch {testdir}/nope1')
        os.system(f'sudo rm {testdir}/nope?')
        os.system(f'touch {testdir}/nope1')
        os.system(f'touch {testdir}/nope2')
        os.system(f'chmod 000 {testdir}/nope?')
        TEST.run(f'download {testdir}/dest CLUSTER2 {testdir}/nope1',
                 expected_out=[Error('Permission denied'), Error('Permission denied')])
        TEST.run(f'download {testdir}/dest CLUSTER2 {testdir}/nope?',
                 expected_out=[Error('Permission denied'), Error('Permission denied'),
                               Error('Permission denied'), Error('Permission denied')])
        # There must be at least one source specified (regardless of what actually exists remotely)
        TEST.run(f'download {testdir}/dest CLUSTER2',
                 expected_err='No remote files specified')
        # Copy fully-specified filenames
        TEST.run(test=f'download {testdir}/dest CLUSTER2 {testdir}/source/a {testdir}/source/b',
                 verification=f'ls -fr {testdir}/dest | (f: f.relative_to("{testdir}/dest")) | sort',
                 expected_out=[f'{node1}/a', f'{node1}/b', f'{node2}/a', f'{node2}/b'])
        # Leave files in place, delete some of them, try downloading again
        os.system(f'rm -rf {testdir}/dest/{node1}')
        os.system(f'rm -rf {testdir}/dest/{node2}/*')
        TEST.run(test=f'download {testdir}/dest CLUSTER2 {testdir}/source/a {testdir}/source/b',
                 verification=f'ls -fr {testdir}/dest | (f: f.relative_to("{testdir}/dest")) | sort',
                 expected_out=[f'{node1}/a', f'{node1}/b', f'{node2}/a', f'{node2}/b'])
        os.system(f'rm -rf {testdir}/dest/*')
        # Filename with spaces
        TEST.run(test=f'download {testdir}/dest CLUSTER2 "{testdir}/source/a\\ b"',
                 verification=f'ls -fr {testdir}/dest | (f: f.relative_to("{testdir}/dest")) | sort',
                 expected_out=[f'{node1}/a b', f'{node2}/a b'])
        os.system(f'rm -rf {testdir}/dest/*')
        # # Relative directory
        # TEST.run('cd /tmp')
        # TEST.run(test='download dest jao /tmp/source/a /tmp/source/b',
        #          verification='ls -f /tmp/dest | (f: f.name)',
        #          expected_out=['a', 'b'])
        # os.system('rm /tmp/dest/*')
        # Wildcard
        TEST.run(test=f'download {testdir}/dest CLUSTER2 {testdir}/source/a*',
                 verification=f'ls -fr {testdir}/dest | (f: f.relative_to("{testdir}/dest")) | sort',
                 expected_out=[f'{node1}/a', f'{node1}/a b',
                               f'{node2}/a', f'{node2}/a b'])
        os.system(f'rm -rf {testdir}/dest/*')


@timeit
def test_bug_126():
    TEST.run('fact = (|x: gen (x) 1 | args (|n: gen (n) 1 | red * | map (f: (n, f))|)|)')
    TEST.run(test='fact (5) >$ f',
             verification='f <$',
             expected_out=[(1, 1), (2, 2), (3, 6), (4, 24), (5, 120)])


@timeit
def test_bug_136():
    TEST.run('gen 3 1 | args (|n: gen 2 100 | (f: f+n)|) | red +',
             expected_out=[615])


@timeit
def test_bug_151():
    TEST.run('bytime = (|sort (f: f.mtime)|)')
    TEST.run('ls ~ | bytime >$ a')
    TEST.run('ls ~ | sort (f: f.mtime) >$ b')
    TEST.run('a <$ difference (|b <$|) | red count',
             expected_out=[0])
    TEST.run('b <$ difference (|a <$|) | red count',
             expected_out=[0])


@timeit
def test_bug_152():
    # Same test case as for bug 126. Failure was different as code changes.
    pass


@timeit
def test_bug_10():
    TEST.run('sort', expected_err='cannot be the first operator in a pipeline')
    TEST.run('unique', expected_err='cannot be the first operator in a pipeline')
    TEST.run('window -o 2', expected_err='cannot be the first operator in a pipeline')
    TEST.run('map (3)', expected_out=[3])
    TEST.run('args(|f: gen(3)|)', expected_err='cannot be the first operator in a pipeline')


@timeit
def test_bug_154():
    TEST.reset_environment()
    TEST.run('gen 3 >$ f')
    TEST.run('f <$ (y: -y)', expected_out=[0, -1, -2])


@timeit
def test_bug_168():
    os.system('rm -rf /tmp/hello')
    os.system('echo hello1 > /tmp/hello')
    os.system('echo hello2 >> /tmp/hello')
    TEST.run('read /tmp/hello | red count',
             expected_out=[2])
    TEST.run('cat /tmp/hello | red count',
             expected_out=[2])
    os.system('rm -rf /tmp/hello')


@timeit
def test_bug_185():
    # Unbound var
    TEST.run('varop',
             expected_err='oops')
    # var masking executable
    # var masking builtin
    # Remove masking var


@timeit
def test_bug_190():
    with TestDir(TEST.env) as testdir:
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


@timeit
def test_bug_196():
    TEST.run('gn = (| n: (n is None) |)')
    TEST.run('gn', expected_out=[True])
    TEST.run('gn = (| n: gen (int(n)) |)')
    TEST.run('gn', expected_err='argument must be')
    TEST.run('g = (| gen 3 |)')
    TEST.run('g 5', expected_err='Too many arguments')
    TEST.run('gn = (| n: gen (int(n)) |)')
    TEST.run('gn', expected_err='argument must be')
    TEST.run('gn 3', expected_out=[0, 1, 2])
    TEST.run('gn 3 4', expected_err='Too many arguments')


@timeit
def test_bug_197():
    TEST.run('runpipeline', expected_err='not executable')


@timeit
def test_bug_198():
    with TestDir(TEST.env) as testdir:
        # IsADirectoryError
        TEST.run(f'gen 3 > {testdir}', expected_err='Is a directory')
        os.system(f'touch {testdir}/cannot_write')
        # PermissionError
        os.system(f'chmod 000 {testdir}/cannot_write')
        TEST.run(f'gen 3 > {testdir}/cannot_write', expected_err='Permission denied')
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
        TEST.run(f'read {source}',
                 expected_out=["""123,a,'b,c'""", '''"d,e"'''])
        TEST.run(f'read -c {source}',
                 expected_out=[('123', 'a', "'b", "c'"),
                               'd,e'])
        # Test --csv reading and writing
        TEST.run(f'read -c {source} | write -c {target}')
        TEST.run(f'read {target}',
                 expected_out=['''"123","a","'b","c'"''', '"d,e"'])
        TEST.run(f'read -c {target}',
                 expected_out=[('123', 'a', "'b", "c'"),
                               'd,e'])
        # Test whether write -c output followed by read -c/write -c is a fixed point.
        TEST.run(f'read -c {target} | write -c {target2}')
        TEST.run(f'read {target2}',
                 expected_out=['''"123","a","'b","c'"''', '"d,e"'])
        TEST.run(f'read -c {target2}',
                 expected_out=[('123', 'a', "'b", "c'"),
                               'd,e'])


@timeit
def test_bug_202():
    TEST.run('env -d f | select (*f: False)')
    TEST.run('p = (| f |)')
    TEST.run('p', expected_err="not executable")
    TEST.run('p 4', expected_err='Too many arguments')
    TEST.run('f = (| gen 3 |)')
    TEST.run('p 4', expected_err='Too many arguments')
    TEST.run('p', expected_out=[0, 1, 2])
    TEST.run('p = (| f 4 |)')
    TEST.run('f = (| n: gen (int(n)) |)')
    TEST.run('p', expected_out=[0, 1, 2, 3])
    TEST.run('p 6', expected_err='Too many arguments')


@timeit
def test_bug_203():
    TEST.run('p = (| gen 3 |)')
    TEST.run('(p)', expected_out=['gen 3'])
    TEST.run('p = (| n: gen (int(n)) |)')
    TEST.run('(p)', expected_out=['n: gen (int(n))'])


@timeit
def test_bug_206():
    base = '/tmp/test_cd_pushd'
    home = pathlib.Path('~').expanduser().absolute()
    os.system(f'mkdir {base}')
    TEST.run(test=f'cd {base}',
             verification='pwd | (d: str(d))',
             expected_out=base)
    TEST.run(test='mkdir "a b" x1 x2',
             verification='ls -fd | sort | (d: str(d))',
             expected_out=['.', "'a b'", 'x1', 'x2'])
    # Wildcard
    TEST.run(test='cd a*',
             verification='pwd | (d: str(d))',
             expected_out=f"'{base}/a b'")
    TEST.run(test='cd ..',
             verification='pwd | (d: str(d))',
             expected_out=base)
    TEST.run(test='pushd *b',
             verification='pwd | (d: str(d))',
             expected_out=f"'{base}/a b'")
    TEST.run(test='popd',
             verification='pwd | (d: str(d))',
             expected_out=base)
    # Default
    TEST.run(test='cd',
             verification='pwd | (d: str(d))',
             expected_out=home)
    TEST.run(test=f'cd {base}',
             verification='pwd | (d: str(d))',
             expected_out=base)
    # Errors
    TEST.run('cd x*',
             expected_err='Too many paths')
    TEST.run("pwd | (d: str(d))",
             expected_out=base)
    TEST.run('pushd x*',
             expected_err='Too many paths')
    TEST.run("pwd | (d: str(d))",
             expected_out=base)
    TEST.run('cd no_such_dir',
             expected_err='No qualifying path')
    TEST.run("pwd | (d: str(d))",
             expected_out=base)
    TEST.run('pushd no_such_dir',
             expected_err='No qualifying path')
    TEST.run("pwd | (d: str(d))",
             expected_out=base)
    TEST.run('cd no_such_dir*',
             expected_err='No qualifying path')
    TEST.run("pwd | (d: str(d))",
             expected_out=base)
    TEST.run('pushd no_such_dir*',
             expected_err='No qualifying path')
    TEST.run("pwd | (d: str(d))",
             expected_out=base)
    TEST.run('cd /tmp')
    os.system(f'rm -rf {base}')


@timeit
def test_bug_212():
    TEST.run('gen 3 | args (| f: ((f, -f)) |)',
             expected_out=[(0, 0), (1, -1), (2, -2)])
    TEST.run('sudo (| gen 3 | args (| f: ((f, -f)) |) |)',
             expected_out=[(0, 0), (1, -1), (2, -2)])


@timeit
def test_bug_229():
    TEST.run('gn = (| n: gen (int(n)) >$ g |)')
    TEST.run('gn 3')
    TEST.run('g <$',
             expected_out=[0, 1, 2])


@timeit
def test_bug_230():
    with TestDir(TEST.env) as testdir:
        TEST.cd(testdir)
        os.system('touch a1 a2')
        TEST.run('bash ls -l a? | (f: (f[-2:]))',
                 expected_out=['a1', 'a2'])
        TEST.run('bash "ls -i ??" | (f: (f[-2:]))',
                 expected_out=['a1', 'a2'])


@timeit
def test_bug_247():
    TEST.run('gen 3 | (f: f / (1-f))',
             expected_out=[0.0, Error('division by zero'), -2.0])
    TEST.run('gen 3 | args (| f: (f / (1-f)) |)',
             expected_out=[0.0, Error('division by zero'), -2.0])
    TEST.run('gen 6 | case (f: f%2==0) (| (f: f // (f-2)) |) (| (f: f * 100) |)',
             expected_out=[0, 100, Error('by zero'), 300, 2, 500])


@timeit
def test_bug_252():
    TEST.run('gen 9 | args (| a, b, c: ((-a, -b, -c)) |)',
             expected_out=[(0, -1, -2),
                           (-3, -4, -5),
                           (-6, -7, -8)])
    TEST.run('gen 8 | args (| a, b, c: ((-a, -b, -c)) |)',
             expected_out=[(0, -1, -2),
                           (-3, -4, -5),
                           Error('bad operand type')])


@timeit
def test_bug_258():
    TEST.run(test='cd /',
             verification='pwd | (p: str(p))',
             expected_out=['/'])


# Generalization of bug 195
@timeit
def test_pipeline_vars():
    TEST.reset_environment()
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
    TEST.run('p = (| args (| n: gen 3 100 | (f: (n, f)) |) |)')
    TEST.run('gen 3 1 | p',
             expected_out=[(1, 100), (1, 101), (1, 102),
                           (2, 100), (2, 101), (2, 102),
                           (3, 100), (3, 101), (3, 102)])
    TEST.run('q = (| args (| f, y: (f + y) |) |)')
    TEST.run('gen 10 | q', expected_out=[1, 5, 9, 13, 17])
    # join
    TEST.run('x100 = (| gen 3 1 | (f: (f, f * 100)) |)')
    TEST.run('x1000 = (| gen 3 1 | (f: (f, f * 1000)) |)')
    TEST.run('gen 3 1 | (f: (f, f * 10)) | join x100 | join x1000',
             expected_out=[(1, 10, 100, 1000), (2, 20, 200, 2000), (3, 30, 300, 3000)])
    # remote
    node1 = marcel.object.cluster.Host(None, TEST.env.getvar('NODE1'))
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
    TEST.run('sum <$', expected_out=[15])
    TEST.run('prod <$', expected_out=[120])


def main_slow_tests():
    TEST.reset_environment()
    test_upload()
    test_pipeline_vars()
    test_remote()
    test_download()


# For bugs that aren't specific to a single op.
@timeit
def test_bugs():
    test_bug_10()
    test_bug_126()
    test_bug_136()
    test_bug_151()
    test_bug_154()
    test_bug_168()
    test_bug_190()
    test_bug_196()
    test_bug_197()
    test_bug_198()
    test_bug_200()
    test_bug_202()
    test_bug_203()
    test_bug_206()
    test_bug_212()
    test_bug_229()
    test_bug_230()
    test_bug_247()
    test_bug_252()
    test_bug_258()


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
    test_bugs()


def main_dev():
    pass


def main():
    TEST.reset_environment()
    main_dev()
    main_stable()
    main_slow_tests()
    TEST.report_failures('test_ops')
    sys.exit(TEST.failures)


main()
