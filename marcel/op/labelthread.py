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

import marcel.core

# TODO: DEBUGGING
ID_COUNTER = 0


class LabelThread(marcel.core.Op):

    def __init__(self, env):
        super().__init__(env)
        self.label_list = None
        self.label_tuple = None
        global ID_COUNTER
        self.id = ID_COUNTER
        ID_COUNTER += 1

    def __repr__(self):
        return (f'labelthread(#{self.id}: {self.label_list})'
                if self.label_list is not None
                else f'labelthread(#{self.id})')

    # AbstractOp

    def receive(self, x):
        self.send(self.label_tuple + x if type(x) is tuple else self.label_list + x)

    # The labelthread op only is used on a copy of the pipeline owned by fork. It runs
    # on each thread of the fork, attaching the thread label to output from that thread's
    # execution of the pipeline. We don't want these labelthread instances all calling
    # send_complete (which the default implementation of receive_complete does), because
    # this will result in n+1 calls of the parent pipeline's receiver -- one for each of the
    # n threads, and another from the parent.
    # See bug 4.
    def receive_complete(self):
        pass

    def receive_error(self, error):
        error.set_label(self.label_tuple[0])
        super().receive_error(error)

    # LabelThread

    def set_label(self, label):
        self.label_list = [label]
        self.label_tuple = (label,)
