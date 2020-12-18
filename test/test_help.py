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

text = '''{P,wrap=F,indent=4}
(0, 0, 0)
(1, -1, 1)
(2, -2, 4)
(3, -3, 9)

'''


def plain_and_formatted(label, text):
    print(f'{label}: ORIGINAL')
    print(text)
    print('-----------------------------------------------------------------------------')
    print(f'{label}: FORMATTED')
    print(formatter.format(text))


plain_and_formatted('text', text)
