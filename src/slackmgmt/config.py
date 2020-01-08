import toml


def toml_provider(file_path, cmd_name):
    with open(file_path) as config_data:
        return toml.load(config_data)
