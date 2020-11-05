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

from time import time as now

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
    """
    Return the number of seconds.

    Args:
        n: (todo): write your description
    """
    return 60 * n


def hours(n):
    """
    Return the number of seconds

    Args:
        n: (array): write your description
    """
    return 3600 * n


def days(n):
    """
    Return the number of days

    Args:
        n: (int): write your description
    """
    return 24 * 3600 * n


def remote(user, identity, host=None, hosts=None):
    """
    Run a remote command.

    Args:
        user: (todo): write your description
        identity: (str): write your description
        host: (str): write your description
        hosts: (list): write your description
    """
    return Cluster(user, identity, host, hosts)


def database(driver, dbname, user, password=None, host=None, port=None):
    """
    Create a database.

    Args:
        driver: (todo): write your description
        dbname: (str): write your description
        user: (todo): write your description
        password: (str): write your description
        host: (str): write your description
        port: (int): write your description
    """
    return Database(driver, dbname, user, password, host, port)
