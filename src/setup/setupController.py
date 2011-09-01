import os, time, curses, ConfigParser

from core import panel, labelPanel, control, controlPanel, scrollPanel, popupPanel, textInput, tools

REDRAW_RATE = 5
HOME=os.getenv("HOME")
DEFAULT_CONFIG_PATH=os.path.abspath(HOME+"/.shadow/shadow-cli.conf")
DEFAULT_CONFIGS = {"setup" : {"install-root" : HOME+"/.local"}}

def setDefaultConfig():
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

class SetupController:
    def __init__(self, stdscr):
        self.screen = stdscr
        
        self.labelp = None
        self.controlp = None
        self.scrollp = None
        self.popupp = None
        
        self.controls = None
        self.isDone = False
        self.lastDrawn = 0
        
        self.config = setDefaultConfig()
    
    def getScreen(self):
        return self.screen
    
    def redraw(self, force = True):
        # always force if too much time passed
        currentTime = time.time()
        if self.lastDrawn + REDRAW_RATE <= currentTime: force = True
        
        if self.labelp.isVisible(): self.labelp.redraw(force)
        if self.controlp.isVisible(): self.controlp.redraw(force)
        if self.scrollp.isVisible(): self.scrollp.redraw(force)
        if self.popupp.isVisible(): self.popupp.redraw(force)
        
        self.screen.refresh()
        
    def start(self):
         # allows for background transparency
        try: curses.use_default_colors()
        except curses.error: pass
        
        # makes the cursor invisible
        try: curses.curs_set(0)
        except curses.error: pass

        # setup panels
        self.labelp = labelPanel.LabelPanel(self.screen)
        self.labelp.setMessage("Shadow Setup Wizard -- q: quit")
        self.labelp.setVisible(True)
        
        self.controlp = controlPanel.ControlPanel(self.screen, 1, 0)
        self.controlp.setMessage("Welcome to the Shadow Setup Wizard. Please select "
                      "from the controls below to setup and install Shadow.")
        self.controlp.setVisible(True)
        
        self.controls = []
        self.controls.append(control.Control("Auto Setup", "Performs an automatic configuration of a Shadow installation by downloading, building, and installing Shadow and any missing dependencies to the user's home directory using default options."))
        self.controls.append(control.Control("Interactive Setup", "Interactively configure Shadow as above."))
        self.controls.append(control.Control("Uninstall Shadow", "Uninstall Shadow using cached installation options."))
        self.controls.append(control.Control("Quit", "Exit the Shadow Setup Wizard."))
        
        self.controlp.setControls(self.controls)

        self.scrollp = scrollPanel.ScrollPanel(self.screen, "Setup Log", 1, -1)
        self.scrollp.setVisible(False)
        
        self.popupp = popupPanel.PopupPanel(self.screen, 2, 2)
        self.popupp.setVisible(False)
        
        # used in case some commands want to chain execute another command
        chainKey = None
        
        while not self.isDone:
            self.redraw(True)
            
            # wait for user keyboard input until timeout, unless an override was set
            if chainKey:
                key, chainKey = chainKey, None
            else:
                curses.halfdelay(REDRAW_RATE * 10)
                key = self.screen.getch()
            
            if key == ord('q') or key == ord('Q'):
                self.stop()
            elif key == ord('h') or key == ord('H'):
                pass
            elif key == ord('s') or key == ord('S'):
                if self.scrollp.isVisible(): self.scrollp.saveLog()
            elif key == ord('l') - 96:
                # force redraw when ctrl+l is pressed
                self.redraw(True)
            #elif key == 27 and self.popupp.isVisible():
            #    self.popupp.setVisible(False)
            else:
                if self.controlp.isVisible():
                    isKeyConsumed = self.controlp.handleKey(key)
                    if isKeyConsumed:
                        if self.needsTransition(): self.doTransition()
                elif self.scrollp.isVisible():
                    self.scrollp.handleKey(key)
    
    def popup(self, query, default):
        self.popupp.setQuery(query)
        self.popupp.setDefaultResponse(default)
        self.popupp.setVisible(True)
        self.redraw(True)
        response = self.popupp.getUserResponse()
        self.popupp.setVisible(False)
        self.redraw(True)
        return response
        
    def needsTransition(self):
        for c in self.controls:
            if c.isExecuted(): return True
        return False
                
    def doTransition(self):
        self.controlp.setVisible(False)
        self.scrollp.setVisible(True)
        
        for c in self.controls:
            if c.isExecuted():
                n = c.getName()
                if n == "Auto Setup": self.doAutoSetup()
                elif n == "Interactive Setup": self.doInteractiveSetup()
                elif n == "Uninstall": self.doUninstall()
                elif n == "Quit": self.stop()
                
    def doAutoSetup(self):
        # spawn a thread to execute all the setup commands and fill the log
        pass
    
    def doInteractiveSetup(self):
        query = "Please enter the root install path for Shadow and its plug-ins and dependencies. The default is recommended. (**Required**)"
        default = os.path.abspath(HOME+"/.local/")
        installPathRoot = self.popup(query, default)
        # install path is required, return
        # TODO should log this
        if installPathRoot is None: return
        
        query = "We need to download and build a custom version of OpenSSL for Shadow applications that use it. If your system version of OpenSSL was configured with \'-fPIC shared\', you may be able to ignore this by pressing ESC. In that case you will need to provide the path to your OpenSSL install. (Note - if a local copy is cached, no download will be performed.)"
        default = "http://www.openssl.org/source/openssl-1.0.0d.tar.gz"
        opensslUrl = self.popup(query, default)
        opensslInstallPath = installPathRoot
        
        if opensslUrl is None:
            query = "You chose not to do a custom build of OpenSSL. Please provide the OpenSSL root install path. (**Required**)"
            default = installPathRoot
            opensslInstallPath = self.popup(query, default)
            # install path is required, return
            # TODO should log this
            if opensslInstallPath is None: return
        else:
            # do the download and install
            pass
        
        query = "We need to download and build a custom version of libevent-2.0 for Shadow applications that use it. If your system version of libevent-2.0 was configured with \'CFLAGS=\"-fPIC -I"+opensslInstallPath+"\" LDFLAGS=\"-L"+opensslInstallPath+"\"\', you may be able to ignore this by pressing ESC. (Note - if a local copy is cached, no download will be performed.)"
        default = "http://monkey.org/~provos/libevent-2.0.11-stable.tar.gz"
        libeventUrl = self.popup(query, default)
        libeventInstallPath = installPathRoot
        
        if libeventUrl is None:
            query = "You chose not to do a custom build of libevent-2.0. Please provide the libevent-2.0 root install path. (**Required**)"
            default = installPathRoot
            libeventInstallPath = self.popup(query, default)
            # install path is required, return
            # TODO should log this
            if libeventInstallPath is None: return
        else:
            # do the download and install
            pass
    
    def doUninstall(self):
        # spawn a thread to execute the uninstall commands and fill the log
        # remove ~/.local/bin/shadow*
        #        ~/.local/lib/libshadow*
        #      -rf  ~/.local/share/shadow
        pass
                        
    def stop(self):
        """
        Terminates after the input is processed.
        """
        self.isDone = True
        self.scrollp.join()
