#
#
#
import json
import os

import zGui

#===============================
#
#
CONFIG_FILE = 'urcfg.json'

G_configured = False

#===============================
#
#
class Config:

    def __init__(self, path=None):
        self.path = path
        self.dev_name = None
        self.load()

    @property
    def defaults(self):
        return {
            'dev_name':'HC-05',
        }

    def load(self):
        global G_configured
        tmp = {}
        if  os.path.isfile(self.path):
            G_configured = True
            with open(self.path) as f:
                try:
                    tmp = json.load(f)
                except ValueError:
                    tmp = {}
        for k, v in tmp.items():
            if  getattr(self, k) is None:
                setattr(self, k, v)
        for k, v in self.defaults.items():
            if  getattr(self, k) is None:
                setattr(self, k, v)

    def save(self):
        global G_configured
        tmp = {}
        while True:
            self.gui = zGui.Gui()
            self.gui.ask_device_name(self.set_dev_name_cb)
            if  self.dev_name != None:
                break
        for k, v in self.defaults.items():
            tmp[k] = getattr(self, k)
        with open(self.path, 'w') as f:
            json.dump(tmp, f, indent=4, separators=(',', ': '), sort_keys=True)
            G_configured = True
    

    #===========================
    #
    #
    def set_dev_name_cb(self, name):
        self.dev_name = name
        print(f'device name = {self.dev_name}')

#================================
#
#
if  __name__ == '__main__':
    import sys
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--config', default=CONFIG_FILE, help=f'default file is {CONFIG_FILE}')
    parser.add_argument('-r', '--reset', action='store_true')
    arg = parser.parse_args()

    config = Config(arg.config)

    if  arg.reset:
        print(f'config file {arg.config} is removed')
        os.remove(arg.config)

    if  not os.path.isfile(arg.config):
        print(f'config file {arg.config} is not exist')
        print('creating config file ...')
        config.save()

    sys.exit(0)

#
#
#
