# from marcel.builtin import *
# import datetime


COLOR_EXT_IMAGE = Color(3, 0, 2, BOLD)
COLOR_EXT_SOURCE = Color(0, 3, 4, BOLD)

COLOR_SCHEME.file_file = Color(5, 5, 5, BOLD)
COLOR_SCHEME.file_dir = Color(0, 2, 3, BOLD)
COLOR_SCHEME.file_link = Color(4, 2, 0, BOLD)
COLOR_SCHEME.file_executable = Color(0, 4, 0, BOLD)
COLOR_SCHEME.file_extension = {
    'jpg': COLOR_EXT_IMAGE,
    'jpeg': COLOR_EXT_IMAGE,
    'png': COLOR_EXT_IMAGE,
    'mov': COLOR_EXT_IMAGE,
    'avi': COLOR_EXT_IMAGE,
    'gif': COLOR_EXT_IMAGE,
    'py': COLOR_EXT_SOURCE,
    'c': COLOR_EXT_SOURCE,
    'c++': COLOR_EXT_SOURCE,
    'cpp': COLOR_EXT_SOURCE,
    'cxx': COLOR_EXT_SOURCE,
    'h': COLOR_EXT_SOURCE,
    'java': COLOR_EXT_SOURCE,
    'php': COLOR_EXT_SOURCE
}
COLOR_SCHEME.error = Color(5, 5, 0)
COLOR_SCHEME.process_pid = Color(0, 3, 5, BOLD)
COLOR_SCHEME.process_ppid = Color(0, 2, 4, BOLD)
COLOR_SCHEME.process_status = Color(3, 1, 0, BOLD)
COLOR_SCHEME.process_user = Color(0, 2, 2, BOLD)
COLOR_SCHEME.process_command = Color(3, 2, 0, BOLD)
COLOR_SCHEME.help_reference = Color(5, 3, 0)
COLOR_SCHEME.help_bold = Color(5, 4, 1, BOLD)
COLOR_SCHEME.help_italic = Color(5, 5, 2, ITALIC)
COLOR_SCHEME.help_name = Color(4, 1, 0)
COLOR_SCHEME.history_id = Color(0, 3, 5, BOLD)
COLOR_SCHEME.history_command = Color(4, 3, 0, BOLD)
COLOR_SCHEME.color_scheme_key = Color(2, 4, 0)
COLOR_SCHEME.color_scheme_value = Color(0, 3, 4)

PROMPT = (
    Color(5, 0, 0, BOLD),
    'M ',
    Color(5, 2, 2, BOLD),
    MARCEL_VERSION,
    ' ',
    Color(2, 1, 0, BOLD),
    USER,
    '@',
    HOST,
    ' ',
    Color(3, 2, 0, BOLD),
    lambda: ('~' + PWD[len(HOME):]) if PWD.startswith(HOME) else PWD,
    '$ '
)

PROMPT_CONTINUATION = (
    Color(5, 0, 0, BOLD),
    'M ',
    Color(3, 4, 0, BOLD),
    '+$    '
)

jao = cluster(user='jao',
              identity='/home/jao/.ssh/id_rsa',
              host='localhost')

NODE1 = '127.0.0.1'
NODE2 = 'localhost'
CLUSTER2 = cluster(user='jao',
                   identity='/home/jao/.ssh/id_rsa',
                   hosts=[NODE1, NODE2])

acme = cluster(user='jao',
               identity='/home/jao/.ssh/id_rsa',
               host='acme')

root = cluster(user='root',
               identity='/home/jao/.ssh/id_rsa',
               host='localhost')


geophile = cluster(user='ec2-user',
                   identity='/home/jao/.ssh/aws1.pem.txt',
                   host='geophile.com')

all = cluster(user='jao',
              identity='/home/jao/.ssh/id_rsa',
              hosts=['localhost', 'acme'])

jdb = database(driver='psycopg2',
               dbname='jao',
               user='jao')

DB_DEFAULT = jdb

INTERACTIVE_EXECUTABLES = [
    'emacs',
    'less',
    'man',
    'more',
    'psql',
    'top',
    'vi',
    'vim'
]

RUN_ON_STARTUP = '''
import marcel.builtin *
import datetime
recent = (|d: select (f: now() - f.mtime < days(float(d)))|)

ext = (|e: select (f: f.suffix[1:] == e)|)

loc = (| ls -0 ~/git/marcel/marcel ~/git/marcel/test \
       | args (| d: ls -fr (d) \
                  | ext py \
                  | (f: f.read().count('\\n')) \
                  | red + \
                  | (n: (d, n)) |) |)

ft = (|sort (f: f.mtime)|)

import random
rand = (|range, n: gen (int(n)) | (x: random.randint(0, int(range)-1))|)
types = (| head 1 | \
           args (| x: \
               ((x,) if type(x) is not tuple else x) | \
               (*x: tuple([type(y) for y in x])) \
           |) \
        |)

concat = (| args --all (| x: (x) |) |)

quiet = (| select (*x: False) |)
'''


import time
def monitor(thread_id, sleep_sec):
    print(f'Thread {thread_id}: start')
    time.sleep(sleep_sec)
    print(f'Thread {thread_id}: stop')
    return thread_id

