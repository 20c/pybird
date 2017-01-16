
from datetime import datetime
import json


def json_hook(data):
    date_keys = (
        'last_change',
        'last_reboot',
        'last_reconfiguration',
        )
    for key in date_keys:
        if key in data:
            data[key] = datetime.strptime(data[key], "%Y-%m-%dT%H:%M:%S")
    return data


class JSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, datetime):
            return o.isoformat()

        return json.JSONEncoder.default(self, o)

def dumps(data):
    return json.dumps(data, cls=JSONEncoder)

def load(fobj):
    return json.load(fobj, object_hook=json_hook)

