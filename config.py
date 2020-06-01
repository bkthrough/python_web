import config_override
import config_default

configs = config_default.configs


def merge(default, override):
    for key in override:
        if isinstance(override[key], dict):
            if key not in default:
                default[key] = override[key]
            merge(default[key], override[key])
        else:
            default[key] = override[key]
    return default


configs = merge(configs, config_override.configs)


class Dict(dict):
    def __getattr__(self, key):
        return self[key]

    def __setattr__(self, key, val):
        self[key] = val


def toDict(d):
    res = Dict()
    for k, v in d.items():
        res[k] = toDict(v) if isinstance(v, dict) else v
    return res


configs = toDict(configs)
