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

text = '''
Comments:
{L}- {r:cat /etc/passwd}: Write each line of {r:/etc/passwd} to the output stream.
{L}- {r:map (line: line.split(':'))}: Split the lines at the {n:} separators, yielding 7-tuples.
{L}- {r:select (*line: line[-1] == '/bin/bash')}: Select those lines in which the last field is 
{r:/bin/bash}.
{L}- {r:map (*line: line[0])}: Keep the username field of each input tuple.
{L}- {r:xargs echo}: Combine the incoming usernames into a single line, which is printed to {n:stdout}.
{L}- {r:\\ }: A line terminating in {r:\\ }indicates that the command continues on the next line.
'''


print(f'ORIGINAL: {text}')
formatted = formatter.format(text)
print('-----------------------------------------------------------------------------')
print(f'FORMATTED: {formatted}')
