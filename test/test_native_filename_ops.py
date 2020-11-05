import os
import pathlib
import shutil

import marcel.object.error

import test_base

Error = marcel.object.error.Error
start_dir = os.getcwd()
test_dir = '/tmp/test'
TEST = test_base.TestConsole()


def relative(base, x):
    """
    Return the relative path relative to x.

    Args:
        base: (todo): write your description
        x: (todo): write your description
    """
    x_path = pathlib.Path(x)
    base_path = pathlib.Path(base)
    display_path = x_path.relative_to(base_path)
    return display_path


def absolute(base, x):
    """
    Return the absolute absolute path.

    Args:
        base: (str): write your description
        x: (todo): write your description
    """
    return pathlib.Path(base) / x


def test_setup():
    """
    Create a test suite

    Args:
    """
    TEST.cd(test_dir + '/..')
    os.system(f'rm -rf {test_dir}')
    os.system(f'mkdir {test_dir}')
    TEST.cd(test_dir)


def test_mv():
    """
    Run the test suite.

    Args:
    """
    # Move file
    test_setup()
    os.system('echo asdf > f')
    TEST.run(test='mv f g',
             verification='ls -f | map (f: (f.name, f.size))',
             expected_out=[('g', 5)])
    # Move into dir
    test_setup()
    os.system('echo asdf > f')
    os.system('echo asdfasdf > g')
    os.system('mkdir d')
    TEST.run('mv f g d',
             verification='ls -f d | map (f: (f.name, f.size))',
             expected_out=[('f', 5), ('g', 9)])
    # Funny names
    test_setup()
    os.system('echo asdf > "a b"')
    os.system('echo asdfasdf > c\\ d')
    TEST.run(test='mv a\\ b c\\ d',
             verification='ls -f | map (f: (f.name, f.size))',
             expected_out=[('c d', 5)])
    # TODO: Test error



def test_cp():
    """
    Run test test suite.

    Args:
    """
    # Copy file
    test_setup()
    os.system('echo asdf > f')
    TEST.run(test='cp f g',
             verification='ls -f | map (f: (f.name, f.size))',
             expected_out=[('f', 5), ('g', 5)])
    # Copy into dir
    test_setup()
    os.system('echo asdf > f')
    os.system('echo asdfasdf > g')
    os.system('mkdir d')
    TEST.run('cp f g d',
             verification='ls -f d | map (f: (f.name, f.size))',
             expected_out=[('f', 5), ('g', 9)])
    # Funny names
    test_setup()
    os.system('echo asdf > "a b"')
    os.system('echo asdfasdf > c\\ d')
    TEST.run(test='cp a\\ b c\\ d',
             verification='ls -f | map (f: (f.name, f.size))',
             expected_out=[('a b', 5), ('c d', 5)])


def main():
    """
    Run the test.

    Args:
    """
    test_mv()
    test_cp()
    print(f'Test failures: {TEST.failures}')


main()
