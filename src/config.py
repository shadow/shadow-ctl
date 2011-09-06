'''
Default config options for the cli.
'''
import os, ConfigParser, curses
from tools import *
from enum import *

# basic setup modes
SetupMode = Enum("AUTOLAST", "AUTODEFAULT", "INTERACTIVE", "UNINSTALL", "CANCEL")



# all options that can be configured
Options = Enum("ROOT", "DOOPENSSL", "OPENSSLROOT", "OPENSSLURL")

SetupOptions = {SetupMode.AUTODEFAULT: (Options.ROOT,
                                        Options.DOOPENSSL,
                                        Options.OPENSSLROOT,
                                        Options.OPENSSLURL)}

# other options provided in the prompts
CANCEL, NEXT, BACK = "Cancel", "Next", "Back"

DESC_SIZE = 5 # height of the description field
MSG_COLOR = "green"
OPTION_COLOR = "yellow"
DISABLED_COLOR = "cyan"

HOME = os.getenv("HOME")
DEFAULT_CONFIG_PATH = os.path.abspath(HOME + "/.shadow/shadow-cli.conf")

DEFAULT_CONFIGS = {"setup" : {
                              "install-root" : HOME + "/.local",
                              "download" : HOME + "/.shadow/download-cache/",
                              "build" : HOME + "/.shadow/build-cache/",
                              "openssl" : "http://www.openssl.org/source/openssl-1.0.0d.tar.gz",
                              "libevent" : "http://monkey.org/~provos/libevent-2.0.11-stable.tar.gz",
                              "shadow" : "http://shadow.cs.umn.edu/downloads/shadow-release.tar.gz",
                              "scallion" : "http://shadow.cs.umn.edu/downloads/shadow-scallion-release.tar.gz",
                              "resources" : "http://shadow.cs.umn.edu/downloads/shadow-resources.tar.gz",
                              },
                   }

def loadConfig(readCache=True):
    d = os.path.dirname(DEFAULT_CONFIG_PATH)
    if not os.path.exists(d): os.makedirs(d)

    conf = ConfigParser.ConfigParser()
    if readCache: conf.read(DEFAULT_CONFIG_PATH)

    for section in DEFAULT_CONFIGS:
        if not conf.has_section(section): conf.add_section(section)
        for option in DEFAULT_CONFIGS[section]:
            value = DEFAULT_CONFIGS[section][option]
            if not conf.has_option(section, option): conf.set(section, option, value)

    return conf

def saveConfig(conf):
    with open(DEFAULT_CONFIG_PATH, 'w') as f: conf.write(f)

class ConfigOption:
    """
    Attributes of a configuration option.
    """

    def __init__(self, key, group, default):
        """
        Configuration option constructor.

        Arguments:
          key     - configuration option identifier used when querying attributes
          group   - configuration attribute group this belongs to
          default - initial value, uses the config default if unset
        """

        self.key = key
        self.group = group
        self.descriptionCache = None
        self.descriptionCacheArg = None
        self.value = default
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
        return prefix + "temp label"#CONFIG["wizard.label.%s" % self.group].get(self.key, "")

    def getDescription(self, width, prefix=""):
        if not self.descriptionCache or self.descriptionCacheArg != width:
            #optDescription = CONFIG["wizard.description.%s" % self.group].get(self.key, "")
            optDescription = "temp description"
            self.descriptionCache = splitStr(optDescription, width)
            self.descriptionCacheArg = width

        return [prefix + line for line in self.descriptionCache]

class ToggleConfigOption(ConfigOption):
    """
    Configuration option representing a boolean.
    """

    def __init__(self, key, group, default, trueLabel, falseLabel):
        ConfigOption.__init__(self, key, group, default)
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
