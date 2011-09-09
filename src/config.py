'''
Default configs.
'''
import os, curses
from ConfigParser import SafeConfigParser
from tools import *
from enum import *

# sections for each config file
Sections = Enum("general", "setup", "cli")

CONFIG_BASE = "~/.shadow"
CONFIG_PATH = os.path.expanduser(CONFIG_BASE + "/shadow-cli.conf")
CONFIG = None
DEFAULT_CONFIG_PATH = os.path.abspath(os.path.dirname(__file__) + "/../config/shadow-cli.conf.default")
DEFAULT_CONFIG = None

def _loadConfig(readCache=True):
    d = SafeConfigParser()
    d.read(DEFAULT_CONFIG_PATH)
    
    # do we return defaults only?
    if not readCache or not os.path.exists(CONFIG_PATH): return d
    
    c = SafeConfigParser()
    c.read(CONFIG_PATH)

    # merge in the defaults that dont exist, if any
    for section in d.sections():
        if not c.has_section(section): c.add_section(section)
        for option in d.options(section):
            default = d.get(section, option)
            if not c.has_option(section, option): c.set(section, option, default)

    return c


def getDefaultConfig():
    global DEFAULT_CONFIG
    # return the default configurations
    # TODO - caller could modify and overwrite the defaults!! fix this.
    if DEFAULT_CONFIG is None: DEFAULT_CONFIG = _loadConfig(False)
    return DEFAULT_CONFIG

def getConfig():
    global CONFIG
    if CONFIG is None: CONFIG = _loadConfig(True)
    return CONFIG

def isConfigured(): 
    return os.path.exists(CONFIG_PATH)

def saveConfig(conf):
    d = os.path.dirname(CONFIG_PATH)
    if not os.path.exists(d): os.makedirs(d)
    with open(CONFIG_PATH, 'w') as f: conf.write(f)
