import argparse

parser = argparse.ArgumentParser(prog='abc')
parser.add_argument('-f', '--foo', type=int, help='Specify a foo')
parser.add_argument('bar')
print(parser.parse_args(['-f', '3', 'ABC']))
print(parser.parse_args(['-h']))
