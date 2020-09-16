from marcel.builtin import *


jao = remote(user='jao',
             identity='/home/jao/.ssh/id_rsa',
             host='localhost')

define_db(name='jao',
          driver='psycopg2',
          dbname='jao',
          user='jao')

DB_DEFAULT = 'jao'
