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

import threading
import time

tl = threading.local()
tl.x = None


class Env:
    
    def __init__(self):
        """
        Initialize the thread.

        Args:
            self: (todo): write your description
        """
        self.thread_local = threading.local()
        self.thread_local.x = None


THREADS = 3
env = Env()


class Thread(threading.Thread):

    def __init__(self, x):
        """
        Initialize the internal state.

        Args:
            self: (todo): write your description
            x: (int): write your description
        """
        super().__init__()
        self.x = x

    def run(self):
        """
        Runs the thread

        Args:
            self: (todo): write your description
        """
        env.thread_local.x = self.x
        for i in range(10):
            print(f'{self.x}: {env.thread_local.x}')
            time.sleep(0.2)
            env.thread_local.x += 1


threads = []
for t in range(1, THREADS + 1):
    id = t * 1000
    thread = Thread(id)
    threads.append(thread)
    thread.start()
for thread in threads:
    thread.join()
