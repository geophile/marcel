from parse import *


def main():
    parser = Parser('gen 5 | out')
    parser.parse()

    parser = Parser('ls | f (s: s + "asdf")')
    token = parser.next_token()
    while token:
        print(token)
        token = parser.next_token()


main()
