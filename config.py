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

print(configs)
