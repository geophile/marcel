import os
import io
import shutil
import contextlib
import pathlib

from osh.env import ENV
from osh.main import run_command


class Test:
    failures = 0

    @staticmethod
    def new_file(filename):
        path = pathlib.Path(filename)
        if path.exists():
            path.unlink()
        path.open()

    @staticmethod
    def check_eq(command, expected, actual):
        if expected != actual:
            print('%s failed:' % command)
            print('    expected:\n<<<%s>>>' % expected)
            print('    actual:\n<<<%s>>>' % actual)
            Test.failures += 1

    @staticmethod
    def check_substring(command, expected, actual):
        if expected not in actual:
            print('%s failed. Expected substring not found in actual:' % command)
            print('    expected:\n<<<%s>>>' % expected)
            print('    actual:\n<<<%s>>>' % actual)
            Test.failures += 1

    @staticmethod
    def fail(command, message):
        print('%s failed: %s' % (command, message))
        Test.failures += 1

    @staticmethod
    def run(command, expected_out=None, expected_err=None, file=None):
        out = io.StringIO()
        err = io.StringIO()
        try:
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                run_command(command)
            actual_out = Test.file_contents(file) if file else out.getvalue()
            actual_err = err.getvalue()
            Test.check_eq(command,
                          Test.to_string(expected_out) if expected_out else '',
                          actual_out)
            if expected_err:
                Test.check_substring(command, expected_err, actual_err)
            elif actual_err:
                Test.fail(command, 'Unexpected error: %s' % actual_err)
        except Exception as e:
            print('%s: Terminated by uncaught exception: %s' % (command, e))
            Test.failures += 1

    @staticmethod
    def file_contents(filename):
        file = open(filename, 'r')
        contents = ''.join(file.readlines())
        file.close()
        return contents

    @staticmethod
    def to_string(x):
        if isinstance(x, str):
            return x
        elif isinstance(x, tuple) or isinstance(x, list):
            return '\n'.join([str(o) for o in x]) + '\n'
        else:
            return str(x)

    @staticmethod
    def delete_file(filename):
        os.remove(filename)


def test_gen():
    Test.run('gen 5 | out',
             expected_out=[(0,), (1,), (2,), (3,), (4,)])
    Test.run('gen 5 10 | out',
             expected_out=[(10,), (11,), (12,), (13,), (14,)])
    Test.run('gen 5 10 123 | out',
             expected_err='unrecognized arguments: 123')
    Test.run('gen 5 -5 | out',
             expected_out=[(-5,), (-4,), (-3,), (-2,), (-1,)])
    Test.run('gen 3 -p 2 | out',
             expected_out=[('00',), ('01',), ('02',)])
    Test.run('gen 3 --pad 2 | out',
             expected_out=[('00',), ('01',), ('02',)])
    Test.run('gen 3 99 -p 3 | out',
             expected_out=[('099',), ('100',), ('101',)])
    Test.run('gen 3 99 -p 2 | out',
             expected_err='Padding too small')
    Test.run('gen 3 -p 3 99 | out',
             expected_err='unrecognized arguments: 99')
    Test.run('gen 3 -10 -p 4 | out',
             expected_err='Padding incompatible with START < 0')


def test_out():
    output_filename = '/tmp/out.txt'
    Test.run('gen 3 | out %s',
             expected_out=[0, 1, 2])
    Test.run('gen 3',
             expected_out=[0, 1, 2])
    Test.run('gen 3 | out -c',
             expected_out=[0, 1, 2])
    Test.run('gen 3 | out --csv',
             expected_out=[0, 1, 2])
    Test.run('gen 3 | out -c %s',
             expected_err='-c/--csv and FORMAT specifications are incompatible')
    Test.run('gen 3 | out -f %s' % output_filename,
             expected_out=[(0,), (1,), (2,)], file=output_filename)
    Test.run('gen 3 | out --file %s' % output_filename,
             expected_out=[(0,), (1,), (2,)], file=output_filename)
    Test.delete_file(output_filename)
    Test.run('gen 3 | out -a %s' % output_filename,
             expected_out=[(0,), (1,), (2,)],
             file=output_filename)
    Test.run('gen 3 | out --append %s' % output_filename,
             expected_out=[(0,), (1,), (2,), (0,), (1,), (2,)],
             file=output_filename)
    Test.run('gen 3 | out -a %s -f %s' % (output_filename, output_filename),
             expected_err='argument -f/--file: not allowed with argument -a/--append')
    Test.delete_file(output_filename)


def test_sort():
    # TODO: test rows, e.g. gen 5 | f (x: (x, x)) | sort
    Test.run('gen 5 | sort | out %s', expected_out=[0, 1, 2, 3, 4])
    Test.run('gen 5 | sort (lambda x: -x) | out %s', expected_out=[4, 3, 2, 1, 0])


def test_ls():
    # base/
    #     a1
    #     a2
    #     b1
    #     b2
    #     d1/
    #         f11
    #         f12
    #         f13
    #     d2/
    #         f21
    #         f22
    #         f23
    #         d21/
    #             f211
    #             f212
    tmp = '/tmp'  # tmp/
    base = '/tmp/testls'  # base/
    a1 = '/tmp/testls/a1'  # a1
    a2 = '/tmp/testls/a2'  # a2
    b1 = '/tmp/testls/b1'  # b1
    b2 = '/tmp/testls/b2'  # b2
    d1 = '/tmp/testls/d1'  # d1/
    f11 = '/tmp/testls/d1/f11'  # f11
    f12 = '/tmp/testls/d1/f12'  # f12
    f13 = '/tmp/testls/d1/f13'  # f13
    d2 = '/tmp/testls/d2'  # d2/
    f21 = '/tmp/testls/d2/f21'  # f21
    f22 = '/tmp/testls/d2/f22'  # f22
    f23 = '/tmp/testls/d2/f23'  # f23
    d21 = '/tmp/testls/d2/d21'  # d21/
    f211 = '/tmp/testls/d2/d21/f211'  # f211
    f212 = '/tmp/testls/d2/d21/f212'  # f212
    # Start clean
    shutil.rmtree(base, ignore_errors=True)
    # Create test data
    os.mkdir(base)
    os.mkdir(d1)
    os.mkdir(d2)
    os.mkdir(d21)
    pathlib.Path(a1).touch()
    pathlib.Path(a2).touch()
    pathlib.Path(b1).touch()
    pathlib.Path(b2).touch()
    pathlib.Path(f11).touch()
    pathlib.Path(f12).touch()
    pathlib.Path(f13).touch()
    pathlib.Path(f21).touch()
    pathlib.Path(f22).touch()
    pathlib.Path(f23).touch()
    pathlib.Path(f211).touch()
    pathlib.Path(f212).touch()
    # Tests
    # 0/1/r flags with file
    Test.run('ls /tmp/testls/a1 | map (f: f.abspath) | sort',
             expected_out=sorted([a1]))
    Test.run('ls -0 /tmp/testls/a1 | map (f: f.abspath) | sort',
             expected_out=sorted([a1]))
    Test.run('ls -1 /tmp/testls/a1 | map (f: f.abspath) | sort',
             expected_out=sorted([a1]))
    Test.run('ls -r /tmp/testls/a1 | map (f: f.abspath) | sort',
             expected_out=sorted([a1]))
    # 0/1/r flags with directory
    Test.run('ls /tmp/testls | map (f: f.abspath) | sort',
             expected_out=sorted([a1, a2, b1, b2, d1, d2]))
    Test.run('ls -0 /tmp/testls | map (f: f.abspath) | sort',
             expected_out=sorted([a1, a2, b1, b2, d1, d2]))
    Test.run('ls -1 /tmp/testls | map (f: f.abspath) | sort',
             expected_out=sorted([a1, a2, b1, b2, d1, f11, f12, f13, d2, f21, f22, f23, d21]))
    Test.run('ls -r /tmp/testls | map (f: f.abspath) | sort',
             expected_out=sorted([a1, a2, b1, b2, d1, f11, f12, f13, d2, f21, f22, f23, d21, f211, f212]))
    # 0/1/r flags with pattern matching files
    Test.run('ls /tmp/testls/a? | map (f: f.abspath) | sort',
             expected_out=sorted([a1, a2]))
    Test.run('ls -0 /tmp/testls/a? | map (f: f.abspath) | sort',
             expected_out=sorted([a1, a2]))
    Test.run('ls -1 /tmp/testls/a? | map (f: f.abspath) | sort',
             expected_out=sorted([a1, a2]))
    Test.run('ls -r /tmp/testls/a? | map (f: f.abspath) | sort',
             expected_out=sorted([a1, a2]))
    # 0/1/r flags with pattern matching directories
    Test.run('ls /tmp/testls/d? | map (f: f.abspath) | sort',
             expected_out=sorted([d1, d2]))
    Test.run('ls -0 /tmp/testls/d? | map (f: f.abspath) | sort',
             expected_out=sorted([d1, d2]))
    Test.run('ls -1 /tmp/testls/d? | map (f: f.abspath) | sort',
             expected_out=sorted([d1, f11, f12, f13, d2, f21, f22, f23, d21]))
    Test.run('ls -r /tmp/testls/d? | map (f: f.abspath) | sort',
             expected_out=sorted([d1, f11, f12, f13, d2, f21, f22, f23, d21, f211, f212]))
    # In current directory, test 0/1/r flags with file
    ENV.cd(pathlib.Path(tmp))
    Test.run('ls -0 testls/b1 | map (f: f.abspath) | sort',
             expected_out=sorted([b1]))
    Test.run('ls -1 testls/b1 | map (f: f.abspath) | sort',
             expected_out=sorted([b1]))
    Test.run('ls -r testls/b1 | map (f: f.abspath) | sort',
             expected_out=sorted([b1]))
    # In current directory, test 0/1/r flags with directory
    Test.run('ls -0 testls | map (f: f.abspath) | sort',
             expected_out=sorted([a1, a2, b1, b2, d1, d2]))
    Test.run('ls -1 testls | map (f: f.abspath) | sort',
             expected_out=sorted([a1, a2, b1, b2, d1, f11, f12, f13, d2, f21, f22, f23, d21]))
    Test.run('ls -r testls | map (f: f.abspath) | sort',
             expected_out=sorted([a1, a2, b1, b2, d1, f11, f12, f13, d2, f21, f22, f23, d21, f211, f212]))
    # In current directory, test 0/1/r flags with pattern matching directories
    Test.run('ls -0 testls/*2 | map (f: f.abspath) | sort',
             expected_out=sorted([a2, b2, d2]))
    Test.run('ls -1 testls/*2 | map (f: f.abspath) | sort',
             expected_out=sorted([a2, b2, d2, f21, f22, f23, d21]))
    Test.run('ls -r testls/*2 | map (f: f.abspath) | sort',
             expected_out=sorted([a2, b2, d2, f21, f22, f23, d21, f211, f212]))
    # Test f/d/s flags
    Test.run('ls -fr /tmp/testls | map (f: f.abspath) | sort',
             expected_out=sorted([a1, a2, b1, b2, f11, f12, f13, f21, f22, f23, f211, f212]))
    Test.run('ls -dr /tmp/testls | map (f: f.abspath) | sort',
             expected_out=sorted([d1, d2, d21]))
    Test.run('ls -fdr /tmp/testls | map (f: f.abspath) | sort',
             expected_out=sorted([a1, a2, b1, b2, d1, d2, f11, f12, f13, f21, f22, f23, d21, f211, f212]))
    # TODO: symlinks
    # Test multiple filenames/globs
    ENV.cd(pathlib.Path(base))
    Test.run('ls -0 a1 b* | map (f: f.abspath) | sort',
             expected_out=sorted([a1, b1, b2]))
    Test.run('ls -0 *2 d1/f* | map (f: f.abspath) | sort',
             expected_out=sorted([a2, b2, f11, f12, f13, d2]))
    # Test multiple globs, with files qualifying multiple times. Should be reported once. (Linux ls gets this wrong.)
    Test.run('ls -0 a* *1 | map (f: f.abspath) | sort',
             expected_out=sorted([a1, a2, b1, d1]))


def test_map():
    Test.run('gen 5 | map (x: -x)',
             expected_out=[0, -1, -2, -3, -4])
    Test.run('gen 5 | map (lambda x: -x)',
             expected_out=[0, -1, -2, -3, -4])
    Test.run('map (3)',
             expected_out=[3])
    Test.run('map (: 3)',
             expected_out=[3])
    Test.run('map (lambda: 3)',
             expected_out=[3])


def test_select():
    Test.run('gen 5 | select (x: True)',
             expected_out=[0, 1, 2, 3, 4])
    Test.run('gen 5 | select (x: False)',
             expected_out=[])
    Test.run('gen 5 | select (x: x % 2 == 1)',
             expected_out=[1, 3])


def test_red():
    # Test function symbols
    Test.run('gen 5 1 | red +',
             expected_out=[15])
    Test.run('gen 5 1 | red *',
             expected_out=[120])
    Test.run('gen 5 1 | red ^',
             expected_out=[1])
    Test.run('gen 20 1 | select (x: x in (3, 7, 15)) | red &',
             expected_out=[3])
    Test.run('gen 75 | select (x: x in (18, 36, 73)) | red \|',
             expected_out=[127])
    Test.run('gen 3 | map (x: x == 1) | red and',
             expected_out=[False])
    Test.run('gen 3 | map (x: x == 1) | red or',
             expected_out=[True])
    Test.run('gen 5 | red max',
             expected_out=[4])
    Test.run('gen 5 | red min',
             expected_out=[0])
    # Test incremental reduction
    Test.run('gen 5 1 | red -i +',
             expected_out=[(1, 1), (2, 3), (3, 6), (4, 10), (5, 15)])
    # Test incremental reduction
    Test.run('gen 5 1 | red --incremental +',
             expected_out=[(1, 1), (2, 3), (3, 6), (4, 10), (5, 15)])
    # Test lambdas
    Test.run('gen 5 1 | map (x: (x, x)) | red (x, y: x + y) (x, y: x * y)',
             expected_out=[(15, 120)])
    # Test multiple reduction
    Test.run('gen 5 1 | map (x: (x, x)) | red + *',
             expected_out=[(15, 120)])
    # Test multiple incremental reduction
    Test.run('gen 5 1 | map (x: (x, x)) | red -i + *',
             expected_out=[(1, 1, 1, 1),
                           (2, 2, 3, 2),
                           (3, 3, 6, 6),
                           (4, 4, 10, 24),
                           (5, 5, 15, 120)])
    # Test grouping
    Test.run('gen 9 1 | map (x: (x, x // 2, x * 100, x // 2)) | red + . + .',
             expected_out=[(1, 0, 100, 0),
                           (5, 1, 500, 1),
                           (9, 2, 900, 2),
                           (13, 3, 1300, 3),
                           (17, 4, 1700, 4)])
    # Test incremental grouping
    Test.run('gen 9 1 | map (x: (x, x // 2, x * 100, x // 2)) | red -i + . + .',
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
    Test.run('gen 5 | expand',
             expected_out=[0, 1, 2, 3, 4])
    Test.run('gen 5 | map (x: ([x, x],)) | expand',
             expected_out=[0, 0, 1, 1, 2, 2, 3, 3, 4, 4])
    Test.run('gen 5 | map (x: ((x, x),)) | expand',
             expected_out=[0, 0, 1, 1, 2, 2, 3, 3, 4, 4])
    Test.run('gen 5 | expand 0',
             expected_out=[0, 1, 2, 3, 4])
    Test.run('gen 5 | map (x: ([x, x],)) | expand 0',
             expected_out=[0, 0, 1, 1, 2, 2, 3, 3, 4, 4])
    Test.run('gen 5 | map (x: ((x, x),)) | expand 0',
             expected_out=[0, 0, 1, 1, 2, 2, 3, 3, 4, 4])
    # Test non-singletons
    Test.run('gen 5 | map (x: (x, -x)) | expand',
             expected_out=[0, 0, 1, -1, 2, -2, 3, -3, 4, -4])
    Test.run('gen 5 | map (x: (x, -x)) | expand 0',
             expected_out=[(0, 0), (1, -1), (2, -2), (3, -3), (4, -4)])
    Test.run('gen 5 | map (x: (x, -x)) | expand 1',
             expected_out=[(0, 0), (1, -1), (2, -2), (3, -3), (4, -4)])
    Test.run('gen 5 | map (x: (x, -x)) | expand 2',
             expected_out=[(0, 0), (1, -1), (2, -2), (3, -3), (4, -4)])
    # Expand list
    Test.run('gen 5 | map (x: ([100, 200], x, -x)) | expand 0',
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
    Test.run('gen 5 | map (x: (x, [100, 200], -x)) | expand 1',
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
    Test.run('gen 5 | map (x: (x, -x, [100, 200])) | expand 2',
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
    Test.run('gen 5 | map (x: (x, -x, [100, 200])) | expand 3',
             expected_out=[(0, 0, [100, 200]),
                           (1, -1, [100, 200]),
                           (2, -2, [100, 200]),
                           (3, -3, [100, 200]),
                           (4, -4, [100, 200])])
    # Expand tuple
    Test.run('gen 5 | map (x: ((100, 200), x, -x)) | expand 0',
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
    # Expand file
    with open('/tmp/test_expand_1', 'w') as file:
        file.writelines(['abc\n', 'def\n'])  # lf at end of file
    with open('/tmp/test_expand_2', 'w') as file:
        file.writelines(['ghi\n', 'jkl'])    # No lf at end of file
    Test.run('ls /tmp/test_expand_? | expand',
             expected_out=['abc\n', 'def\n', 'ghi\n', 'jkl'])
    os.remove('/tmp/test_expand_1')
    os.remove('/tmp/test_expand_2')


def test_no_such_op():
    Test.run('gen 5 | abc', expected_err='abc is not recognized as a command')


def main():
    # test_gen()
    # test_out()
    # test_sort()
    # test_map()
    # test_ls()
    # test_select()
    # test_red()
    test_expand()
    # test_ps()  How?
    test_no_such_op()
    # test cd: absolute, relative, target does not exist
    print('Test failures: %s' % Test.failures)


main()
