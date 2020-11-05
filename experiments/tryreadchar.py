import sys
import readchar
from readchar.key import *

CTRL_R = '\x12'
PROMPT = '> '
lines = []




def main():
    """
    Main function.

    Args:
    """
    print(PROMPT, end='')
    position = 0
    line = 0
    text = ''
    while True:
        k = readchar.readkey()
        if k == UP:
            pass
        elif k == DOWN:
            pass
        elif k == LEFT:
            position = max(position - 1, 0)
        elif k == RIGHT:
            position = min(position + 1, len(text))
        elif k == BACKSPACE:
            text = text[:-1]
            position = min(position, len(text))
        elif k == SUPR:  # This is the Delete key?!
            text = text[:position] + text[position + 1]
        elif k == LF:
            lines.append(text)
            line += 1
            text = ''
            
        print('key: ' + k)
        if k == LF:
            print('LF')
        elif k == CR:
            print('CR')
        elif k == ENTER:
            print('ENTER')
        elif k == BACKSPACE:
            print('BACKSPACE')
        elif k == SUPR:
            print('SUPR')
        elif k == SPACE:
            print('SPACE')
        elif k == ESC:
            print('ESC')
        elif k == CTRL_A:
            print('CTRL_A')
        elif k == CTRL_B:
            print('CTRL_B')
        elif k == CTRL_C:
            print('CTRL_C')
        elif k == CTRL_D:
            print('CTRL_D')
        elif k == CTRL_E:
            print('CTRL_E')
        elif k == CTRL_F:
            print('CTRL_F')
        elif k == CTRL_Z:
            print('CTRL_Z')
        elif k == ALT_A:
            print('ALT_A')
        elif k == CTRL_ALT_A:
            print('CTRL_ALT_A')
        elif k == UP:
            print('UP')
        elif k == DOWN:
            print('DOWN')
        elif k == LEFT:
            print('LEFT')
        elif k == RIGHT:
            print('RIGHT')
        elif k == CTRL_ALT_SUPR:
            print('CTRL_ALT_SUPR')
        elif k == F1:
            print('F1')
        elif k == F2:
            print('F2')
        elif k == F3:
            print('F3')
        elif k == F4:
            print('F4')
        elif k == F5:
            print('F5')
        elif k == F6:
            print('F6')
        elif k == F7:
            print('F7')
        elif k == F8:
            print('F8')
        elif k == F9:
            print('F9')
        elif k == F10:
            print('F10')
        elif k == F11:
            print('F11')
        elif k == F12:
            print('F12')
        elif k == PAGE_UP:
            print('PAGE_UP')
        elif k == PAGE_DOWN:
            print('PAGE_DOWN')
        elif k == HOME:
            print('HOME')
        elif k == END:
            print('END')
        elif k == INSERT:
            print('INSERT')
        elif k == SUPR:
            print('SUPR')
        elif len(k) == 1:
            if k == '^':
                sys.exit(0)
            else:
                print(k)
        else:
            print('???')


main()
