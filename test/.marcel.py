from marcel.builtin import *

# Convenient for testing to have NODE1 precede NODE2 lexicographically
NODE1 = '127.0.0.1'
NODE2 = 'localhost'

CLUSTER1 = cluster(user='jao', host=NODE1, identity='/home/jao/.ssh/id_rsa')

CLUSTER2 = cluster(user='jao', hosts=[NODE1, NODE2], identity='/home/jao/.ssh/id_rsa')

jdb = database(driver='psycopg2',
               dbname='jao',
               user='jao',
               password='jao')

set_db_default(jdb)

RUN_ON_STARTUP = '''
ext = (| e: select (f: f.suffix == '.' + e)|)
grem = (| pattern, files: read -l (files) | select (f, l: pattern in l) | map (f, l: f) | unique |)
'''

# Bug 242
def growset(acc, x):
    if acc is None:
        acc = set()
    acc.add(x)
    return acc

def dec(x):
    return x - 1
