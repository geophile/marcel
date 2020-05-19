import marcel.parser

def parse_test_line(line):
    try:
        last = line.index('<<')
        text = line[:last].strip()
        expected = line[last:].strip()
        if expected.startswith('<<') and expected.endswith('>>'):
            expected = expected[2:-2]
        else:
            assert False
    except ValueError:
        last = line.index('<')
        text = line[:last].strip()
        expected = line[last:].strip()
        if expected.startswith('<') and expected.endswith('>'):
            expected = expected[1:-1]
        else:
            assert False
    return text, expected


def is_test_line(line):
    line = line.strip()
    return len(line) > 0 and line[0] != '#'


def test_one(tokenizer, line):
    text, expected = parse_test_line(line)
    try:
        actual = tokenizer(text).value()
        if expected != actual:
            print(f'input: {text}\texpected: {expected}\tactual: {actual}')
    except Exception as e:
        if e.__class__.__name__ != expected:
            print(f'input: {text}\texpected:{expected}\terror: ({e.__name__}, {e})')


def test_all(input_filename, tokenizer):
    with open(input_filename, 'r') as input:
        for line in input.readlines():
            # print(line)
            if is_test_line(line):
                test_one(tokenizer, line)


def main():
    test_all('test_python_string.txt', lambda text: marcel.parser.PythonString(text, 0))
    test_all('test_shell_string.txt', lambda text: marcel.parser.String(text, 0))
    test_all('test_embedded_python.txt', lambda text: marcel.parser.Expression(text, 0))


main()
