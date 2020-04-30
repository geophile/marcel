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

text = 'Hello \\\\backslash\\\\ inside {n:formatting\\\\too}'

print(f'ORIGINAL: {text}')
formatted = formatter.format(text)
print('-----------------------------------------------------------------------------')
print(f'FORMATTED: {formatted}')
