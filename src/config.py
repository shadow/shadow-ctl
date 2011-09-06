'''
Default config and options for the cli.

There are two main types: options which the user can configure, such
the install path, and configs that change the interface, such as the wizard
welcome message, options labels, etc. We keep separate enums for each.

Based on code from the arm project, developed by Damian Johnson under GPLv3
(www.atagar.com - atagar@torproject.org)
'''
import os, curses
from ConfigParser import SafeConfigParser
from tools import *
from enum import *

# sections for each config file
Sections = Enum("setup", "cli")

CONFIG_BASE = "~/.shadow"
CONFIG_PATH = os.path.expanduser(CONFIG_BASE + "/shadow-cli.conf")
CONFIG = None
DEFAULT_CONFIG_PATH = os.path.abspath(os.path.dirname(__file__) + "/../config/shadow-cli.conf.default")
DEFAULT_CONFIG = None

DESC_SIZE = 5 # height of the description field
MSG_COLOR = "green"
OPTION_COLOR = "yellow"
DISABLED_COLOR = "cyan"

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
    if conf is DEFAULT_CONFIG: return
    d = os.path.dirname(CONFIG_PATH)
    if not os.path.exists(d): os.makedirs(d)
    with open(CONFIG_PATH, 'w') as f: conf.write(f)

class Option:
    """
    Represents a UI option on screen, and holds its attributes.
    """

    def __init__(self, section, name, defaultValue=None):
        """
        Configuration option constructor.

        Arguments:
          section   - configuration attribute group this belongs to
          name     - configuration option identifier used when querying attributes
          defaultValue - initial value, uses the config default if unset
        """

        self.key = name
        self.group = section
        self.descriptionCache = None
        self.descriptionCacheArg = None
        self.value = defaultValue if defaultValue is not None else getDefaultConfig().getOption(section, name)
        self.validator = None
        self._isEnabled = True

    def getKey(self):
        return self.key

    def getValue(self):
        return self.value

    def getDisplayValue(self):
        return self.value

    def getDisplayAttr(self):
        myColor = OPTION_COLOR if self.isEnabled() else DISABLED_COLOR
        return curses.A_BOLD | getColor(myColor)

    def isEnabled(self):
        return self._isEnabled

    def setEnabled(self, isEnabled):
        self._isEnabled = isEnabled

    def setValidator(self, validator):
        """
        Custom function used to check that a value is valid before setting it.
        This functor should accept two arguments: this option and the value we're
        attempting to set. If its invalid then a ValueError with the reason is
        expected.

        Arguments:
          validator - functor for checking the validitiy of values we set
        """

        self.validator = validator

    def setValue(self, value):
        """
        Attempts to set our value. If a validator has been set then we first check
        if it's alright, raising a ValueError with the reason if not.

        Arguments:
          value - value we're attempting to set
        """

        if self.validator: self.validator(self, value)
        self.value = value

    def getLabel(self, prefix=""):
        return prefix + getConfig().get(self.group, self.key)

    def getDescription(self, width, prefix=""):
        if not self.descriptionCache or self.descriptionCacheArg != width:
            #optDescription = CONFIG["wizard.description.%s" % self.group].get(self.key, "")
            optDescription = "temp description"
            self.descriptionCache = splitStr(optDescription, width)
            self.descriptionCacheArg = width

        return [prefix + line for line in self.descriptionCache]

class ToggleOption(Option):
    """
    An option representing a boolean.
    """

    def __init__(self, key, group, default, trueLabel, falseLabel):
        Option.__init__(self, key, group, default)
        self.trueLabel = trueLabel
        self.falseLabel = falseLabel

    def getDisplayValue(self):
        return self.trueLabel if self.value else self.falseLabel

    def toggle(self):
        # This isn't really here to validate the value (after all this is a
        # boolean, the options are limited!), but rather give a method for functors
        # to be triggered when selected.

        if self.validator: self.validator(self, not self.value)
        self.value = not self.value
