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

import datetime
from time import time as now

# import symbols that we want in the marcel namespace
from marcel.object.color import Color
from marcel.object.cluster import Cluster
from marcel.object.db import Database
from marcel.object.file import File
from marcel.object.process import Process
from marcel.util import username, groupname, quote_files

_COMMANDS = '''
#    read = [map (f: f.readlines()) | expand]
'''


def minutes(n):
    return 60 * n


def hours(n):
    return 3600 * n


def days(n):
    return 24 * 3600 * n


def cluster(user, identity, host=None, hosts=None):
    return Cluster(user, identity, host, hosts)


def epoch(year, month, day, hour=0, minute=0, sec=0, usec=0):
    return datetime.datetime(year, month, day, hour, minute, sec, usec).timestamp()


def database(driver, dbname, user, password=None, host=None, port=None):
    return Database(driver, dbname, user, password, host, port)
