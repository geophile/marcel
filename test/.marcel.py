from time import time as now

from marcel.builtin import *


define_remote(name='jao',
              user='jao',
              identity='/home/jao/.ssh/id_rsa',
              host='localhost')

define_db(name='jao',
          driver='psycopg2',
          dbname='jao',
          user='jao')

DB_DEFAULT = 'jao'
