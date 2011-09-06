"""
Provides user prompts for setting up shadow.
"""

import curses, shutil

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
    
    if mode == SetupModes.LAST: wizardDoSetup(getConfig(), lp)
    elif mode == SetupModes.DEFAULT: 
        wizardDoClearCache(getConfig(), lp)
        wizardDoSetup(getDefaultConfig(), lp)
    elif mode == SetupModes.CUSTOM: 
        # use the wizard to configure and store custom options
        wizardDoClearCache(getConfig(), lp)
        wizardAskConfigure(stdscr, lp)
        wizardDoSetup(getConfig(), lp)
    elif mode == SetupModes.UNINSTALL: wizardDoUninstall(getConfig(), lp)
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
    pass

def wizardDoClearCache(config, logger, doBuildCache=True, doDownloadCache=False):
    cachedir = os.path.expanduser(config.get("setup", "cache"))
    buildcachedir = cachedir + "/build"
    downloadcachedir = cachedir + "/download"
    
    for (do, d) in [(doBuildCache, buildcachedir), (doDownloadCache, downloadcachedir)]:
        if do and os.path.exists(d): 
            shutil.rmtree(d)
            logger.debug("removed directory: " + d)
        
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

    logger.info("Uninstall complete!")
