import os, time, shutil, curses, threading

from core import labelPanel, control, controlPanel, scrollPanel, popupPanel, config
from setup import setupUtil

REDRAW_RATE = 1
HOME = os.getenv("HOME")

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

        self.workers = None
        self.config = config.loadConfig()

    def getScreen(self):
        return self.screen

    def redraw(self, force=True):
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
        self.labelp.setMessage("Shadow Setup Wizard -- r: restart, q: quit")
        self.labelp.setVisible(True)

        self.controlp = controlPanel.ControlPanel(self.screen, 1, 0)
        self.controlp.setMessage("Welcome to the Shadow Setup Wizard. Please select "
                      "from the controls below to setup and install Shadow.")
        self.controlp.setVisible(True)

        self.controls = []
        self.controls.append(control.Control("Auto Setup", "Performs an automatic configuration of a Shadow installation by downloading, building, and installing Shadow and any missing dependencies to the user's home directory using default options. A build-cache is created in " + self.config.get("setup", "build") + " and not cleared. Future Auto Setups will re-use this cache."))
        self.controls.append(control.Control("Interactive Setup", "Interactively configure Shadow as above. This option first clears the build-cache that may have been previously created in " + self.config.get("setup", "build") + "."))
        self.controls.append(control.Control("Uninstall Shadow", "Uninstall Shadow and clear cache."))

        self.controlp.setControls(self.controls)

        self.scrollp = scrollPanel.ScrollPanel(self.screen, "Setup Log", 1, -1)
        self.scrollp.setVisible(False)

        self.popupp = popupPanel.PopupPanel(self.screen, 2, 2)
        self.popupp.setVisible(False)

        self.workers = list()

        restart = False
        while not self.isDone:
            # flush the messages from other threads into the panel display
            self.scrollp.flush()
            self.redraw(True)

            # wait for user keyboard input until timeout, unless an override was set
            #curses.halfdelay(int(REDRAW_RATE * 10))
            key = self.screen.getch()

            if key == ord('q') or key == ord('Q'):
                self.stop()
            elif key == ord('r') or key == ord('R'):
                restart = True
                self.stop()
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
                        if self.needsTransition():
                            t = threading.Thread(target=SetupController.doTransition, args=(self,))
                            self.workers.append(t)
                            t.start()
                elif self.scrollp.isVisible():
                    self.scrollp.handleKey(key)

        return restart

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
        self.redraw(True)

        for c in self.controls:
            if c.isExecuted():
                n = c.getName()
                r = True
                if n == "Auto Setup": r = self.doAutoSetup()
                elif n == "Interactive Setup": r = self.doInteractiveSetup()
                elif n == "Uninstall Shadow": r = self.doUninstall()
                if not r: self.scrollp.asyncQ.put("**There was an ERROR. Check the log.")

    def doAutoSetup(self):
        installPathRoot = self.config.get("setup", "install-root")

        cmdlist = ["./config --prefix=" + installPathRoot + " -fPIC shared", "make", "make install"]
        if not self.autoHelper("openssl", cmdlist): return False

        cmdlist = ["./configure --prefix=" + installPathRoot + " CFLAGS=\"-fPIC -I" + installPathRoot + "\" LDFLAGS=\"-L" + installPathRoot + "\"", "make", "make install"]
        if not self.autoHelper("libevent", cmdlist): return False

        cmdlist = []
        if not self.autoHelper("resources", cmdlist): return False

        # resource path returned for shadow is incorrect because of server link
        resourcePath = self.downloadHelper("shadow")
        for name in os.listdir(self.config.get("setup", "build")):
            if name.find("shadow-shadow-") > -1: resourcePath = os.path.abspath(self.config.get("setup", "build") + "/" + name)
        buildPath = resourcePath + "/build"
        if not os.path.exists(buildPath): os.makedirs(buildPath)
        cmdList = ["cmake " + resourcePath + " -DCMAKE_BUILD_PREFIX=" + buildPath + " -DCMAKE_INSTALL_PREFIX=" + installPathRoot + " -DCMAKE_EXTRA_INCLUDES=" + installPathRoot + "/include" + " -DCMAKE_EXTRA_LIBRARIES=" + installPathRoot + "/lib", "make", "make install"]

        cwd = os.getcwd()
        os.chdir(buildPath)

        for cmd in cmdList:
            if setupUtil.callCollect(cmd, self.scrollp.asyncQ) != 0:
                os.chdir(cwd)
                return False

        os.chdir(cwd)
        return True

    def autoHelper(self, confOption, cmdList):
        resourcePath = self.downloadHelper(confOption)
        cwd = os.getcwd()
        os.chdir(resourcePath)

        for cmd in cmdList:
            if setupUtil.callCollect(cmd, self.scrollp.asyncQ) != 0: return False

        os.chdir(cwd)
        return True

    def downloadHelper(self, confOption):
        url = self.config.get("setup", confOption)
        self.scrollp.asyncQ.put("Please wait while we download " + url)
        resourcePath = setupUtil.getTGZResource(url, self.config.get("setup", "download"), self.config.get("setup", "build"))
        self.scrollp.asyncQ.put("Finished downloading " + url)
        return os.path.abspath(resourcePath)

    def doInteractiveSetup(self):
        # clear all build cache, not download cache
        dir = self.config.get("setup", "build")
        if os.path.exists(dir): shutil.rmtree(dir)

        query = "Please enter the root install path for Shadow and its plug-ins and dependencies. The default is recommended. (**Required**)"
        default = self.config.get("setup", "install-root")
        installPathRoot = self.popup(query, default)
        # install path is required, return
        # TODO should log this
        if installPathRoot is None: return

        query = "We need to download and build a custom version of OpenSSL for Shadow applications that use it. If your system version of OpenSSL was configured with \'-fPIC shared\', you may be able to ignore this by pressing ESC. In that case you will need to provide the path to your OpenSSL install. (Note - if a local copy is cached, no download will be performed.)"
        default = self.config.get("setup", "openssl")
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
            resourcePath = setupUtil.getTGZResource(opensslUrl, self.config.get("setup", "download"), self.config.get("setup", "build"))

        query = "We need to download and build a custom version of libevent-2.0 for Shadow applications that use it. If your system version of libevent-2.0 was configured with \'CFLAGS=\"-fPIC -I" + opensslInstallPath + "\" LDFLAGS=\"-L" + opensslInstallPath + "\"\', you may be able to ignore this by pressing ESC. (Note - if a local copy is cached, no download will be performed.)"
        default = self.config.get("setup", "libevent")
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
            resourcePath = setupUtil.getTGZResource(libeventUrl, self.config.get("setup", "download"), self.config.get("setup", "build"))

    def doUninstall(self):
        # remove ~/.local/bin/shadow*
        #        ~/.local/lib/libshadow*
        #      -rf  ~/.local/share/shadow
        dir = os.path.abspath(self.config.get("setup", "build"))
        if os.path.exists(dir): shutil.rmtree(dir)

        dir = os.path.abspath(self.config.get("setup", "download"))
        if os.path.exists(dir): shutil.rmtree(dir)

        dir = os.path.abspath(self.config.get("setup", "install-root") + "/share/shadow")
        if os.path.exists(dir): shutil.rmtree(dir)

        top = os.path.abspath(self.config.get("setup", "install-root") + "/lib")
        for root, dirs, files in os.walk(top, topdown=False):
            for name in files:
                if name.find("libshadow") > -1: os.remove(os.path.join(root, name))

        top = os.path.abspath(self.config.get("setup", "install-root") + "/bin")
        for root, dirs, files in os.walk(top, topdown=False):
            for name in files:
                if name.find("shadow") > -1: os.remove(os.path.join(root, name))

        self.scrollp.add("Uninstall complete! Configuration options left in " + config.DEFAULT_CONFIG_PATH)
        self.redraw(True)

        return True

    def stop(self):
        """
        Terminates after the input is processed.
        """
        self.isDone = True
        config.saveConfig(self.config)
        self.scrollp.add("cli finished, waiting for threads... (CTRL-C to kill)")
        self.scrollp.redraw(True)
        for t in self.workers: t.join()
