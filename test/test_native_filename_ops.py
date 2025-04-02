import os
import pathlib

import marcel.object.error

import test_base

Error = marcel.object.error.Error
start_dir = os.getcwd()
TestDir = test_base.TestDir
TEST = test_base.TestConsole()


def relative(base, x):
    x_path = pathlib.Path(x)
    base_path = pathlib.Path(base)
    display_path = x_path.relative_to(base_path)
    return display_path


def absolute(base, x):
    return pathlib.Path(base) / x


def test_mv():
    # Move file
    with TestDir(TEST.env) as testdir:
        TEST.run(f'cd {testdir}')
        os.system('echo asdf > f')
        TEST.run(test='mv f g',
                 verification='ls -f | map (f: (f.name, f.size))',
                 expected_out=[('g', 5)])
    # Move into dir
    with TestDir(TEST.env) as testdir:
        TEST.run(f'cd {testdir}')
        os.system('echo asdf > f')
        os.system('echo asdfasdf > g')
        os.system('mkdir d')
        TEST.run('mv f g d',
                 verification='ls -f d | map (f: (f.name, f.size))',
                 expected_out=[('f', 5), ('g', 9)])
    # Funny names
    with TestDir(TEST.env) as testdir:
        TEST.run(f'cd {testdir}')
        os.system('echo asdf > "a b"')
        os.system('echo asdfasdf > c\\ d')
        TEST.run(test='mv a\\ b c\\ d',
                 verification='ls -f | map (f: (f.name, f.size))',
                 expected_out=[('c d', 5)])
        # TODO: Test error


def test_cp():
    # Copy file
    with TestDir(TEST.env) as testdir:
        TEST.run(f'cd {testdir}')
        os.system('echo asdf > f')
        TEST.run(test='cp f g',
                 verification='ls -f | map (f: (f.name, f.size))',
                 expected_out=[('f', 5), ('g', 5)])
    # Copy into dir
    with TestDir(TEST.env) as testdir:
        TEST.run(f'cd {testdir}')
        os.system('echo asdf > f')
        os.system('echo asdfasdf > g')
        os.system('mkdir d')
        TEST.run('cp f g d',
                 verification='ls -f d | map (f: (f.name, f.size))',
                 expected_out=[('f', 5), ('g', 9)])
    # Funny names
    with TestDir(TEST.env) as testdir:
        TEST.run(f'cd {testdir}')
        os.system('echo asdf > "a b"')
        os.system('echo asdfasdf > c\\ d')
        TEST.run(test='cp a\\ b c\\ d',
                 verification='ls -f | map (f: (f.name, f.size))',
                 expected_out=[('a b', 5), ('c d', 5)])
        TEST.run(test='cp "c d" \'e f\'',
                 verification='ls -f | map (f: (f.name, f.size))',
                 expected_out = [('a b', 5), ('c d', 5), ('e f', 5)])


def main():
    test_mv()
    test_cp()
    TEST.report_failures('test_native_filename_ops')


main()
