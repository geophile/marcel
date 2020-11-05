# This file is part of Marcel.
# 
# Marcel is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation, either version 3 of the License, or at your
# option) any later version.
# 
# Marcel is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
# for more details.
# 
# You should have received a copy of the GNU General Public License
# along with Marcel.  If not, see <https://www.gnu.org/licenses/>.

try:
    import psycopg2
except ModuleNotFoundError:
    pass
import time


N = 100000
FILLER = 'x' * 100


def standard():
    """
    Standardize the standard database

    Args:
    """
    conn = psycopg2.connect(dbname='jao', user='jao')
    cursor = conn.cursor()
    cursor.execute('drop table if exists t')
    cursor.execute('create table t(x int not null primary key, s varchar)')
    conn.commit()
    start = time.time()
    for i in range(N):
        cursor.execute('insert into t(x, s) values(%s, %s)', (i, FILLER))
    conn.commit()
    stop = time.time()
    elapsed = stop - start
    average_msec = 1000 * elapsed / N
    cursor.close()
    conn.close()
    print(f'Inserted {N} rows in {elapsed} sec, {average_msec} msec per row')


def mogrify(batch_size):
    """
    Mogrify mogrify

    Args:
        batch_size: (int): write your description
    """
    conn = psycopg2.connect(dbname='jao', user='jao')
    cursor = conn.cursor()
    cursor.execute('drop table if exists t')
    cursor.execute('create table t(x int not null primary key, s varchar)')
    conn.commit()
    start = time.time()
    id = 0
    for i in range(N // batch_size):
        batch = []
        for j in range(batch_size):
            batch.append(cursor.mogrify('(%s, %s)', (id, FILLER)).decode('utf8'))
            id += 1
        values = ','.join(batch)
        sql = 'insert into t(x, s) values%s' % values
        cursor.execute(sql)
    conn.commit()
    stop = time.time()
    elapsed = stop - start
    cursor.close()
    conn.close()
    print(f'Inserted {N} rows, batch size {batch_size}, in {elapsed} sec')


def mogrify_vs_standard():
    """
    Mogrify standard standard deviation.

    Args:
    """
    standard()
    for b in (10, 100, 200, 500, 1000, 2000):
        mogrify(b)


def param_styles():
    """
    List all styles

    Args:
    """
    conn = psycopg2.connect(dbname='jao', user='jao')
    cursor = conn.cursor()
    cursor.execute('drop table if exists t')
    cursor.execute('create table t(x int not null primary key, s varchar)')
    conn.commit()
    cursor.execute('insert into t values(%s, %s)', (1, 'one'))
    for x, y in ((2, 'two'), (3, 'three')):
        cursor.execute('insert into t values(%(x)s, %(y)s)', {'x': x, 'y': y, 'z': 3})
    conn.commit()
    cursor.execute('select * from t')
    for t in cursor.fetchall():
        print(t)

param_styles()