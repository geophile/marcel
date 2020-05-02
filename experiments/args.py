import argparse


def test(s):
    args = s.split()
    print(f'{args} -> {parser.parse_args(args)}')


parser = argparse.ArgumentParser()
parser.add_argument('--foo', nargs='?')
test('--foo')
test('--foo True')
test('--foo False')
