'''
Default config options for the cli.
'''
import os, ConfigParser

HOME=os.getenv("HOME")
DEFAULT_CONFIG_PATH=os.path.abspath(HOME+"/.shadow/shadow-cli.conf")
DEFAULT_CONFIGS = {"setup" : {
                              "install-root" : HOME+"/.local", 
                              "download" : HOME+"/.shadow/download-cache/",
                              "build" : HOME+"/.shadow/build-cache/",
                              "openssl" : "http://www.openssl.org/source/openssl-1.0.0d.tar.gz",
                              "libevent" : "http://monkey.org/~provos/libevent-2.0.11-stable.tar.gz",
                              "shadow" : "http://shadow.cs.umn.edu/downloads/shadow-release.tar.gz",
                              "scallion" : "http://shadow.cs.umn.edu/downloads/shadow-scallion-release.tar.gz",
                              "resources" : "http://shadow.cs.umn.edu/downloads/shadow-resources.tar.gz",
                              },
                   }

def loadConfig():
    d = os.path.dirname(DEFAULT_CONFIG_PATH)
    if not os.path.exists(d): os.makedirs(d)
    
    conf = ConfigParser.ConfigParser()
    conf.read(DEFAULT_CONFIG_PATH)
    
    for section in DEFAULT_CONFIGS:
        if not conf.has_section(section): conf.add_section(section)
        for option in DEFAULT_CONFIGS[section]:
            value = DEFAULT_CONFIGS[section][option]
            if not conf.has_option(section, option): conf.set(section, option, value)
            
    return conf

def saveConfig(conf):
    with open(DEFAULT_CONFIG_PATH, 'w') as f:
        conf.write(f)