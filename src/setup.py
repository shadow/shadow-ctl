"""
Provides user prompts for setting up shadow.
"""

import curses, shutil, threading

from controller import *
from panel import *
from popup import *
from log import *
from config import *

SetupModes = Enum("LAST", "DEFAULT", "CUSTOM", "UNINSTALL", "CANCEL",)
CONTROLLER = None

def start(stdscr):
    global CONTROLLER

    # main controller that handles all the panels, popups, etc
    CONTROLLER = Controller(stdscr, "p: pause, h: help, q: quit")

    # setup the log panel as its own page
    lp = LogPanel(stdscr, LogLevels.DEBUG, CONTROLLER.getPopupManager())
    CONTROLLER.addPagePanels([lp])

    # start the threaded panels (e.g. log panel)
    for p in CONTROLLER.getDaemonPanels(): p.start()
    lp.info("shadow-cli initialized")

    # make sure toolbar is drawn
    CONTROLLER.redraw(True)

    # launch the setup wizard to get setup mode
    mode = wizardAskMode(stdscr, lp)
    helpkey = None
    
    # the thread that will do the setup work
    setupThread = None
    
    # selectively create and start the setup thread
    if mode == SetupModes.LAST:
        # setup without clearing cache
        setupThread = threading.Thread(target=wizardDoSetup, args=(getConfig(), lp))
        setupThread.start()
    elif mode == SetupModes.DEFAULT: 
        # setup using default config
        _clearCacheHelper(getConfig(), lp)
        setupThread = threading.Thread(target=wizardDoSetup, args=(getDefaultConfig(), lp))
        setupThread.start()
    elif mode == SetupModes.CUSTOM: 
        # use the wizard to configure and store custom options
        _clearCacheHelper(getConfig(), lp)
        wizardAskConfigure(stdscr, lp)
        setupThread = threading.Thread(target=wizardDoSetup, args=(getConfig(), lp))
        setupThread.start()
    elif mode == SetupModes.UNINSTALL: 
        wizardDoUninstall(getConfig(), lp)
    else: helpkey = ord('q')
    
    # now we want the log to be shown
    lp.setVisible(True)
    # need to force a redraw to completely clear wizard
    CONTROLLER.redraw(True)

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
    if setupThread is not None: setupThread.join()
    
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
    cp.setMessage(config.get("cli", "description.welcome"))
    cp.setVisible(True)

    choices = []
    if isConfigured(): choices.append((config.get("cli", "label.mode.autolast"), config.get("cli", "description.mode.autolast")))
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
    if selection == config.get("cli", "label.mode.autolast"):
        mode = SetupModes.LAST
    elif selection == config.get("cli", "label.mode.autodefault"):
        mode = SetupModes.DEFAULT
    elif selection == config.get("cli", "label.mode.custom"):
        mode = SetupModes.CUSTOM
    elif selection == config.get("cli", "label.mode.uninstall"):
        mode = SetupModes.UNINSTALL

    return mode

def wizardAskConfigure(stdscr, logger):
    pass

def wizardDoSetup(config, logger):
    # use the configured options to launch the setup worker thread that will
    # actually do the downloads, configure, make, etc
    prefix = os.path.abspath(os.path.expanduser(config.get("setup", "prefix")))
    
    # extra flags for building
    extraIncludePaths = os.path.abspath(os.path.expanduser(config.get("setup", "includepathlist")))
    extraIncludeFlagList = ["-I" + include for include in extraIncludePaths.split(';')]
    extraIncludeFlags = " ".join(extraIncludeFlagList)
    
    # extra search paths for libs
    extraLibPaths = os.path.abspath(os.path.expanduser(config.get("setup", "libpathlist")))
    extraLibFlagList = ["-L" + lib for lib in extraLibPaths.split(';')]
    extraLibFlags = " ".join(extraLibFlagList)
    
    # openssl
    cmdlist = ["./config --prefix=" + prefix + " -fPIC shared", "make", "make install"]
    if not _setupHelper(config, "opensslurl", cmdlist, logger): return
    
    # libevent
    cmdlist = ["./configure --prefix=" + prefix + " CFLAGS=\"-fPIC " + extraIncludeFlags + "\" LDFLAGS=\"" + extraLibFlags + "\"", "make", "make install"]
    if not _setupHelper(config, "libeventurl", cmdlist, logger): return
    
    # shadow resources
    cmdlist = []
    if not _setupHelper(config, "shadowresourcesurl", cmdlist, logger): return
    
    # shadow
    cmdList = ["cmake -DCMAKE_BUILD_PREFIX=./build -DCMAKE_INSTALL_PREFIX=" + prefix + " -DCMAKE_EXTRA_INCLUDES=" + extraIncludePaths + " -DCMAKE_EXTRA_LIBRARIES=" + extraLibPaths, "make", "make install"]
    if not _setupHelper(config, "shadowurl", cmdlist, logger): return
    
    
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

def _setupHelper(config, key, cmdlist, logger):
    archive = _downloadHelper(config, key, logger)
    if archive is None: return False
    path = _extractHelper(config, archive, logger)
    if path is None: return False
    return _buildHelper(cmdlist, path, logger)
    
def _downloadHelper(config, key, logger):
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

def _extractHelper(config, archive, logger):
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

def _buildHelper(cmdlist, workingDirectory, logger):
#    for cmd in cmdlist:
#        logger.info("running \'" + cmd + "\' from \'" + workingDirectory + "\'")
#        if loggedCall(cmd, workingDirectory, logger) != 0: return False
    return True

def _clearCacheHelper(config, logger, clearBuildCache=True, clearDownloadCache=False):
    cachedir = os.path.expanduser(config.get("setup", "cache"))
    buildcachedir = os.path.abspath(cachedir + "/build")
    downloadcachedir = os.path.abspath(cachedir + "/download")
    
    for (clear, d) in [(clearBuildCache, buildcachedir), (clearDownloadCache, downloadcachedir)]:
        if clear and os.path.exists(d): 
            shutil.rmtree(d)
            logger.debug("removed directory: " + d)