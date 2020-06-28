import os

import test_base

TEST = test_base.TestTabCompletion()


def test_op():
    # No candidates
    TEST.run(line='xyz', text='xyz',
             expected=[])
    # Single candidate
    TEST.run(line='l', text='l',
             expected=['ls', 'load'])
    TEST.run(line='ls', text='ls',
             expected=['ls '])
    # Multiple candidates
    TEST.run(line='h', text='h',
             expected=['head', 'help', 'history'])
    TEST.run(line='he', text='he',
             expected=['head', 'help'])
    TEST.run(line='hea', text='hea',
             expected=['head '])
    TEST.run(line='head', text='head',
             expected=['head '])


def test_executables():
    TEST.run(line='ech', text='ech',
             expected=['echo '])


def test_flags():
    TEST.run(line='window -', text='-',
             expected=['-o', '--overlap', '-d', '--disjoint'])
    TEST.run(line='window --', text='--',
             expected=['--overlap', '--disjoint'])
    TEST.run(line='reverse -', text='-',
             expected=[])


def test_filenames():
    os.system('rm -rf /tmp/test')
    os.mkdir('/tmp/test')
    os.mkdir('/tmp/test/abcx')
    os.mkdir('/tmp/test/abcy')
    os.system('touch /tmp/test/abcz')
    TEST.run(line='ls /tmp/test/ab', text='/tmp/test/ab',
             expected=['/tmp/test/abcx/', '/tmp/test/abcy/', '/tmp/test/abcz'])
    TEST.run(line='ls /tmp/test/abcz', text='/tmp/test/abcz',
             expected=['/tmp/test/abcz '])
    # Executable
    TEST.run(line='echo /tmp/test/a', text='/tmp/test/a',
             expected=['/tmp/test/abcx/', '/tmp/test/abcy/', '/tmp/test/abcz'])


def main_stable():
    test_op()
    test_executables()
    test_flags()
    test_filenames()
    pass


def main_dev():
    pass


def main():
    TEST.reset_environment()
    main_stable()
    # main_dev()
    print(f'Test failures: {TEST.failures}')


main()
