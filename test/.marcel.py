from marcel.builtin import *

# Convenient for testing to have NODE1 precede NODE2 lexicographically
NODE1 = '127.0.0.1'
NODE2 = 'localhost'

CLUSTER1 = cluster(user='jao',
                   identity='/home/jao/.ssh/id_rsa',
                   host=NODE1)

CLUSTER2 = cluster(user='jao',
                   identity='/home/jao/.ssh/id_rsa',
                   hosts=[NODE1, NODE2])

jdb = database(driver='psycopg2',
               dbname='jao',
               user='jao',
               password='jao')

DB_DEFAULT = jdb

RUN_ON_STARTUP = '''
ext = (| e: select (f: f.suffix == '.' + e)|)
grem = (| pattern, files: read -l (files) | select (f, l: pattern in l) | map (f, l: f) | unique |)
'''
