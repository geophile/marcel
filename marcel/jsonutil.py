import json


class _O(object):

    def __repr__(self):
        return str(self.__dict__)

    def __getitem__(self, key):
        return self.__dict__[key]


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
            o.__dict__ = {k: JSONUtil.dict_to_object(v) for (k, v) in j.items()}
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

