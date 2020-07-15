import marcel.helpformatter


class TestColorScheme:

    def __init__(self):
        self.help_reference = 'R'
        self.help_bold = 'B'
        self.help_italic = 'I'
        self.help_name = 'N'
        self.help_color = 'C'

    def bold(self):
        return 1

    def italic(self):
        return 2

    def color(self, r, g, b, style):
        return f'C{r}{g}{b}{"" if style == 0 else "b" if style == 1 else "i" if style == 2 else "bi"}'


def colorize(text, color):
    return f'({color}:{text})'


color_scheme = TestColorScheme()
formatter = marcel.helpformatter.HelpFormatter(color_scheme, colorize)

# This indents by 4:

A = '''
{L,indent=4}loop ((0, 1)) [select (x, y: y < 1000000) | map (x, y: (y, x + y))] | map (x, y: x)
'''

# This does not:

B = '''
{L,indent=4,wrap=F}loop ((0, 1)) [select (x, y: y < 1000000) | map (x, y: (y, x + y))] | map (x, y: x)
'''

# This does indent:

C = '''
{L,indent=4,wrap=T}loop ((0, 1)) [select (x, y: y < 1000000) | map (x, y: (y, x + y))] | map (x, y: x)
'''

# So wrap=F causes indent to be ignored.


def plain_and_formatted(label, text):
    print(f'{label}: ORIGINAL')
    print(text)
    print(f'{label}: FORMATTED')
    print(formatter.format(text))
    print('-----------------------------------------------------------------------------')


plain_and_formatted('A', A)
plain_and_formatted('B', B)
plain_and_formatted('C', C)
