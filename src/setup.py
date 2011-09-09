"""
Provides user prompts for setting up shadow.
"""

import curses, shutil, threading

from controller import *
from panel import *
from popup import *
from log import *
from config import *
from enum import *
from input import *

SetupModes = Enum("LAST", "DEFAULT", "CUSTOM", "UNINSTALL", "CANCEL",)
CONTROLLER = None

def start(stdscr):
    global CONTROLLER

    # main controller that handles all the panels, popups, etc
    CONTROLLER = Controller(stdscr, "p: pause, h: help, q: quit")

    # setup the log panel as its own page
    configLogLevel = LogLevels.values()[LogLevels.indexOf(toCamelCase(getConfig().get("general", "loglevel")))]
    lp = LogPanel(stdscr, configLogLevel, CONTROLLER.getPopupManager())
    CONTROLLER.addPagePanels([lp])

    # start the threaded panels (e.g. log panel)
    for p in CONTROLLER.getDaemonPanels(): p.start()
    lp.info("shadow-cli initialized")

    # make sure toolbar is drawn
    CONTROLLER.redraw(True)

    # Used if track if we need to show the mode selection multiple times
    askMode = True
    while askMode:
        # launch the setup wizard to get setup mode
        mode = wizardAskMode(stdscr, lp)
        askMode = False
        
        # the thread that will do the setup work while we run the display
        setupThread = None
        
        # selectively create and start the setup thread
        if mode == SetupModes.DEFAULT: 
            # setup using default config
            setupThread = SetupThread(getDefaultConfig(), lp)
            setupThread.start()
        elif mode == SetupModes.CUSTOM: 
            # use the wizard to configure and store custom options
            askMode = wizardAskConfigure(stdscr, lp)
            setupThread = SetupThread(getConfig(), lp)
            setupThread.start()
        elif mode == SetupModes.UNINSTALL: 
            wizardDoUninstall(getConfig(), lp)
        else:
            CONTROLLER.quit()
            return
    
    # now we want the log to be shown
    lp.setVisible(True)
    # need to force a redraw to completely clear wizard
    CONTROLLER.redraw(True)

    helpkey = None
    while not CONTROLLER.isDone():

        CONTROLLER.redraw(False)
        stdscr.refresh()

        key, helpkey = helpkey, None
        if key is None:
            # wait for user keyboard input until timeout
            curses.halfdelay(int(REFRESH_RATE * 10))
            key = stdscr.getch()

        if key == curses.KEY_RIGHT:
            CONTROLLER.nextPage()
        elif key == curses.KEY_LEFT:
            CONTROLLER.prevPage()
        elif key == ord('a') or key == ord('A'):
            CONTROLLER.getPopupManager().showAboutPopup()
        elif key == ord('h') or key == ord('H'):
            helpkey = CONTROLLER.getPopupManager().showHelpPopup()
            # if push h twice, use it to toggle help off
            if helpkey == ord('h') or helpkey == ord('H'): helpkey = None
        elif key == ord('p') or key == ord('P'):
            CONTROLLER.setPaused(not CONTROLLER.isPaused())
        elif key == ord('q') or key == ord('Q'):
            CONTROLLER.quit()
        else:
            for p in CONTROLLER.getDisplayPanels():
                isKeystrokeConsumed = p.handleKey(key)
                if isKeystrokeConsumed: break
                
    lp.info("cli finished, waiting for threads... (CTRL-C to kill)")
    if setupThread is not None: 
        setupThread.stop()
        setupThread.join()
    
def finish():
    global HALT_ACTIVITY
    HALT_ACTIVITY = True
    # stop and join threads
    if CONTROLLER:
        for p in CONTROLLER.getDaemonPanels(): p.stop()
        for p in CONTROLLER.getDaemonPanels(): p.join()

def wizardAskMode(stdscr, logger):
    config = getConfig()

    cp = ControlPanel(stdscr, 1, 0)
    cp.setMessage(config.get("cli", "description.mode.title"))
    cp.setVisible(True)

    choices = []
    choices.append((config.get("cli", "label.mode.autodefault"), config.get("cli", "description.mode.autodefault")))
    choices.append((config.get("cli", "label.mode.custom"), config.get("cli", "description.mode.custom")))
    choices.append((config.get("cli", "label.mode.uninstall"), config.get("cli", "description.mode.uninstall")))
    choices.append((config.get("cli", "label.mode.cancel"), config.get("cli", "description.mode.cancel")))

    cp.setControls(choices)

    curses.cbreak()

    # get the selected method of setup from the choices
    selection = None
    while True:
        cp.redraw(True)
        key = stdscr.getch()
        selection = cp.handleKey(key)
        if selection is not None: break

    logger.debug("wizard selected option \'%s\'" % (selection))
    
    mode = SetupModes.CANCEL
    if selection == config.get("cli", "label.mode.autodefault"):
        mode = SetupModes.DEFAULT
    elif selection == config.get("cli", "label.mode.custom"):
        mode = SetupModes.CUSTOM
    elif selection == config.get("cli", "label.mode.uninstall"):
        mode = SetupModes.UNINSTALL

    return mode

def wizardAskConfigure(stdscr, logger):
    config = getConfig()
    
    # TODO the optionpanel is a bit clunky and needs major refactoring...
    op = OptionPanel(stdscr, 1, 0, config.get("cli", "description.option.title"))
    op.setVisible(True)
    
    opensslSubOption = Option(config.get("cli", "label.option.opensslurl"), config.get("cli", "description.option.opensslurl"), config.get("setup", "opensslurl"), customAttribute=("setup", "opensslurl"))
    libeventSubOption = Option(config.get("cli", "label.option.libeventurl"), config.get("cli", "description.option.libeventurl"), config.get("setup", "libeventurl"), customAttribute=("setup", "libeventurl"))
    scallionSubOption = Option(config.get("cli", "label.option.scallionurl"), config.get("cli", "description.option.scallionurl"), config.get("setup", "scallionurl"), customAttribute=("setup", "scallionurl"))
    pygeoipSubOption = Option(config.get("cli", "label.option.pygeoipurl"), config.get("cli", "description.option.pygeoipurl"), config.get("setup", "pygeoipurl"), customAttribute=("setup", "pygeoipurl"))
    maxmindSubOption = Option(config.get("cli", "label.option.maxmindurl"), config.get("cli", "description.option.maxmindurl"), config.get("setup", "maxmindurl"), customAttribute=("setup", "maxmindurl"))
    torurlSubOption = Option(config.get("cli", "label.option.torurl"), config.get("cli", "description.option.torurl"), config.get("setup", "torurl"), customAttribute=("setup", "torurl"))
    
    op.addOption(Option(config.get("cli", "label.option.prefix"), config.get("cli", "description.option.prefix"), config.get("setup", "prefix"), customAttribute=("setup", "prefix")))
    op.addOption(Option(config.get("cli", "label.option.cache"), config.get("cli", "description.option.cache"), config.get("setup", "cache"), customAttribute=("setup", "cache")))
    op.addOption(ToggleOption(config.get("cli", "label.option.doopenssl"), config.get("cli", "description.option.doopenssl"), "yes", "no", config.getboolean("setup", "doopenssl"), [opensslSubOption], customAttribute=("setup", "doopenssl")))
    op.addOption(ToggleOption(config.get("cli", "label.option.dolibevent"), config.get("cli", "description.option.dolibevent"), "yes", "no", config.getboolean("setup", "dolibevent"), [libeventSubOption], customAttribute=("setup", "dolibevent")))
    op.addOption(Option(config.get("cli", "label.option.shadowresourcesurl"), config.get("cli", "description.option.shadowresourcesurl"), config.get("setup", "shadowresourcesurl"), customAttribute=("setup", "shadowresourcesurl")))
    op.addOption(Option(config.get("cli", "label.option.shadowurl"), config.get("cli", "description.option.shadowurl"), config.get("setup", "shadowurl"), customAttribute=("setup", "shadowurl")))
    op.addOption(ToggleOption(config.get("cli", "label.option.shadowdebug"), config.get("cli", "description.option.shadowdebug"), "yes", "no", config.getboolean("setup", "shadowdebug"), [], customAttribute=("setup", "shadowdebug")))
    op.addOption(ToggleOption(config.get("cli", "label.option.doscallion"), config.get("cli", "description.option.doscallion"), "yes", "no", config.getboolean("setup", "doscallion"), [scallionSubOption, pygeoipSubOption, maxmindSubOption, torurlSubOption], customAttribute=("setup", "doscallion")))
    op.addOption(Option(config.get("cli", "label.option.includepaths"), config.get("cli", "description.option.includepaths"), config.get("setup", "includepaths"), customAttribute=("setup", "includepaths")))
    op.addOption(Option(config.get("cli", "label.option.librarypaths"), config.get("cli", "description.option.librarypaths"), config.get("setup", "librarypaths"), customAttribute=("setup", "librarypaths")))
    
    while True:
        op.redraw(True)
        key = stdscr.getch()
        result = op.handleKey(key)
        
        if result is OptionResult.NEXT: 
            break
        elif result is OptionResult.BACK: 
            return True
    
    # if we get here, we configured and confirmed the options
    # now save new configs
    for o in op.getOptions():
        (group, key) = o.getCustomAttribute()
        config.set(group, key, str(o.getValue()))
        
    saveConfig(config)
    
    # do not show the mode selection screen again
    return False

def wizardDoUninstall(config, logger):
    # shadow related files that need to be uninstalled:
    # prefix/bin/shadow*
    # prefix/lib/libshadow*
    # prefix/share/shadow/
    
    prefixd = os.path.abspath(os.path.expanduser(config.get("setup", "prefix")))
    shareshadowd = prefixd + "/share/shadow"
    libd = prefixd + "/lib"
    bind = prefixd + "/bin"
    based = os.path.abspath(os.path.expanduser(CONFIG_BASE))
    
    if os.path.exists(shareshadowd): 
        shutil.rmtree(shareshadowd)
        logger.debug("removed directory: " + shareshadowd)

    for (d, s) in [(libd, "libshadow"), (bind, "shadow")]:
        for root, dirs, files in os.walk(d, topdown=False):
            for name in files:
                if name.find(s) > -1: 
                    f = os.path.join(root, name)
                    os.remove(f)
                    logger.debug("removed file: " + f)

    if os.path.exists(based): 
        shutil.rmtree(based)
        logger.debug("removed directory: " + based)

    logger.info("uninstall complete!")

def _clearCacheHelper(config, logger, clearShadowCache=True, clearBuildCache=False, clearDownloadCache=False):
    cachedir = os.path.expanduser(config.get("setup", "cache"))
    buildcachedir = os.path.abspath(cachedir + "/build")
    downloadcachedir = os.path.abspath(cachedir + "/download")
    
    shadowcachedir = os.path.abspath(buildcachedir + "/shadow-release")
    scallioncachedir = os.path.abspath(buildcachedir + "/shadow-scallion-release")
    
    for (clear, d) in [(clearShadowCache, shadowcachedir), (clearShadowCache, scallioncachedir), (clearBuildCache, buildcachedir), (clearDownloadCache, downloadcachedir)]:
        if clear and os.path.exists(d): 
            shutil.rmtree(d)
            logger.debug("removed directory: " + d)

class SetupThread(threading.Thread):
    """Thread class with a stop() method. The thread itself has to check
    regularly for the isStopped() condition."""

    def __init__(self, config, logger):
        super(SetupThread, self).__init__()
        self._stop = threading.Event()
        self.config = config
        self.logger = logger
        
        self.setDaemon(True)
        
    def run(self):
        config = self.config
        logger = self.logger
        
        # use the configured options to actually do the downloads, configure, make, etc
        prefix = os.path.abspath(os.path.expanduser(config.get("setup", "prefix")))
        
        # extra flags for building
        extraIncludePaths = os.path.abspath(os.path.expanduser(config.get("setup", "includepaths")))
        extraIncludeFlagList = ["-I" + include for include in extraIncludePaths.split(';') if include != ""]
        extraIncludeFlags = " ".join(extraIncludeFlagList)
        logger.debug("using compiler flags \'" + extraIncludeFlags + "\'")
        
        # extra search paths for libs
        extraLibPaths = os.path.abspath(os.path.expanduser(config.get("setup", "librarypaths")))
        extraLibFlagList = ["-L" + lib for lib in extraLibPaths.split(';') if lib != ""]
        extraLibFlags = " ".join(extraLibFlagList)
        logger.debug("using linker flags \'" + extraLibFlags + "\'")
        
        # lets be optimistic ;)
        success = True
        
        if success and config.getboolean("setup", "doopenssl"):
            # openssl (-DPURIFY is needed to run in valgrind if plugin uses openssl)
            cmdlist = ["./config --prefix=" + prefix + " -fPIC shared -DPURIFY", "make", "make install"]
            success = self._setupHelper(config, "opensslurl", cmdlist, logger)
        
        if success and config.getboolean("setup", "dolibevent"):
            # libevent
            cmdlist = ["./configure --prefix=" + prefix + " CFLAGS=\"-fPIC " + extraIncludeFlags + "\" LDFLAGS=\"" + extraLibFlags + "\"", "make", "make install"]
            success = self._setupHelper(config, "libeventurl", cmdlist, logger)
        
        if success:
            # shadow resources
            cmdlist = []
            success = self._setupHelper(config, "shadowresourcesurl", cmdlist, logger)
        
        if success:
            # shadow
            cmdList = ["cmake -DCMAKE_BUILD_PREFIX=. -DCMAKE_INSTALL_PREFIX=" + prefix + " -DCMAKE_EXTRA_INCLUDES=" + extraIncludePaths + " -DCMAKE_EXTRA_LIBRARIES=" + extraLibPaths, "make", "make install"]
            success = self._setupHelper(config, "shadowurl", cmdList, logger)
            
        # TODO fix scallion support
        if success and config.getboolean("setup", "doscallion"):
            if success and config.getboolean("setup", "domaxmind"):
                cmdList = [] # TODO
                success = self._setupHelper(config, "maxmindurl", cmdList, logger)
                
            if success and config.getboolean("setup", "dopygeoip"):
                cmdList = [] # TODO
                success = self._setupHelper(config, "pygeoipurl", cmdList, logger)
            
            if success:    
                cmdList = [] # TODO
                success = self._setupHelper(config, "scallionurl", cmdList, logger)
        
        if success:
            logger.info("setup succeeded! please check \'" + prefix + "/bin\' for binaries.")
            logger.info("please add \'" + prefix + "/bin\' to you PATH.")
        else: logger.info("setup failed... please check the log file.")
        
    def _setupHelper(self, config, key, cmdlist, logger):
        archive = self._downloadHelper(config, key, logger)
        if archive is None: 
            logger.error("cannot proceed: problem downloading " + archive)
            return False
        path = self._extractHelper(config, archive, logger)
        if path is None: 
            logger.error("cannot proceed: problem extracting " + archive)
            return False
        success = self._executeHelper(cmdlist, path, logger)
        if not success:
            logger.error("cannot proceed: problem building " + path)
            return False
        return True
        
    def _downloadHelper(self, config, key, logger):
        url = config.get("setup", key)
        cache = os.path.abspath(os.path.expanduser(config.get("setup", "cache")))
        
        # make sure directories exist
        dlPath = os.path.abspath(cache + "/download")
        if not os.path.exists(dlPath): os.makedirs(dlPath)
    
        targetFile = os.path.abspath(dlPath + "/" + os.path.basename(url))
    
        # only download if not cached
        if os.path.exists(targetFile):
            logger.info("using cached resource " + targetFile)
        else:
            logger.info("downloading resource " + url + " ...")
            if download(url, targetFile) != 0: return None
        
        return targetFile
    
    def _extractHelper(self, config, archive, logger):
        cache = os.path.abspath(os.path.expanduser(config.get("setup", "cache")))
        
        # make sure directories exist
        buildPath = os.path.abspath(cache + "/build")
        if not os.path.exists(buildPath): os.makedirs(buildPath)
        
        # find the directory given by the tar name
        baseFilename = os.path.basename(archive)
        baseDirectory = baseFilename[:baseFilename.rindex(".tar.gz")]
        basePath = os.path.abspath(buildPath + "/" + baseDirectory)
        
        # extract only if not already cached
        if os.path.exists(basePath):
            logger.info("using cached build files in \'" + basePath + "\'")
        else:
            # first extract to temporary directory
            tmpPath = os.path.abspath(buildPath + "/tmp")
            if os.path.exists(tmpPath): shutil.rmtree(tmpPath)
            os.makedirs(tmpPath)
            
            logger.info("extracting \'" + archive + "\' to \'" + basePath + "\'")
            if tarfile.is_tarfile(archive):
                tar = tarfile.open(archive, "r:gz")
                tar.extractall(path=tmpPath)
                tar.close()
            else: 
                logger.error("downloded archive \'" + archive + "\' is not a tarfile!")
                return None
            
            # we can not rely on the stuff we extract to be a directory, or if it is, that the
            # directory is named the same as baseDirectory from above, so we fix it
            # here by moving contents of single root directories in tmp to the basePath.
            dlist = os.listdir(tmpPath)
            if len(dlist) > 1:
                # must not be single directory, so move tmppath/*
                logger.debug("the downloded archive \'" + archive + "\' contains more than a single directory")
                shutil.move(tmpPath, basePath)
            elif len(dlist) == 1:
                d = dlist.pop()
                p = os.path.abspath(tmpPath + "/" + d)
                if os.path.isdir(p): 
                    shutil.move(p, basePath)
                else: 
                    logger.debug("the downloded archive \'" + archive + "\' contains a single file")
                    return None
            else: 
                logger.error("downloded archive \'" + archive + "\' contains no files")
                return None
            
            # cleanup
            if os.path.exists(tmpPath): shutil.rmtree(tmpPath)
            
        # either the path already existed, or we downloaded and successfully extracted
        return basePath
    
    def _executeHelper(self, cmdlist, workingDirectory, logger):
        for cmd in cmdlist:
            logger.info("running \'" + cmd + "\' from \'" + workingDirectory + "\'")
    
            # run the command in a separate process
            # use shlex.split to avoid breaking up single args that have spaces in them into two args
            p = subprocess.Popen(shlex.split(cmd), cwd=workingDirectory, 
                                 stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        
            # while the command is executing, watch and log its output
            while True:
                # TODO if the command produces no output, can we sleep to avoid spinloop?
                line = p.stdout.readline()
                if not line: break
                logger.debug(line.strip())
                
                if self.isStopped():
                    p.terminate()
                    break
                if logger.isPaused():
                    # TODO do we need os.killpg(pid, signal.SIGCONT) instead? 
                    p.send_signal(signal.SIGSTOP)
                    while logger.isPaused(): time.sleep(1)
                    p.send_signal(signal.SIGCONT)
        
            # return the finished processes returncode
            r = p.wait()
            logger.info("Command: \'" + cmd + "\' returned \'" + str(r) + "\'")
        
            if r != 0: return False
        return True

    def stop(self):
        self._stop.set()

    def isStopped(self):
        return self._stop.isSet()
    