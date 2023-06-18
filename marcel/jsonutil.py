import json


class JSONUtil(object):

    def __init__(self):
        self.decoder = json.JSONDecoder(object_hook=JSONUtil.dict_to_object)
        self.encoder = json.JSONEncoder()

    @staticmethod
    def dict_to_object(j):
        class _O(object):

            def __repr__(self):
                return str(self.__dict__)

        if type(j) is dict:
            o = _O()
            o.__dict__ = {k: JSONUtil.dict_to_object(v) for (k, v) in j.items()}
            return o
        elif type(j) is list:
            return [JSONUtil.dict_to_object(x) for x in j]
        else:
            return j
