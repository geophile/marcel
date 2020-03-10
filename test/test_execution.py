import contextlib
import io
import os
import pathlib
import shutil

import marcel.core
import marcel.main
import marcel.object.error
import marcel.object.host
from marcel.util import *

Error = marcel.object.error.Error
start_dir = os.getcwd()
MAIN = marcel.main.Main()


class Test:

    failures = 0

    @staticmethod
    def new_file(filename):
        path = pathlib.Path(filename)
        if path.exists():
            path.unlink()
        path.open()

    @staticmethod
    def check_ok(command, expected, actual):
        expected = Test.remove_empty_line_at_end(expected.split('\n'))
        actual = Test.remove_empty_line_at_end(actual.split('\n'))
        ok = True
        n = len(expected)
        if len(actual) == n:
            i = 0
            while ok and i < n:
                e = expected[i]
                a = actual[i]
                e_error = e.startswith('Error(') and e.endswith(')')
                a_error = a.startswith('Error(') and a.endswith(')')
                if e_error and a_error:
                    # Check that e message is a substring of a message
                    e_message = e[6:-1]
                    a_message = a[6:-1]
                    ok = e_message in a_message
                elif e_error or a_error:
                    ok = False
                else:
                    ok = a == e
                i += 1
        else:
            ok = False
        if not ok:
            print(f'{command} failed:')
            print(f'    expected:\n<<<{expected}>>>')
            print(f'    actual:\n<<<{actual}>>>')
            Test.failures += 1

    @staticmethod
    def check_substring(command, expected, actual):
        if expected not in actual:
            print(f'{command} failed. Expected substring not found in actual:')
            print(f'    expected:\n<<<{expected}>>>')
            print(f'    actual:\n<<<{actual}>>>')
            Test.failures += 1

    @staticmethod
    def fail(command, message):
        print(f'{command} failed: {message}')
        Test.failures += 1

    @staticmethod
    def run_and_capture_output(command):
        out = io.StringIO()
        err = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            MAIN.run_command(command)
        return out.getvalue(), err.getvalue()

    @staticmethod
    def run(test,
            verification=None,
            expected_out=None,
            expected_err=None,
            file=None):
        # test is the thing being tested. Usually it will produce output that can be used for verification.
        # For operations with side effects (e.g. rm), a separate verification command is needed.
        if verification is None and expected_out is None and expected_err is None and file is None:
            MAIN.run_command(test)
        else:
            print(f'TESTING: {test}')
            try:
                if verification is None:
                    actual_out, actual_err = Test.run_and_capture_output(test)
                else:
                    Test.run_and_capture_output(test)
                    actual_out, actual_err = Test.run_and_capture_output(verification)
                if file:
                    actual_out = Test.file_contents(file)
                if expected_out:
                    Test.check_ok(test, Test.to_string(expected_out), actual_out)
                if expected_err:
                    Test.check_substring(test, expected_err, actual_err)
                elif actual_err:
                    Test.fail(test, f'Unexpected error: {actual_err}')
            except Exception as e:
                print(f'{test}: Terminated by uncaught exception: {e}')
                print_stack()
                Test.failures += 1
            except marcel.exception.KillCommandException as e:
                print(f'{test}: Terminated by KillCommandException: {e}')

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

    @staticmethod
    def remove_empty_line_at_end(lines):
        if len(lines[-1]) == 0:
            del lines[-1]
        return lines

    @staticmethod
    def cd(path):
        MAIN.run_command(f'cd {path}')


def test_no_such_op():
    Test.run('gen 5 | abc', expected_err='Unknown op abc')


def test_gen():
    # Explicit out
    Test.run('gen 5 | out',
             expected_out=[0, 1, 2, 3, 4])
    # Implicit out
    Test.run('gen 5',
             expected_out=[0, 1, 2, 3, 4])
    Test.run('gen 5 10 | out',
             expected_out=[10, 11, 12, 13, 14])
    Test.run('gen 5 10 123 | out',
             expected_err='unrecognized arguments: 123')
    Test.run('gen 5 -5 | out',
             expected_out=[-5, -4, -3, -2, -1])
    Test.run('gen 3 -p 2 | out',
             expected_out=['00', '01', '02'])
    Test.run('gen 3 --pad 2 | out',
             expected_out=['00', '01', '02'])
    Test.run('gen 3 99 -p 3 | out',
             expected_out=['099', '100', '101'])
    Test.run('gen 3 99 -p 2 | out',
             expected_err='Padding too small')
    Test.run('gen 3 -p 3 99 | out',
             expected_err='unrecognized arguments: 99')
    Test.run('gen 3 -10 -p 4 | out',
             expected_err='Padding incompatible with START < 0')
    # Error along with output
    Test.run('gen 3 -1 | map (x: 5 / x)',
             expected_out=[-5.0, Error('division by zero'), 5.0])


def test_out():
    output_filename = '/tmp/out.txt'
    Test.run('gen 3 | out {}',
             expected_out=[0, 1, 2])
    Test.run('gen 3',
             expected_out=[0, 1, 2])
    Test.run('gen 3 | out -c',
             expected_out=[0, 1, 2])
    Test.run('gen 3 | out --csv',
             expected_out=[0, 1, 2])
    Test.run('gen 3 | out -c {}',
             expected_err='-c/--csv and FORMAT specifications are incompatible')
    Test.run(f'gen 3 | out -f {output_filename}',
             expected_out=[0, 1, 2], file=output_filename)
    Test.run(f'gen 3 | out --file {output_filename}',
             expected_out=[0, 1, 2], file=output_filename)
    Test.delete_file(output_filename)
    Test.run(f'gen 3 | out -a {output_filename}',
             expected_out=[0, 1, 2],
             file=output_filename)
    Test.run(f'gen 3 | out --append {output_filename}',
             expected_out=[0, 1, 2, 0, 1, 2],
             file=output_filename)
    Test.run(f'gen 3 | out -a {output_filename} -f {output_filename}',
             expected_err='argument -f/--file: not allowed with argument -a/--append')
    Test.delete_file(output_filename)


def test_sort():
    Test.run('gen 5 | sort', expected_out=[0, 1, 2, 3, 4])
    Test.run('gen 5 | sort (lambda x: -x)', expected_out=[4, 3, 2, 1, 0])
    Test.run('gen 5 | map (x: (-x, x)) | sort', expected_out=[(-4, 4), (-3, 3), (-2, 2), (-1, 1), (0, 0)])


def test_ls():
    def relative(base, x):
        x_path = pathlib.Path(x)
        base_path = pathlib.Path(base)
        display_path = x_path.relative_to(base_path)
        return display_path

    # testls/
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
    dot = pathlib.Path('.')
    tmp = '/tmp'  # tmp/
    testls = '/tmp/testls'  # testls/
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
    shutil.rmtree(testls, ignore_errors=True)
    # Create test data
    os.mkdir(testls)
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
    # No files specified
    Test.cd(testls)
    Test.run('ls | map (f: f.render_compact())',
             expected_out=sorted(relative(testls, x) for x in
                                 [testls, a1, a2, b1, b2, d1, d2]))
    Test.run('ls -0 | map (f: f.render_compact())',
             expected_out=sorted(relative(testls, x) for x in
                                 [testls]))
    Test.run('ls -1 | map (f: f.render_compact())',
             expected_out=sorted(relative(testls, x) for x in
                                 [testls, a1, a2, b1, b2, d1, d2]))
    Test.run('ls -r | map (f: f.render_compact())',
             expected_out=sorted(relative(testls, x) for x in
                                 [testls, a1, a2, b1, b2, d1, f11, f12, f13, d2, f21, f22, f23, d21, f211, f212]))
    # 0/1/r flags with file
    Test.run('ls /tmp/testls/a1 | map (f: f.render_compact())',
             expected_out=sorted([a1]))
    Test.run('ls -0 /tmp/testls/a1 | map (f: f.render_compact())',
             expected_out=sorted([a1]))
    Test.run('ls -1 /tmp/testls/a1 | map (f: f.render_compact())',
             expected_out=sorted([a1]))
    Test.run('ls -r /tmp/testls/a1 | map (f: f.render_compact())',
             expected_out=sorted([a1]))
    # 0/1/r flags with directory
    Test.run('ls /tmp/testls | map (f: f.render_compact())',
             expected_out=sorted([relative('/tmp/testls', x) for x in
                                  [testls, a1, a2, b1, b2, d1, d2]]))
    Test.run('ls -0 /tmp/testls | map (f: f.render_compact())',
             expected_out=sorted([relative('/tmp/testls', x) for x in
                                  [testls]]))
    Test.run('ls -1 /tmp/testls | map (f: f.render_compact())',
             expected_out=sorted([relative('/tmp/testls', x) for x in
                                  [testls, a1, a2, b1, b2, d1, d2]]))
    Test.run('ls -r /tmp/testls | map (f: f.render_compact())',
             expected_out=sorted([relative('/tmp/testls', x) for x in
                                  [testls, a1, a2, b1, b2, d1, f11, f12, f13, d2, f21, f22, f23, d21, f211, f212]]))
    # 0/1/r flags with pattern matching files
    Test.run('ls /tmp/testls/a? | map (f: f.render_compact())',
             expected_out=sorted([a1, a2]))
    Test.run('ls -0 /tmp/testls/a? | map (f: f.render_compact())',
             expected_out=sorted([a1, a2]))
    Test.run('ls -1 /tmp/testls/a? | map (f: f.render_compact())',
             expected_out=sorted([a1, a2]))
    Test.run('ls -r /tmp/testls/a? | map (f: f.render_compact())',
             expected_out=sorted([a1, a2]))
    # 0/1/r flags with pattern matching directories
    Test.run('ls /tmp/testls/d? | map (f: f.render_compact())',
             expected_out=sorted([d1, f11, f12, f13, d2, f21, f22, f23, d21]))
    Test.run('ls -0 /tmp/testls/d? | map (f: f.render_compact())',
             expected_out=sorted([d1, d2]))
    Test.run('ls -1 /tmp/testls/d? | map (f: f.render_compact())',
             expected_out=sorted([d1, f11, f12, f13, d2, f21, f22, f23, d21]))
    Test.run('ls -r /tmp/testls/d? | map (f: f.render_compact())',
             expected_out=sorted([d1, f11, f12, f13, d2, f21, f22, f23, d21, f211, f212]))
    # In current directory, test 0/1/r flags with file
    Test.cd(tmp)
    Test.run('ls testls/b1 | map (f: f.render_compact())',
             expected_out=sorted([b1]))
    Test.run('ls -0 testls/b1 | map (f: f.render_compact())',
             expected_out=sorted([b1]))
    Test.run('ls -1 testls/b1 | map (f: f.render_compact())',
             expected_out=sorted([b1]))
    Test.run('ls -r testls/b1 | map (f: f.render_compact())',
             expected_out=sorted([b1]))
    # In current directory, test 0/1/r flags with directory
    Test.cd(tmp)
    Test.run('ls testls | map (f: f.render_compact())',
             expected_out=sorted([relative(testls, x) for x in
                                  [testls, a1, a2, b1, b2, d1, d2]]))
    Test.run('ls -0 testls | map (f: f.render_compact())',
             expected_out=sorted([relative(testls, testls)]))
    Test.run('ls -1 testls | map (f: f.render_compact())',
             expected_out=sorted([relative(testls, x) for x in
                                  [testls, a1, a2, b1, b2, d1, d2]]))
    Test.run('ls -r testls | map (f: f.render_compact())',
             expected_out=sorted([relative(testls, x) for x in
                                  [testls, a1, a2, b1, b2, d1, f11, f12, f13, d2, f21, f22, f23, d21, f211, f212]]))
    # In current directory, test 0/1/r flags with pattern matching directories
    Test.cd(tmp)
    Test.run('ls testls/*2 | map (f: f.render_compact())',
             expected_out=sorted([a2, b2, d2, f21, f22, f23, d21]))
    Test.run('ls -0 testls/*2 | map (f: f.render_compact())',
             expected_out=sorted([a2, b2, d2]))
    Test.run('ls -1 testls/*2 | map (f: f.render_compact())',
             expected_out=sorted([a2, b2, d2, f21, f22, f23, d21]))
    Test.run('ls -r testls/*2 | map (f: f.render_compact())',
             expected_out=sorted([a2, b2, d2, f21, f22, f23, d21, f211, f212]))
    # Test f/d/s flags
    Test.cd(tmp)
    Test.run('ls -fr /tmp/testls | map (f: f.render_compact())',
             expected_out=sorted([relative(testls, x) for x in
                                  [a1, a2, b1, b2, f11, f12, f13, f21, f22, f23, f211, f212]]))
    Test.run('ls -dr /tmp/testls | map (f: f.render_compact())',
             expected_out=sorted([relative(testls, x) for x in
                                  [testls, d1, d2, d21]]))
    Test.run('ls -fdr /tmp/testls | map (f: f.render_compact())',
             expected_out=sorted([relative(testls, x) for x in
                                  [testls, a1, a2, b1, b2, d1, d2, f11, f12, f13, f21, f22, f23, d21, f211, f212]]))
    # Test multiple filenames/globs
    Test.cd(testls)
    Test.run('ls -0 a1 b* | map (f: f.render_compact())',
             expected_out=sorted([a1, b1, b2]))
    Test.run('ls -0 *2 d1/f* | map (f: f.render_compact())',
             expected_out=sorted([a2, b2, f11, f12, f13, d2]))
    # Test multiple globs, with files qualifying multiple times. Should be reported once.
    # (Linux ls gets this wrong IMHO.)
    Test.cd(testls)
    Test.run('ls -0 a* *1 | map (f: f.render_compact())',
             expected_out=sorted([a1, a2, b1, d1]))
    # TODO: symlinks
    reset_environment()


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
        file.writelines(['ghi\n', 'jkl'])  # No lf at end of file
    Test.run('ls /tmp/test_expand_? | expand',
             expected_out=['abc', 'def', 'ghi', 'jkl'])
    Test.run('ls /tmp/test_expand_? | map (f: (str(f), f)) | expand 1',
             expected_out=[('/tmp/test_expand_1', 'abc'),
                           ('/tmp/test_expand_1', 'def'),
                           ('/tmp/test_expand_2', 'ghi'),
                           ('/tmp/test_expand_2', 'jkl')])
    os.remove('/tmp/test_expand_1')
    os.remove('/tmp/test_expand_2')


def test_head():
    Test.run('gen 100 | head 0',
             expected_out=[])
    Test.run('gen 100 | head 1',
             expected_out=[0])
    Test.run('gen 100 | head 2',
             expected_out=[0, 1])
    Test.run('gen 100 | head 3',
             expected_out=[0, 1, 2])
    Test.run('gen 3 | head 3',
             expected_out=[0, 1, 2])
    Test.run('gen 3 | head 4',
             expected_out=[0, 1, 2])


def test_tail():
    Test.run('gen 100 | tail 0',
             expected_out=[])
    Test.run('gen 100 | tail 1',
             expected_out=[99])
    Test.run('gen 100 | tail 2',
             expected_out=[98, 99])
    Test.run('gen 100 | tail 3',
             expected_out=[97, 98, 99])
    Test.run('gen 3 | tail 3',
             expected_out=[0, 1, 2])
    Test.run('gen 3 | tail 4',
             expected_out=[0, 1, 2])


def test_reverse():
    Test.run('gen 5 | select (x: False) | reverse',
             expected_out=[])
    Test.run('gen 5 | reverse',
             expected_out=[4, 3, 2, 1, 0])


def test_squish():
    Test.run('gen 5 | squish',
             expected_out=[0, 1, 2, 3, 4])
    Test.run('gen 5 | squish +',
             expected_out=[0, 1, 2, 3, 4])
    Test.run('gen 5 | map (x: (x, -x)) | squish',
             expected_out=[0, 0, 0, 0, 0])
    Test.run('gen 5 | map (x: (x, -x)) | squish +',
             expected_out=[0, 0, 0, 0, 0])
    Test.run('gen 5 | map (x: (x, -x)) | squish min',
             expected_out=[0, -1, -2, -3, -4])
    Test.run('gen 5 | map (x: (x, -x)) | squish max',
             expected_out=[0, 1, 2, 3, 4])
    Test.run('gen 5 | map (x: ([-x, x], [-x, x])) | squish +',
             expected_out=[(0, 0, 0, 0),
                           (-1, 1, -1, 1),
                           (-2, 2, -2, 2),
                           (-3, 3, -3, 3),
                           (-4, 4, -4, 4)])


def test_unique():
    Test.run('gen 10 | unique',
             expected_out=[0, 1, 2, 3, 4, 5, 6, 7, 8, 9])
    Test.run('gen 10 | select (x: False) | unique',
             expected_out=[])
    Test.run('gen 10 | unique -c',
             expected_out=[0, 1, 2, 3, 4, 5, 6, 7, 8, 9])
    Test.run('gen 10 | select (x: False) | unique -c',
             expected_out=[])
    Test.run('gen 10 | map (x: x // 3) | unique',
             expected_out=[0, 1, 2, 3])
    Test.run('gen 10 | map (x: x // 3) | unique -c',
             expected_out=[0, 1, 2, 3])
    Test.run('gen 10 | map (x: x // 3) | unique --consecutive',
             expected_out=[0, 1, 2, 3])
    Test.run('gen 10 | map (x: x % 3) | unique',
             expected_out=[0, 1, 2])


def test_window():
    Test.run('gen 10 | window (x: False)',
             expected_out=[((0,), (1,), (2,), (3,), (4,), (5,), (6,), (7,), (8,), (9,))])
    Test.run('gen 10 | window (x: True)',
             expected_out=[(0,), (1,), (2,), (3,), (4,), (5,), (6,), (7,), (8,), (9,)])
    Test.run('gen 10 | window -o 1',
             expected_out=[(0,), (1,), (2,), (3,), (4,), (5,), (6,), (7,), (8,), (9,)])
    Test.run('gen 10 | window -o 3',
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
    Test.run('gen 10 | window -d 1',
             expected_out=[(0,), (1,), (2,), (3,), (4,), (5,), (6,), (7,), (8,), (9,)])
    Test.run('gen 10 | window -d 3',
             expected_out=[((0,), (1,), (2,)),
                           ((3,), (4,), (5,)),
                           ((6,), (7,), (8,)),
                           ((9,), (None,), (None,))])
    # Negative-test args
    Test.run('gen 10 | window -d 33 -o 22',
             expected_err='argument -o/--overlap: not allowed with argument -d/--disjoint')
    Test.run('gen 10 | window',
             expected_err='Incorrect arguments given for window')
    Test.run('gen 10 | window -o 3 (x: True)',
             expected_err='Incorrect arguments given for window')


def test_bash():
    Test.run('bash echo hello  world',
             expected_out=['hello world'])
    # TODO: This doesn't work. quoted string has two spaces, but output has one.
    # Test.run('bash echo "hello  world"',
    #          expected_out=['hello  world\n'])


def test_fork():
    Test.run('@1 [ gen 3 100 ]',
             expected_out=[(0, 100), (0, 101), (0, 102)])
    Test.run('@3 [ gen 3 100 ] | sort',
             expected_out=[(0, 100), (0, 101), (0, 102),
                           (1, 100), (1, 101), (1, 102),
                           (2, 100), (2, 101), (2, 102)])


def test_namespace():
    config_file = '/tmp/.marcel.py'
    config_path = pathlib.Path(config_file)
    # Default namespace has just __builtins__ and initial set of env vars.
    config_path.touch()
    config_path.unlink()
    config_path.touch()
    reset_environment(config_file)
    Test.run('map (globals().keys())',
             expected_out=["dict_keys(['USER', 'HOME', 'HOST', 'PWD', '__builtins__'])"])
    # Try to use an undefined symbol
    Test.run('map (pi)',
             expected_out=[Error("name 'pi' is not defined")])
    # Try a namespace importing symbols in the math module
    config_path.unlink()
    with open(config_file, 'w') as file:
        file.writelines('from math import *')
    reset_environment(config_file)
    Test.run('map (pi)',
             expected_out=['3.141592653589793'])
    # Reset environment
    reset_environment()


def test_remote():
    localhost = marcel.object.host.Host('localhost', None)
    # Test.run('@jao [ gen 3 ]',
    #          expected_out=[(localhost, 0), (localhost, 1), (localhost, 2)])
    # Handling of remote errors
    Test.run('@jao [ gen 3 -1 | map (x: 5 / x) ]',
             expected_out=[(localhost, -5.0), Error('division by zero'), (localhost, 5.0)])
    # Bug 4
    Test.run('@jao [ gen 3 ] | red . +',
             expected_out=[(localhost, 3)])
    Test.run('@jao [ gen 10 | map (x: (x%2, x)) | red . + ]',
             expected_out=[(localhost, 0, 20), (localhost, 1, 25)])


def test_rm():
    def setup(dir):
        Test.cd(tmp)
        Test.run('bash rm -rf base')
        Test.run('mkdir base')
        Test.cd(base)
        Test.run('mkdir d1')
        Test.run('mkdir d2')
        Test.run('touch d1/f11')
        Test.run('touch d1/f12')
        Test.run('touch d2/f21')
        Test.run('touch d2/f22')
        Test.run('touch f1')
        Test.run('touch f2')
        Test.cd(dir)

    dot = '.'
    tmp = '/tmp'
    base = '/tmp/base'
    d1 = 'd1'
    d2 = 'd2'
    f1 = 'f1'
    f2 = 'f2'
    f11 = 'd1/f11'
    f12 = 'd1/f12'
    f21 = 'd2/f21'
    f22 = 'd2/f22'
    # Remove a file
    setup(base)
    Test.run('ls -r /tmp/base | map (f: f.render_compact())',
             expected_out=sorted([dot, d1, f11, f12, d2, f21, f22, f1, f2]))
    Test.run(test='rm f1',
             verification='ls -r /tmp/base | map (f: f.render_compact())',
             expected_out=sorted([dot, d1, f11, f12, d2, f21, f22, f2]))
    Test.run(test='rm d1/f11 d1/f12',
             verification='ls -r /tmp/base | map (f: f.render_compact())',
             expected_out=sorted([dot, d1, d2, f21, f22, f2]))
    # Remove a file via absolute path
    setup('/home/jao')
    Test.run(test='rm /tmp/base/f1',
             verification='ls -r /tmp/base | map (f: f.render_compact())',
             expected_out=sorted([dot, d1, f11, f12, d2, f21, f22, f2]))
    Test.run(test='rm /tmp/base/d1/f11 /tmp/base/d1/f12',
             verification='ls -r /tmp/base | map (f: f.render_compact())',
             expected_out=sorted([dot, d1, d2, f21, f22, f2]))
    # Remove a directory
    setup(base)
    Test.run(test='rm /tmp/base/d1',
             verification='ls -r /tmp/base | map (f: f.render_compact())',
             expected_out=sorted([dot, d2, f21, f22, f1, f2]))
    # Remove via glob
    setup(base)
    Test.run(test='rm /tmp/base/*2',
             verification='ls -r /tmp/base | map (f: f.render_compact())',
             expected_out=sorted([dot, d1, f11, f12, f1]))
    # Remove via piping
    setup(base)
    Test.run(test='ls /tmp/base/*2 | rm',
             verification='ls -r /tmp/base | map (f: f.render_compact())',
             expected_out=sorted([dot, d1, f11, f12, f1]))
    # Erroneous
    setup(base)
    Test.run('ls /tmp/base/*2 | rm f1',
             expected_err='rm cannot receive input from a pipe')


def test_mv():
    def setup(dir):
        Test.cd(tmp)
        Test.run('bash rm -rf base')
        Test.run('mkdir base')
        Test.cd(base)
        Test.run('mkdir d1')
        Test.run('mkdir d2')
        Test.run('touch d1/f11')
        Test.run('touch d1/f12')
        Test.run('touch d2/f21')
        Test.run('touch d2/f22')
        Test.run('touch f1')
        Test.run('touch f2')
        Test.cd(dir)
    dot = '.'
    tmp = '/tmp'
    base = '/tmp/base'
    d1 = 'd1'
    d2 = 'd2'
    f1 = 'f1'
    f2 = 'f2'
    f11 = 'd1/f11'
    f12 = 'd1/f12'
    f21 = 'd2/f21'
    f22 = 'd2/f22'
    f1_in_d1 = 'd1/f1'
    f2_in_d1 = 'd1/f2'
    d2_in_d1 = 'd1/d2'
    f21_in_d1 = 'd1/d2/f21'
    f22_in_d1 = 'd1/d2/f22'
    d1_in_d2 = 'd2/d1'
    f11_in_d2 = 'd2/d1/f11'
    f12_in_d2 = 'd2/d1/f12'
    t = 't'
    # Move one file to missing target
    setup(base)
    Test.run(test='mv f1 t',
             verification='ls -r | map (f: f.render_compact())',
             expected_out=sorted([dot, d1, f11, f12, d2, f21, f22, f2, t]))
    # Move one file to existing file
    setup(base)
    Test.run(test='mv f1 f2',
             verification='ls -r | map (f: f.render_compact())',
             expected_out=sorted([dot, d1, f11, f12, d2, f21, f22, f2]))
    # Move one file to existing directory
    setup(base)
    Test.run(test='mv f1 d1',
             verification='ls -r | map (f: f.render_compact())',
             expected_out=sorted([dot, d1, f11, f12, f1_in_d1, d2, f21, f22, f2]))
    # Move multiple files to missing target
    setup(base)
    Test.run(test='mv ?1 f? t',
             expected_err='Cannot move multiple sources to a non-existent target')
    # Move multiple files to existing file
    setup(base)
    Test.run(test='mv ?1 f? f1',
             expected_err='Cannot move multiple sources to a file target')
    # Move multiple files to existing directory
    setup(base)
    Test.run(test='mv ?2 f? d1',
             verification='ls -r | map (f: f.render_compact())',
             expected_out=sorted([dot, d1, f11, f12, d2_in_d1, f21_in_d1, f22_in_d1, f1_in_d1, f2_in_d1]))
    # Move file over self
    setup(base)
    Test.run(test='mv ?2 f? d1',
             verification='ls -r | map (f: f.render_compact())',
             expected_out=sorted([dot, d1, f11, f12, d2_in_d1, f21_in_d1, f22_in_d1, f1_in_d1, f2_in_d1]))
    # Move directory into self. First check the error, then the result
    setup(base)
    Test.run(test='mv d1 d2 d2',
             expected_out=[Error('Cannot move directory over self')])
    setup(base)
    Test.run(test='mv d1 d2 d2',
             verification='ls -r | map (f: f.render_compact())',
             expected_out=sorted([dot, d2, f21, f22, d1_in_d2, f11_in_d2, f12_in_d2, f1, f2]))
    # Pipe in files to be moved
    setup(base)
    Test.run(test='ls ?2 f? | mv d1',
             verification='ls -r | map (f: f.render_compact())',
             expected_out=sorted([dot, d1, f11, f12, d2_in_d1, f21_in_d1, f22_in_d1, f1_in_d1, f2_in_d1]))


def reset_environment(config_file='./.marcel.py'):
    MAIN.global_state.env = marcel.env.Environment(config_file)
    os.chdir(start_dir)


def main_stable():
    test_gen()
    test_out()
    test_sort()
    test_map()
    test_ls()
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
    test_namespace()
    # test_remote()
    test_rm()
    test_mv()
    test_no_such_op()


def main_dev():
    pass
    # TODO: test_ps()  How?
    # TODO: test cd: absolute, relative, target does not exist


def main():
    reset_environment()
    main_stable()
    main_dev()
    print(f'Test failures: {Test.failures}')


main()
