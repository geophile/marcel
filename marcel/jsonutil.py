# This file is part of Marcel.
#
# Marcel is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation, either version 3 of the License, (or at your
# option) any later version.
#
# Marcel is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
# for more details.
#
# You should have received a copy of the GNU General Public License
# along with Marcel.  If not, see <https://www.gnu.org/licenses/>.

import json

from marcel.structish import Struct as _O


class JSONUtil(object):
    class CustomDecoder(json.JSONDecoder):

        def __init__(self):
            super().__init__(object_hook=JSONUtil.dict_to_object)

    class CustomEncoder(json.JSONEncoder):

        def default(self, x):
            return JSONUtil.object_to_dict(x)

    def __init__(self):
        self.decoder = JSONUtil.CustomDecoder()
        self.encoder = JSONUtil.CustomEncoder()

    @staticmethod
    def dict_to_object(j):
        if type(j) is dict:
            o = _O()
            o.assign({k: JSONUtil.dict_to_object(v) for (k, v) in j.items()})
            return o
        elif type(j) is list:
            return [JSONUtil.dict_to_object(x) for x in j]
        else:
            return j

    @staticmethod
    def object_to_dict(x):
        try:
            return {k: JSONUtil.object_to_dict(v) for (k, v) in x.__dict__.items()}
        except AttributeError:
            return x

