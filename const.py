import os

class Constant(object):
    conf_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tmp')
    config_path = os.path.join(conf_dir, 'config.json')
    storage_path = os.path.join(conf_dir, 'database.json')
    cookie_path = os.path.join(conf_dir, 'cookie')

# c = Constant()
# print(c.config_path)
