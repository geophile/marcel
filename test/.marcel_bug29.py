from math import *
import datetime

def longer(x, y):
    if len(x) > len(y):
        return x
    else:
        return y

def todate(t):
    if t > (1 << 31):
        t = int(t / 1000)
    return datetime.datetime.fromtimestamp(t).strftime('%Y-%m-%d %H:%M:%S')
    
def timestamp(x):
    return datetime.datetime.strptime(x + "000", '%Y-%m-%d %H:%M:%S.%f').strftime('%s')

define_remote(name='jao',
              hosts=['localhost'],
              user='jao',
              identity='/home/jao/.ssh/id_rsa')

define_colors(image_highlight=Color(3, 0, 2, bold=True),
              red_bold=Color(5, 0, 0, bold=True),
              white_bold=Color(5, 5, 5, bold=True),
              white=Color(5, 5, 5))

define_color_scheme(file_file='white_bold',
                    file_dir=Color(0, 2, 3, bold=True),
                    file_link=Color(4, 2, 0, bold=True),
                    file_executable=Color(0, 4, 0, bold=True),
                    file_extension={'.jpg': 'image_highlight',
                                    '.jpeg': 'image_highlight',
                                    '.png': 'image_highlight',
                                    '.gif': 'image_highlight'},
                    error=Color(5, 5, 0),
                    process_pid=Color(0, 2, 4, bold=True),
                    process_commandline=Color(3, 2, 0, bold=True))

define_prompt([
    'red_bold',
    'M ',
    Color(0, 2, 1, bold=True),
    USER,
    '@',
    HOST,
    'white',
    ':',
    Color(0, 3, 3, bold=True),
    lambda: ('~' + PWD[len(HOME):]) if PWD.startswith(HOME) else PWD,
    '$ '])

define_continuation_prompt([
    'red_bold',
    'M ',
    Color(3, 4, 0, bold=True),
    '+$ '])
